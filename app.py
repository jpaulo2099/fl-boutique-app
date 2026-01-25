import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import uuid
from datetime import datetime, timedelta
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="FL Boutique - Gestão", layout="wide")

# --- FUNÇÕES DE UTILIDADE ---
def converter_input_para_float(valor_str):
    """Converte '1.200,50' ou '85,90' para float python."""
    try:
        if not valor_str: return 0.0
        # Remove R$ e espaços
        limpo = str(valor_str).replace("R$", "").replace(" ", "")
        
        # Lógica para tratar ponto e vírgula
        if "." in limpo and "," in limpo:
            limpo = limpo.replace(".", "").replace(",", ".")
        elif "," in limpo:
            limpo = limpo.replace(",", ".")
            
        return float(limpo)
    except:
        return 0.0

def format_brl(value):
    """Exibe float como R$ 1.000,00"""
    try:
        if value is None or str(value).strip() == "": return "R$ 0,00"
        val_float = float(value)
        return f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(value)

# --- FUNÇÃO DE LOGIN ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["passwords"]["acesso_loja"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.markdown("""
        <style>
        .stTextInput > label {color: #5C3A3B !important;}
        .stTextInput input {background-color: #FFFFFF !important; color: #000000 !important;}
        </style>
        """, unsafe_allow_html=True)
    
    st.title("🔒 Acesso Restrito - FL Boutique")
    st.text_input("Digite a senha de acesso:", type="password", on_change=password_entered, key="password")
    
    if "password_correct" in st.session_state:
        st.error("😕 Senha incorreta.")
    return False

if not check_password():
    st.stop()

# --- ESTILIZAÇÃO CSS (VERSÃO COMPLETA/SEGURA) ---
st.markdown("""
    <style>
    /* 1. FUNDO GERAL CLARO */
    .stApp { background-color: #FDF2F4 !important; }
    
    /* 2. TEXTOS E FONTES */
    h1, h2, h3, h4, h5, h6, p, span, label, li, .stMarkdown, .stText, th, td, .stMetricLabel { 
        color: #5C3A3B !important; 
    }
    
    /* 3. MENU LATERAL (Sidebar) */
    section[data-testid="stSidebar"] {
        background-color: #FFF0F5 !important;
        color: #5C3A3B !important;
    }
    div[role="radiogroup"] label { color: #5C3A3B !important; }
    
    /* 4. INPUTS E CAMPOS (Forçando Branco Puro para iPhone) */
    .stTextInput input, .stNumberInput input, .stDateInput input {
        background-color: #FFFFFF !important; 
        color: #000000 !important; 
        border-color: #E69496 !important;
        caret-color: #000000 !important;
    }
    
    /* 5. SELECTBOX / DROPDOWN */
    div[data-baseweb="select"] > div { 
        background-color: #FFFFFF !important; 
        color: #000000 !important; 
        border-color: #E69496 !important; 
    }
    div[data-baseweb="select"] span { color: #000000 !important; }
    div[data-baseweb="select"] svg { fill: #5C3A3B !important; }
    
    /* Popover/Lista Suspensa (Correção Fundo Preto) */
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

    /* 6. BOTÕES */
    .stButton > button { 
        background-color: #E69496 !important; 
        color: white !important; 
        border: none; font-weight: bold; 
    }
    .stButton > button:hover { background-color: #D4787A !important; }
    
    /* 7. TABELA */
    [data-testid="stDataFrame"] { background-color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

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

def gerar_lancamentos(total, parcelas, forma, cli, origem):
    lancs = []
    hoje = datetime.now()
    val_parc = round(total/parcelas, 2)
    dif = round(total - (val_parc * parcelas), 2)
    
    for i in range(parcelas):
        venc = hoje if parcelas == 1 else hoje + timedelta(days=30*(i+1))
        val = val_parc + dif if i == parcelas-1 else val_parc
        status = "Pago" if (forma in ["Dinheiro", "Pix"] and parcelas == 1) else "Pendente"
        
        # Salva com PONTO
        val_str = f"{val:.2f}" 
        
        lancs.append([
            str(uuid.uuid4()),
            hoje.strftime("%Y-%m-%d"),
            venc.strftime("%Y-%m-%d"),
            "Venda",
            f"{origem} - {cli} ({i+1}/{parcelas})",
            val_str,
            forma,
            status
        ])
    return lancs

# --- INTERFACE ---
c1, c2 = st.columns([1, 4])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png", width=80)
    else: st.write("👜")
with c2:
    st.title("FL Boutique")
    st.caption("Sistema de Gestão")

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
            # ESTOQUE
            custo_total = 0
            for x in df_prod[df_prod['status']=='Disponível']['preco_custo']:
                custo_total += converter_input_para_float(x)
            
            # FINANCEIRO
            receber = 0
            caixa = 0
            
            for idx, row in df_fin.iterrows():
                val = converter_input_para_float(row['valor'])
                
                # A Receber (Apenas Vendas Pendentes)
                if row['tipo'] == 'Venda' and row['status_pagamento'] == 'Pendente':
                    receber += val
                
                # Em Caixa (Entradas Pagas - Saídas Pagas)
                if row['status_pagamento'] == 'Pago':
                    if row['tipo'] in ['Venda', 'Entrada']: # Dinheiro entrando
                        caixa += val
                    elif row['tipo'] == 'Despesa': # Dinheiro saindo
                        caixa -= val

            c1, c2, c3 = st.columns(3)
            c1.metric("Estoque (Custo)", format_brl(custo_total))
            c2.metric("A Receber", format_brl(receber))
            c3.metric("Caixa Atual", format_brl(caixa))
            
        except Exception as e: st.warning(f"Erro cálculo: {e}")

elif menu == "Venda Direta":
    st.header("🛒 Nova Venda")
    df_cli = load_data("Clientes")
    df_prod = load_data("Produtos")
    
    if not df_cli.empty and not df_prod.empty:
        cli = st.selectbox("Cliente", df_cli['nome'].unique())
        disp = df_prod[df_prod['status']=='Disponível']
        
        p_map = {}
        for i, row in disp.iterrows():
            val_float = converter_input_para_float(row['preco_venda'])
            lbl = f"{row['nome']} - {row['tamanho']} ({format_brl(val_float)})"
            p_map[lbl] = {'id': row['id'], 'val': val_float}
            
        sels = st.multiselect("Produtos", list(p_map.keys()))
        subtotal = sum([p_map[x]['val'] for x in sels])
        
        st.divider()
        st.markdown(f"#### Subtotal: {format_brl(subtotal)}")
        
        # --- LÓGICA DE DESCONTO INTELIGENTE CORRIGIDA ---
        if 'venda_subtotal' not in st.session_state or st.session_state.venda_subtotal != subtotal:
            st.session_state.venda_subtotal = float(subtotal)
            st.session_state.desc_pct = 0.0
            st.session_state.val_final = float(subtotal)

        # Callbacks
        def update_from_pct():
            pct = st.session_state.key_pct
            st.session_state.desc_pct = pct
            if st.session_state.venda_subtotal > 0:
                st.session_state.val_final = st.session_state.venda_subtotal * (1 - pct/100)

        def update_from_val():
            val = st.session_state.key_val
            st.session_state.val_final = val
            if st.session_state.venda_subtotal > 0:
                st.session_state.desc_pct = ((st.session_state.venda_subtotal - val) / st.session_state.venda_subtotal) * 100

        c_desc_pct, c_val_final = st.columns(2)
        with c_desc_pct:
            # FIX: Convertendo values para float explicitamente para evitar MixedNumericTypesError
            st.number_input(
                "Desconto (%)", 
                min_value=0.0, 
                max_value=100.0, 
                step=1.0, 
                key="key_pct", 
                on_change=update_from_pct, 
                value=float(st.session_state.desc_pct)
            )
        with c_val_final:
            st.number_input(
                "Valor Final (R$)", 
                min_value=0.0, 
                step=0.01, # Step decimal para valor monetário
                key="key_val", 
                on_change=update_from_val, 
                value=float(st.session_state.val_final),
                format="%.2f"
            )
            
        final = st.session_state.val_final
        # ----------------------------------------

        st.divider()
        c1, c2 = st.columns(2)
        with c1: forma = st.selectbox("Pagamento", ["Pix", "Dinheiro", "Cartão Crédito", "Cartão Débito"])
        with c2: parc = st.number_input("Parcelas", 1, 12, 1)
        
        if st.button("Finalizar Venda"):
            if final > 0:
                for x in sels: update_product_status(p_map[x]['id'], "Vendido")
                for l in gerar_lancamentos(final, parc, forma, cli, "Venda Direta"): append_data("Financeiro", l)
                st.success("Venda Realizada!")
                st.balloons()
                # Limpa estado
                st.session_state.venda_subtotal = 0.0
                st.session_state.val_final = 0.0
                st.session_state.desc_pct = 0.0
                st.rerun()
            else: st.warning("Valor inválido")

elif menu == "Produtos":
    st.header("👗 Produtos")
    t1, t2, t3 = st.tabs(["Cadastrar", "Editar", "Excluir"])
    
    with t1:
        st.info("💡 Digite o valor normalmente (Ex: 85,90).")
        with st.form("add"):
            nome = st.text_input("Nome")
            tam = st.selectbox("Tamanho", ["PP","P","M","G","GG","Único"])
            custo_txt = st.text_input("Custo (R$)", value="0,00")
            venda_txt = st.text_input("Venda (R$)", value="0,00")
            
            if st.form_submit_button("Salvar"):
                c_float = converter_input_para_float(custo_txt)
                v_float = converter_input_para_float(venda_txt)
                
                # Salva com PONTO
                c_save = f"{c_float:.2f}"
                v_save = f"{v_float:.2f}"
                
                append_data("Produtos", [str(uuid.uuid4()), nome, tam, c_save, v_save, "Disponível"])
                st.success("Produto Salvo!")
                st.rerun()

    df = load_data("Produtos")
    
    if not df.empty:
        df_show = df.drop(columns=['id'], errors='ignore').copy()
        if 'preco_custo' in df_show.columns:
            df_show['preco_custo'] = df_show['preco_custo'].apply(lambda x: format_brl(converter_input_para_float(x)))
        if 'preco_venda' in df_show.columns:
            df_show['preco_venda'] = df_show['preco_venda'].apply(lambda x: format_brl(converter_input_para_float(x)))
        st.dataframe(df_show, use_container_width=True)
        
    with t2:
        if not df.empty:
            p_opts = {f"{row['nome']} - {row['tamanho']}": row['id'] for i, row in df.iterrows()}
            sel = st.selectbox("Editar qual?", list(p_opts.keys()))
            row = df[df['id']==p_opts[sel]].iloc[0]
            with st.form("edit"):
                n_nome = st.text_input("Nome", value=row['nome'])
                n_tam = st.selectbox("Tamanho", ["PP","P","M","G","GG","Único"], index=["PP","P","M","G","GG","Único"].index(row['tamanho']) if row['tamanho'] in ["PP","P","M","G","GG","Único"] else 0)
                
                val_c_atual = format_brl(converter_input_para_float(row['preco_custo'])).replace("R$ ","")
                val_v_atual = format_brl(converter_input_para_float(row['preco_venda'])).replace("R$ ","")
                
                n_custo = st.text_input("Custo", value=val_c_atual)
                n_venda = st.text_input("Venda", value=val_v_atual)
                
                if st.form_submit_button("Atualizar"):
                    cf = f"{converter_input_para_float(n_custo):.2f}"
                    vf = f"{converter_input_para_float(n_venda):.2f}"
                    update_data("Produtos", p_opts[sel], {2:n_nome, 3:n_tam, 4:cf, 5:vf})
                    st.success("Atualizado!")
                    st.rerun()

    with t3:
        if not df.empty:
            sel_del = st.selectbox("Excluir qual?", list(p_opts.keys()), key='del_p')
            if st.button("Confirmar Exclusão"):
                delete_data("Produtos", p_opts[sel_del])
                st.success("Excluído!")
                st.rerun()

elif menu == "Clientes":
    st.header("👥 Clientes")
    t1, t2, t3 = st.tabs(["Cadastrar", "Editar", "Excluir"])
    with t1:
        with st.form("c_add"):
            nom = st.text_input("Nome")
            zap = st.text_input("WhatsApp")
            end = st.text_input("Endereço")
            if st.form_submit_button("Salvar"):
                append_data("Clientes", [str(uuid.uuid4()), nom, zap, end])
                st.success("Salvo!")
                st.rerun()
    
    df = load_data("Clientes")
    if not df.empty: st.dataframe(df.drop(columns=['id'], errors='ignore'), use_container_width=True)
    
    with t2:
        if not df.empty:
            c_opts = {row['nome']: row['id'] for i, row in df.iterrows()}
            sel = st.selectbox("Editar", list(c_opts.keys()))
            row = df[df['id']==c_opts[sel]].iloc[0]
            with st.form("c_edit"):
                nn = st.text_input("Nome", row['nome'])
                nz = st.text_input("Whats", row['whatsapp'])
                ne = st.text_input("End", row['endereco'])
                if st.form_submit_button("Atualizar"):
                    update_data("Clientes", c_opts[sel], {2:nn, 3:nz, 4:ne})
                    st.success("Ok!")
                    st.rerun()
    with t3:
        if not df.empty:
            sel_d = st.selectbox("Excluir", list(c_opts.keys()), key='del_c')
            if st.button("Apagar Cliente"):
                delete_data("Clientes", c_opts[sel_d])
                st.success("Apagado!")
                st.rerun()

elif menu == "Controle de Malas":
    st.header("👜 Malas")
    t1, t2, t3 = st.tabs(["Enviar", "Retorno", "Cancelar"])
    df_c = load_data("Clientes")
    df_p = load_data("Produtos")
    
    with t1:
        if not df_c.empty and not df_p.empty:
            with st.form("nm"):
                cli = st.selectbox("Cliente", df_c['nome'].unique())
                disp = df_p[df_p['status']=='Disponível']
                pm = {f"{r['nome']} {r['tamanho']}": r['id'] for i,r in disp.iterrows()}
                sels = st.multiselect("Peças", list(pm.keys()))
                if st.form_submit_button("Enviar"):
                    ids = ",".join([pm[x] for x in sels])
                    cid = df_c[df_c['nome']==cli]['id'].values[0]
                    append_data("Malas", [str(uuid.uuid4()), cid, cli, datetime.now().strftime("%Y-%m-%d"), ids, "Aberta"])
                    for x in sels: update_product_status(pm[x], "Em Mala")
                    st.success("Enviado!")
                    st.rerun()

    with t2:
        df_m = load_data("Malas")
        if not df_m.empty and 'status' in df_m.columns:
            abertas = df_m[df_m['status']=='Aberta']
            if not abertas.empty:
                m_opts = {f"{r['nome_cliente']} ({r['data_envio']})": r['id'] for i,r in abertas.iterrows()}
                sel = st.selectbox("Mala", list(m_opts.keys()))
                row = abertas[abertas['id']==m_opts[sel]].iloc[0]
                l_ids = str(row['lista_ids_produtos']).split(',')
                
                st.write(f"Cliente: {row['nome_cliente']}")
                with st.form("ret"):
                    devs = {}
                    for pid in l_ids:
                        pi = df_p[df_p['id']==pid]
                        if not pi.empty:
                            val_fmt = format_brl(converter_input_para_float(pi['preco_venda'].values[0]))
                            lbl = f"{pi['nome'].values[0]} ({val_fmt})"
                            devs[pid] = st.checkbox(f"DEVOLVEU: {lbl}", True, key=pid)
                    
                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1: fp = st.selectbox("Pagamento", ["Pix","Dinheiro","Cartão"])
                    with c2: pa = st.number_input("Parcelas", 1,12,1)
                    
                    if st.form_submit_button("Processar"):
                        tot = 0
                        for pid, dev in devs.items():
                            if dev: update_product_status(pid, "Disponível")
                            else:
                                update_product_status(pid, "Vendido")
                                val = converter_input_para_float(df_p[df_p['id']==pid]['preco_venda'].values[0])
                                tot += val
                        if tot > 0:
                            for l in gerar_lancamentos(tot, pa, fp, row['nome_cliente'], "Mala"): append_data("Financeiro", l)
                        
                        update_data("Malas", m_opts[sel], {6: "Finalizada"})
                        st.success("Concluído!")
                        st.rerun()

    with t3:
        if not df_m.empty:
             del_m = st.selectbox("Excluir Mala", list(m_opts.keys()) if 'm_opts' in locals() else [])
             if st.button("Cancelar Mala"):
                 mid = m_opts[del_m]
                 pids = str(df_m[df_m['id']==mid]['lista_ids_produtos'].values[0]).split(',')
                 for p in pids: update_product_status(p, "Disponível")
                 delete_data("Malas", mid)
                 st.success("Cancelada e produtos devolvidos!")
                 st.rerun()

elif menu == "Financeiro":
    st.header("💰 Finanças")
    df = load_data("Financeiro")
    t1, t2, t3, t4 = st.tabs(["Extrato", "Receber", "Novo Lançamento", "Excluir"])
    
    with t1:
        if not df.empty:
            show = df.drop(columns=['id'], errors='ignore').copy()
            if 'valor' in show.columns:
                show['valor'] = show['valor'].apply(lambda x: format_brl(converter_input_para_float(x)))
            st.dataframe(show, use_container_width=True)

    with t2:
        if not df.empty:
            pen = df[(df['status_pagamento']=='Pendente') & (df['tipo']=='Venda')]
            if not pen.empty:
                opts = {}
                for i, r in pen.iterrows():
                    val_fmt = format_brl(converter_input_para_float(r['valor']))
                    lbl = f"{r['descricao']} - {val_fmt}"
                    opts[lbl] = r['id']
                sel = st.selectbox("Confirmar qual?", list(opts.keys()))
                if st.button("Confirmar Recebimento"):
                    update_finance_status(opts[sel], "Pago")
                    st.success("Recebido!")
                    st.rerun()
            else: st.info("Nada pendente.")
            
    with t3:
        st.subheader("Registrar Despesa ou Entrada")
        with st.form("manual"):
            tipo = st.selectbox("Tipo", ["Despesa", "Entrada"])
            desc = st.text_input("Descrição (Ex: Conta de Luz, Aporte Inicial)")
            val_txt = st.text_input("Valor (R$)", value="0,00")
            data_mov = st.date_input("Data", datetime.now())
            status = st.selectbox("Status", ["Pago", "Pendente"])
            
            if st.form_submit_button("Lançar"):
                val_float = converter_input_para_float(val_txt)
                val_save = f"{val_float:.2f}"
                forma = "Manual"
                
                row = [
                    str(uuid.uuid4()),
                    data_mov.strftime("%Y-%m-%d"),
                    data_mov.strftime("%Y-%m-%d"),
                    tipo,
                    desc,
                    val_save,
                    forma,
                    status
                ]
                append_data("Financeiro", row)
                st.success("Lançamento registrado!")
                st.rerun()

    with t4:
        if not df.empty:
            opts = {f"{r['descricao']} ({r['valor']})": r['id'] for i,r in df.iterrows()}
            sel = st.selectbox("Apagar Lançamento", list(opts.keys()))
            if st.button("Apagar"):
                delete_data("Financeiro", opts[sel])
                st.success("Apagado!")
                st.rerun()