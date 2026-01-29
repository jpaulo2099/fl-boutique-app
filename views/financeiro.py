import streamlit as st
import utils as ut
import database as db
import uuid
import pandas as pd
from datetime import datetime

def show_financeiro():
    st.header("💰 Finanças")
    t1, t2, t3, t4 = st.tabs(["Extrato", "Receber", "Lançar", "Excluir"])
    df = db.load_data("Financeiro")
    
    # --- TAB 1: EXTRATO (COM ORDENAÇÃO CORRIGIDA) ---
    with t1:
        if not df.empty:
            # 1. Preparar Dados
            df_show = df.drop(columns=['id'], errors='ignore').copy()
            
            # Converte colunas de data para o tipo DATETIME (para ordenar corretamente)
            # O errors='coerce' transforma datas inválidas em NaT (Not a Time) para não quebrar
            if 'data_lancamento' in df_show.columns:
                df_show['data_lancamento'] = pd.to_datetime(df_show['data_lancamento'], errors='coerce')
                
            if 'data_vencimento' in df_show.columns:
                df_show['data_vencimento'] = pd.to_datetime(df_show['data_vencimento'], errors='coerce')
            
            # Converte valor para float para ordenar corretamente pelo preço também, se quiser
            df_show['valor_num'] = df_show['valor'].apply(ut.converter_input_para_float)

            # 2. Ordenação Padrão (Data de Vencimento)
            df_show = df_show.sort_values(by='data_vencimento', ascending=True)

            # 3. Formatação Visual (Moeda)
            # Criamos uma coluna visual, mas mantemos a original ou usamos column_config do Streamlit
            df_show['valor_fmt'] = df_show['valor_num'].apply(ut.format_brl)
            
            # Selecionar colunas finais para exibir
            cols_to_show = ['data_lancamento', 'data_vencimento', 'tipo', 'descricao', 'valor_num', 'forma_pagamento', 'status_pagamento']
            # Filtra colunas que realmente existem no df
            cols_existentes = [c for c in cols_to_show if c in df_show.columns]
            
            final_df = df_show[cols_existentes]

            # 4. Exibição Inteligente (Column Config)
            # Aqui dizemos ao Streamlit: "Isso é uma data, mostre como DD/MM/AAAA"
            st.dataframe(
                final_df, 
                use_container_width=True,
                column_config={
                    "data_lancamento": st.column_config.DateColumn("Data Lançamento", format="DD/MM/YYYY"),
                    "data_vencimento": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                    "valor_num": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "tipo": "Tipo",
                    "descricao": "Descrição",
                    "forma_pagamento": "Forma",
                    "status_pagamento": "Status"
                },
                hide_index=True
            )
        else:
            st.info("Sem lançamentos.")

    # --- TAB 2: RECEBER (COM EDIÇÃO DE VALOR) ---
    with t2:
        if not df.empty:
            # Filtra pendentes de Venda
            pen = df[(df['status_pagamento']=='Pendente') & (df['tipo']=='Venda')]
            
            if not pen.empty:
                # Dicionário para identificar o registro
                op = {f"{r['descricao']} - {ut.format_brl(ut.converter_input_para_float(r['valor']))} ({ut.format_data_br(r['data_vencimento'])})": r['id'] for i,r in pen.iterrows()}
                
                sel = st.selectbox("Selecione o Recebimento", list(op.keys()))
                id_sel = op[sel]
                
                # Busca os dados originais do item selecionado para preencher o campo
                item_dados = pen[pen['id'] == id_sel].iloc[0]
                valor_original_str = item_dados['valor'] # Ex: "100,00" ou "100.00"
                
                # Converte para formatar bonitinho no input
                val_float = ut.converter_input_para_float(valor_original_str)
                val_fmt = f"{val_float:.2f}".replace('.', ',')
                
                st.divider()
                c_val, c_btn = st.columns([1, 1])
                
                with c_val:
                    # Permite editar o valor
                    novo_valor_txt = st.text_input("Valor Recebido (R$)", value=val_fmt, help="Edite caso o cliente pague um valor diferente.")
                
                with c_btn:
                    st.write("") # Espaço
                    st.write("") 
                    if st.button("✅ Confirmar Recebimento"):
                        # Converte o novo valor para salvar no banco
                        novo_valor_float = ut.converter_input_para_float(novo_valor_txt)
                        novo_valor_save = f"{novo_valor_float:.2f}" # Salva como "100.00"
                        
                        if db.confirmar_recebimento(id_sel, novo_valor_save):
                            st.success(f"Recebido R$ {novo_valor_txt}! Status atualizado.")
                            st.rerun()
            else: 
                st.info("Nenhuma conta a receber pendente.")

    # --- TAB 3: LANÇAR (Mantido Igual) ---
    with t3:
        with st.form("fin_man"):
            tp = st.selectbox("Tipo", ["Despesa", "Entrada"])
            ds = st.text_input("Descrição")
            vl = st.text_input("Valor (R$)", "0,00")
            
            dt = st.date_input("Data", datetime.now(), format="DD/MM/YYYY")
            stt = st.selectbox("Status", ["Pago", "Pendente"])
            
            mes_bloqueado = db.is_mes_fechado(dt)
            
            submitted = st.form_submit_button("Lançar")
            
            if submitted:
                if mes_bloqueado:
                    st.error(f"⛔ O mês de {dt.strftime('%m/%Y')} está FECHADO. Não é possível lançar nesta data.")
                else:
                    vf = f"{ut.converter_input_para_float(vl):.2f}"
                    db.append_data("Financeiro", [str(uuid.uuid4()), dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m-%d"), tp, ds, vf, "Manual", stt])
                    st.success("Lançado!")
                    st.rerun()
                    
    # --- TAB 4: EXCLUIR (Mantido Igual) ---
    with t4:
        if not df.empty:
            op = {f"{r['descricao']} ({r['valor']})": r['id'] for i,r in df.iterrows()}
            sl = st.selectbox("Apagar", list(op.keys()))
            
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