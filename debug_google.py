import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

print("--- INICIANDO DIAGNÓSTICO ---")

# 1. Verifica arquivo local
if os.path.exists("credentials.json"):
    print("[OK] Arquivo 'credentials.json' encontrado.")
else:
    print("[ERRO FATAL] O arquivo 'credentials.json' NÃO está na pasta.")
    exit()

# 2. Tenta Autenticar
try:
    print("Tentando autenticar com a API...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    print("[OK] Autenticação (OAuth) passou.")
except Exception as e:
    print(f"[ERRO DE AUTENTICAÇÃO]: {e}")
    exit()

# 3. Tenta Abrir a Planilha
try:
    print("Procurando planilha 'FL Boutique Sistema'...")
    # IMPORTANTE: O nome aqui tem que ser IDÊNTICO ao do Google Sheets
    sh = client.open("FL Boutique Sistema") 
    print(f"[OK] Planilha encontrada! ID: {sh.id}")
except gspread.SpreadsheetNotFound:
    print("[ERRO] Planilha não encontrada! Verifique:")
    print("   1. O nome está EXATAMENTE 'FL Boutique Sistema' no Google?")
    print("   2. Você compartilhou a planilha com o email do client_email que está no JSON?")
    exit()
except Exception as e:
    print(f"[ERRO GENÉRICO]: {e}")
    exit()

# 4. Tenta Ler uma Aba
try:
    print("Tentando ler aba 'Produtos'...")
    ws = sh.worksheet("Produtos")
    data = ws.get_all_records()
    print(f"[OK] Leitura realizada! Linhas retornadas: {len(data)}")
except gspread.WorksheetNotFound:
    print("[ERRO] Aba 'Produtos' não existe. Verifique se criou as abas corretamente.")
    exit()
except Exception as e:
    print(f"[ERRO DE LEITURA]: {e}")
    exit()

print("--- DIAGNÓSTICO CONCLUÍDO COM SUCESSO ---")