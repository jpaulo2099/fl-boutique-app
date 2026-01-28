import streamlit as st
import database as db
import uuid


def show_clientes():
    st.header("👥 Clientes")
    t1, t2, t3 = st.tabs(["Cadastrar", "Editar", "Excluir"])
    
    df = db.load_data("Clientes")
    
    with t1:
        with st.form("cad_cli"):
            n = st.text_input("Nome")
            w = st.text_input("WhatsApp")
            e = st.text_input("Endereço")
            if st.form_submit_button("Salvar"):
                db.append_data("Clientes", [str(uuid.uuid4()), n, w, e])
                st.success("Salvo!")
                st.rerun()
        
        st.divider()
        st.markdown("### 📋 Lista de Clientes")
        if not df.empty:
            # --- CORREÇÃO DA NUMERAÇÃO E ORDEM ---
            # 1. Ordena
            # 2. Reseta o índice e apaga o antigo (drop=True)
            # 3. Ajusta para começar do 1
            df_show = df.drop(columns=['id'], errors='ignore').sort_values('nome').reset_index(drop=True)
            df_show.index = df_show.index + 1
            st.dataframe(df_show, use_container_width=True)
        else:
            st.info("Nenhum cliente cadastrado.")

    with t2:
        if not df.empty:
            copts = {r['nome']: r['id'] for i, r in df.iterrows()}
            lista_edit = sorted(list(copts.keys()))
            
            sel = st.selectbox("Editar", lista_edit)
            row = df[df['id']==copts[sel]].iloc[0]
            with st.form("ed_cli"):
                nn = st.text_input("Nome", row['nome'])
                nw = st.text_input("Zap", row['whatsapp'])
                ne = st.text_input("End", row['endereco'])
                if st.form_submit_button("Salvar"):
                    db.update_data("Clientes", copts[sel], {2:nn, 3:nw, 4:ne})
                    st.success("Ok!")
                    st.rerun()
    with t3:
        if not df.empty:
            copts = {r['nome']: r['id'] for i, r in df.iterrows()}
            lista_del = sorted(list(copts.keys()))
            sel_d = st.selectbox("Excluir", lista_del, key='del_c')
            if st.button("Apagar"):
                db.delete_data("Clientes", copts[sel_d])
                st.success("Apagado!")
                st.rerun()
