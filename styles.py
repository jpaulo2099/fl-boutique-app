import streamlit as st

def apply_custom_style():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] { font-family: 'Montserrat', sans-serif; }
        .stApp { 
            background-color: #FDF2F4; 
            background-image: linear-gradient(180deg, #FDF2F4 0%, #FFFFFF 100%);
        }
        
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF;
            box-shadow: 2px 0 10px rgba(0,0,0,0.05);
            border-right: none;
        }
        
        h1, h2, h3 { color: #5C3A3B !important; font-weight: 600 !important; }
        p, label, span, li, .stMarkdown, .stText, th, td { color: #4A4A4A !important; }
        
        /* Cards de Métricas */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF;
            padding: 15px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            border: 1px solid #F0F0F0;
        }
        div[data-testid="stMetricValue"] { color: #5C3A3B !important; }

        /* Inputs */
        .stTextInput input, .stNumberInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E0E0E0 !important;
            border-radius: 10px !important;
            color: #333 !important;
        }
        
        /* Botões */
        .stButton > button {
            background: linear-gradient(90deg, #E69496 0%, #D4787A 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 25px !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 10px rgba(212, 120, 122, 0.3);
        }
        .stButton > button:hover { transform: scale(1.02); }

        /* Tabelas */
        [data-testid="stDataFrame"] {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            border: 1px solid #F0F0F0;
        }
        .stAlert { border-radius: 12px; border: none; }
        </style>
    """, unsafe_allow_html=True)