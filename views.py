import streamlit as st
import uuid
import time
from datetime import datetime, timedelta
import database as db
import utils as ut
import pandas as pd

def show_dashboard():
    st.header("Visão Geral")
    df_fin = db.load_data("Financeiro")
    df_prod = db.load_data("Produtos")
    if not df_fin.empty and not df_prod.empty:
        try:
            prods_disp = df_prod[df_prod['status']=='Disponível']
            custo_total_estoque = sum([ut.converter_input_para_float(x) for x in prods_disp['preco_custo']])
            qtd_produtos = len(prods_disp)
            
            receber = 0
            caixa_bruto = 0
            taxas_cartao = 0
            vendas_no_mes = 0
            valor_vendas_mes = 0
            mes_atual = datetime.now().strftime("%Y-%m")
            
            for idx, row in df_fin.iterrows():
                val = ut.converter_input_para_float(row['valor'])
                data_lanc = str(row['data_lancamento'])
                
                if row['tipo'] == 'Venda' and data_lanc.startswith(mes_atual):
                    valor_vendas_mes += val
                    vendas_no_mes += 1
                if row['tipo'] == 'Venda' and row['status_pagamento'] == 'Pendente':
                    receber += val
                if row['status_pagamento'] == 'Pago':
                    if row['tipo'] in ['Venda', 'Entrada']:
                        caixa_bruto += val
                        forma = str(row['forma_pagamento']).lower()
                        if any(x in forma for x in ["cartão", "credito", "debito", "crédito", "débito"]):
                            taxas_cartao += val * 0.12
                    elif row['tipo'] == 'Despesa':
                        caixa_bruto -= val

            caixa_liquido = caixa_bruto - taxas_cartao
            ticket_medio = valor_vendas_mes / vendas_no_mes if vendas_no_mes > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Caixa Líquido", ut.format_brl(caixa_liquido), delta=f"- {ut.format_brl(taxas_cartao)} Taxas")
            c2.metric("A Receber", ut.format_brl(receber))
            c3.metric("Estoque (Custo)", ut.format_brl(custo_total_estoque))
            c4.metric("Taxas Pagas", ut.format_brl(taxas_cartao))
            st.divider()
            c5, c6, c7 = st.columns(3)
            c5.metric("Peças Disponíveis", f"{qtd_produtos} un.")
            c6.metric("Vol. Vendas (Mês)", f"{vendas_no_mes}")
            c7.metric("Ticket Médio", ut.format_brl(ticket_medio))
        except Exception as e: st.warning(f"Erro Dash: {e}")

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

def show_produtos():
    st.header("👗 Produtos")
    t1, t2, t3, t4, t5 = st.tabs(["Novo", "Reposição", "Estoque", "Editar", "Excluir"])
    
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

        venda = st.text_input("Venda (R$)", key="p_ven", value="0,00")
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
        if not df.empty:
            df['qtd_real'] = df['status'].apply(lambda x: 0 if x == 'Vendido' else 1)
            resumo = df.groupby(['nome', 'tamanho', 'preco_custo', 'preco_venda'])['qtd_real'].sum().reset_index()
            
            resumo.rename(columns={'qtd_real': 'Quantidade', 'preco_custo': 'Custo', 'preco_venda': 'Venda'}, inplace=True)
            resumo = resumo.sort_values(by=['nome', 'tamanho'])
            
            resumo['Custo'] = resumo['Custo'].apply(lambda x: ut.format_brl(ut.converter_input_para_float(x)))
            resumo['Venda'] = resumo['Venda'].apply(lambda x: ut.format_brl(ut.converter_input_para_float(x)))
            
            st.dataframe(resumo, use_container_width=True)
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

