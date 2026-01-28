import streamlit as st
import utils as ut
import database as db
from datetime import datetime, timedelta
import time


def show_venda_direta():
    st.header("🛒 Nova Venda")
    df_cli = db.load_data("Clientes")
    df_prod = db.load_data("Produtos")
    
    if not df_cli.empty and not df_prod.empty:
        c1, c2 = st.columns([1, 3])
        # DATA FORMATADA NO INPUT
        with c1: data_venda = st.date_input("Data da Venda", datetime.now(), format="DD/MM/YYYY")
        
        # ORDENAÇÃO ALFABÉTICA
        lista_clientes = sorted(df_cli['nome'].unique())
        with c2: cli = st.selectbox("Cliente", lista_clientes)
            
        disp = df_prod[df_prod['status']=='Disponível']
        p_map = {}
        for i, row in disp.iterrows():
            val = ut.converter_input_para_float(row['preco_venda'])
            lbl = f"{row['nome']} - {row['tamanho']} ({ut.format_brl(val)})"
            p_map[lbl] = {'id': row['id'], 'val': val}
            
        sels = st.multiselect("Produtos", list(p_map.keys()))
        subtotal = sum([p_map[x]['val'] for x in sels])
        
        st.divider()
        st.markdown(f"#### Subtotal: {ut.format_brl(subtotal)}")
        
        if 'venda_subtotal' not in st.session_state or st.session_state.venda_subtotal != subtotal:
            st.session_state.venda_subtotal = float(subtotal)
            st.session_state.desc_pct = 0.0
            st.session_state.val_final = float(subtotal)

        def update_from_pct():
            pct = st.session_state.key_pct
            new = st.session_state.venda_subtotal * (1 - pct / 100)
            st.session_state.key_val = float(f"{new:.2f}")
        def update_from_val():
            val = st.session_state.key_val
            base = st.session_state.venda_subtotal
            if base > 0: st.session_state.key_pct = float(f"{((base - val)/base)*100:.1f}")
            else: st.session_state.key_pct = 0.0
        
        st.session_state.venda_subtotal = float(subtotal)
        c3, c4 = st.columns(2)
        with c3: st.number_input("Desconto (%)", 0.0, 100.0, key="key_pct", on_change=update_from_pct)
        with c4: st.number_input("Valor Final (R$)", 0.0, key="key_val", on_change=update_from_val, format="%.2f")
        final = st.session_state.key_val

        st.divider()
        c5, c6 = st.columns(2)
        with c5: forma = st.selectbox("Pagamento", ["Pix", "Dinheiro", "Cartão Crédito", "Cartão Débito"])
        with c6: parc = st.number_input("Parcelas", 1, 12, 1)
        
        datas_escolhidas = []
        with st.expander("📅 Datas de Pagamento", expanded=False):
            cols = st.columns(min(parc, 4))
            for i in range(parc):
                padrao = data_venda if parc == 1 else data_venda + timedelta(days=30*(i+1))
                # DATA FORMATADA NOS INPUTS DE PARCELA
                d = cols[i % 4].date_input(f"P{i+1}", value=padrao, key=f"d_vd_{i}", format="DD/MM/YYYY")
                datas_escolhidas.append(d)
        
        if st.button("Finalizar Venda"):
            if final > 0:
                updates = {p_map[x]['id']: "Vendido" for x in sels}
                db.update_product_status_batch(updates)
                for l in ut.gerar_lancamentos(final, parc, forma, cli, "Venda Direta", data_venda, datas_escolhidas): 
                    db.append_data("Financeiro", l)
                
                st.success("Venda Realizada!")
                st.session_state.venda_subtotal = 0.0
                st.session_state.key_pct = 0.0
                st.session_state.key_val = 0.0
                time.sleep(1.5)
                st.rerun()
            else: st.warning("Valor inválido")

