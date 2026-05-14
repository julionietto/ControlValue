import streamlit as st
import pandas as pd

if 'df_prov' not in st.session_state:
    st.session_state.df_prov = pd.DataFrame([
        {'ano': 2024, 'ticker': 'PETR4', 'mes': 1, 'valor': 10.0},
        {'ano': 2024, 'ticker': 'PETR4', 'mes': 2, 'valor': 20.0},
    ])

@st.dialog("Editar")
def dialog_editar_provento(ano, ticker, df_prov):
    meses_nomes_dict = {1: 'Janeiro', 2: 'Fevereiro'}
    meses_ordem = ['Janeiro', 'Fevereiro']
    
    selected_mes_nome = st.selectbox("Mês", meses_ordem, key=f"mes_edit_prov_{ano}_{ticker}")
    selected_mes_num = {v: k for k, v in meses_nomes_dict.items()}[selected_mes_nome]
    
    current_val = df_prov[(df_prov['ano'] == ano) & (df_prov['ticker'] == ticker) & (df_prov['mes'] == selected_mes_num)]
    default_val = float(current_val['valor'].iloc[0]) if not current_val.empty else 0.0
    
    novo_valor = st.number_input("Valor", value=default_val, key=f"val_edit_{ano}_{ticker}_{selected_mes_num}")
    
    st.write(f"selected_mes_num: {selected_mes_num}")
    st.write(f"default_val: {default_val}")
    st.write(f"novo_valor: {novo_valor}")

if st.button("Open"):
    dialog_editar_provento(2024, 'PETR4', st.session_state.df_prov)
