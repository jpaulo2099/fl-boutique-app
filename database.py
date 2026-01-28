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