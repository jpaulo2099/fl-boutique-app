import streamlit as st
import database as db
import time

def show_configuracoes():
    st.header("⚙️ Configurações do Sistema")
    st.caption("Ajuste os parâmetros de cálculo de preço e taxas financeiras.")

    # 1. Carregar Configs Atuais
    configs = db.get_configs()
    
    if not configs:
        st.warning("Não foi possível carregar as configurações. Verifique a aba 'Configuracoes' na planilha.")
        # Valores padrão de fallback para não quebrar a tela
        configs = {'taxa_cartao': 12.0, 'custo_fixo': 1.06, 'markup': 2.0, 'taxa_extra': 1.12}

    with st.form("form_configs"):
        st.subheader("💳 Financeiro")
        c1, c2 = st.columns(2)
        with c1:
            taxa_cartao = st.number_input("Taxa Média do Cartão (%)", 
                                          value=configs.get('taxa_cartao', 12.0), 
                                          step=0.1, format="%.2f",
                                          help="Usado para calcular o 'Caixa Líquido' no Dashboard.")
            
        st.divider()
        st.subheader("🏷️ Precificação (Sugestão)")
        st.markdown("Fórmula: `(Custo + Custo Fixo) * Markup * Taxa Extra`")
        
        c3, c4, c5 = st.columns(3)
        with c3:
            custo_fixo = st.number_input("Custo Fixo (R$)", 
                                         value=configs.get('custo_fixo', 1.06),
                                         step=0.01, format="%.2f",
                                         help="Valor somado ao custo da peça (Ex: Embalagem, Etiqueta).")
        with c4:
            markup = st.number_input("Markup (Multiplicador)", 
                                     value=configs.get('markup', 2.0),
                                     step=0.1, format="%.2f",
                                     help="Multiplicador de lucro. 2.0 significa 100% sobre o custo ajustado.")
        with c5:
            taxa_extra = st.number_input("Taxa Extra (Multiplicador)", 
                                         value=configs.get('taxa_extra', 1.12),
                                         step=0.01, format="%.2f",
                                         help="Multiplicador final (Ex: 1.12 para cobrir 12% de taxas/impostos).")

        # Botão Salvar
        st.write("")
        if st.form_submit_button("💾 Salvar Novos Parâmetros"):
            novos_dados = {
                'taxa_cartao': taxa_cartao,
                'custo_fixo': custo_fixo,
                'markup': markup,
                'taxa_extra': taxa_extra
            }
            
            if db.save_configs(novos_dados):
                st.success("Configurações atualizadas com sucesso!")
                time.sleep(1.5)
                st.rerun()