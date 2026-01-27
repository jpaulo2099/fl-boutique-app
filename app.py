import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import uuid
from datetime import datetime, timedelta
import os
import time
# import urllib.parse  <-- [ESTRATÉGIA UX] Comentado para futuro

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="FL Boutique - Gestão", layout="wide")

# --- FUNÇÕES DE UTILIDADE ---
def converter_input_para_float(valor_str):
    """Converte '1.200,50' ou '85,90' para float python."""
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
    """Exibe float como R$ 1.000,00"""
    try:
        if value is None or str(value).strip() == "": return "R$ 0,00"
        val_float = float(value)
        return f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(value)

# [ESTRATÉGIA UX] Função comentada até termos os telefones dos clientes
# def gerar_link_whatsapp(telefone, mensagem):
#     tel_limpo = "".join(filter(str.isdigit, str(telefone)))
#     if not tel_limpo.startswith("55") and len(tel_limpo) >= 10:
#         tel_limpo = "55" + tel_limpo
#     msg_codificada = urllib.parse.quote(mensagem)
#     return f"https://wa.me/{tel_limpo}?text={msg_codificada}"

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
    """Atualização simples (um a um)"""
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
    """
    Recebe {pid: novo_status}. Faz 1 Leitura para evitar erro 429.
    """
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Produtos")
            all_records = ws.get_all_records()
            id_map = {row['id']: i + 2 for i, row in enumerate(all_records)}
            
            headers = ws.row_values(1)
            try:
                col_status = headers.index("status") + 1
            except:
                col_status = 6
            
            for pid, novo_status in updates_dict.items():
                if pid in id_map:
                    row_num = id_map[pid]
                    ws.update_cell(row_num, col_status, novo_status)
                    time.sleep(0.1) 
            
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erro no lote: {e}")
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
            if parcelas == 1:
                venc = hoje
            else:
                venc = hoje + timedelta(days=30*(i+1))
            
        val = val_parc + dif if i == parcelas-1 else val_parc
        status = "Pago" if (forma in ["Dinheiro", "Pix"] and parcelas == 1) else "Pendente"
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
    st.caption("Sistema de Gestão v22.0")

# --- LOGIN ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["passwords"]["acesso_loja"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input("Digite a senha de acesso:", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state:
        st.error("😕 Senha incorreta.")
    return False

if not check_password():
    st.stop()

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
            custo_total_estoque = 0
            qtd_produtos = len(prods_disp)
            
            for x in prods_disp['preco_custo']:
                custo_total_estoque += converter_input_para_float(x)
            
            receber = 0
            caixa_bruto = 0
            taxas_cartao = 0
            
            mes_atual = datetime.now().strftime("%Y-%m")
            vendas_no_mes = 0
            valor_vendas_mes = 0
            
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
                        if "cartão" in forma or "credito" in forma or "debito" in forma or "crédito" in forma or "débito" in forma:
                            taxa = val * 0.12
                            taxas_cartao += taxa
                    elif row['tipo'] == 'Despesa':
                        caixa_bruto -= val

            caixa_liquido = caixa_bruto - taxas_cartao
            ticket_medio = valor_vendas_mes / vendas_no_mes if vendas_no_mes > 0 else 0

            st.markdown("### 💸 Financeiro")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Caixa Líquido (Real)", format_brl(caixa_liquido), delta=f"- {format_brl(taxas_cartao)} Taxas")
            c2.metric("A Receber", format_brl(receber))
            c3.metric("Estoque (Custo)", format_brl(custo_total_estoque))
            c4.metric("Taxas Pagas (Cartão)", format_brl(taxas_cartao))

            st.divider()

            st.markdown("### 📊 Operacional (Mês Atual)")
            c5, c6, c7 = st.columns(3)
            c5.metric("Peças Disponíveis", f"{qtd_produtos} un.")
            c6.metric("Vol. Vendas (Lançamentos)", f"{vendas_no_mes}")
            c7.metric("Ticket Médio (Aprox.)", format_brl(ticket_medio))
            
        except Exception as e: st.warning(f"Erro cálculo: {e}")

