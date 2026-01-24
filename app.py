import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import uuid
from datetime import datetime
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="FL Boutique - Gestão", layout="wide")

# --- ESTILIZAÇÃO CSS PERSONALIZADA ---
st.markdown("""
    <style>
    /* Fundo da aplicação */
    .stApp {
        background-color: #FDF2F4; /* Um rosê bem clarinho */
    }
    
    /* Botões */
    .stButton>button {
        background-color: #E69496; /* Rosê mais forte */
        color: white;
        border-radius: 10px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #D4787A;
        color: white;
    }

    /* Títulos e Cabeçalhos */
    h1, h2, h3 {
        color: #5C3A3B; /* Um marrom suave para contraste */
    }
    
    /* Menu Lateral */
    [data-testid="stSidebar"] {
        background-color: #FFF0F5;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS (ROBUSTA) ---
@st.cache_resource
def get_connection():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # PRIORIDADE 1: Arquivo JSON Local (Ambiente de Dev)
        # Como seu diagnóstico passou com o JSON, vamos forçar o uso dele se existir.
        if os.path.exists("credentials.json"):
            # st.toast("Modo DEV: Usando credentials.json local", icon="🛠️")
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        
        # PRIORIDADE 2: Secrets do Streamlit (Ambiente de Produção/Cloud)
        elif "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        else:
            st.error("🚨 ERRO CRÍTICO: Nenhuma credencial encontrada (nem JSON local, nem Secrets).")
            return None

        client = gspread.authorize(creds)
        # Abre a planilha
        spreadsheet = client.open("FL Boutique Sistema") 
        return spreadsheet

    except Exception as e:
        st.error(f"🚨 Falha na Conexão: {e}")
        return None

# --- FUNÇÕES AUXILIARES DE DADOS ---
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
            # Limpa o cache para que os dados novos apareçam imediatamente
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
                # Verifica se a coluna status existe
                if "status" in headers:
                    col_index = headers.index("status") + 1
                    ws.update_cell(cell.row, col_index, new_status)
                    st.cache_data.clear() # Limpa cache para atualizar visualização
                else:
                    st.error("Coluna 'status' não encontrada no cabeçalho.")
        except Exception as e:
            st.error(f"Erro ao atualizar status: {e}")

# --- INTERFACE E LÓGICA ---

st.title("👗 FL Boutique Moda Cristã")
st.markdown("**Sistema de Gestão - Fran & Loamí**")

# Carrega conexão inicial para testar
conn_test = get_connection()

if conn_test:
    menu = st.sidebar.radio("Navegação", ["Dashboard", "Venda Direta", "Controle de Malas", "Produtos", "Clientes", "Financeiro"])

    if menu == "Dashboard":
        st.header("Visão Geral")
        df_fin = load_data("Financeiro")
        df_prod = load_data("Produtos")
        
        if not df_fin.empty and not df_prod.empty:
            # Tratamento de erro caso as colunas venham como texto
            try:
                # Remove R$ e converte
                # (Assumindo dados limpos, mas prevenindo crash)
                total_estoque = df_prod[df_prod['status'] == 'Disponível']['preco_custo'].sum()
                
                receita_pendente = df_fin[(df_fin['tipo'] == 'Venda') & (df_fin['status_pagamento'] == 'Pendente')]['valor'].sum()
                caixa_atual = df_fin[(df_fin['tipo'] == 'Venda') & (df_fin['status_pagamento'] == 'Pago')]['valor'].sum()
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Valor em Estoque (Custo)", f"R$ {total_estoque:,.2f}")
                col2.metric("A Receber (Fiado/Pendente)", f"R$ {receita_pendente:,.2f}")
                col3.metric("Caixa Real (Pago)", f"R$ {caixa_atual:,.2f}")
            except Exception as e:
                st.warning(f"Não foi possível calcular métricas (verifique formato dos números): {e}")
        else:
            st.info("Cadastre produtos e vendas para ver as métricas.")

    elif menu == "Venda Direta":
        st.header("🛒 Registrar Venda Presencial")
        
        df_clientes = load_data("Clientes")
        df_produtos = load_data("Produtos")
        
        if not df_clientes.empty and not df_produtos.empty:
            with st.form("form_venda_direta"):
                cliente = st.selectbox("Cliente", df_clientes['nome'].unique())
                
                # Filtra apenas produtos disponíveis
                prods_disponiveis = df_produtos[df_produtos['status'] == 'Disponível']
                
                if prods_disponiveis.empty:
                    st.warning("Nenhum produto disponível no estoque.")
                    produtos_selecionados = []
                    submit = st.form_submit_button("Finalizar Venda", disabled=True)
                else:
                    opcoes_prod = prods_disponiveis.apply(lambda x: f"{x['id']} | {x['nome']} - {x['tamanho']} - R${x['preco_venda']}", axis=1)
                    produtos_selecionados = st.multiselect("Selecione as peças", options=opcoes_prod)
                    ja_pagou = st.checkbox("Pagamento já realizado?", value=True)
                    submit = st.form_submit_button("Finalizar Venda")
                
                if submit and produtos_selecionados:
                    total_venda = 0
                    
                    for p_str in produtos_selecionados:
                        p_id = p_str.split(" | ")[0]
                        # Pega o preço
                        preco = df_produtos[df_produtos['id'] == p_id]['preco_venda'].values[0]
                        total_venda += float(preco)
                        
                        # 1. Atualiza Estoque
                        update_product_status(p_id, "Vendido")
                    
                    # 2. Lança no Financeiro
                    status_pag = "Pago" if ja_pagou else "Pendente"
                    novo_fin = [
                        str(uuid.uuid4()),
                        datetime.now().strftime("%Y-%m-%d"),
                        "Venda",
                        f"Venda Direta para {cliente}",
                        total_venda,
                        status_pag
                    ]
                    append_data("Financeiro", novo_fin)
                    
                    st.success(f"Venda de R$ {total_venda} registrada com sucesso!")
                    st.rerun()
        else:
            st.warning("Cadastre Clientes e Produtos primeiro na aba lateral.")

    elif menu == "Controle de Malas":
        st.header("👜 Delivery de Malas")
        tab1, tab2 = st.tabs(["Nova Mala", "Retorno de Mala"])
        
        df_clientes = load_data("Clientes")
        df_produtos = load_data("Produtos")
        
        with tab1:
            st.subheader("Montar Mala para Envio")
            if df_clientes.empty or df_produtos.empty:
                 st.warning("Necessário cadastrar clientes e produtos antes.")
            else:
                with st.form("nova_mala"):
                    cliente_mala = st.selectbox("Selecione a Cliente", df_clientes['nome'].unique())
                    
                    # Filtra disponíveis
                    prods_disp = df_produtos[df_produtos['status'] == 'Disponível']
                    opcoes_mala = prods_disp.apply(lambda x: f"{x['id']} | {x['nome']} - {x['tamanho']}", axis=1)
                    
                    itens_mala = st.multiselect("Escolha as peças para a mala", options=opcoes_mala)
                    
                    enviar = st.form_submit_button("Registrar Envio da Mala")
                    
                    if enviar and itens_mala:
                        ids_mala = [item.split(" | ")[0] for item in itens_mala]
                        ids_string = ",".join(ids_mala)
                        
                        id_cliente = df_clientes[df_clientes['nome'] == cliente_mala]['id'].values[0]
                        
                        nova_mala_row = [
                            str(uuid.uuid4()),
                            id_cliente,
                            cliente_mala,
                            datetime.now().strftime("%Y-%m-%d"),
                            ids_string,
                            "Aberta"
                        ]
                        append_data("Malas", nova_mala_row)
                        
                        for pid in ids_mala:
                            update_product_status(pid, "Em Mala")
                        
                        st.success(f"Mala para {cliente_mala} criada! Produtos atualizados.")
                        st.rerun()

        with tab2:
            st.subheader("Processar Retorno")
            df_malas = load_data("Malas")
            
            if not df_malas.empty:
                # Verifica se existe coluna status antes de filtrar
                if 'status' in df_malas.columns:
                    malas_abertas = df_malas[df_malas['status'] == 'Aberta']
                else:
                    malas_abertas = pd.DataFrame()

                if malas_abertas.empty:
                    st.info("Nenhuma mala aberta no momento.")
                else:
                    mala_selecionada_id = st.selectbox("Selecione a Mala retornada", malas_abertas['id'].astype(str) + " - " + malas_abertas['nome_cliente'])
                    id_mala_real = mala_selecionada_id.split(" - ")[0]
                    
                    dados_mala = malas_abertas[malas_abertas['id'] == id_mala_real].iloc[0]
                    lista_ids = str(dados_mala['lista_ids_produtos']).split(",")
                    nome_cli = dados_mala['nome_cliente']
                    
                    st.write(f"**Cliente:** {nome_cli} | **Enviado em:** {dados_mala['data_envio']}")
                    st.warning("⚠️ DESMARQUE as peças que foram VENDIDAS (Ficaram com a cliente).")
                    
                    with st.form("baixa_mala"):
                        retornos = {}
                        
                        for pid in lista_ids:
                            prod_info = df_produtos[df_produtos['id'] == pid]
                            if not prod_info.empty:
                                nome_p = prod_info['nome'].values[0]
                                preco_p = prod_info['preco_venda'].values[0]
                                label = f"{nome_p} (R$ {preco_p})"
                                # Checkbox marcado por padrão = Voltou
                                retornos[pid] = st.checkbox(f"DEVOLVEU: {label}", value=True, key=pid)
                            
                        btn_baixa = st.form_submit_button("Processar Mala")
                        
                        if btn_baixa:
                            conn = get_connection()
                            ws_malas = conn.worksheet("Malas")
                            venda_total = 0
                            
                            for pid, devolveu in retornos.items():
                                if devolveu:
                                    update_product_status(pid, "Disponível")
                                else:
                                    # Vendeu
                                    update_product_status(pid, "Vendido")
                                    prod_price = df_produtos[df_produtos['id'] == pid]['preco_venda'].values[0]
                                    venda_total += float(prod_price)
                            
                            if venda_total > 0:
                                novo_fin = [
                                    str(uuid.uuid4()),
                                    datetime.now().strftime("%Y-%m-%d"),
                                    "Venda",
                                    f"Mala Delivery - {nome_cli}",
                                    venda_total,
                                    "Pendente"
                                ]
                                append_data("Financeiro", novo_fin)
                                st.success(f"Venda de R$ {venda_total} gerada!")

                            cell = ws_malas.find(id_mala_real)
                            headers = ws_malas.row_values(1)
                            col_status = headers.index("status") + 1
                            ws_malas.update_cell(cell.row, col_status, "Finalizada")
                            
                            st.success("Mala processada e fechada com sucesso!")
                            st.rerun()
            else:
                 st.info("Nenhuma mala encontrada.")

    elif menu == "Produtos":
        st.header("Gerenciar Produtos")
        with st.expander("Cadastrar Novo Produto"):
            with st.form("novo_prod"):
                nome = st.text_input("Nome da Peça")
                tamanho = st.selectbox("Tamanho", ["PP", "P", "M", "G", "GG", "XG", "Único"])
                custo = st.number_input("Preço de Custo", min_value=0.0, format="%.2f")
                venda = st.number_input("Preço de Venda", min_value=0.0, format="%.2f")
                
                cadastrar = st.form_submit_button("Cadastrar")
                if cadastrar:
                    # id, nome, tamanho, preco_custo, preco_venda, status
                    row = [str(uuid.uuid4()), nome, tamanho, float(custo), float(venda), "Disponível"]
                    append_data("Produtos", row)
                    st.success("Produto cadastrado!")
                    st.rerun()
        
        st.dataframe(load_data("Produtos"))

    elif menu == "Clientes":
        st.header("Gerenciar Clientes")
        with st.expander("Novo Cliente"):
            with st.form("novo_cli"):
                nome = st.text_input("Nome")
                whats = st.text_input("WhatsApp")
                end = st.text_input("Endereço")
                if st.form_submit_button("Salvar"):
                    row = [str(uuid.uuid4()), nome, whats, end]
                    append_data("Clientes", row)
                    st.success("Cliente Salvo!")
                    st.rerun()
        st.dataframe(load_data("Clientes"))

    elif menu == "Financeiro":
        st.header("Fluxo de Caixa")
        df = load_data("Financeiro")
        st.dataframe(df)

else:
    st.error("O sistema não conseguiu conectar na planilha. Verifique o log acima.")