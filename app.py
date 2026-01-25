import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import uuid
from datetime import datetime
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="FL Boutique - Gestão", layout="wide")

# --- FUNÇÃO DE LOGIN (SEGURANÇA SIMPLES) ---
def check_password():
    """Retorna True se o usuário tiver a senha correta."""

    def password_entered():
        """Verifica se a senha inserida bate com a do secrets."""
        if st.session_state["password"] == st.secrets["passwords"]["acesso_loja"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Não armazena a senha
        else:
            st.session_state["password_correct"] = False

    # Se já validou, retorna True
    if st.session_state.get("password_correct", False):
        return True

    # Se não validou, mostra o input
    st.markdown(
        """
        <style>
        /* Estilo específico para a tela de login */
        .stTextInput > label {color: #5C3A3B !important;}
        </style>
        """, unsafe_allow_html=True
    )
    
    st.title("🔒 Acesso Restrito - FL Boutique")
    st.text_input(
        "Digite a senha de acesso:", type="password", on_change=password_entered, key="password"
    )
    
    if "password_correct" in st.session_state:
        st.error("😕 Senha incorreta. Tente novamente.")

    return False

# --- VERIFICAÇÃO DE LOGIN ---
if not check_password():
    st.stop()  # O App para aqui se não estiver logado

# ========================================================
# DAQUI PRA BAIXO É O APP QUE SÓ APARECE APÓS O LOGIN
# ========================================================

# --- ESTILIZAÇÃO CSS (CORRIGINDO MODO ESCURO) ---
st.markdown("""
    <style>
    /* Força o Fundo Rosê */
    .stApp {
        background-color: #FDF2F4;
    }
    
    /* CORREÇÃO DO MODO ESCURO: Força cor do texto para Marrom/Preto em TUDO */
    html, body, p, div, span, label, h1, h2, h3, h4, h5, h6, .stMarkdown, .stText {
        color: #5C3A3B !important; /* Marrom elegante */
    }
    
    /* Inputs e Selectbox - Texto dentro deles */
    .stTextInput input, .stNumberInput input, .stSelectbox div, .stMultiSelect div {
        color: #333333 !important; /* Preto para facilitar leitura no input */
    }

    /* Botões */
    .stButton>button {
        background-color: #E69496; 
        color: white !important; /* Texto do botão sempre branco */
        border-radius: 10px;
        border: none;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #D4787A;
        color: white !important;
    }

    /* Ajuste do Menu Lateral */
    [data-testid="stSidebar"] {
        background-color: #FFF0F5;
    }
    [data-testid="stSidebar"] * {
        color: #5C3A3B !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
@st.cache_resource
def get_connection():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # PRIORIDADE 1: JSON Local
        if os.path.exists("credentials.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        
        # PRIORIDADE 2: Secrets do Streamlit
        elif "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        else:
            st.error("🚨 ERRO CRÍTICO: Nenhuma credencial encontrada.")
            return None

        client = gspread.authorize(creds)
        spreadsheet = client.open("FL Boutique Sistema") 
        return spreadsheet

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
        except gspread.WorksheetNotFound:
            st.error(f"Aba '{sheet_name}' não encontrada.")
            return pd.DataFrame()
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
            st.error(f"Erro ao salvar dados: {e}")

def update_product_status(product_id, new_status):
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Produtos")
            cell = ws.find(product_id)
            if cell:
                headers = ws.row_values(1)
                if "status" in headers:
                    col_index = headers.index("status") + 1
                    ws.update_cell(cell.row, col_index, new_status)
                    st.cache_data.clear()
        except Exception as e:
            st.error(f"Erro ao atualizar status: {e}")

# --- INTERFACE PRINCIPAL ---

st.title("👗 FL Boutique Moda Cristã")
st.markdown("**Sistema de Gestão - Fran & Loamí**")

# Botão de Logout (Sair)
if st.sidebar.button("Sair / Logout"):
    st.session_state["password_correct"] = False
    st.rerun()

conn_test = get_connection()

if conn_test:
    menu = st.sidebar.radio("Navegação", ["Dashboard", "Venda Direta", "Controle de Malas", "Produtos", "Clientes", "Financeiro"])

    if menu == "Dashboard":
        st.header("Visão Geral")
        df_fin = load_data("Financeiro")
        df_prod = load_data("Produtos")
        
        if not df_fin.empty and not df_prod.empty:
            try:
                # Garante que os valores sejam numéricos
                df_prod['preco_custo'] = pd.to_numeric(df_prod['preco_custo'], errors='coerce').fillna(0)
                df_fin['valor'] = pd.to_numeric(df_fin['valor'], errors='coerce').fillna(0)

                total_estoque = df_prod[df_prod['status'] == 'Disponível']['preco_custo'].sum()
                receita_pendente = df_fin[(df_fin['tipo'] == 'Venda') & (df_fin['status_pagamento'] == 'Pendente')]['valor'].sum()
                caixa_atual = df_fin[(df_fin['tipo'] == 'Venda') & (df_fin['status_pagamento'] == 'Pago')]['valor'].sum()
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Valor em Estoque (Custo)", f"R$ {total_estoque:,.2f}")
                col2.metric("A Receber (Fiado/Pendente)", f"R$ {receita_pendente:,.2f}")
                col3.metric("Caixa Real (Pago)", f"R$ {caixa_atual:,.2f}")
            except Exception as e:
                st.warning(f"Erro ao calcular métricas: {e}")
        else:
            st.info("Cadastre produtos e vendas para ver as métricas.")

    elif menu == "Venda Direta":
        st.header("🛒 Registrar Venda Presencial")
        df_clientes = load_data("Clientes")
        df_produtos = load_data("Produtos")
        
        if not df_clientes.empty and not df_produtos.empty:
            with st.form("form_venda_direta"):
                cliente = st.selectbox("Cliente", df_clientes['nome'].unique())
                prods_disponiveis = df_produtos[df_produtos['status'] == 'Disponível']
                
                if prods_disponiveis.empty:
                    st.warning("Sem estoque disponível.")
                    submit = st.form_submit_button("Vender", disabled=True)
                else:
                    opcoes_prod = prods_disponiveis.apply(lambda x: f"{x['id']} | {x['nome']} - {x['tamanho']} - R${x['preco_venda']}", axis=1)
                    produtos_selecionados = st.multiselect("Selecione as peças", options=opcoes_prod)
                    ja_pagou = st.checkbox("Pagamento já realizado?", value=True)
                    submit = st.form_submit_button("Finalizar Venda")
                
                if submit and produtos_selecionados:
                    total_venda = 0
                    for p_str in produtos_selecionados:
                        p_id = p_str.split(" | ")[0]
                        preco = df_produtos[df_produtos['id'] == p_id]['preco_venda'].values[0]
                        total_venda += float(str(preco).replace(',','.'))
                        update_product_status(p_id, "Vendido")
                    
                    status_pag = "Pago" if ja_pagou else "Pendente"
                    novo_fin = [str(uuid.uuid4()), datetime.now().strftime("%Y-%m-%d"), "Venda", f"Venda Direta para {cliente}", total_venda, status_pag]
                    append_data("Financeiro", novo_fin)
                    st.success(f"Venda de R$ {total_venda} registrada!")
                    st.rerun()
        else:
            st.warning("Cadastre Clientes e Produtos primeiro.")

    elif menu == "Controle de Malas":
        st.header("👜 Delivery de Malas")
        tab1, tab2 = st.tabs(["Nova Mala", "Retorno de Mala"])
        df_clientes = load_data("Clientes")
        df_produtos = load_data("Produtos")
        
        with tab1:
            st.subheader("Montar Mala")
            if df_clientes.empty or df_produtos.empty:
                 st.warning("Faltam cadastros.")
            else:
                with st.form("nova_mala"):
                    cliente_mala = st.selectbox("Cliente", df_clientes['nome'].unique())
                    prods_disp = df_produtos[df_produtos['status'] == 'Disponível']
                    opcoes_mala = prods_disp.apply(lambda x: f"{x['id']} | {x['nome']} - {x['tamanho']}", axis=1)
                    itens_mala = st.multiselect("Peças para a mala", options=opcoes_mala)
                    enviar = st.form_submit_button("Registrar Mala")
                    
                    if enviar and itens_mala:
                        ids_mala = [item.split(" | ")[0] for item in itens_mala]
                        ids_string = ",".join(ids_mala)
                        id_cliente = df_clientes[df_clientes['nome'] == cliente_mala]['id'].values[0]
                        
                        nova_mala_row = [str(uuid.uuid4()), id_cliente, cliente_mala, datetime.now().strftime("%Y-%m-%d"), ids_string, "Aberta"]
                        append_data("Malas", nova_mala_row)
                        for pid in ids_mala: update_product_status(pid, "Em Mala")
                        st.success(f"Mala para {cliente_mala} criada!")
                        st.rerun()

        with tab2:
            st.subheader("Retorno")
            df_malas = load_data("Malas")
            if not df_malas.empty and 'status' in df_malas.columns:
                malas_abertas = df_malas[df_malas['status'] == 'Aberta']
                if malas_abertas.empty:
                    st.info("Nenhuma mala aberta.")
                else:
                    mala_id_str = st.selectbox("Selecione a Mala", malas_abertas['id'].astype(str) + " - " + malas_abertas['nome_cliente'])
                    id_mala_real = mala_id_str.split(" - ")[0]
                    dados = malas_abertas[malas_abertas['id'] == id_mala_real].iloc[0]
                    lista_ids = str(dados['lista_ids_produtos']).split(",")
                    
                    st.write(f"Cliente: **{dados['nome_cliente']}**")
                    st.warning("⚠️ Marque o que **DEVOLVEU** (Peças não vendidas).")
                    
                    with st.form("baixa"):
                        retornos = {}
                        for pid in lista_ids:
                            p_info = df_produtos[df_produtos['id'] == pid]
                            if not p_info.empty:
                                label = f"{p_info['nome'].values[0]} (R$ {p_info['preco_venda'].values[0]})"
                                retornos[pid] = st.checkbox(f"DEVOLVEU: {label}", value=True, key=pid)
                        
                        if st.form_submit_button("Processar Mala"):
                            venda_total = 0
                            conn = get_connection()
                            ws_malas = conn.worksheet("Malas")
                            
                            for pid, devolveu in retornos.items():
                                if devolveu:
                                    update_product_status(pid, "Disponível")
                                else:
                                    update_product_status(pid, "Vendido")
                                    price = df_produtos[df_produtos['id'] == pid]['preco_venda'].values[0]
                                    venda_total += float(str(price).replace(',','.'))
                            
                            if venda_total > 0:
                                novo_fin = [str(uuid.uuid4()), datetime.now().strftime("%Y-%m-%d"), "Venda", f"Mala - {dados['nome_cliente']}", venda_total, "Pendente"]
                                append_data("Financeiro", novo_fin)
                                st.success(f"Venda de R$ {venda_total} gerada!")
                            
                            cell = ws_malas.find(id_mala_real)
                            headers = ws_malas.row_values(1)
                            ws_malas.update_cell(cell.row, headers.index("status")+1, "Finalizada")
                            st.success("Mala finalizada!")
                            st.rerun()
            else: st.info("Sem malas registradas.")

    elif menu == "Produtos":
        st.header("Gerenciar Produtos")
        with st.expander("Novo Produto"):
            with st.form("add_prod"):
                nome = st.text_input("Nome")
                tam = st.selectbox("Tamanho", ["PP","P","M","G","GG","XG","Único"])
                custo = st.number_input("Custo", min_value=0.0)
                venda = st.number_input("Venda", min_value=0.0)
                if st.form_submit_button("Salvar"):
                    append_data("Produtos", [str(uuid.uuid4()), nome, tam, custo, venda, "Disponível"])
                    st.success("Salvo!")
                    st.rerun()
        st.dataframe(load_data("Produtos"))

    elif menu == "Clientes":
        st.header("Gerenciar Clientes")
        with st.expander("Novo Cliente"):
            with st.form("add_cli"):
                nome = st.text_input("Nome")
                whats = st.text_input("WhatsApp")
                end = st.text_input("Endereço")
                if st.form_submit_button("Salvar"):
                    append_data("Clientes", [str(uuid.uuid4()), nome, whats, end])
                    st.success("Salvo!")
                    st.rerun()
        st.dataframe(load_data("Clientes"))

    elif menu == "Financeiro":
        st.header("Fluxo de Caixa")
        st.dataframe(load_data("Financeiro"))

else:
    st.error("Erro de conexão com a planilha.")