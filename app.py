import streamlit as st
import os
import styles
from datetime import datetime

# --- IMPORTS DOS NOVOS MÓDULOS ---
# O Streamlit adiciona a raiz ao PATH, então isso funciona:
from views import dashboard, vendas, compras, malas, produtos, clientes, financeiro, relatorios

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="FL Boutique - Gestão", layout="wide")

# Aplica o CSS
styles.apply_custom_style()

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

    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🔒 Acesso Restrito")
        st.text_input("Senha", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state:
            st.error("😕 Senha incorreta.")
    return False

if not check_password():
    st.stop()

# --- SIDEBAR E NAVEGAÇÃO ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=120)
    else:
        st.header("FL Boutique")
    
    st.write(f"Olá! Hoje é {datetime.now().strftime('%d/%m')}")
    st.divider()
    
    menu = st.radio("Navegação", [
        "Dashboard", 
	"Relatórios Avançados",
        "Venda Direta", 
        "Pedido de Compra", 
        "Controle de Malas", 
        "Produtos", 
        "Clientes", 
        "Financeiro"
    ])
    
    st.divider()
    if st.button("Sair"):
        st.session_state["password_correct"] = False
        st.rerun()

# --- ROTEAMENTO DE TELAS ---
if menu == "Dashboard":
    dashboard.show_dashboard()
elif menu == "Relatórios Avançados": # <--- ROTA NOVA
    relatorios.show_relatorios()
elif menu == "Venda Direta":
    vendas.show_venda_direta()
elif menu == "Pedido de Compra":
    compras.show_compras()
elif menu == "Controle de Malas":
    malas.show_malas()
elif menu == "Produtos":
    produtos.show_produtos()
elif menu == "Clientes":
    clientes.show_clientes()
elif menu == "Financeiro":
    financeiro.show_financeiro()