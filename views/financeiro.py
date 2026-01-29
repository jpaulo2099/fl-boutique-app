import streamlit as st
import utils as ut
import database as db
import uuid
from datetime import datetime

def show_financeiro():
    st.header("💰 Finanças")
    t1, t2, t3, t4 = st.tabs(["Extrato", "Receber", "Lançar", "Excluir"])
    df = db.load_data("Financeiro")
    
    with t1:
        if not df.empty:
            sh = df.drop(columns=['id'], errors='ignore').copy()
            if 'valor' in sh.columns: sh['valor'] = sh['valor'].apply(lambda x: ut.format_brl(ut.converter_input_para_float(x)))
            if 'data_lancamento' in sh.columns:
                sh['data_lancamento'] = sh['data_lancamento'].apply(ut.format_data_br)
            if 'data_vencimento' in sh.columns:
                sh['data_vencimento'] = sh['data_vencimento'].apply(ut.format_data_br)
                
            st.dataframe(sh, use_container_width=True)
    with t2:
        if not df.empty:
            pen = df[(df['status_pagamento']=='Pendente') & (df['tipo']=='Venda')]
            if not pen.empty:
                op = {f"{r['descricao']} - {ut.format_brl(ut.converter_input_para_float(r['valor']))}": r['id'] for i,r in pen.iterrows()}
                sl = st.selectbox("Receber", list(op.keys()))
                if st.button("Confirmar"):
                    db.update_finance_status(op[sl], "Pago")
                    st.success("Recebido!")
                    st.rerun()
            else: st.info("Nada pendente.")
    with t3:
        with st.form("fin_man"):
            tp = st.selectbox("Tipo", ["Despesa", "Entrada"])
            ds = st.text_input("Descrição")
            vl = st.text_input("Valor (R$)", "0,00")
            
            # 1. PRIMEIRO CRIA A DATA
            dt = st.date_input("Data", datetime.now(), format="DD/MM/YYYY")
            stt = st.selectbox("Status", ["Pago", "Pendente"])
            
            # 2. DEPOIS VERIFICA SE ESTÁ FECHADO
            mes_bloqueado = db.is_mes_fechado(dt)
            
            # Botão de Enviar
            submitted = st.form_submit_button("Lançar")
            
            if submitted:
                if mes_bloqueado:
                    st.error(f"⛔ O mês de {dt.strftime('%m/%Y')} está FECHADO. Não é possível lançar nesta data.")
                else:
                    vf = f"{ut.converter_input_para_float(vl):.2f}"
                    db.append_data("Financeiro", [str(uuid.uuid4()), dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m-%d"), tp, ds, vf, "Manual", stt])
                    st.success("Lançado!")
                    st.rerun()
                    
    with t4:
        if not df.empty:
            op = {f"{r['descricao']} ({r['valor']})": r['id'] for i,r in df.iterrows()}
            sl = st.selectbox("Apagar", list(op.keys()))
            
            # Para excluir, precisamos saber a data do registro selecionado para validar o bloqueio
            # Mas o selectbox só nos dá o ID. Vamos buscar o registro completo.
            id_selecionado = op[sl]
            registro_sel = df[df['id'] == id_selecionado].iloc[0]
            data_registro = registro_sel['data_lancamento']
            
            if st.button("Apagar Registro"):
                if db.is_mes_fechado(data_registro):
                     st.error(f"⛔ Este registro pertence a um mês FECHADO ({ut.format_data_br(data_registro)}). Não pode ser excluído.")
                else:
                    db.delete_data("Financeiro", id_selecionado)
                    st.success("Apagado!")
                    st.rerun()