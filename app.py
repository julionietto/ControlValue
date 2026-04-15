import streamlit as st

# Esconde menus e footer
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

import database as db
from streamlit_autorefresh import st_autorefresh
from components.ui import render_top_header
from components.global_dialogs import dialog_importar_ativos, dialog_importar_proventos, dialog_user_profile

db.init_db()

st.set_page_config(page_title="Ativos Financeiros", page_icon="📈", layout="wide")

# Injeção de CSS personalizado
import os
style_path = os.path.join(os.path.dirname(__file__), "style.css")
if os.path.exists(style_path):
    with open(style_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

from views.auth import render_auth_view
from views.admin import render_admin_view
from views.derivativos import render_derivativos_view
from views.proventos import render_proventos_view
from views.geral import render_visao_geral_view

# Lógica de Autenticação
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'table_key' not in st.session_state:
    st.session_state.table_key = 0

if not st.session_state.authenticated:
    render_auth_view()

# Inicializar variáveis de controle no session_state
if 'refresh_id' not in st.session_state:
    st.session_state.refresh_id = 0
if 'show_confirm_delete' not in st.session_state:
    st.session_state.show_confirm_delete = False
if 'delete_asset_info' not in st.session_state:
    st.session_state.delete_asset_info = None
if 'viewing_history' not in st.session_state:
    st.session_state.viewing_history = None # Armazena os dados do ativo sendo visualizado
if 'is_first_load' not in st.session_state:
    st.session_state.is_first_load = True

# Atualização automática a cada 5 minutos (300.000 ms)
st_autorefresh(interval=300000, key="datarefresh")

# ==============================
# MENU DE PERFIL
# ==============================

# Dispara os diálogos de forma segura por fora do popover para que funcionem bem após recriação
if st.session_state.pop('trigger_dialog_ativos', False):
    dialog_importar_ativos()
if st.session_state.pop('trigger_dialog_proventos', False):
    dialog_importar_proventos()
if st.session_state.pop('trigger_dialog_perfil', False):
    dialog_user_profile()

# ==============================
# ADMIN DASHBOARD
# ==============================
if st.session_state.get('is_admin', False):
    render_admin_view()
    st.stop()

# Verifica e cria dashboard do próximo ano (Automated Task)
if 'rollover_checked' not in st.session_state:
    if db.check_and_create_next_year_dashboard(st.session_state.user_id):
        st.session_state.refresh_id += 1
    st.session_state.rollover_checked = True

# Top Header com Título e Logout
render_top_header("Ativos Financeiros", "Controle de investimentos e análise de performance em tempo real.")
# Pega a navegação inicial do estado (que é inicializada posteriormente, mas tratamos aqui)
current_view = st.session_state.get('navigation_tab', 'Visão Geral')

# Área Principal - Divisão de Telas Baseada na Seleção
if current_view == "Proventos" or current_view == "Proventos Recebidos":
    render_proventos_view()

if current_view == "Derivativos":
    render_derivativos_view()

if current_view == "Visão Geral":
    render_visao_geral_view()
