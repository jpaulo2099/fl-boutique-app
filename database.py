import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.cell import Cell # <--- IMPORTANTE: NECESSÁRIO PARA O BATCH
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

def append_data_batch(sheet_name, list_of_rows):
    conn = get_connection()
    if conn:
        try:
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

# --- FUNÇÃO DE LOTE CORRIGIDA (SEM LOOP DE API) ---
def update_product_status_batch(updates_dict):
    """
    Recebe um dicionário { 'ID_PRODUTO': 'NOVO_STATUS' }
    Faz apenas DUAS requisições à API: uma de leitura e uma de escrita.
    """
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Produtos")
            
            # 1. Requisição de Leitura (Pega todos os IDs da coluna 1)
            # Isso é rápido e leve.
            lista_ids = ws.col_values(1) 
            
            cells_to_update = []
            
            # 2. Monta o pacote de atualizações localmente
            for pid, new_status in updates_dict.items():
                if pid in lista_ids:
                    # +1 porque lista começa em 0 e planilha em 1
                    row_idx = lista_ids.index(pid) + 1 
                    
                    # Coluna 6 é o Status (A=1, B=2... F=6). 
                    # CONFIRA SE NA SUA PLANILHA O STATUS É A COLUNA F.
                    # Se for outra, mude o número 6 abaixo.
                    cells_to_update.append(Cell(row_idx, 6, new_status))
            
            # 3. Requisição de Escrita (Envia tudo de uma vez)
            if cells_to_update:
                ws.update_cells(cells_to_update)
                st.cache_data.clear()
                return True
            return True # Se não tinha nada pra atualizar, retorna true
            
        except Exception as e:
            st.error(f"Erro no Batch Update: {e}")
            return False
    return False

def get_meses_fechados():
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Fechamentos")
            records = ws.get_all_records()
            return [r['mes_ano'] for r in records if r['status'] == 'Fechado']
        except:
            return []
    return []

def alternar_fechamento_mes(mes_ano, acao):
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Fechamentos")
            cell = ws.find(mes_ano)
            
            if cell:
                status = "Fechado" if acao == 'Fechar' else "Aberto"
                ws.update_cell(cell.row, 2, status)
            else:
                if acao == 'Fechar':
                    ws.append_row([mes_ano, "Fechado"])
            
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erro ao atualizar fechamento: {e}")
            return False
    return False

def is_mes_fechado(data_verificacao):
    try:
        str_data = str(data_verificacao)
        mes_ano = str_data[:7] 
        fechados = get_meses_fechados()
        if mes_ano in fechados:
            return True
        return False
    except:
        return False

# --- CONFIGURAÇÕES DO SISTEMA ---

def get_configs():
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Configuracoes")
            records = ws.get_all_records()
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
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Configuracoes")
            ws.clear()
            ws.append_row(["parametro", "valor"]) 
            
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

def confirmar_recebimento(id_registro, valor_final):
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Financeiro")
            cell = ws.find(id_registro)
            
            if cell:
                # Atualiza Coluna 6 (Valor) e Coluna 8 (Status)
                ws.update_cell(cell.row, 6, valor_final)
                ws.update_cell(cell.row, 8, "Pago")
                
                st.cache_data.clear()
                return True
        except Exception as e:
            st.error(f"Erro ao confirmar recebimento: {e}")
            return False
    return False