elif menu == "Venda Direta":
    st.header("🛒 Nova Venda")
    df_cli = load_data("Clientes")
    df_prod = load_data("Produtos")
    
    if not df_cli.empty and not df_prod.empty:
        c_data, c_cli = st.columns([1, 3])
        with c_data:
            data_venda = st.date_input("Data da Venda", datetime.now())
        with c_cli:
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
        
        if 'venda_subtotal' not in st.session_state or st.session_state.venda_subtotal != subtotal:
            st.session_state.venda_subtotal = float(subtotal)
            st.session_state.desc_pct = 0.0
            st.session_state.val_final = float(subtotal)

        def update_val_from_pct():
            pct = st.session_state.key_pct
            new_val = st.session_state.venda_subtotal * (1 - pct / 100)
            st.session_state.key_val = float(f"{new_val:.2f}")

        def update_pct_from_val():
            val = st.session_state.key_val
            base = st.session_state.venda_subtotal
            if base > 0:
                new_pct = ((base - val) / base) * 100
                st.session_state.key_pct = float(f"{new_pct:.1f}")
            else:
                st.session_state.key_pct = 0.0
        
        st.session_state.venda_subtotal = float(subtotal)

        c_desc_pct, c_val_final = st.columns(2)
        with c_desc_pct:
            st.number_input("Desconto (%)", 0.0, 100.0, step=1.0, key="key_pct", on_change=update_val_from_pct)
        with c_val_final:
            st.number_input("Valor Final (R$)", 0.0, step=0.01, key="key_val", on_change=update_pct_from_val, format="%.2f")
            
        final = st.session_state.key_val

        st.divider()
        c1, c2 = st.columns(2)
        with c1: forma = st.selectbox("Pagamento", ["Pix", "Dinheiro", "Cartão Crédito", "Cartão Débito"])
        with c2: parc = st.number_input("Parcelas", 1, 12, 1)
        
        datas_escolhidas = []
        with st.expander("📅 Personalizar Datas de Pagamento", expanded=False):
            st.caption("Datas calculadas a partir da Data da Venda.")
            cols = st.columns(min(parc, 4))
            for i in range(parc):
                if parc == 1:
                    padrao = data_venda
                else:
                    padrao = data_venda + timedelta(days=30*(i+1))
                d = cols[i % 4].date_input(f"Parcela {i+1}", value=padrao, key=f"date_vd_{i}")
                datas_escolhidas.append(d)
        
        if st.button("Finalizar Venda"):
            if final > 0:
                updates = {p_map[x]['id']: "Vendido" for x in sels}
                update_product_status_batch(updates)
                
                for l in gerar_lancamentos(final, parc, forma, cli, "Venda Direta", data_base=data_venda, datas_customizadas=datas_escolhidas): 
                    append_data("Financeiro", l)
                
                st.success("Venda Realizada!")
                
                # [ESTRATÉGIA UX] WhatsApp Comentado
                # txt = f"*FL BOUTIQUE* 🛍️\nObrigada pela compra, *{cli}*!\n\nItens:\n" + "\n".join([f"- {x}" for x in sels]) + f"\n\nTotal: {format_brl(final)}\nData: {data_venda.strftime('%d/%m/%Y')}"
                # st.link_button("📲 Enviar Comprovante", gerar_link_whatsapp("", txt))
                
                st.session_state.venda_subtotal = 0.0
                st.session_state.key_pct = 0.0
                st.session_state.key_val = 0.0
                time.sleep(2)
                st.rerun()
            else: st.warning("Valor inválido")

