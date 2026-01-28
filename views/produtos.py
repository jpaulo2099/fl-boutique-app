import streamlit as st
import utils as ut
import database as db
import uuid
import time
import pandas as pd

def show_produtos():
    st.header("👗 Produtos")
    t1, t2, t3, t4, t5 = st.tabs(["Novo", "Reposição", "Estoque (Agrupado)", "Editar", "Excluir"])
    
    with t1:
        st.info("💡 Digite o Custo e aperte 'Enter' para ver sugestão.")
        nome = st.text_input("Nome", key="p_nom")
        tam = st.selectbox("Tamanho", ["PP","P","M","G","GG","Único"], key="p_tam")
        custo = st.text_input("Custo (R$)", key="p_cus")
        
        if custo and custo != "0,00":
            c_val = ut.converter_input_para_float(custo)
            if c_val > 0:
                sug = (c_val + 1.06) * 2 * 1.12
                st.info(f"💰 Sugestão: {ut.format_brl(sug)}")
                if st.button("Usar Sugestão"): st.session_state.p_ven = f"{sug:.2f}".replace('.', ',')

                venda = st.text_input("Venda (R$)", key="p_ven")

                qtd = st.number_input("Qtd Peças", 1, value=1, key="p_qtd")
        
        if st.button("Salvar Produto"):
            if nome:
                c_f = ut.converter_input_para_float(custo)
                v_f = ut.converter_input_para_float(venda)
                conn = db.get_connection()
                if conn:
                    ws = conn.worksheet("Produtos")
                    rows = [[str(uuid.uuid4()), nome, tam, f"{c_f:.2f}", f"{v_f:.2f}", "Disponível"] for _ in range(qtd)]
                    for r in rows: ws.append_row(r)
                    st.cache_data.clear()
                st.success(f"{qtd} Produtos Salvos!")
                time.sleep(1)
                st.rerun()

    with t2:
        df = db.load_data("Produtos")
        if not df.empty:
            opts = df[['nome', 'tamanho', 'preco_custo', 'preco_venda']].drop_duplicates(subset=['nome', 'tamanho'])
            m_opt = {f"{r['nome']} - {r['tamanho']}": r for i, r in opts.iterrows()}
            sel = st.selectbox("Produto", list(m_opt.keys()))
            dat = m_opt[sel]
            
            st.divider()
            st.caption("Valores do lote anterior:")
            c_v = st.text_input("Custo Novo", value=ut.format_brl(ut.converter_input_para_float(dat['preco_custo'])).replace("R$ ",""))
            v_v = st.text_input("Venda Nova", value=ut.format_brl(ut.converter_input_para_float(dat['preco_venda'])).replace("R$ ",""))
            q_v = st.number_input("Qtd Adicional", 1)
            
            if st.button("Adicionar Estoque"):
                cf = ut.converter_input_para_float(c_v)
                vf = ut.converter_input_para_float(v_v)
                conn = db.get_connection()
                if conn:
                    ws = conn.worksheet("Produtos")
                    rows = [[str(uuid.uuid4()), dat['nome'], dat['tamanho'], f"{cf:.2f}", f"{vf:.2f}", "Disponível"] for _ in range(q_v)]
                    for r in rows: ws.append_row(r)
                    st.cache_data.clear()
                st.success("Adicionado!")
                st.rerun()

    with t3:
        # --- VISUALIZAÇÃO HIERÁRQUICA (CATEGORIA -> PRODUTOS) ---
        if not df.empty:
            # 1. Preparar Dados
            # Qtd Real: Se vendido é 0, se Disponivel/Mala é 1
            df['qtd_real'] = df['status'].apply(lambda x: 0 if x == 'Vendido' else 1)
            
            # Extrair Categoria (Primeira palavra do nome)
            # Ex: "Blazer Manga Longa" -> "Blazer"
            df['Categoria'] = df['nome'].apply(lambda x: x.split(' ')[0].capitalize() if len(str(x).split(' ')) > 0 else "Outros")

            # 2. Calcular Totais por Categoria (Para o título do Expander)
            resumo_cat = df.groupby('Categoria')['qtd_real'].sum().reset_index()
            resumo_cat = resumo_cat.sort_values(by='Categoria')

            st.info("Clique nas categorias abaixo para ver os detalhes.")

            # 3. Loop para criar os Expanders
            for index, row_cat in resumo_cat.iterrows():
                categoria = row_cat['Categoria']
                total_pecas = row_cat['qtd_real']
                
                # Só mostra se tiver item cadastrado (mesmo que qtd seja 0, para histórico)
                # Se quiser esconder categorias zeradas, adicione: if total_pecas > 0:
                
                # Cria o "Blazer (6)"
                with st.expander(f"📂 {categoria} ({total_pecas} peças)", expanded=False):
                    
                    # Filtra apenas os produtos dessa categoria
                    df_filtrado = df[df['Categoria'] == categoria].copy()
                    
                    # Agrupa os detalhes (Nome Completo + Tamanho)
                    detalhes = df_filtrado.groupby(['nome', 'tamanho', 'preco_custo', 'preco_venda'])['qtd_real'].sum().reset_index()
                    detalhes.rename(columns={'qtd_real': 'Qtd', 'nome': 'Produto', 'tamanho': 'Tam'}, inplace=True)
                    
                    # Formatação de Moeda
                    detalhes['Custo'] = detalhes['preco_custo'].apply(lambda x: ut.format_brl(ut.converter_input_para_float(x)))
                    detalhes['Venda'] = detalhes['preco_venda'].apply(lambda x: ut.format_brl(ut.converter_input_para_float(x)))
                    
                    # Exibe a tabela filha limpa
                    st.dataframe(
                        detalhes[['Produto', 'Tam', 'Qtd', 'Custo', 'Venda']], 
                        use_container_width=True,
                        hide_index=True
                    )
        else:
            st.info("Sem produtos cadastrados.")

    with t4:
        if not df.empty:
            p_opts = {f"{r['nome']} - {r['tamanho']}": r['id'] for i, r in df.iterrows()}
            sel = st.selectbox("Editar", list(p_opts.keys()))
            row = df[df['id']==p_opts[sel]].iloc[0]
            with st.form("ed_p"):
                nn = st.text_input("Nome", row['nome'])
                nt = st.selectbox("Tam", ["PP","P","M","G","GG","Único"], index=["PP","P","M","G","GG","Único"].index(row['tamanho']) if row['tamanho'] in ["PP","P","M","G","GG","Único"] else 0)
                nc = st.text_input("Custo", ut.format_brl(ut.converter_input_para_float(row['preco_custo'])).replace("R$ ",""))
                nv = st.text_input("Venda", ut.format_brl(ut.converter_input_para_float(row['preco_venda'])).replace("R$ ",""))
                if st.form_submit_button("Salvar"):
                    cf = f"{ut.converter_input_para_float(nc):.2f}"
                    vf = f"{ut.converter_input_para_float(nv):.2f}"
                    db.update_data("Produtos", p_opts[sel], {2:nn, 3:nt, 4:cf, 5:vf})
                    st.success("Atualizado!")
                    st.rerun()

    with t5:
        if not df.empty:
            sel_d = st.selectbox("Excluir", list(p_opts.keys()), key='del_p')
            if st.button("Confirmar Exclusão"):
                db.delete_data("Produtos", p_opts[sel_d])
                st.success("Excluído!")
                st.rerun()