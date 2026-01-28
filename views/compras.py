import streamlit as st
import utils as ut
import database as db
import pandas as pd
import uuid
from datetime import datetime, timedelta
import time

def show_compras():
    st.header("📦 Pedido de Compra (Entrada)")
    st.caption("Cadastre produtos e lance a despesa automaticamente.")

    # Inicializa o carrinho na sessão se não existir
    if 'carrinho_compra' not in st.session_state:
        st.session_state.carrinho_compra = []

    # --- PARTE 1: ADICIONAR ITEM AO CARRINHO ---
    with st.expander("📝 Adicionar Item ao Pedido", expanded=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: nome = st.text_input("Nome do Produto", key="c_nome")
        with c2: tam = st.selectbox("Tamanho", ["PP","P","M","G","GG","Único"], key="c_tam")
        with c3: qtd = st.number_input("Quantidade", 1, 100, 1, key="c_qtd")
        
        c4, c5, c6 = st.columns([1, 1, 1])
        with c4: 
            custo_txt = st.text_input("Custo Unit. (R$)", key="c_custo")
            
            # --- LÓGICA DE SUGESTÃO DE PREÇO ---
            if custo_txt and custo_txt != "0,00":
                c_val = ut.converter_input_para_float(custo_txt)
                if c_val > 0:
                    # Fórmula da precificação
                    sugestao_val = (c_val + 1.06) * 2 * 1.12
                    st.info(f"💡 Sugestão: {ut.format_brl(sugestao_val)}")

                    # Botão para aplicar a sugestão
                    if st.button("Usar Sugestão", key="btn_use_sug"):
                        st.session_state.c_venda = f"{sugestao_val:.2f}".replace('.', ',')
                        st.rerun()

        with c5: venda = st.text_input("Venda Unit. (R$)", key="c_venda")
        
        # Botão de ação local
        with c6:
            st.write("") # Espaçamento para alinhar o botão
            st.write("")
            if st.button("➕ Colocar na Lista"):
                if nome and custo_txt and venda:
                    item = {
                        'nome': nome,
                        'tamanho': tam,
                        'qtd': qtd,
                        'custo': ut.converter_input_para_float(custo_txt),
                        'venda': ut.converter_input_para_float(venda)
                    }
                    st.session_state.carrinho_compra.append(item)
                    st.success(f"{nome} adicionado!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.warning("Preencha Nome, Custo e Venda.")

    # --- PARTE 2: VISUALIZAR LISTA E FINALIZAR ---
    st.divider()
    
    if len(st.session_state.carrinho_compra) > 0:
        st.subheader("🛒 Itens no Pedido")
        
        # Mostra tabela do carrinho
        df_cart = pd.DataFrame(st.session_state.carrinho_compra)
        df_cart['Total Custo'] = df_cart['custo'] * df_cart['qtd']
        
        # Formata para exibir
        df_show = df_cart.copy()
        df_show['custo'] = df_show['custo'].apply(ut.format_brl)
        df_show['venda'] = df_show['venda'].apply(ut.format_brl)
        df_show['Total Custo'] = df_show['Total Custo'].apply(ut.format_brl)
        
        st.dataframe(df_show[['nome', 'tamanho', 'qtd', 'custo', 'Total Custo']], use_container_width=True)
        
        total_pedido = df_cart['Total Custo'].sum()
        qtd_total_pecas = df_cart['qtd'].sum()
        
        c_tot, c_limp = st.columns([3, 1])
        with c_tot:
            st.markdown(f"### 💰 Total do Pedido: {ut.format_brl(total_pedido)}")
        with c_limp:
            if st.button("🗑️ Limpar Lista"):
                st.session_state.carrinho_compra = []
                st.rerun()
            
        st.divider()
        st.subheader("💳 Dados do Pagamento (Lançar Despesa)")
        
        # --- REMOVIDO ST.FORM PARA PERMITIR DATAS DINÂMICAS ---
        c_forn, c_data = st.columns([2, 1])
        with c_forn: fornecedor = st.text_input("Fornecedor / Origem (Ex: Brás, Loja Z)")
        with c_data: data_compra = st.date_input("Data da Compra", datetime.now(), format="DD/MM/YYYY")
        
        c_pag1, c_pag2 = st.columns(2)
        with c_pag1: forma = st.selectbox("Forma de Pagamento", ["Pix", "Dinheiro", "Cartão Crédito", "Boleto"])
        with c_pag2: parc = st.number_input("Parcelas", 1, 12, 1)
        
        # --- LÓGICA DE DATAS PERSONALIZADAS (IGUAL VENDA) ---
        datas_compra = []
        with st.expander("📅 Personalizar Datas de Pagamento", expanded=False):
            st.caption("Datas calculadas a partir da Data da Compra.")
            cols = st.columns(min(parc, 4))
            for i in range(parc):
                if parc == 1:
                    padrao = data_compra
                else:
                    padrao = data_compra + timedelta(days=30*(i+1))
                
                d = cols[i % 4].date_input(f"Parcela {i+1}", value=padrao, key=f"d_compra_{i}", format="DD/MM/YYYY")
                datas_compra.append(d)

        st.write("")
        if st.button("✅ Finalizar Compra e Atualizar Estoque", type="primary"):
            if fornecedor:
                # 1. GERAR LISTA DE PRODUTOS PARA O BANCO
                novos_produtos = []
                for item in st.session_state.carrinho_compra:
                    c_save = f"{item['custo']:.2f}"
                    v_save = f"{item['venda']:.2f}"
                    # Cria N linhas para N quantidades
                    for _ in range(item['qtd']):
                        novos_produtos.append([
                            str(uuid.uuid4()), 
                            item['nome'], 
                            item['tamanho'], 
                            c_save, 
                            v_save, 
                            "Disponível"
                        ])
                
                # 2. SALVAR PRODUTOS EM LOTE
                if db.append_data_batch("Produtos", novos_produtos):
                    
                    # 3. GERAR FINANCEIRO COM DATAS PERSONALIZADAS
                    lancs = ut.gerar_lancamentos(
                        total=total_pedido, 
                        parcelas=parc, 
                        forma=forma, 
                        cli=fornecedor, 
                        origem_texto="Compra Estoque", 
                        data_base=data_compra,
                        datas_customizadas=datas_compra, # Passando as datas escolhidas
                        tipo="Despesa"
                    )
                    
                    db.append_data_batch("Financeiro", lancs)
                    
                    st.success(f"Sucesso! {qtd_total_pecas} peças cadastradas e Despesa de {ut.format_brl(total_pedido)} lançada.")
                    st.session_state.carrinho_compra = []
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Erro ao salvar produtos. Tente novamente.")
            else:
                st.warning("Informe o Fornecedor antes de finalizar.")
    else:
        st.info("Adicione itens acima para iniciar o pedido.")