elif menu == "Produtos":
    st.header("👗 Produtos")
    t1, t2, t3, t4, t5 = st.tabs(["🆕 Novo Cadastro", "📦 Reposição (Add Qtd)", "📊 Visão de Estoque", "✏️ Editar", "🗑️ Excluir"])
    
    with t1:
        st.info("💡 Dica: Digite o Custo e aperte 'Enter' para ver a Sugestão.")
        if "prod_nome" not in st.session_state: st.session_state.prod_nome = ""
        if "prod_custo" not in st.session_state: st.session_state.prod_custo = "0,00"
        if "prod_venda" not in st.session_state: st.session_state.prod_venda = "0,00"

        nome = st.text_input("Nome", key="prod_nome")
        tam = st.selectbox("Tamanho", ["PP","P","M","G","GG","Único"], key="prod_tam")
        custo_txt = st.text_input("Custo da Peça (R$)", key="prod_custo")
        
        sugestao_val = 0.0
        if custo_txt and custo_txt != "0,00":
            c_val = converter_input_para_float(custo_txt)
            if c_val > 0:
                sugestao_val = (c_val + 1.06) * 2 * 1.12
                st.info(f"💰 **Sugestão: {format_brl(sugestao_val)}**")
                if st.button("Usar Preço Sugerido", key="btn_sug_novo"):
                    st.session_state.prod_venda = f"{sugestao_val:.2f}".replace('.', ',')
                    st.rerun()

        venda_txt = st.text_input("Preço de Venda Final (R$)", key="prod_venda")
        qtd_cadastro = st.number_input("Quantidade de Peças", min_value=1, value=1, key="qtd_novo")
        
        if st.button("Salvar Novo Produto"):
            if nome:
                c_float = converter_input_para_float(custo_txt)
                v_float = converter_input_para_float(venda_txt)
                c_save = f"{c_float:.2f}"
                v_save = f"{v_float:.2f}"
                conn = get_connection()
                if conn:
                    ws = conn.worksheet("Produtos")
                    rows = [[str(uuid.uuid4()), nome, tam, c_save, v_save, "Disponível"] for _ in range(qtd_cadastro)]
                    for r in rows: ws.append_row(r)
                    st.cache_data.clear()

                st.success(f"{qtd_cadastro} Produtos Criados!")
                st.session_state.prod_nome = ""
                st.session_state.prod_custo = "0,00"
                st.session_state.prod_venda = "0,00"
                st.rerun()
            else:
                st.warning("Preencha o nome.")

    with t2:
        if not df_prod.empty:
            unique_opts = df_prod[['nome', 'tamanho', 'preco_custo', 'preco_venda']].drop_duplicates(subset=['nome', 'tamanho'])
            opt_map = {f"{row['nome']} - {row['tamanho']}": row for i, row in unique_opts.iterrows()}
            
            sel_repo = st.selectbox("Selecione o Produto", list(opt_map.keys()))
            dados_repo = opt_map[sel_repo]
            
            st.divider()
            c_pre = format_brl(converter_input_para_float(dados_repo['preco_custo'])).replace("R$ ","")
            v_pre = format_brl(converter_input_para_float(dados_repo['preco_venda'])).replace("R$ ","")
            
            c_repo = st.text_input("Custo (R$)", value=c_pre, key="custo_repo")
            v_repo = st.text_input("Venda (R$)", value=v_pre, key="venda_repo")
            q_repo = st.number_input("Quantidade a Adicionar", min_value=1, value=1, key="qtd_repo")
            
            if st.button("Adicionar ao Estoque"):
                c_float = converter_input_para_float(c_repo)
                v_float = converter_input_para_float(v_repo)
                c_save = f"{c_float:.2f}"
                v_save = f"{v_float:.2f}"
                conn = get_connection()
                if conn:
                    ws = conn.worksheet("Produtos")
                    rows = [[str(uuid.uuid4()), dados_repo['nome'], dados_repo['tamanho'], c_save, v_save, "Disponível"] for _ in range(q_repo)]
                    for r in rows: ws.append_row(r)
                    st.cache_data.clear()
                st.success(f"Adicionado {q_repo} unidades!")
                st.rerun()

    with t3:
        st.subheader("📦 Visão Consolidada")
        if not df_prod.empty:
            estoque_real = df_prod[df_prod['status'] == 'Disponível']
            if not estoque_real.empty:
                resumo = estoque_real.groupby(['nome', 'tamanho']).size().reset_index(name='Quantidade')
                st.dataframe(resumo, use_container_width=True)
            else:
                st.info("Sem estoque disponível.")

    with t4:
        if not df_prod.empty:
            p_opts = {f"{row['nome']} - {row['tamanho']}": row['id'] for i, row in df_prod.iterrows()}
            sel = st.selectbox("Editar qual?", list(p_opts.keys()))
            row = df_prod[df_prod['id']==p_opts[sel]].iloc[0]
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

    with t5:
        if not df_prod.empty:
            sel_del = st.selectbox("Excluir qual?", list(p_opts.keys()), key='del_p')
            if st.button("Confirmar Exclusão"):
                delete_data("Produtos", p_opts[sel_del])
                st.success("Excluído!")
                st.rerun()
    
    st.divider()
    if not df_prod.empty:
        df_show = df_prod.drop(columns=['id'], errors='ignore').copy()
        if 'preco_custo' in df_show.columns:
            df_show['preco_custo'] = df_show['preco_custo'].apply(lambda x: format_brl(converter_input_para_float(x)))
        if 'preco_venda' in df_show.columns:
            df_show['preco_venda'] = df_show['preco_venda'].apply(lambda x: format_brl(converter_input_para_float(x)))
        st.dataframe(df_show, use_container_width=True)

