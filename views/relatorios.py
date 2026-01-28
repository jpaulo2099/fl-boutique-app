import streamlit as st
import pandas as pd
import plotly.express as px
import database as db
import utils as ut
from datetime import datetime

def show_relatorios():
    st.header("📈 Relatórios Gerenciais")
    st.caption("Acompanhe a saúde financeira e operacional da loja.")

    # Carrega dados
    df_fin = db.load_data("Financeiro")
    df_prod = db.load_data("Produtos")
    
    if df_fin.empty or df_prod.empty:
        st.info("Sem dados suficientes para gerar gráficos.")
        return

    # --- PROCESSAMENTO DE DADOS (ETL) ---
    
    # 1. Preparar Financeiro
    # Converte colunas numéricas e de data
    df_fin['valor_float'] = df_fin['valor'].apply(ut.converter_input_para_float)
    df_fin['data_dt'] = pd.to_datetime(df_fin['data_lancamento'])
    df_fin['mes_ano'] = df_fin['data_dt'].dt.strftime('%Y-%m') # Ex: 2026-01
    
    # 2. Calcular Lucro Real por Mês (DRE Simplificado)
    # Receitas (Vendas + Entradas) vs Despesas
    dre = df_fin.groupby(['mes_ano', 'tipo'])['valor_float'].sum().reset_index()
    
    # Pivotar para ter colunas separadas: mes_ano | Despesa | Venda
    dre_pivot = dre.pivot(index='mes_ano', columns='tipo', values='valor_float').fillna(0).reset_index()
    
    # Garantir que as colunas existem (caso não tenha tido despesa ou venda no mês)
    if 'Venda' not in dre_pivot.columns: dre_pivot['Venda'] = 0
    if 'Despesa' not in dre_pivot.columns: dre_pivot['Despesa'] = 0
    if 'Entrada' in dre_pivot.columns: 
        dre_pivot['Venda'] += dre_pivot['Entrada'] # Soma aportes como entrada positiva
    
    dre_pivot['Lucro'] = dre_pivot['Venda'] - dre_pivot['Despesa']

    # --- VISUALIZAÇÃO ---

    # TAB 1: FINANCEIRO
    t1, t2, t3 = st.tabs(["💰 Financeiro (DRE)", "🏆 Top Clientes", "📦 Estoque & Tamanhos"])

    with t1:
        st.subheader("Faturamento vs. Despesas vs. Lucro")
        
        # Gráfico de Barras Agrupadas
        fig_dre = px.bar(
            dre, 
            x="mes_ano", 
            y="valor_float", 
            color="tipo",
            barmode="group",
            text_auto='.2s',
            title="Receitas x Despesas (Mensal)",
            labels={'valor_float': 'Valor (R$)', 'mes_ano': 'Mês', 'tipo': 'Tipo'},
            color_discrete_map={'Venda': '#2ecc71', 'Despesa': '#e74c3c', 'Entrada': '#3498db'}
        )
        st.plotly_chart(fig_dre, use_container_width=True)
        
        # Gráfico de Linha do Lucro Acumulado
        st.divider()
        st.subheader("Evolução do Lucro Líquido")
        fig_lucro = px.line(
            dre_pivot, 
            x="mes_ano", 
            y="Lucro", 
            markers=True,
            title="Lucro Real (Vendas - Despesas)",
            labels={'Lucro': 'Lucro Líquido (R$)', 'mes_ano': 'Mês'}
        )
        fig_lucro.add_hline(y=0, line_dash="dash", line_color="gray") # Linha de zero
        fig_lucro.update_traces(line_color="#8e44ad", line_width=4)
        st.plotly_chart(fig_lucro, use_container_width=True)

    # TAB 2: RANKING CLIENTES
    with t2:
        st.subheader("Quem são suas melhores clientes?")
        
        # Filtra apenas Vendas pagas ou pendentes (ignora despesas)
        vendas = df_fin[df_fin['tipo'] == 'Venda']
        
        # Extrai nome do cliente da descrição "Venda Direta - Nome (1/X)"
        # Lógica: Pega tudo depois de " - " e antes de " ("
        def extrair_cliente(desc):
            try:
                # Ex: "Venda Direta - Maria Silva (1/2)" -> "Maria Silva"
                if " - " in desc:
                    parte1 = desc.split(" - ")[1]
                    if " (" in parte1:
                        return parte1.split(" (")[0]
                    return parte1
                return "Consumidor Final"
            except:
                return "Outros"

        vendas['Cliente_Nome'] = vendas['descricao'].apply(extrair_cliente)
        
        # Agrupa e Soma
        ranking = vendas.groupby('Cliente_Nome')['valor_float'].sum().reset_index()
        ranking = ranking.sort_values(by='valor_float', ascending=True).tail(10) # Top 10 (tail pq é barra horizontal)
        
        fig_cli = px.bar(
            ranking, 
            x="valor_float", 
            y="Cliente_Nome", 
            orientation='h',
            text_auto='.2s',
            title="Top 10 Clientes (Valor Comprado)",
            labels={'valor_float': 'Total Gasto (R$)', 'Cliente_Nome': 'Cliente'},
            color_discrete_sequence=['#E69496'] # Cor Rosê da marca
        )
        st.plotly_chart(fig_cli, use_container_width=True)

    # TAB 3: CURVA DE TAMANHOS
    with t3:
        st.subheader("Quais tamanhos vendem mais?")
        
        # Filtra apenas produtos vendidos
        vendidos = df_prod[df_prod['status'] == 'Vendido']
        
        if not vendidos.empty:
            contagem_tam = vendidos['tamanho'].value_counts().reset_index()
            contagem_tam.columns = ['Tamanho', 'Qtd Vendida']
            
            # Gráfico de Pizza (Donut)
            fig_tam = px.pie(
                contagem_tam, 
                values='Qtd Vendida', 
                names='Tamanho', 
                title='Distribuição de Vendas por Tamanho',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            st.plotly_chart(fig_tam, use_container_width=True)
        else:
            st.info("Nenhuma venda registrada nos produtos ainda.")