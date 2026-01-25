import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import uuid
from datetime import datetime, timedelta
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="FL Boutique - Gestão", layout="wide")

# --- FUNÇÕES DE FORMATAÇÃO E CONVERSÃO (CORAÇÃO DO SISTEMA) ---
def format_brl(value):
    """Visualização: Transforma 1250.50 em R$ 1.250,50"""
    try:
        if value is None or value == "": return "R$ 0,00"
        val_float = float(value)
        return f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def parse_brl(value_str):
    """
    Entrada: Recebe string "1.250,00" ou "85,90" ou float 85.9
    Saída: Retorna float 1250.0 e 85.9
    """
    if isinstance(value_str, (int, float)):
        return float(value_str)
    
    if not isinstance(value_str, str):
        return 0.0
        
    try:
        # Limpa R$ e espaços
        clean_str = value_str.replace("R$", "").strip()
        # Remove separador de milhar (.) e troca decimal (,) por ponto (.)
        # Ex: "1.250,00" -> "1250,00" -> "1250.00"
        clean_str = clean_str.replace(".", "").replace(",", ".")
        return float(clean_str)
    except:
        return 0.0

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

# --- ESTILIZAÇÃO CSS (VISUAL FINAL) ---
st.markdown("""
    <style>
    /* 1. FUNDO GERAL */
    .stApp { background-color: #FDF2F4 !important; }

    /* 2. TEXTOS */
    h1, h2, h3, h4, h5, h6, p, span, label, li, .stMarkdown, .stText, th, td {
        color: #5C3A3B !important;
    }

    /* 3. INPUTS E CAMPOS DE TEXTO (BRANCO) */
    .stTextInput input, .stNumberInput input, .stDateInput input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #E69496 !important;
    }

    /* 4. SELECTBOX E DROPDOWN (BRANCO E PRETO) */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #E69496 !important;
    }
    div[data-baseweb="select"] span { color: #000000 !important; }
    div[data-baseweb="select"] svg { fill: #5C3A3B !important; }
    
    /* Menu Suspenso (Lista de Opções) */
    ul[data-baseweb="menu"] { background-color: #FFFFFF !important; }
    li[data-baseweb="option"] { color: #000000 !important; background-color: #FFFFFF !important; }
    div[data-baseweb="popover"], div[data-baseweb="popover"] > div { background-color: #FFFFFF !important; }

    /* 5. MENU LATERAL */
    [data-testid="stSidebar"] { background-color: #FFF0F5 !important; }
    [data-testid="stSidebar"] * { color: #5C3A3B !important; }

    /* 6. BOTÕES */
    .stButton > button {
        background-color: #E69496 !important;
        color: white !important;
        border-radius: 10px;
        border: none;
        font-weight: bold;
    }
    .stButton > button:hover { background-color: #D4787A !important; color: white !important; }

    /* 7. TABELAS */
    div[data-testid="stDataFrame"] { background-color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
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

# --- FUNÇÕES DE CRUD ---
def load_data(sheet_name):
    conn = get_connection()
    if conn:
        try:
            worksheet = conn.worksheet(sheet_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"Erro ao ler '{sheet_name}': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def append_data(sheet_name, row_data):
    conn = get_connection()
    if conn:
        try:
            worksheet = conn.worksheet(sheet_name)
            worksheet.append_row(row_data)
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

def update_data(sheet_name, id_value, updated_row_dict):
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet(sheet_name)
            cell = ws.find(id_value)
            if cell:
                for col_idx, val in updated_row_dict.items():
                    ws.update_cell(cell.row, col_idx, val)
                st.cache_data.clear()
                return True
        except Exception as e:
            st.error(f"Erro ao atualizar: {e}")
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
        except Exception as e:
            st.error(f"Erro ao excluir: {e}")
    return False

def update_product_status(product_id, new_status):
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Produtos")
            cell = ws.find(product_id)
            if cell:
                headers = ws.row_values(1)
                col_index = headers.index("status") + 1
                ws.update_cell(cell.row, col_index, new_status)
                st.cache_data.clear()
        except Exception:
            pass

def update_finance_status(finance_id, new_status):
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Financeiro")
            cell = ws.find(finance_id)
            if cell:
                headers = ws.row_values(1)
                col_index = headers.index("status_pagamento") + 1
                ws.update_cell(cell.row, col_index, new_status)
                st.cache_data.clear()
                return True
        except Exception as e:
            st.error(f"Erro ao atualizar financeiro: {e}")
    return False

# --- LÓGICA DE PARCELAMENTO ---
def gerar_lancamentos_financeiros(total, parcelas, forma_pag, cliente_nome, origem):
    lancamentos = []
    data_hoje = datetime.now()
    valor_parcela = round(total / parcelas, 2)
    diferenca = round(total - (valor_parcela * parcelas), 2)
    
    for i in range(parcelas):
        if parcelas == 1:
            data_venc = data_hoje
        else:
            dias_a_somar = 30 * (i + 1)
            data_venc = data_hoje + timedelta(days=dias_a_somar)
            
        valor_final = valor_parcela
        if i == parcelas - 1:
            valor_final += diferenca
            
        status = "Pago" if (forma_pag in ["Dinheiro", "Pix"] and parcelas == 1) else "Pendente"
        desc = f"{origem} - {cliente_nome} ({i+1}/{parcelas})"
        
        # Salva o valor como string formatada PT-BR no banco para facilitar leitura humana
        # O parse_brl cuida da conversão na volta
        row = [
            str(uuid.uuid4()),
            data_hoje.strftime("%Y-%m-%d"),
            data_venc.strftime("%Y-%m-%d"),
            "Venda",
            desc,
            f"{valor_final:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), # Salva como "1.250,50"
            forma_pag,
            status
        ]
        lancamentos.append(row)
    return lancamentos

# --- CALLBACKS PARA CÁLCULO DE DESCONTO ---
def calc_final_from_desc():
    try:
        base = st.session_state.get('base_price', 0.0)
        # Parseando o input de texto para float se necessário, mas aqui são number_inputs
        desc = st.session_state.get('desc_input', 0.0)
        st.session_state.final_value = round(base * (1 - desc / 100), 2)
    except: pass

# --- INTERFACE ---

# Logo
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=100)
    else:
        st.write("👜")
with col_titulo:
    st.title("FL Boutique")
    st.caption("Sistema de Gestão Integrado")

# Menu
if st.sidebar.button("Sair / Logout"):
    st.session_state["password_correct"] = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["Dashboard", "Venda Direta", "Controle de Malas", "Produtos", "Clientes", "Financeiro"])

if menu == "Dashboard":
    st.header("Visão Geral")
    df_fin = load_data("Financeiro")
    df_prod = load_data("Produtos")
    
    if not df_fin.empty and not df_prod.empty:
        try:
            # Aplica o parse_brl para garantir que 8.500,00 vire 8500.00 e 85,00 vire 85.00
            df_prod['preco_custo'] = df_prod['preco_custo'].apply(parse_brl)
            df_fin['valor'] = df_fin['valor'].apply(parse_brl)
            
            total_estoque = df_prod[df_prod['status'] == 'Disponível']['preco_custo'].sum()
            receita_pendente = df_fin[(df_fin['tipo'] == 'Venda') & (df_fin['status_pagamento'] == 'Pendente')]['valor'].sum()
            caixa_real = df_fin[(df_fin['status_pagamento'] == 'Pago')]['valor'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Estoque (Custo)", format_brl(total_estoque))
            c2.metric("A Receber", format_brl(receita_pendente))
            c3.metric("Em Caixa", format_brl(caixa_real))
        except Exception as e:
            st.warning(f"Erro ao calcular métricas: {e}")
    else:
        st.info("Sem dados suficientes.")

elif menu == "Venda Direta":
    st.header("🛒 Nova Venda")
    df_cli = load_data("Clientes")
    df_prod = load_data("Produtos")
    
    if not df_cli.empty and not df_prod.empty:
        cli_opts = df_cli['nome'].unique()
        cliente = st.selectbox("Cliente", cli_opts)
        
        disp = df_prod[df_prod['status'] == 'Disponível']
        # Mapeamento com Preço formatado
        prod_map = {}
        for i, row in disp.iterrows():
            p_val = parse_brl(row['preco_venda'])
            label = f"{row['nome']} - {row['tamanho']} ({format_brl(p_val)})"
            prod_map[label] = row['id']
        
        selecionados = st.multiselect("Produtos", options=list(prod_map.keys()))
        
        # Subtotal
        subtotal = 0.0
        ids_selecionados = []
        for label in selecionados:
            pid = prod_map[label]
            ids_selecionados.append(pid)
            p_val = parse_brl(disp[disp['id'] == pid]['preco_venda'].values[0])
            subtotal += p_val
        
        st.session_state.base_price = subtotal
        
        # Lógica de Inicialização dos valores de negociação
        if 'last_subtotal' not in st.session_state or st.session_state.last_subtotal != subtotal:
            st.session_state.final_input_str = f"{subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            st.session_state.desc_input = 0.0
            st.session_state.last_subtotal = subtotal

        st.divider()
        st.subheader("Negociação")
        
        col_resumo, col_desconto = st.columns(2)
        with col_resumo:
            st.markdown(f"#### Subtotal: {format_brl(subtotal)}")
        
        with col_desconto:
            # Entrada de texto para permitir vírgula
            val_final_txt = st.text_input("Valor Final (R$)", value=st.session_state.final_input_str)
            
            # Converte o texto digitado para float para cálculos
            try:
                val_final_float = parse_brl(val_final_txt)
            except:
                val_final_float = 0.0
            
            # Calcula o desconto (informativo)
            if subtotal > 0:
                desconto_calc = ((subtotal - val_final_float) / subtotal) * 100
            else:
                desconto_calc = 0.0
            
            st.caption(f"Desconto aplicado: {desconto_calc:.2f}%")

        st.divider()
        st.subheader("Pagamento")
        c1, c2 = st.columns(2)
        with c1:
            forma = st.selectbox("Forma de Pagamento", ["Pix", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"])
        with c2:
            parcelas = st.number_input("Parcelas (1 = À vista)", min_value=1, max_value=12, value=1)
            
        if st.button("✅ Finalizar Venda"):
            if selecionados and val_final_float > 0:
                for pid in ids_selecionados: update_product_status(pid, "Vendido")
                
                lancamentos = gerar_lancamentos_financeiros(val_final_float, parcelas, forma, cliente, "Venda Direta")
                for lanc in lancamentos: append_data("Financeiro", lanc)
                
                st.success(f"Venda de {format_brl(val_final_float)} registrada!")
                st.balloons()
                
                # Reset visual
                st.session_state.final_input_str = "0,00"
            else:
                st.warning("Verifique os produtos e o valor final.")

elif menu == "Controle de Malas":
    st.header("👜 Malas Delivery")
    t1, t2, t3 = st.tabs(["Nova Mala", "Retorno/Baixa", "Cancelar/Excluir"])
    df_cli = load_data("Clientes")
    df_prod = load_data("Produtos")
    
    with t1:
        with st.form("nova_mala"):
            st.subheader("Enviar Mala")
            cli_opts = df_cli['nome'].unique() if not df_cli.empty else []
            cliente = st.selectbox("Cliente", cli_opts)
            disp = df_prod[df_prod['status'] == 'Disponível']
            prod_map = {f"{row['nome']} - {row['tamanho']}": row['id'] for i, row in disp.iterrows()}
            sel_mala = st.multiselect("Produtos", list(prod_map.keys()))
            if st.form_submit_button("🚀 Enviar Mala"):
                if sel_mala:
                    ids = [prod_map[k] for k in sel_mala]
                    ids_str = ",".join(ids)
                    cid = df_cli[df_cli['nome'] == cliente]['id'].values[0]
                    row = [str(uuid.uuid4()), cid, cliente, datetime.now().strftime("%Y-%m-%d"), ids_str, "Aberta"]
                    append_data("Malas", row)
                    for i in ids: update_product_status(i, "Em Mala")
                    st.success("Mala enviada com sucesso!")
    
    with t2:
        st.subheader("Processar Retorno")
        df_malas = load_data("Malas")
        if not df_malas.empty and 'status' in df_malas.columns:
            abertas = df_malas[df_malas['status'] == 'Aberta']
            if abertas.empty:
                st.info("Nenhuma mala aberta.")
            else:
                mala_map = {f"{row['nome_cliente']} (Enviada: {row['data_envio']})": row['id'] for i, row in abertas.iterrows()}
                mala_label = st.selectbox("Selecione a Mala", list(mala_map.keys()))
                mala_id = mala_map[mala_label]
                dados_mala = abertas[abertas['id'] == mala_id].iloc[0]
                lista_ids = str(dados_mala['lista_ids_produtos']).split(",")
                
                st.divider()
                st.write(f"**Cliente:** {dados_mala['nome_cliente']}")
                with st.form("baixa_mala"):
                    st.write("Marque o que a cliente **DEVOLVEU**:")
                    devolvidos = {}
                    for pid in lista_ids:
                        p_info = df_prod[df_prod['id'] == pid]
                        if not p_info.empty:
                            p_val = parse_brl(p_info['preco_venda'].values[0])
                            lbl = f"{p_info['nome'].values[0]} - {p_info['tamanho'].values[0]} ({format_brl(p_val)})"
                            devolvidos[pid] = st.checkbox(f"DEVOLVEU: {lbl}", value=True, key=pid)
                    
                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1: forma = st.selectbox("Forma Pagamento", ["Pix", "Dinheiro", "Cartão Crédito", "Cartão Débito"])
                    with c2: parcelas = st.number_input("Parcelas", 1, 12, 1)
                        
                    if st.form_submit_button("✅ Processar Retorno"):
                        total_venda = 0
                        for pid, devolveu in devolvidos.items():
                            if devolveu: update_product_status(pid, "Disponível")
                            else:
                                update_product_status(pid, "Vendido")
                                price = parse_brl(df_prod[df_prod['id'] == pid]['preco_venda'].values[0])
                                total_venda += price
                        if total_venda > 0:
                            lancs = gerar_lancamentos_financeiros(total_venda, parcelas, forma, dados_mala['nome_cliente'], "Mala Delivery")
                            for l in lancs: append_data("Financeiro", l)
                            st.success(f"Venda de {format_brl(total_venda)} gerada!")
                        
                        conn = get_connection()
                        ws_malas = conn.worksheet("Malas")
                        cell = ws_malas.find(mala_id)
                        headers = ws_malas.row_values(1)
                        ws_malas.update_cell(cell.row, headers.index("status")+1, "Finalizada")
                        st.success("Mala finalizada!")
                        st.rerun()

    with t3:
        st.subheader("🗑️ Excluir Registro de Mala")
        df_malas = load_data("Malas")
        if not df_malas.empty:
            mala_map_del = {f"{row['nome_cliente']} - {row['status']} ({row['data_envio']})": row['id'] for i, row in df_malas.iterrows()}
            sel_del_mala = st.selectbox("Selecione a Mala para Excluir", list(mala_map_del.keys()))
            id_del_mala = mala_map_del[sel_del_mala]
            
            if st.button("Confirmar Exclusão da Mala"):
                dados_del = df_malas[df_malas['id'] == id_del_mala].iloc[0]
                if dados_del['status'] == 'Aberta':
                    lista_ids_del = str(dados_del['lista_ids_produtos']).split(",")
                    for pid in lista_ids_del:
                        update_product_status(pid, "Disponível")
                    st.info("Produtos devolvidos ao estoque.")
                
                delete_data("Malas", id_del_mala)
                st.success("Registro de mala excluído!")
                st.rerun()

elif menu == "Financeiro":
    st.header("💰 Fluxo de Caixa")
    df = load_data("Financeiro")
    
    t_view, t_baixa, t_del = st.tabs(["Extrato", "Receber Pagamentos", "Excluir Lançamento"])
    
    with t_view:
        if not df.empty:
            df_display = df.drop(columns=['id'], errors='ignore').copy()
            if 'valor' in df_display.columns:
                 # Usa o parse_brl e depois formata
                 df_display['valor'] = df_display['valor'].apply(lambda x: format_brl(parse_brl(x)))
            st.dataframe(df_display, use_container_width=True)
            
    with t_baixa:
        st.subheader("Confirmar Recebimento")
        if not df.empty:
            pendentes = df[df['status_pagamento'] == 'Pendente']
            if pendentes.empty:
                st.success("Tudo pago!")
            else:
                p_map = {}
                for i, row in pendentes.iterrows():
                    val_fmt = format_brl(parse_brl(row['valor']))
                    lbl = f"{row['descricao']} | {val_fmt} | Venc: {row['data_vencimento']} | {row['forma_pagamento']}"
                    p_map[lbl] = row['id']
                
                selecionado_lbl = st.selectbox("Selecione o pagamento:", list(p_map.keys()))
                if st.button("✅ Confirmar Recebimento"):
                    id_pag = p_map[selecionado_lbl]
                    if update_finance_status(id_pag, "Pago"):
                        st.success("Confirmado!")
                        st.rerun()

    with t_del:
        st.subheader("🗑️ Excluir Venda/Lançamento")
        if not df.empty:
            fin_map = {}
            for i, row in df.iterrows():
                val_fmt = format_brl(parse_brl(row['valor']))
                lbl = f"{row['data_lancamento']} | {row['descricao']} | {val_fmt} ({row['status_pagamento']})"
                fin_map[lbl] = row['id']
            
            sel_fin_del = st.selectbox("Selecione o lançamento para apagar:", list(fin_map.keys()))
            id_fin_del = fin_map[sel_fin_del]
            
            if st.button("Confirmar Exclusão Financeira"):
                delete_data("Financeiro", id_fin_del)
                st.success("Apagado!")
                st.rerun()

elif menu == "Produtos":
    st.header("👗 Produtos")
    t_cad, t_edit, t_del = st.tabs(["Cadastrar", "Editar", "Excluir"])
    
    with t_cad:
        with st.form("new_prod"):
            nome = st.text_input("Nome")
            tam = st.selectbox("Tamanho", ["PP","P","M","G","GG","Único"])
            # TROCA DE INPUT NUMÉRICO POR TEXTO PARA SUPORTAR VÍRGULA
            custo_txt = st.text_input("Custo (Ex: 85,90)", value="0,00")
            venda_txt = st.text_input("Venda (Ex: 120,00)", value="0,00")
            
            if st.form_submit_button("Salvar"):
                c_float = parse_brl(custo_txt)
                v_float = parse_brl(venda_txt)
                
                # Salva como string formatada para garantir leitura correta depois
                c_str = f"{c_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                v_str = f"{v_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
                append_data("Produtos", [str(uuid.uuid4()), nome, tam, c_str, v_str, "Disponível"])
                st.success("Salvo!")
                st.rerun()
    
    df = load_data("Produtos")
    
    with t_edit:
        if not df.empty:
            prod_map = {f"{row['nome']} - {row['tamanho']}": row['id'] for i, row in df.iterrows()}
            sel_prod = st.selectbox("Selecione para Editar", list(prod_map.keys()))
            id_sel = prod_map[sel_prod]
            dados_atuais = df[df['id'] == id_sel].iloc[0]
            with st.form("edit_prod"):
                n_nome = st.text_input("Nome", value=dados_atuais['nome'])
                n_tam = st.selectbox("Tamanho", ["PP","P","M","G","GG","Único"], index=["PP","P","M","G","GG","Único"].index(dados_atuais['tamanho']) if dados_atuais['tamanho'] in ["PP","P","M","G","GG","Único"] else 0)
                
                # Carrega valor formatado para edição
                custo_atual = parse_brl(dados_atuais['preco_custo'])
                venda_atual = parse_brl(dados_atuais['preco_venda'])
                c_fmt = f"{custo_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                v_fmt = f"{venda_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
                n_custo_txt = st.text_input("Custo", value=c_fmt)
                n_venda_txt = st.text_input("Venda", value=v_fmt)
                
                if st.form_submit_button("Atualizar Produto"):
                    nc = parse_brl(n_custo_txt)
                    nv = parse_brl(n_venda_txt)
                    nc_str = f"{nc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    nv_str = f"{nv:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    
                    update_data("Produtos", id_sel, {2: n_nome, 3: n_tam, 4: nc_str, 5: nv_str})
                    st.success("Atualizado!")
                    st.rerun()

    with t_del:
        if not df.empty:
            sel_del = st.selectbox("Selecione para Excluir", list(prod_map.keys()), key="del_prod_sel")
            id_del = prod_map[sel_del]
            if st.button("🗑️ Excluir Produto Definitivamente"):
                delete_data("Produtos", id_del)
                st.success("Excluído!")
                st.rerun()
    
    st.divider()
    if not df.empty:
        df_show = df.drop(columns=['id'], errors='ignore').copy()
        df_show['preco_custo'] = df_show['preco_custo'].apply(lambda x: format_brl(parse_brl(x)))
        df_show['preco_venda'] = df_show['preco_venda'].apply(lambda x: format_brl(parse_brl(x)))
        st.dataframe(df_show)

elif menu == "Clientes":
    st.header("👥 Clientes")
    t_cad, t_edit, t_del = st.tabs(["Cadastrar", "Editar", "Excluir"])
    
    with t_cad:
        with st.form("new_cli"):
            nome = st.text_input("Nome")
            whats = st.text_input("WhatsApp")
            end = st.text_input("Endereço")
            if st.form_submit_button("Salvar"):
                append_data("Clientes", [str(uuid.uuid4()), nome, whats, end])
                st.success("Salvo!")
                st.rerun()
    
    df = load_data("Clientes")
    
    with t_edit:
        if not df.empty:
            cli_map = {row['nome']: row['id'] for i, row in df.iterrows()}
            sel_cli = st.selectbox("Selecione para Editar", list(cli_map.keys()))
            id_sel = cli_map[sel_cli]
            dados = df[df['id'] == id_sel].iloc[0]
            with st.form("edit_cli"):
                n_nome = st.text_input("Nome", value=dados['nome'])
                n_whats = st.text_input("WhatsApp", value=dados['whatsapp'])
                n_end = st.text_input("Endereço", value=dados['endereco'])
                if st.form_submit_button("Atualizar Cliente"):
                    update_data("Clientes", id_sel, {2: n_nome, 3: n_whats, 4: n_end})
                    st.success("Atualizado!")
                    st.rerun()

    with t_del:
         if not df.empty:
            sel_del_c = st.selectbox("Selecione para Excluir", list(cli_map.keys()), key="del_cli_sel")
            id_del_c = cli_map[sel_del_c]
            if st.button("🗑️ Excluir Cliente"):
                delete_data("Clientes", id_del_c)
                st.success("Excluído!")
                st.rerun()
    
    if not df.empty:
        st.dataframe(df.drop(columns=['id'], errors='ignore'))