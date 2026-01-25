import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import uuid
from datetime import datetime, timedelta
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="FL Boutique - Gestão", layout="wide")

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

    st.markdown("<style>.stTextInput > label {color: #5C3A3B !important;}</style>", unsafe_allow_html=True)
    st.title("🔒 Acesso Restrito - FL Boutique")
    st.text_input("Digite a senha de acesso:", type="password", on_change=password_entered, key="password")
    
    if "password_correct" in st.session_state:
        st.error("😕 Senha incorreta.")
    return False

if not check_password():
    st.stop()

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #FDF2F4; }
    html, body, p, div, span, label, h1, h2, h3, h4, h5, h6, .stMarkdown, .stText, td, th { color: #5C3A3B !important; }
    .stTextInput input, .stNumberInput input, .stSelectbox div, .stMultiSelect div { color: #333333 !important; }
    .stButton>button { background-color: #E69496; color: white !important; border-radius: 10px; border: none; font-weight: bold; }
    .stButton>button:hover { background-color: #D4787A; color: white !important; }
    [data-testid="stSidebar"] { background-color: #FFF0F5; }
    [data-testid="stSidebar"] * { color: #5C3A3B !important; }
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

# --- FUNÇÕES AUXILIARES ---
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
    """Gera linhas para o financeiro considerando parcelamento."""
    lancamentos = []
    data_hoje = datetime.now()
    valor_parcela = round(total / parcelas, 2)
    
    # Ajuste de centavos na última parcela
    diferenca = round(total - (valor_parcela * parcelas), 2)
    
    for i in range(parcelas):
        # Calcula data de vencimento (30 dias para cada parcela a partir de hoje)
        # Se for "Dinheiro" ou "Pix" à vista (1x), vencimento é hoje.
        if parcelas == 1:
            data_venc = data_hoje
        else:
            dias_a_somar = 30 * (i + 1)
            data_venc = data_hoje + timedelta(days=dias_a_somar)
            
        valor_final = valor_parcela
        if i == parcelas - 1: # Última parcela pega a diferença
            valor_final += diferenca
            
        status = "Pago" if (forma_pag in ["Dinheiro", "Pix"] and parcelas == 1) else "Pendente"
        
        desc = f"{origem} - {cliente_nome} ({i+1}/{parcelas})"
        
        # Colunas: id, data_lancamento, data_vencimento, tipo, descricao, valor, forma, status
        row = [
            str(uuid.uuid4()),
            data_hoje.strftime("%Y-%m-%d"),
            data_venc.strftime("%Y-%m-%d"),
            "Venda",
            desc,
            f"{valor_final:.2f}".replace('.', ','), # Salva como string formatada PT-BR para visualização
            forma_pag,
            status
        ]
        lancamentos.append(row)
    return lancamentos

# --- INTERFACE ---

# 1. LOGO DA LOJA
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=100)
    else:
        st.write("👜") # Icone caso não tenha imagem
with col_titulo:
    st.title("FL Boutique")
    st.caption("Sistema de Gestão Integrado")

# 2. MENU
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
            # Limpeza de dados para cálculo (troca vírgula por ponto)
            df_prod['preco_custo'] = df_prod['preco_custo'].astype(str).str.replace(',', '.').astype(float)
            df_fin['valor'] = df_fin['valor'].astype(str).str.replace(',', '.').astype(float)
            
            total_estoque = df_prod[df_prod['status'] == 'Disponível']['preco_custo'].sum()
            receita_pendente = df_fin[(df_fin['tipo'] == 'Venda') & (df_fin['status_pagamento'] == 'Pendente')]['valor'].sum()
            caixa_real = df_fin[(df_fin['status_pagamento'] == 'Pago')]['valor'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Estoque (Custo)", f"R$ {total_estoque:,.2f}")
            c2.metric("A Receber", f"R$ {receita_pendente:,.2f}")
            c3.metric("Em Caixa", f"R$ {caixa_real:,.2f}")
        except Exception as e:
            st.warning(f"Dados insuficientes ou erro de formato: {e}")

elif menu == "Venda Direta":
    st.header("🛒 Nova Venda")
    df_cli = load_data("Clientes")
    df_prod = load_data("Produtos")
    
    if not df_cli.empty and not df_prod.empty:
        with st.form("venda_form"):
            # Ocultando IDs na seleção
            cli_opts = df_cli['nome'].unique()
            cliente = st.selectbox("Cliente", cli_opts)
            
            # Produtos disponíveis
            disp = df_prod[df_prod['status'] == 'Disponível']
            # Cria dicionário para mapear Label -> ID
            prod_map = {f"{row['nome']} - {row['tamanho']} (R$ {row['preco_venda']})": row['id'] for i, row in disp.iterrows()}
            
            selecionados = st.multiselect("Produtos", options=list(prod_map.keys()))
            
            c1, c2 = st.columns(2)
            with c1:
                forma = st.selectbox("Forma de Pagamento", ["Pix", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"])
            with c2:
                parcelas = st.number_input("Parcelas (1 = À vista)", min_value=1, max_value=12, value=1)
                
            submit = st.form_submit_button("✅ Finalizar Venda")
            
            if submit and selecionados:
                # Calcula Total
                total_venda = 0
                ids_selecionados = []
                for label in selecionados:
                    pid = prod_map[label]
                    ids_selecionados.append(pid)
                    # Pega preço
                    preco_str = str(disp[disp['id'] == pid]['preco_venda'].values[0]).replace(',', '.')
                    total_venda += float(preco_str)
                
                # 1. Atualiza Produtos
                for pid in ids_selecionados:
                    update_product_status(pid, "Vendido")
                
                # 2. Gera Financeiro (com parcelas)
                lancamentos = gerar_lancamentos_financeiros(total_venda, parcelas, forma, cliente, "Venda Direta")
                for lanc in lancamentos:
                    append_data("Financeiro", lanc)
                
                st.success(f"Venda de R$ {total_venda:.2f} registrada com sucesso!")
                st.balloons()
                # st.rerun() # Opcional: recarregar a página

elif menu == "Controle de Malas":
    st.header("👜 Malas Delivery")
    t1, t2 = st.tabs(["Nova Mala", "Retorno/Baixa"])
    df_cli = load_data("Clientes")
    df_prod = load_data("Produtos")
    
    with t1:
        with st.form("nova_mala"):
            st.subheader("Enviar Mala")
            cli_opts = df_cli['nome'].unique()
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
                # Selectbox amigável sem ID visível
                mala_map = {f"{row['nome_cliente']} (Enviada: {row['data_envio']})": row['id'] for i, row in abertas.iterrows()}
                mala_label = st.selectbox("Selecione a Mala", list(mala_map.keys()))
                mala_id = mala_map[mala_label]
                
                dados_mala = abertas[abertas['id'] == mala_id].iloc[0]
                lista_ids = str(dados_mala['lista_ids_produtos']).split(",")
                
                st.divider()
                st.write(f"**Cliente:** {dados_mala['nome_cliente']}")
                
                with st.form("baixa_mala"):
                    st.write("Marque o que a cliente **DEVOLVEU** (Não comprou):")
                    devolvidos = {}
                    
                    # Recupera produtos da mala
                    for pid in lista_ids:
                        p_info = df_prod[df_prod['id'] == pid]
                        if not p_info.empty:
                            lbl = f"{p_info['nome'].values[0]} - {p_info['tamanho'].values[0]} (R$ {p_info['preco_venda'].values[0]})"
                            # Checkbox marcado = devolveu
                            devolvidos[pid] = st.checkbox(f"DEVOLVEU: {lbl}", value=True, key=pid)
                    
                    st.divider()
                    st.write("Dados para Pagamento (dos itens vendidos):")
                    c1, c2 = st.columns(2)
                    with c1:
                        forma = st.selectbox("Forma Pagamento", ["Pix", "Dinheiro", "Cartão Crédito", "Cartão Débito"])
                    with c2:
                        parcelas = st.number_input("Parcelas", 1, 12, 1)
                        
                    if st.form_submit_button("✅ Processar Retorno"):
                        total_venda = 0
                        # 1. Atualiza Estoque
                        conn = get_connection()
                        ws_malas = conn.worksheet("Malas")
                        
                        items_vendidos = False
                        for pid, devolveu in devolvidos.items():
                            if devolveu:
                                update_product_status(pid, "Disponível")
                            else:
                                update_product_status(pid, "Vendido")
                                price = str(df_prod[df_prod['id'] == pid]['preco_venda'].values[0]).replace(',', '.')
                                total_venda += float(price)
                                items_vendidos = True
                        
                        # 2. Gera Financeiro
                        if total_venda > 0:
                            lancs = gerar_lancamentos_financeiros(total_venda, parcelas, forma, dados_mala['nome_cliente'], "Mala Delivery")
                            for l in lancs: append_data("Financeiro", l)
                            st.success(f"Venda de R$ {total_venda:.2f} gerada!")
                        else:
                            st.info("Nenhuma peça vendida nesta mala.")

                        # 3. Fecha Mala
                        cell = ws_malas.find(mala_id)
                        headers = ws_malas.row_values(1)
                        ws_malas.update_cell(cell.row, headers.index("status")+1, "Finalizada")
                        
                        st.success("Mala baixada com sucesso!")
                        st.rerun()

elif menu == "Financeiro":
    st.header("💰 Fluxo de Caixa")
    df = load_data("Financeiro")
    
    tab_vis, tab_baixa = st.tabs(["Extrato", "Receber Pagamentos"])
    
    with tab_vis:
        # Mostra tabela sem coluna ID
        if not df.empty:
            st.dataframe(df.drop(columns=['id'], errors='ignore'), use_container_width=True)
        else:
            st.info("Sem lançamentos.")
            
    with tab_baixa:
        st.subheader("Confirmar Recebimento")
        if not df.empty:
            # Filtra apenas pendentes
            pendentes = df[df['status_pagamento'] == 'Pendente']
            
            if pendentes.empty:
                st.success("Tudo pago! Nenhuma pendência.")
            else:
                # Cria labels amigáveis
                # Ex: "Maria - 1/3 - R$ 50,00 - Venc: 2026-02-25"
                p_map = {}
                for i, row in pendentes.iterrows():
                    lbl = f"{row['descricao']} | R$ {row['valor']} | Venc: {row['data_vencimento']} | {row['forma_pagamento']}"
                    p_map[lbl] = row['id']
                
                selecionado_lbl = st.selectbox("Selecione o pagamento para dar baixa:", list(p_map.keys()))
                
                if st.button("✅ Confirmar Recebimento"):
                    id_pag = p_map[selecionado_lbl]
                    if update_finance_status(id_pag, "Pago"):
                        st.success("Pagamento confirmado!")
                        st.rerun()

elif menu == "Produtos":
    st.header("👗 Produtos")
    with st.expander("Cadastrar Novo"):
        with st.form("new_prod"):
            nome = st.text_input("Nome")
            tam = st.selectbox("Tamanho", ["PP","P","M","G","GG","Único"])
            custo = st.number_input("Custo", 0.0)
            venda = st.number_input("Venda", 0.0)
            if st.form_submit_button("Salvar"):
                append_data("Produtos", [str(uuid.uuid4()), nome, tam, custo, venda, "Disponível"])
                st.success("Produto Cadastrado!")
                st.rerun()
    
    df = load_data("Produtos")
    if not df.empty:
        st.dataframe(df.drop(columns=['id'], errors='ignore'))

elif menu == "Clientes":
    st.header("👥 Clientes")
    with st.expander("Cadastrar Novo"):
        with st.form("new_cli"):
            nome = st.text_input("Nome")
            whats = st.text_input("WhatsApp")
            end = st.text_input("Endereço")
            if st.form_submit_button("Salvar"):
                append_data("Clientes", [str(uuid.uuid4()), nome, whats, end])
                st.success("Cliente Salvo!")
                st.rerun()
    
    df = load_data("Clientes")
    if not df.empty:
        st.dataframe(df.drop(columns=['id'], errors='ignore'))