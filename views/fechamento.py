import streamlit as st
import database as db
import pandas as pd
from datetime import datetime

def show_fechamento():
    st.header("🔒 Fechamento de Mês")
    st.caption("Trave meses anteriores para impedir edições e lançamentos retroativos.")

    # 1. Carregar status atual
    fechados = db.get_meses_fechados()
    
    # Gerar lista de meses (Do atual para trás, 12 meses)
    hoje = datetime.now()
    ano_atual = hoje.year
    mes_atual = hoje.month

    lista_meses = []

    # Loop de 2026 até o ano atual
    for ano in range(2026, ano_atual + 1):
        # Se for o ano corrente, vai até o mês atual. 
        # Se formos para 2027, o loop de 2026 vai até o mês 12.
        ultimo_mes = mes_atual if ano == ano_atual else 12
        
        for mes in range(1, ultimo_mes + 1):
            # Formata com zero à esquerda (Ex: 2026-01)
            mes_str = f"{ano}-{mes:02d}"
            lista_meses.append(mes_str)
            
    # Ordena para o mais recente ficar no topo da lista (UX melhor)
    lista_meses.sort(reverse=True)
    
    # 2. Interface de Controle
    c1, c2, c3 = st.columns([2, 1, 1])
    
    with c1:
        # Se a lista estiver vazia (antes de 2026?), evita erro
        if not lista_meses: lista_meses = ["2026-01"]
        mes_sel = st.selectbox("Selecione o Mês", lista_meses)
    
    # Verifica status do mês selecionado
    esta_fechado = mes_sel in fechados
    status_texto = "🔴 FECHADO" if esta_fechado else "🟢 ABERTO"
    
    with c2:
        st.markdown(f"**Status:** {status_texto}")
        
    with c3:
        st.write("") # Espaço
        st.write("")
        if esta_fechado:
            if st.button("🔓 Reabrir Mês"):
                if db.alternar_fechamento_mes(mes_sel, "Reabrir"):
                    st.success(f"Mês {mes_sel} reaberto!")
                    st.rerun()
        else:
            if st.button("🔒 Fechar Mês", type="primary"):
                if db.alternar_fechamento_mes(mes_sel, "Fechar"):
                    st.success(f"Mês {mes_sel} fechado com sucesso!")
                    st.rerun()

    st.divider()
    
    # 3. Visualização (Tabela Informativa)
    st.subheader("Histórico de Bloqueios")
    if fechados:
        df_fechados = pd.DataFrame(fechados, columns=["Mês/Ano Bloqueado"])
        df_fechados = df_fechados.sort_values("Mês/Ano Bloqueado", ascending=False)
        st.dataframe(df_fechados, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum mês fechado até o momento.")