elif menu == "Clientes":
    st.header("👥 Clientes")
    t1, t2, t3 = st.tabs(["Cadastrar", "Editar", "Excluir"])
    df_cli = load_data("Clientes")
    with t1:
        with st.form("c_add"):
            nom = st.text_input("Nome")
            zap = st.text_input("WhatsApp")
            end = st.text_input("Endereço")
            if st.form_submit_button("Salvar"):
                append_data("Clientes", [str(uuid.uuid4()), nom, zap, end])
                st.success("Salvo!")
                st.rerun()
    with t2:
        if not df_cli.empty:
            c_opts = {row['nome']: row['id'] for i, row in df_cli.iterrows()}
            sel = st.selectbox("Editar", list(c_opts.keys()))
            row = df_cli[df_cli['id']==c_opts[sel]].iloc[0]
            with st.form("c_edit"):
                nn = st.text_input("Nome", row['nome'])
                nz = st.text_input("Whats", row['whatsapp'])
                ne = st.text_input("End", row['endereco'])
                if st.form_submit_button("Atualizar"):
                    update_data("Clientes", c_opts[sel], {2:nn, 3:nz, 4:ne})
                    st.success("Ok!")
                    st.rerun()
    with t3:
        if not df_cli.empty:
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
                
                # NOVO: Campo Previsão de Retorno
                data_prevista = st.date_input("Previsão de Retorno", datetime.now() + timedelta(days=3))
                
                if st.form_submit_button("Enviar"):
                    ids = ",".join([pm[x] for x in sels])
                    cid = df_c[df_c['nome']==cli]['id'].values[0]
                    updates = {pm[x]: "Em Mala" for x in sels}
                    update_product_status_batch(updates)
                    
                    # Salva Data Prevista na Coluna 7 (ou final)
                    append_data("Malas", [str(uuid.uuid4()), cid, cli, datetime.now().strftime("%Y-%m-%d"), ids, "Aberta", data_prevista.strftime("%Y-%m-%d")])
                    st.success("Enviado!")
                    st.rerun()

    with t2:
        df_m = load_data("Malas")
        if not df_m.empty and 'status' in df_m.columns:
            abertas = df_m[df_m['status']=='Aberta']
            if not abertas.empty:
                m_opts = {}
                for i, r in abertas.iterrows():
                    data_prev = r['6'] if '6' in r else (r.values[6] if len(r.values) > 6 else "-") 
                    label = f"{r['nome_cliente']} (Envio: {r['data_envio']})"
                    m_opts[label] = r['id']

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
                        updates = {}
                        tot = 0
                        itens_ficou = []
                        
                        for pid, dev in devs.items():
                            pi_data = df_p[df_p['id']==pid]
                            nome_peca = pi_data['nome'].values[0] if not pi_data.empty else "Peça"
                            
                            if dev:
                                updates[pid] = "Disponível"
                            else:
                                updates[pid] = "Vendido"
                                val = converter_input_para_float(pi_data['preco_venda'].values[0])
                                tot += val
                                itens_ficou.append(nome_peca)
                        
                        if update_product_status_batch(updates):
                            if tot > 0:
                                for l in gerar_lancamentos(tot, pa, fp, row['nome_cliente'], "Mala"): 
                                    append_data("Financeiro", l)
                            
                            update_data("Malas", m_opts[sel], {6: "Finalizada"})
                            
                            st.success("Concluído!")
                            
                            # [ESTRATÉGIA UX] WhatsApp Comentado
                            # txt = f"*FL BOUTIQUE* 👜\nOlá *{row['nome_cliente']}*! Fechamento da sua malinha:\n\nVocê ficou com:\n" + "\n".join([f"- {x}" for x in itens_ficou]) + f"\n\nTotal: {format_brl(tot)}"
                            # st.link_button("📲 Enviar Resumo WhatsApp", gerar_link_whatsapp("", txt))
                            
                            time.sleep(2)
                            # st.rerun()

    with t3:
        if not df_m.empty:
             del_m = st.selectbox("Excluir Mala", list(m_opts.keys()) if 'm_opts' in locals() else [])
             if st.button("Cancelar Mala"):
                 mid = m_opts[del_m]
                 pids = str(df_m[df_m['id']==mid]['lista_ids_produtos'].values[0]).split(',')
                 updates = {p: "Disponível" for p in pids}
                 update_product_status_batch(updates)
                 delete_data("Malas", mid)
                 st.success("Cancelada e produtos devolvidos!")
                 st.rerun()

elif menu == "Financeiro":
    st.header("💰 Finanças")
    df_fin = load_data("Financeiro")
    t1, t2, t3, t4 = st.tabs(["Extrato", "Receber", "Novo Lançamento", "Excluir"])
    
    with t1:
        if not df_fin.empty:
            show = df_fin.drop(columns=['id'], errors='ignore').copy()
            if 'valor' in show.columns:
                show['valor'] = show['valor'].apply(lambda x: format_brl(converter_input_para_float(x)))
            st.dataframe(show, use_container_width=True)

    with t2:
        if not df_fin.empty:
            pen = df_fin[(df_fin['status_pagamento']=='Pendente') & (df_fin['tipo']=='Venda')]
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
        if not df_fin.empty:
            opts = {f"{r['descricao']} ({r['valor']})": r['id'] for i,r in df_fin.iterrows()}
            sel = st.selectbox("Apagar Lançamento", list(opts.keys()))
            if st.button("Apagar"):
                delete_data("Financeiro", opts[sel])
                st.success("Apagado!")
                st.rerun()