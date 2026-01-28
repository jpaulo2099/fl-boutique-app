import streamlit as st
import utils as ut
import database as db
import uuid
from datetime import datetime, timedelta
import time


def show_malas():
    st.header("👜 Malas")
    t1, t2, t3 = st.tabs(["Enviar", "Retorno", "Cancelar"])
    df_c = db.load_data("Clientes")
    df_p = db.load_data("Produtos")
    
    with t1:
        if not df_c.empty and not df_p.empty:
            with st.form("mal_env"):
                # ORDENAÇÃO
                lista_clientes_mala = sorted(df_c['nome'].unique())
                cl = st.selectbox("Cliente", lista_clientes_mala)
                
                dp = df_p[df_p['status']=='Disponível']
                pm = {f"{r['nome']} {r['tamanho']}": r['id'] for i,r in dp.iterrows()}
                sl = st.multiselect("Peças", list(pm.keys()))
                
                # DATA FORMATADA
                dt_prev = st.date_input("Previsão de Retorno", datetime.now() + timedelta(days=3), format="DD/MM/YYYY")
                
                if st.form_submit_button("Enviar Mala"):
                    ids = ",".join([pm[x] for x in sl])
                    cid = df_c[df_c['nome']==cl]['id'].values[0]
                    upd = {pm[x]: "Em Mala" for x in sl}
                    db.update_product_status_batch(upd)
                    db.append_data("Malas", [str(uuid.uuid4()), cid, cl, datetime.now().strftime("%Y-%m-%d"), ids, "Aberta", dt_prev.strftime("%Y-%m-%d")])
                    st.success("Mala Enviada!")
                    st.rerun()

    with t2:
        df_m = db.load_data("Malas")
        if not df_m.empty and 'status' in df_m.columns:
            abs = df_m[df_m['status']=='Aberta']
            if not abs.empty:
                m_op = {}
                for i, r in abs.iterrows():
                    d_prev = r['6'] if '6' in r else (r.values[6] if len(r.values) > 6 else "-")
                    lbl = f"{r['nome_cliente']} | Envio: {ut.format_data_br(r['data_envio'])} | Prev: {ut.format_data_br(d_prev)}"
                    m_op[lbl] = r['id']

                sel = st.selectbox("Selecionar Mala", list(m_op.keys()))
                row = abs[abs['id']==m_op[sel]].iloc[0]
                lids = str(row['lista_ids_produtos']).split(',')
                
                st.markdown(f"### 👜 Mala de: {row['nome_cliente']}")
                st.caption("Desmarque os itens que a cliente COMPROU (ficou com ela).")
                
                devs = {}
                total_mala = 0.0
                total_pagar = 0.0
                
                for pid in lids:
                    pi = df_p[df_p['id']==pid]
                    if not pi.empty:
                        val = ut.converter_input_para_float(pi['preco_venda'].values[0])
                        val_fmt = ut.format_brl(val)
                        nome = pi['nome'].values[0]
                        total_mala += val
                        is_ret = st.checkbox(f"DEVOLVEU: {nome} ({val_fmt})", True, key=pid)
                        devs[pid] = is_ret
                        if not is_ret: total_pagar += val
                
                st.divider()
                c_tot1, c_tot2 = st.columns(2)
                c_tot1.metric("🎒 Valor da Mala", ut.format_brl(total_mala))
                c_tot2.metric("💸 Valor a Pagar", ut.format_brl(total_pagar))
                st.divider()
                
                c1, c2 = st.columns(2)
                with c1: fp = st.selectbox("Pagamento", ["Pix","Dinheiro","Cartão"])
                with c2: pa = st.number_input("Parcelas", 1, 12, 1)
                
                datas_mala = []
                with st.expander("📅 Datas de Pagamento", expanded=False):
                    cols = st.columns(min(pa, 4))
                    for i in range(pa):
                        padrao = datetime.now() if pa == 1 else datetime.now() + timedelta(days=30*(i+1))
                        # DATA FORMATADA
                        d = cols[i % 4].date_input(f"P{i+1}", value=padrao, key=f"dm_{i}", format="DD/MM/YYYY")
                        datas_mala.append(d)
                
                if st.button("Processar Retorno"):
                    upd = {}
                    tot = 0
                    for pid, dev in devs.items():
                        val = ut.converter_input_para_float(df_p[df_p['id']==pid]['preco_venda'].values[0])
                        if dev: upd[pid] = "Disponível"
                        else: 
                            upd[pid] = "Vendido"
                            tot += val
                    
                    if db.update_product_status_batch(upd):
                        if tot > 0:
                            for l in ut.gerar_lancamentos(tot, pa, fp, row['nome_cliente'], "Mala", datas_customizadas=datas_mala): 
                                db.append_data("Financeiro", l)
                        db.update_data("Malas", m_op[sel], {6: "Finalizada"})
                        st.success("Mala Finalizada!")
                        time.sleep(1.5)
                        st.rerun()

    with t3:
        if not df_m.empty:
            sel_d = st.selectbox("Cancelar Mala", list(m_op.keys()) if 'm_op' in locals() else [], key="canc")
            if st.button("Confirmar Cancelamento"):
                mid = m_op[sel_d]
                pids = str(df_m[df_m['id']==mid]['lista_ids_produtos'].values[0]).split(',')
                upd = {p: "Disponível" for p in pids}
                db.update_product_status_batch(upd)
                db.delete_data("Malas", mid)
                st.success("Cancelada!")
                st.rerun()