def show_financeiro():
    st.header("💰 Finanças")
    t1, t2, t3, t4 = st.tabs(["Extrato", "Receber", "Lançar", "Excluir"])
    df = db.load_data("Financeiro")
    
    with t1:
        if not df.empty:
            sh = df.drop(columns=['id'], errors='ignore').copy()
            if 'valor' in sh.columns: sh['valor'] = sh['valor'].apply(lambda x: ut.format_brl(ut.converter_input_para_float(x)))
            # DATA FORMATADA NO DATAFRAME
            if 'data_lancamento' in sh.columns:
                sh['data_lancamento'] = sh['data_lancamento'].apply(ut.format_data_br)
            if 'data_vencimento' in sh.columns:
                sh['data_vencimento'] = sh['data_vencimento'].apply(ut.format_data_br)
                
            st.dataframe(sh, use_container_width=True)
    with t2:
        if not df.empty:
            pen = df[(df['status_pagamento']=='Pendente') & (df['tipo']=='Venda')]
            if not pen.empty:
                op = {f"{r['descricao']} - {ut.format_brl(ut.converter_input_para_float(r['valor']))}": r['id'] for i,r in pen.iterrows()}
                sl = st.selectbox("Receber", list(op.keys()))
                if st.button("Confirmar"):
                    db.update_finance_status(op[sl], "Pago")
                    st.success("Recebido!")
                    st.rerun()
            else: st.info("Nada pendente.")
    with t3:
        with st.form("fin_man"):
            tp = st.selectbox("Tipo", ["Despesa", "Entrada"])
            ds = st.text_input("Descrição")
            vl = st.text_input("Valor (R$)", "0,00")
            # DATA FORMATADA
            dt = st.date_input("Data", datetime.now(), format="DD/MM/YYYY")
            stt = st.selectbox("Status", ["Pago", "Pendente"])
            if st.form_submit_button("Lançar"):
                vf = f"{ut.converter_input_para_float(vl):.2f}"
                db.append_data("Financeiro", [str(uuid.uuid4()), dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m-%d"), tp, ds, vf, "Manual", stt])
                st.success("Lançado!")
                st.rerun()
    with t4:
        if not df.empty:
            op = {f"{r['descricao']} ({r['valor']})": r['id'] for i,r in df.iterrows()}
            sl = st.selectbox("Apagar", list(op.keys()))
            if st.button("Apagar Registro"):
                db.delete_data("Financeiro", op[sl])
                st.success("Apagado!")
                st.rerun()

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
        
        c4, c5, c6 = st.columns(3)
        with c4: custo = st.text_input("Custo Unit. (R$)", key="c_custo")
        with c5: venda = st.text_input("Venda Unit. (R$)", key="c_venda")
        
        # Botão de ação local (não salva no banco ainda)
        if st.button("➕ Colocar na Lista"):
            if nome and custo and venda:
                # Salva no estado temporário
                item = {
                    'nome': nome,
                    'tamanho': tam,
                    'qtd': qtd,
                    'custo': ut.converter_input_para_float(custo),
                    'venda': ut.converter_input_para_float(venda)
                }
                st.session_state.carrinho_compra.append(item)
                st.success(f"{nome} adicionado à lista!")
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
        # Calcula totais
        df_cart['Total Custo'] = df_cart['custo'] * df_cart['qtd']
        df_cart['Total Venda (Prev)'] = df_cart['venda'] * df_cart['qtd']
        
        # Formata para exibir
        df_show = df_cart.copy()
        df_show['custo'] = df_show['custo'].apply(ut.format_brl)
        df_show['venda'] = df_show['venda'].apply(ut.format_brl)
        df_show['Total Custo'] = df_show['Total Custo'].apply(ut.format_brl)
        
        st.dataframe(df_show[['nome', 'tamanho', 'qtd', 'custo', 'Total Custo']], use_container_width=True)
        
        total_pedido = df_cart['Total Custo'].sum() # Soma dos floats originais
        qtd_total_pecas = df_cart['qtd'].sum()
        
        st.markdown(f"### 💰 Total do Pedido: {ut.format_brl(total_pedido)}")
        
        # Botão para limpar carrinho
        if st.button("🗑️ Limpar Lista"):
            st.session_state.carrinho_compra = []
            st.rerun()
            
        st.divider()
        st.subheader("💳 Dados do Pagamento (Lançar Despesa)")
        
        with st.form("fechar_pedido"):
            c_forn, c_data = st.columns([2, 1])
            with c_forn: fornecedor = st.text_input("Fornecedor / Origem (Ex: Brás, Loja Z)")
            with c_data: data_compra = st.date_input("Data da Compra", datetime.now(), format="DD/MM/YYYY")
            
            c_pag1, c_pag2 = st.columns(2)
            with c_pag1: forma = st.selectbox("Forma de Pagamento", ["Pix", "Dinheiro", "Cartão Crédito", "Boleto"])
            with c_pag2: parc = st.number_input("Parcelas", 1, 12, 1)
            
            # OBS: Não coloquei datas personalizadas aqui para não complicar demais agora, 
            # mas usa a lógica padrão (30/60/90). Se quiserem, adicionamos depois.
            
            if st.form_submit_button("✅ Finalizar Compra e Atualizar Estoque"):
                if fornecedor:
                    # 1. GERAR LISTA DE PRODUTOS PARA O BANCO (Multiplicando pela Qtd)
                    novos_produtos = []
                    for item in st.session_state.carrinho_compra:
                        c_save = f"{item['custo']:.2f}"
                        v_save = f"{item['venda']:.2f}"
                        # Cria N linhas para N quantidades (Loop de cadastro)
                        for _ in range(item['qtd']):
                            novos_produtos.append([
                                str(uuid.uuid4()), 
                                item['nome'], 
                                item['tamanho'], 
                                c_save, 
                                v_save, 
                                "Disponível"
                            ])
                    
                    # 2. SALVAR PRODUTOS EM LOTE (1 Chamada de API)
                    if db.append_data_batch("Produtos", novos_produtos):
                        
                        # 3. GERAR FINANCEIRO (DESPESA)
                        lancs = ut.gerar_lancamentos(
                            total=total_pedido, 
                            parcelas=parc, 
                            forma=forma, 
                            cli=fornecedor, 
                            origem_texto="Compra Estoque", 
                            data_base=data_compra,
                            tipo="Despesa" # Importante!
                        )
                        
                        # Salva financeiro em lote também
                        db.append_data_batch("Financeiro", lancs)
                        
                        st.success(f"Sucesso! {qtd_total_pecas} peças cadastradas e Despesa de {ut.format_brl(total_pedido)} lançada.")
                        st.session_state.carrinho_compra = [] # Limpa carrinho
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Erro ao salvar produtos. Tente novamente.")
                else:
                    st.warning("Informe o Fornecedor.")
    else:
        st.info("Adicione itens acima para iniciar o pedido.")