import streamlit as st
import utils as ut
import database as db


def show_dashboard():
    st.header("Visão Geral")
    df_fin = db.load_data("Financeiro")
    df_prod = db.load_data("Produtos")
    if not df_fin.empty and not df_prod.empty:
        try:
            prods_disp = df_prod[df_prod['status']=='Disponível']
            custo_total_estoque = sum([ut.converter_input_para_float(x) for x in prods_disp['preco_custo']])
            qtd_produtos = len(prods_disp)
            
            receber = 0
            caixa_bruto = 0
            taxas_cartao = 0
            vendas_no_mes = 0
            valor_vendas_mes = 0
            mes_atual = datetime.now().strftime("%Y-%m")
            
            for idx, row in df_fin.iterrows():
                val = ut.converter_input_para_float(row['valor'])
                data_lanc = str(row['data_lancamento'])
                
                if row['tipo'] == 'Venda' and data_lanc.startswith(mes_atual):
                    valor_vendas_mes += val
                    vendas_no_mes += 1
                if row['tipo'] == 'Venda' and row['status_pagamento'] == 'Pendente':
                    receber += val
                if row['status_pagamento'] == 'Pago':
                    if row['tipo'] in ['Venda', 'Entrada']:
                        caixa_bruto += val
                        forma = str(row['forma_pagamento']).lower()
                        if any(x in forma for x in ["cartão", "credito", "debito", "crédito", "débito"]):
                            taxas_cartao += val * 0.12
                    elif row['tipo'] == 'Despesa':
                        caixa_bruto -= val

            caixa_liquido = caixa_bruto - taxas_cartao
            ticket_medio = valor_vendas_mes / vendas_no_mes if vendas_no_mes > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Caixa Líquido", ut.format_brl(caixa_liquido), delta=f"- {ut.format_brl(taxas_cartao)} Taxas")
            c2.metric("A Receber", ut.format_brl(receber))
            c3.metric("Estoque (Custo)", ut.format_brl(custo_total_estoque))
            c4.metric("Taxas Pagas", ut.format_brl(taxas_cartao))
            st.divider()
            c5, c6, c7 = st.columns(3)
            c5.metric("Peças Disponíveis", f"{qtd_produtos} un.")
            c6.metric("Vol. Vendas (Mês)", f"{vendas_no_mes}")
            c7.metric("Ticket Médio", ut.format_brl(ticket_medio))
        except Exception as e: st.warning(f"Erro Dash: {e}")
