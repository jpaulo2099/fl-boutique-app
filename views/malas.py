import streamlit as st
import utils as ut
import database as db
import uuid
import pandas as pd
from datetime import datetime, timedelta
import time

def show_malas():
    st.header("👜 Malas")
    
    # 1. ATUALIZADO: Adicionada a aba "Histórico"
    t1, t2, t3, t4 = st.tabs(["Enviar", "Retorno", "Cancelar", "📜 Histórico"])
    
    df_c = db.load_data("Clientes")
    df_p = db.load_data("Produtos")
    df_m = db.load_data("Malas") # Carrega aqui para usar em todas as abas
    
    # --- ABA 1: ENVIAR ---
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
                    if sl:
                        ids = ",".join([pm[x] for x in sl])
                        cid = df_c[df_c['nome']==cl]['id'].values[0]
                        
                        # ATUALIZAÇÃO EM LOTE (BATCH)
                        upd = {pm[x]: "Em Mala" for x in sl}
                        
                        if db.update_product_status_batch(upd):
                            db.append_data("Malas", [
                                str(uuid.uuid4()), 
                                cid, 
                                cl, 
                                datetime.now().strftime("%Y-%m-%d"), 
                                ids, 
                                "Aberta", 
                                dt_prev.strftime("%Y-%m-%d")
                            ])
                            st.success(f"Mala enviada com {len(sl)} itens!")
                            st.rerun()
                        else:
                            st.error("Erro ao atualizar estoque. Tente novamente.")
                    else:
                        st.warning("Selecione pelo menos uma peça.")

    # --- ABA 2: RETORNO ---
    with t2:
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
                            for l in ut.gerar_lancamentos(tot, pa, fp, row['nome_cliente'], "Mala", data_base=datetime.now(), datas_customizadas=datas_mala, tipo="Venda"): 
                                db.append_data("Financeiro", l)
                        
                        # Atualiza status da mala para Finalizada
                        db.update_data("Malas", m_op[sel], {6: "Finalizada"})
                        st.success("Mala Finalizada!")
                        time.sleep(1.5)
                        st.rerun()

    # --- ABA 3: CANCELAR ---
    with t3:
        if not df_m.empty and 'status' in df_m.columns:
            abs = df_m[df_m['status']=='Aberta']
            if not abs.empty:
                # Recria o dicionário apenas para as abertas (para evitar erro de chave)
                m_op_canc = {}
                for i, r in abs.iterrows():
                    lbl = f"{r['nome_cliente']} | Envio: {ut.format_data_br(r['data_envio'])}"
                    m_op_canc[lbl] = r['id']

                sel_d = st.selectbox("Cancelar Mala", list(m_op_canc.keys()), key="canc")
                
                if st.button("Confirmar Cancelamento"):
                    mid = m_op_canc[sel_d]
                    # Recupera IDs para destravar
                    raw_ids = df_m[df_m['id']==mid]['lista_ids_produtos'].values
                    if len(raw_ids) > 0:
                        pids = str(raw_ids[0]).split(',')
                        upd = {p: "Disponível" for p in pids}
                        
                        if db.update_product_status_batch(upd):
                            db.delete_data("Malas", mid)
                            st.success("Cancelada e Estoque Liberado!")
                            time.sleep(1.5)
                            st.rerun()
            else:
                st.info("Nenhuma mala aberta para cancelar.")

    # --- ABA 4: HISTÓRICO (NOVO!) ---
    with t4:
        st.markdown("### 📜 Histórico de Malas Finalizadas")
        if not df_m.empty and 'status' in df_m.columns:
            # Filtra apenas as finalizadas
            hist = df_m[df_m['status'] == 'Finalizada'].copy()
            
            if not hist.empty:
                # Formata data para ordenar corretamente
                hist['data_envio_dt'] = pd.to_datetime(hist['data_envio'], errors='coerce')
                hist = hist.sort_values(by='data_envio_dt', ascending=False)
                
                # Formatação visual
                hist['Data Envio'] = hist['data_envio'].apply(ut.format_data_br)
                
                # Exibe Tabela Resumida
                st.dataframe(
                    hist[['Data Envio', 'nome_cliente', 'status']], 
                    use_container_width=True,
                    hide_index=True
                )
                
                st.divider()
                st.caption("🔍 Detalhes da Mala")
                
                # Seletor para ver o que tinha dentro da mala antiga
                op_hist = {f"{r['nome_cliente']} ({ut.format_data_br(r['data_envio'])})": r['id'] for i,r in hist.iterrows()}
                sel_hist = st.selectbox("Selecione para ver os itens:", list(op_hist.keys()))
                
                if sel_hist:
                    mala_detalhe = hist[hist['id'] == op_hist[sel_hist]].iloc[0]
                    lista_ids_hist = str(mala_detalhe['lista_ids_produtos']).split(',')
                    
                    # Busca nomes dos produtos
                    itens_nomes = []
                    valor_estimado = 0
                    
                    for pid in lista_ids_hist:
                        prod = df_p[df_p['id'] == pid]
                        if not prod.empty:
                            nm = prod['nome'].values[0]
                            tm = prod['tamanho'].values[0]
                            vl = ut.converter_input_para_float(prod['preco_venda'].values[0])
                            itens_nomes.append(f"{nm} ({tm}) - {ut.format_brl(vl)}")
                            valor_estimado += vl
                        else:
                            itens_nomes.append(f"Produto excluído/não encontrado ({pid})")
                    
                    st.write(f"**Total Estimado da Mala:** {ut.format_brl(valor_estimado)}")
                    st.write("**Itens:**")
                    for item in itens_nomes:
                        st.text(f"- {item}")

            else:
                st.info("Nenhuma mala foi finalizada ainda.")
        else:
            st.info("Sem dados de malas.")

    # --- ZONA DE PERIGO (MANTIDA NO FINAL) ---
    st.divider()
    with st.expander("🆘 Zona de Perigo: Destravar Estoque (Correção de Erros)"):
        st.warning("Use esta ferramenta se ocorrer um erro na criação da mala e os produtos ficarem presos com status 'Em Mala'.")
        
        travados = df_p[df_p['status'] == 'Em Mala']
        
        if not travados.empty:
            st.error(f"⚠️ Atenção: Existem {len(travados)} produtos marcados como 'Em Mala' no sistema.")
            
            op_trav = {f"{r['nome']} ({r['tamanho']}) - {r['id']}": r['id'] for i, r in travados.iterrows()}
            
            if st.checkbox("Selecionar Todos os Travados"):
                sels_trav = list(op_trav.keys())
            else:
                sels_trav = st.multiselect("Selecione os produtos para DEVOLVER ao Estoque (Disponível):", list(op_trav.keys()))
            
            st.write("")
            if st.button("🔓 Forçar Liberação (Disponível)", type="primary"):
                if sels_trav:
                    upd_force = {op_trav[k]: "Disponível" for k in sels_trav}
                    
                    if db.update_product_status_batch(upd_force):
                        st.success(f"Sucesso! {len(sels_trav)} produtos foram devolvidos para 'Disponível'.")
                        time.sleep(1.5)
                        st.rerun()
                else:
                    st.warning("Selecione pelo menos um item.")
        else:
            st.success("Tudo limpo! Nenhum produto travado no limbo.")