import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import time

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

# --- NOVA FUNÇÃO DE LOTE PARA SALVAR VÁRIOS PRODUTOS DE UMA VEZ ---
def append_data_batch(sheet_name, list_of_rows):
    conn = get_connection()
    if conn:
        try:
            # append_rows (plural) é muito mais eficiente
            conn.worksheet(sheet_name).append_rows(list_of_rows)
            st.cache_data.clear()
            return True
        except Exception as e: 
            st.error(f"Erro salvar lote: {e}")
            return False

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

def get_meses_fechados():
    """Retorna uma lista de strings 'YYYY-MM' que estão fechados."""
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Fechamentos")
            records = ws.get_all_records()
            # Retorna apenas os que estão com status 'Fechado'
            return [r['mes_ano'] for r in records if r['status'] == 'Fechado']
        except:
            return []
    return []

def alternar_fechamento_mes(mes_ano, acao):
    """
    acao: 'Fechar' ou 'Reabrir'
    mes_ano: '2025-01'
    """
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Fechamentos")
            cell = ws.find(mes_ano)
            
            if cell:
                # Se já existe, atualiza
                status = "Fechado" if acao == 'Fechar' else "Aberto"
                ws.update_cell(cell.row, 2, status)
            else:
                # Se não existe e quer fechar, cria
                if acao == 'Fechar':
                    ws.append_row([mes_ano, "Fechado"])
            
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erro ao atualizar fechamento: {e}")
            return False
    return False

def is_mes_fechado(data_verificacao):
    """
    Recebe datetime ou string 'YYYY-MM-DD'.
    Retorna True se o mês estiver fechado (Bloqueado).
    Retorna False se estiver aberto (Permitido).
    """
    try:
        # Garante que temos uma string YYYY-MM
        str_data = str(data_verificacao)
        mes_ano = str_data[:7] # Pega "2025-01"
        
        fechados = get_meses_fechados()
        if mes_ano in fechados:
            return True
        return False
    except:
        return False

# --- CONFIGURAÇÕES DO SISTEMA ---

def get_configs():
    """
    Retorna um dicionário com as configs. 
    Ex: {'taxa_cartao': 12.0, 'markup': 2.0}
    """
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Configuracoes")
            records = ws.get_all_records()
            # Converte lista de dicts [{'parametro': 'x', 'valor': 1}] em dict {x: 1}
            config_dict = {}
            for r in records:
                try:
                    config_dict[r['parametro']] = float(str(r['valor']).replace(',', '.'))
                except:
                    config_dict[r['parametro']] = 0.0
            return config_dict
        except:
            return {}
    return {}

def save_configs(novos_valores):
    """
    Recebe dict {'taxa_cartao': 10} e salva na planilha.
    Por segurança, apaga tudo e reescreve para manter a ordem.
    """
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Configuracoes")
            ws.clear()
            ws.append_row(["parametro", "valor"]) # Cabeçalho
            
            rows = []
            for k, v in novos_valores.items():
                rows.append([k, v])
            
            ws.append_rows(rows)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar configs: {e}")
            return False
    return False