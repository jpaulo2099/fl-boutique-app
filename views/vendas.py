import streamlit as st
import pandas as pd
from datetime import datetime
import utils as ut
import database as db
import uuid
import time

def show_venda_direta():
    st.header("🛍️ Nova Venda")
    
    # --- INICIALIZAÇÃO DO CARRINHO (SESSION STATE) ---
    if 'carrinho' not in st.session_state:
        st.session_state['carrinho'] = []
    
    df_c = db.load_data("Clientes")
    df_p = db.load_data("Produtos")
    
    if df_c.empty or df_p.empty:
        st.warning("Cadastre clientes e produtos antes de vender.")
        return

    # --- 1. DADOS DA VENDA ---
    c1, c2 = st.columns([2, 1])
    with c1:
        # Ordena clientes alfabeticamente
        lista_clientes = sorted(df_c['nome'].unique())
        cliente = st.selectbox("Cliente", lista_clientes)
    with c2:
        data_venda = st.date_input("Data", datetime.now())

    st.divider()

    # --- 2. SELEÇÃO DE PRODUTOS (AGRUPADOS) ---
    # Filtra apenas disponíveis
    disponiveis = df_p[df_p['status'] == 'Disponível'].copy()
    
    if not disponiveis.empty:
        # CRIAR UMA COLUNA 'SKU' PARA AGRUPAR ITENS IGUAIS
        # Ex: Se tiver 3 'Calça Jeans M', vira uma linha só com Qtd=3
        disponiveis['sku_display'] = disponiveis['nome'] + " | Tam: " + disponiveis['tamanho']
        
        # Agrupa e conta o estoque
        estoque_agrupado = disponiveis.groupby('sku_display').agg({
            'id': 'count',                 # Conta quantos tem
            'preco_venda': 'first',        # Pega o preço do primeiro
            'nome': 'first',
            'tamanho': 'first'
        }).rename(columns={'id': 'qtd_estoque'}).reset_index()

        # Input de Seleção (Busca por Texto)
        c_prod, c_qtd, c_add = st.columns([3, 1, 1])
        
        with c_prod:
            # Cria lista dropdown: "Calça Jeans | Tam: M (5 em estoque)"
            opcoes = estoque_agrupado['sku_display'] + " (" + estoque_agrupado['qtd_estoque'].astype(str) + " disp.)"
            escolha_fmt = st.selectbox("Buscar Produto", options=opcoes, index=None, placeholder="Digite para buscar...")
        
        # Lógica para pegar os dados do item selecionado
        qtd_max = 1
        preco_sugerido = 0.0
        sku_selecionado = None
        
        if escolha_fmt:
            # Reconstrói a chave 'sku_display' tirando a parte do "(X disp.)"
            sku_selecionado = escolha_fmt.split(" (")[0]
            dados_prod = estoque_agrupado[estoque_agrupado['sku_display'] == sku_selecionado].iloc[0]
            
            qtd_max = int(dados_prod['qtd_estoque'])
            preco_sugerido = ut.converter_input_para_float(dados_prod['preco_venda'])

        with c_qtd:
            # O input de quantidade respeita o limite do estoque
            qtd_venda = st.number_input("Qtd.", min_value=1, max_value=qtd_max, step=1, disabled=(sku_selecionado is None))
            
        with c_add:
            st.write("") 
            st.write("")
            # Botão Adicionar
            if st.button("➕ Incluir", type="primary", disabled=(sku_selecionado is None)):
                # Adiciona ao carrinho na sessão
                # Verifica se já não adicionou esse item antes para somar (opcional, aqui cria nova linha)
                st.session_state['carrinho'].append({
                    "sku": sku_selecionado,
                    "nome": dados_prod['nome'],
                    "tamanho": dados_prod['tamanho'],
                    "qtd": qtd_venda,
                    "preco_unit": preco_sugerido,
                    "total": qtd_venda * preco_sugerido
                })
                st.rerun() # Atualiza a tela para mostrar no carrinho

    # --- 3. VISUALIZAÇÃO DO CARRINHO (LISTA VERTICAL) ---
    if len(st.session_state['carrinho']) > 0:
        st.markdown("### 🛒 Itens no Carrinho")
        
        # Converte carrinho em DataFrame para exibir e permitir edição (se quiser)
        df_cart = pd.DataFrame(st.session_state['carrinho'])
        
        # Mostra tabela bonitinha
        st.dataframe(
            df_cart[['nome', 'tamanho', 'qtd', 'preco_unit', 'total']],
            column_config={
                "nome": "Produto",
                "tamanho": "Tam",
                "qtd": "Qtd",
                "preco_unit": st.column_config.NumberColumn("Valor Unit.", format="R$ %.2f"),
                "total": st.column_config.NumberColumn("Total", format="R$ %.2f"),
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Botão para limpar carrinho se errar
        if st.button("🗑️ Limpar Carrinho"):
            st.session_state['carrinho'] = []
            st.rerun()

        st.divider()

        # --- 4. FECHAMENTO ---
        total_geral = df_cart['total'].sum()
        
        c_pag, c_resumo = st.columns([1, 1])
        
        with c_pag:
            st.subheader("Pagamento")
            forma = st.selectbox("Forma de Pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro"])
            parcelas = st.number_input("Parcelas", 1, 12, 1)
            
            # Se quiser dar desconto no total final
            valor_final = st.number_input("Valor Final (R$)", value=float(total_geral), format="%.2f")

        with c_resumo:
            st.metric("Total da Venda", ut.format_brl(total_geral))
            if valor_final != total_geral:
                st.caption(f"Desconto/Ajuste: {ut.format_brl(total_geral - valor_final)}")
            
            st.write("")
            if st.button("✅ FINALIZAR VENDA", type="primary", use_container_width=True):
                # --- PROCESSAMENTO MÁGICO ---
                # Aqui transformamos o Carrinho (Qtd) em IDs Reais do Banco
                
                sucesso_global = True
                lista_ids_para_baixar = {} # Dict {id: 'Vendido'}
                descricao_venda = f"Venda Direta - {cliente}"
                
                # 1. Alocar IDs para cada item do carrinho
                for item in st.session_state['carrinho']:
                    # Busca X produtos disponíveis com esse Nome e Tamanho
                    filtro = (df_p['nome'] == item['nome']) & \
                             (df_p['tamanho'] == item['tamanho']) & \
                             (df_p['status'] == 'Disponível')
                    
                    ids_disponiveis = df_p[filtro]['id'].head(item['qtd']).values
                    
                    if len(ids_disponiveis) < item['qtd']:
                        st.error(f"Estoque insuficiente para {item['nome']} durante o processamento.")
                        sucesso_global = False
                        break
                    
                    # Adiciona na lista de baixa
                    for pid in ids_disponiveis:
                        lista_ids_para_baixar[pid] = "Vendido"

                if sucesso_global:
                    # 2. Baixar Estoque em Lote (Batch Update)
                    if db.update_product_status_batch(lista_ids_para_baixar):
                        
                        # 3. Gerar Lançamento Financeiro (ÚNICO para toda a compra)
                        # Usando a função utilitária que já lida com Pix/Datas
                        lancs = ut.gerar_lancamentos(
                            total=valor_final,
                            parcelas=parcelas,
                            forma=forma,
                            cli=cliente,
                            origem_texto="Venda Loja",
                            data_base=data_venda,
                            tipo="Venda" # Receita
                        )
                        
                        for l in lancs:
                            db.append_data("Financeiro", l)
                        
                        st.success("Venda Realizada com Sucesso!")
                        st.balloons()
                        st.session_state['carrinho'] = [] # Limpa carrinho
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar estoque. Tente novamente.")
    
    else:
        st.info("Selecione produtos acima para iniciar a venda.")