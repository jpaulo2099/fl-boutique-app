import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import uuid
from datetime import datetime, timedelta
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="FL Boutique - Gestão", layout="wide")

# --- FUNÇÕES DE ESTILO E FORMATAÇÃO ---
def format_brl(value):
    """Formata float para moeda brasileira R$ 1.000,00"""
    try:
        if value is None: return "R$ 0,00"
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return value

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

    # Estilo específico para tela de login
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

# --- ESTILIZAÇÃO CSS (CORREÇÃO DE CORES E FUNDOS - VERSÃO FORTE) ---
st.markdown("""
    <style>
    /* 1. FUNDO GERAL DA APLICAÇÃO */
    .stApp { 
        background-color: #FDF2F4 !important; 
    }
    
    /* 2. BARRA SUPERIOR (HEADER) */
    header[data-testid="stHeader"] {
        background-color: #FDF2F4 !important;
    }
    
    /* 3. TEXTOS GERAIS (Força cor escura em tudo) */
    html, body, p, div, span, label, h1, h2, h3, h4, h5, h6, .stMarkdown, .stText, td, th { 
        color: #5C3A3B !important; 
    }

    /* 4. CORREÇÃO DE INPUTS E SELECTBOX (Fundo Branco Obrigatório) */
    
    /* Input de Texto e Número (Container e Campo) */
    .stTextInput > div > div, .stNumberInput > div > div {
        background-color: #FFFFFF !important;
        border-color: #E69496 !important;
        color: #000000 !important;
    }
    
    /* O texto digitado dentro do input */
    input[type="text"], input[type="number"], input[type="password"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important; /* Correção iPhone Safari */
        caret-color: #000000 !important; /* Cor do cursor */
    }

    /* Selectbox e Multiselect (Caixa Fechada) */
    .stSelectbox > div > div, .stMultiSelect > div > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-color: #E69496 !important;
    }
    
    /* O texto selecionado dentro do Selectbox */
    .stSelectbox div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
    }

    /* 5. MENU LATERAL */
    [data-testid="stSidebar"] { 
        background-color: #FFF0F5 !important; 
    }
    [data-testid="stSidebar"] * { 
        color: #5C3A3B !important; 
    }

    /* 6. BOTÕES */
    .stButton>button { 
        background-color: #E69496 !important; 
        color: white !important; 
        border-radius: 10px; 
        border: none; 
        font-weight: bold; 
    }
    .stButton>button:hover { 
        background-color: #D4787A !important; 
        color: white !important; 
    }
    
    /* 7. CHECKBOX */
    .stCheckbox label span {
        color: #5C3A3B !important;
    }
    
    /* 8. DATAFRAME / TABELAS */
    [data-testid="stDataFrame"] {
        background-color: #FFFFFF !important;
    }
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