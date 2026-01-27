import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import uuid
from datetime import datetime, timedelta
import os
import time
# import urllib.parse  <-- [ESTRATÉGIA UX] Mantido em espera

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="FL Boutique - Gestão", layout="wide")

# --- FUNÇÕES DE UTILIDADE ---
def converter_input_para_float(valor_str):
    try:
        if not valor_str: return 0.0
        limpo = str(valor_str).replace("R$", "").replace(" ", "")
        if "." in limpo and "," in limpo:
            limpo = limpo.replace(".", "").replace(",", ".")
        elif "," in limpo:
            limpo = limpo.replace(",", ".")
        return float(limpo)
    except:
        return 0.0

def format_brl(value):
    try:
        if value is None or str(value).strip() == "": return "R$ 0,00"
        val_float = float(value)
        return f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(value)

def format_data_br(data_iso):
    """Converte AAAA-MM-DD para DD/MM"""
    try:
        if not data_iso or len(str(data_iso)) < 10: return "-"
        data_obj = datetime.strptime(str(data_iso)[:10], "%Y-%m-%d")
        return data_obj.strftime("%d/%m")
    except:
        return data_iso

# --- CONEXÃO GOOGLE SHEETS ---
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if os.path.exists("credentials.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        elif "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            st.error("🚨 Sem credenciais.")
            return None
        client = gspread.authorize(creds)
        return client.open("FL Boutique Sistema")
    except Exception as e:
        st.error(f"🚨 Falha na Conexão: {e}")
        return None

# --- FUNÇÕES CRUD ---
def load_data(sheet_name):
    conn = get_connection()
    if conn:
        try:
            return pd.DataFrame(conn.worksheet(sheet_name).get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

def append_data(sheet_name, row_data):
    conn = get_connection()
    if conn:
        try:
            conn.worksheet(sheet_name).append_row(row_data)
            st.cache_data.clear()
        except Exception as e: st.error(f"Erro salvar: {e}")

def update_data(sheet_name, id_value, updated_row_dict):
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet(sheet_name)
            cell = ws.find(id_value)
            if cell:
                for col_idx, val in updated_row_dict.items(): ws.update_cell(cell.row, col_idx, val)
                st.cache_data.clear()
                return True
        except: pass
    return False

def delete_data(sheet_name, id_value):
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet(sheet_name)
            cell = ws.find(id_value)
            if cell:
                ws.delete_rows(cell.row)
                st.cache_data.clear()
                return True
        except: pass
    return False

def update_product_status(pid, status):
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Produtos")
            cell = ws.find(pid)
            if cell:
                ws.update_cell(cell.row, ws.row_values(1).index("status")+1, status)
                st.cache_data.clear()
        except: pass

def update_finance_status(fid, status):
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Financeiro")
            cell = ws.find(fid)
            if cell:
                ws.update_cell(cell.row, ws.row_values(1).index("status_pagamento")+1, status)
                st.cache_data.clear()
                return True
        except: pass
    return False

def update_product_status_batch(updates_dict):
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Produtos")
            all_records = ws.get_all_records()
            id_map = {row['id']: i + 2 for i, row in enumerate(all_records)}
            headers = ws.row_values(1)
            try: col_status = headers.index("status") + 1
            except: col_status = 6
            
            for pid, novo_status in updates_dict.items():
                if pid in id_map:
                    ws.update_cell(id_map[pid], col_status, novo_status)
                    time.sleep(0.1)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erro lote: {e}")
            return False

def gerar_lancamentos(total, parcelas, forma, cli, origem, data_base=None, datas_customizadas=None):
    lancs = []
    hoje = data_base if data_base else datetime.now()
    val_parc = round(total/parcelas, 2)
    dif = round(total - (val_parc * parcelas), 2)
    
    for i in range(parcelas):
        if datas_customizadas and len(datas_customizadas) > i:
            venc = datas_customizadas[i]
        else:
            if parcelas == 1: venc = hoje
            else: venc = hoje + timedelta(days=30*(i+1))
            
        val = val_parc + dif if i == parcelas-1 else val_parc
        status = "Pago" if (forma in ["Dinheiro", "Pix"] and parcelas == 1) else "Pendente"
        
        lancs.append([
            str(uuid.uuid4()),
            hoje.strftime("%Y-%m-%d"),
            venc.strftime("%Y-%m-%d"),
            "Venda",
            f"{origem} - {cli} ({i+1}/{parcelas})",
            f"{val:.2f}",
            forma,
            status
        ])
    return lancs

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #FDF2F4 !important; }
    h1, h2, h3, h4, h5, h6, p, span, label, li, .stMarkdown, .stText, th, td, .stMetricLabel { 
        color: #5C3A3B !important; 
    }
    section[data-testid="stSidebar"] {
        background-color: #FFF0F5 !important;
        color: #5C3A3B !important;
    }
    div[role="radiogroup"] label { color: #5C3A3B !important; }
    .stTextInput input, .stNumberInput input, .stDateInput input {
        background-color: #FFFFFF !important; 
        color: #000000 !important; 
        border-color: #E69496 !important;
        caret-color: #000000 !important;
    }
    div[data-baseweb="select"] > div { 
        background-color: #FFFFFF !important; 
        color: #000000 !important; 
        border-color: #E69496 !important; 
    }
    div[data-baseweb="select"] span { color: #000000 !important; }
    div[data-baseweb="select"] svg { fill: #5C3A3B !important; }
    div[data-baseweb="popover"], div[data-baseweb="popover"] > div, ul[data-baseweb="menu"] {
        background-color: #FFFFFF !important;
    }
    li[data-baseweb="option"] { 
        color: #000000 !important; 
        background-color: #FFFFFF !important; 
    }
    li[data-baseweb="option"]:hover { 
        background-color: #FFE4E1 !important; 
    }
    li[data-baseweb="option"] div { color: #000000 !important; }
    .stButton > button { 
        background-color: #E69496 !important; 
        color: white !important; 
        border: none; font-weight: bold; 
    }
    .stButton > button:hover { background-color: #D4787A !important; }
    [data-testid="stDataFrame"] { background-color: #FFFFFF !important; }
    .stAlert { background-color: #FFFFFF !important; color: #000000 !important; border: 1px solid #E69496; }
    </style>
    """, unsafe_allow_html=True)

# --- INTERFACE ---
c1, c2 = st.columns([1, 4])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png", width=80)
    else: st.write("👜")
with c2:
    st.title("FL Boutique")
    st.caption("Sistema de Gestão v24.0")

def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["passwords"]["acesso_loja"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if st.session_state.get("password_correct", False): return True
    st.text_input("Digite a senha de acesso:", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state: st.error("😕 Senha incorreta.")
    return False

if not check_password(): st.stop()

if st.sidebar.button("Sair"):
    st.session_state["password_correct"] = False
    st.rerun()

menu = st.sidebar.radio("Menu", ["Dashboard", "Venda Direta", "Controle de Malas", "Produtos", "Clientes", "Financeiro"])

if menu == "Dashboard":
    st.header("Visão Geral")
    df_fin = load_data("Financeiro")
    df_prod = load_data("Produtos")
    if not df_fin.empty and not df_prod.empty:
        try:
            prods_disp = df_prod[df_prod['status']=='Disponível']
            custo_total_estoque = sum([converter_input_para_float(x) for x in prods_disp['preco_custo']])
            qtd_produtos = len(prods_disp)
            
            receber = 0
            caixa_bruto = 0
            taxas_cartao = 0
            vendas_no_mes = 0
            valor_vendas_mes = 0
            mes_atual = datetime.now().strftime("%Y-%m")
            
            for idx, row in df_fin.iterrows():
                val = converter_input_para_float(row['valor'])
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
            c1.metric("Caixa Líquido", format_brl(caixa_liquido), delta=f"- {format_brl(taxas_cartao)} Taxas")
            c2.metric("A Receber", format_brl(receber))
            c3.metric("Estoque (Custo)", format_brl(custo_total_estoque))
            c4.metric("Taxas Pagas", format_brl(taxas_cartao))
            st.divider()
            c5, c6, c7 = st.columns(3)
            c5.metric("Peças Disponíveis", f"{qtd_produtos} un.")
            c6.metric("Vol. Vendas (Mês)", f"{vendas_no_mes}")
            c7.metric("Ticket Médio", format_brl(ticket_medio))
        except Exception as e: st.warning(f"Erro Dash: {e}")

elif menu == "Venda Direta":
    st.header("🛒 Nova Venda")
    df_cli = load_data("Clientes")
    df_prod = load_data("Produtos")
    
    if not df_cli.empty and not df_prod.empty:
        c1, c2 = st.columns([1, 3])
        with c1: data_venda = st.date_input("Data da Venda", datetime.now())
        with c2: cli = st.selectbox("Cliente", df_cli['nome'].unique())
            
        disp = df_prod[df_prod['status']=='Disponível']
        p_map = {}
        for i, row in disp.iterrows():
            val = converter_input_para_float(row['preco_venda'])
            lbl = f"{row['nome']} - {row['tamanho']} ({format_brl(val)})"
            p_map[lbl] = {'id': row['id'], 'val': val}
            
        sels = st.multiselect("Produtos", list(p_map.keys()))
        subtotal = sum([p_map[x]['val'] for x in sels])
        
        st.divider()
        st.markdown(f"#### Subtotal: {format_brl(subtotal)}")
        
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
                d = cols[i % 4].date_input(f"P{i+1}", value=padrao, key=f"d_vd_{i}")
                datas_escolhidas.append(d)
        
        if st.button("Finalizar Venda"):
            if final > 0:
                updates = {p_map[x]['id']: "Vendido" for x in sels}
                update_product_status_batch(updates)
                for l in gerar_lancamentos(final, parc, forma, cli, "Venda Direta", data_venda, datas_escolhidas): 
                    append_data("Financeiro", l)
                
                st.success("Venda Realizada!")
                st.session_state.venda_subtotal = 0.0
                st.session_state.key_pct = 0.0
                st.session_state.key_val = 0.0
                time.sleep(1.5)
                st.rerun()
            else: st.warning("Valor inválido")

elif menu == "Produtos":
    st.header("👗 Produtos")
    t1, t2, t3, t4, t5 = st.tabs(["Novo", "Reposição", "Estoque", "Editar", "Excluir"])
    
    with t1:
        st.info("💡 Digite o Custo e aperte 'Enter' para ver sugestão.")
        nome = st.text_input("Nome", key="p_nom")
        tam = st.selectbox("Tamanho", ["PP","P","M","G","GG","Único"], key="p_tam")
        custo = st.text_input("Custo (R$)", key="p_cus")
        
        if custo and custo != "0,00":
            c_val = converter_input_para_float(custo)
            if c_val > 0:
                sug = (c_val + 1.06) * 2 * 1.12
                st.info(f"💰 Sugestão: {format_brl(sug)}")
                if st.button("Usar Sugestão"): st.session_state.p_ven = f"{sug:.2f}".replace('.', ',')

        venda = st.text_input("Venda (R$)", key="p_ven", value="0,00")
        qtd = st.number_input("Qtd Peças", 1, value=1, key="p_qtd")
        
        if st.button("Salvar Produto"):
            if nome:
                c_f = converter_input_para_float(custo)
                v_f = converter_input_para_float(venda)
                conn = get_connection()
                if conn:
                    ws = conn.worksheet("Produtos")
                    rows = [[str(uuid.uuid4()), nome, tam, f"{c_f:.2f}", f"{v_f:.2f}", "Disponível"] for _ in range(qtd)]
                    for r in rows: ws.append_row(r)
                    st.cache_data.clear()
                st.success(f"{qtd} Produtos Salvos!")
                time.sleep(1)
                st.rerun()

    with t2:
        df = load_data("Produtos")
        if not df.empty:
            opts = df[['nome', 'tamanho', 'preco_custo', 'preco_venda']].drop_duplicates(subset=['nome', 'tamanho'])
            m_opt = {f"{r['nome']} - {r['tamanho']}": r for i, r in opts.iterrows()}
            sel = st.selectbox("Produto", list(m_opt.keys()))
            dat = m_opt[sel]
            
            st.divider()
            st.caption("Valores do lote anterior:")
            c_v = st.text_input("Custo Novo", value=format_brl(converter_input_para_float(dat['preco_custo'])).replace("R$ ",""))
            v_v = st.text_input("Venda Nova", value=format_brl(converter_input_para_float(dat['preco_venda'])).replace("R$ ",""))
            q_v = st.number_input("Qtd Adicional", 1)
            
            if st.button("Adicionar Estoque"):
                cf = converter_input_para_float(c_v)
                vf = converter_input_para_float(v_v)
                conn = get_connection()
                if conn:
                    ws = conn.worksheet("Produtos")
                    rows = [[str(uuid.uuid4()), dat['nome'], dat['tamanho'], f"{cf:.2f}", f"{vf:.2f}", "Disponível"] for _ in range(q_v)]
                    for r in rows: ws.append_row(r)
                    st.cache_data.clear()
                st.success("Adicionado!")
                st.rerun()

    with t3:
        if not df.empty:
            disp = df[df['status'] == 'Disponível']
            if not disp.empty:
                st.dataframe(disp.groupby(['nome', 'tamanho']).size().reset_index(name='Qtd'), use_container_width=True)
            else: st.info("Sem estoque.")

    with t4:
        if not df.empty:
            p_opts = {f"{r['nome']} - {r['tamanho']}": r['id'] for i, r in df.iterrows()}
            sel = st.selectbox("Editar", list(p_opts.keys()))
            row = df[df['id']==p_opts[sel]].iloc[0]
            with st.form("ed_p"):
                nn = st.text_input("Nome", row['nome'])
                nt = st.selectbox("Tam", ["PP","P","M","G","GG","Único"], index=["PP","P","M","G","GG","Único"].index(row['tamanho']) if row['tamanho'] in ["PP","P","M","G","GG","Único"] else 0)
                nc = st.text_input("Custo", format_brl(converter_input_para_float(row['preco_custo'])).replace("R$ ",""))
                nv = st.text_input("Venda", format_brl(converter_input_para_float(row['preco_venda'])).replace("R$ ",""))
                if st.form_submit_button("Salvar"):
                    cf = f"{converter_input_para_float(nc):.2f}"
                    vf = f"{converter_input_para_float(nv):.2f}"
                    update_data("Produtos", p_opts[sel], {2:nn, 3:nt, 4:cf, 5:vf})
                    st.success("Atualizado!")
                    st.rerun()

    with t5:
        if not df.empty:
            sel_d = st.selectbox("Excluir", list(p_opts.keys()), key='del_p')
            if st.button("Confirmar Exclusão"):
                delete_data("Produtos", p_opts[sel_d])
                st.success("Excluído!")
                st.rerun()

elif menu == "Clientes":
    st.header("👥 Clientes")
    t1, t2, t3 = st.tabs(["Cadastrar", "Editar", "Excluir"])
    with t1:
        with st.form("cad_cli"):
            n = st.text_input("Nome")
            w = st.text_input("WhatsApp")
            e = st.text_input("Endereço")
            if st.form_submit_button("Salvar"):
                append_data("Clientes", [str(uuid.uuid4()), n, w, e])
                st.success("Salvo!")
                st.rerun()
    df = load_data("Clientes")
    with t2:
        if not df.empty:
            copts = {r['nome']: r['id'] for i, r in df.iterrows()}
            sel = st.selectbox("Editar", list(copts.keys()))
            row = df[df['id']==copts[sel]].iloc[0]
            with st.form("ed_cli"):
                nn = st.text_input("Nome", row['nome'])
                nw = st.text_input("Zap", row['whatsapp'])
                ne = st.text_input("End", row['endereco'])
                if st.form_submit_button("Salvar"):
                    update_data("Clientes", copts[sel], {2:nn, 3:nw, 4:ne})
                    st.success("Ok!")
                    st.rerun()
    with t3:
        if not df.empty:
            sel_d = st.selectbox("Excluir", list(copts.keys()), key='del_c')
            if st.button("Apagar"):
                delete_data("Clientes", copts[sel_d])
                st.success("Apagado!")
                st.rerun()

elif menu == "Controle de Malas":
    st.header("👜 Malas")
    t1, t2, t3 = st.tabs(["Enviar", "Retorno", "Cancelar"])
    df_c = load_data("Clientes")
    df_p = load_data("Produtos")
    
    with t1:
        if not df_c.empty and not df_p.empty:
            with st.form("mal_env"):
                cl = st.selectbox("Cliente", df_c['nome'].unique())
                dp = df_p[df_p['status']=='Disponível']
                pm = {f"{r['nome']} {r['tamanho']}": r['id'] for i,r in dp.iterrows()}
                sl = st.multiselect("Peças", list(pm.keys()))
                dt_prev = st.date_input("Previsão de Retorno", datetime.now() + timedelta(days=3))
                
                if st.form_submit_button("Enviar Mala"):
                    ids = ",".join([pm[x] for x in sl])
                    cid = df_c[df_c['nome']==cl]['id'].values[0]
                    upd = {pm[x]: "Em Mala" for x in sl}
                    update_product_status_batch(upd)
                    append_data("Malas", [str(uuid.uuid4()), cid, cl, datetime.now().strftime("%Y-%m-%d"), ids, "Aberta", dt_prev.strftime("%Y-%m-%d")])
                    st.success("Mala Enviada!")
                    st.rerun()

    with t2:
        df_m = load_data("Malas")
        if not df_m.empty and 'status' in df_m.columns:
            abs = df_m[df_m['status']=='Aberta']
            if not abs.empty:
                m_op = {}
                for i, r in abs.iterrows():
                    d_prev = r['6'] if '6' in r else (r.values[6] if len(r.values) > 6 else "-")
                    lbl = f"{r['nome_cliente']} | Envio: {format_data_br(r['data_envio'])} | Prev: {format_data_br(d_prev)}"
                    m_op[lbl] = r['id']

                sel = st.selectbox("Selecionar Mala", list(m_op.keys()))
                row = abs[abs['id']==m_op[sel]].iloc[0]
                lids = str(row['lista_ids_produtos']).split(',')
                
                st.markdown(f"### 👜 Mala de: {row['nome_cliente']}")
                st.caption("Desmarque os itens que a cliente COMPROU (ficou com ela).")
                
                # --- LÓGICA DE CÁLCULO EM TEMPO REAL (SEM FORM) ---
                devs = {}
                total_mala = 0.0
                total_pagar = 0.0
                
                for pid in lids:
                    pi = df_p[df_p['id']==pid]
                    if not pi.empty:
                        val = converter_input_para_float(pi['preco_venda'].values[0])
                        val_fmt = format_brl(val)
                        nome = pi['nome'].values[0]
                        total_mala += val
                        
                        # O padrão é marcado (Devolveu). Se desmarcar, soma no pagar.
                        is_ret = st.checkbox(f"DEVOLVEU: {nome} ({val_fmt})", True, key=pid)
                        devs[pid] = is_ret
                        
                        if not is_ret:
                            total_pagar += val
                
                st.divider()
                c_tot1, c_tot2 = st.columns(2)
                c_tot1.metric("🎒 Valor da Mala", format_brl(total_mala))
                c_tot2.metric("💸 Valor a Pagar", format_brl(total_pagar))
                st.divider()
                
                c1, c2 = st.columns(2)
                with c1: fp = st.selectbox("Pagamento", ["Pix","Dinheiro","Cartão"])
                with c2: pa = st.number_input("Parcelas", 1, 12, 1)
                
                if st.button("Processar Retorno"):
                    upd = {}
                    tot = 0
                    for pid, dev in devs.items():
                        val = converter_input_para_float(df_p[df_p['id']==pid]['preco_venda'].values[0])
                        if dev: upd[pid] = "Disponível"
                        else: 
                            upd[pid] = "Vendido"
                            tot += val
                    
                    if update_product_status_batch(upd):
                        if tot > 0:
                            for l in gerar_lancamentos(tot, pa, fp, row['nome_cliente'], "Mala"): append_data("Financeiro", l)
                        update_data("Malas", m_op[sel], {6: "Finalizada"})
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
                update_product_status_batch(upd)
                delete_data("Malas", mid)
                st.success("Cancelada!")
                st.rerun()

elif menu == "Financeiro":
    st.header("💰 Finanças")
    t1, t2, t3, t4 = st.tabs(["Extrato", "Receber", "Lançar", "Excluir"])
    df = load_data("Financeiro")
    
    with t1:
        if not df.empty:
            sh = df.drop(columns=['id'], errors='ignore').copy()
            if 'valor' in sh.columns: sh['valor'] = sh['valor'].apply(lambda x: format_brl(converter_input_para_float(x)))
            st.dataframe(sh, use_container_width=True)
    with t2:
        if not df.empty:
            pen = df[(df['status_pagamento']=='Pendente') & (df['tipo']=='Venda')]
            if not pen.empty:
                op = {f"{r['descricao']} - {format_brl(converter_input_para_float(r['valor']))}": r['id'] for i,r in pen.iterrows()}
                sl = st.selectbox("Receber", list(op.keys()))
                if st.button("Confirmar"):
                    update_finance_status(op[sl], "Pago")
                    st.success("Recebido!")
                    st.rerun()
            else: st.info("Nada pendente.")
    with t3:
        with st.form("fin_man"):
            tp = st.selectbox("Tipo", ["Despesa", "Entrada"])
            ds = st.text_input("Descrição")
            vl = st.text_input("Valor (R$)", "0,00")
            dt = st.date_input("Data", datetime.now())
            stt = st.selectbox("Status", ["Pago", "Pendente"])
            if st.form_submit_button("Lançar"):
                vf = f"{converter_input_para_float(vl):.2f}"
                append_data("Financeiro", [str(uuid.uuid4()), dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m-%d"), tp, ds, vf, "Manual", stt])
                st.success("Lançado!")
                st.rerun()
    with t4:
        if not df.empty:
            op = {f"{r['descricao']} ({r['valor']})": r['id'] for i,r in df.iterrows()}
            sl = st.selectbox("Apagar", list(op.keys()))
            if st.button("Apagar Registro"):
                delete_data("Financeiro", op[sl])
                st.success("Apagado!")
                st.rerun()