import streamlit as st
import base64
import os
from utils.formatters import escape_html

def create_card(label, value, delta=None):
    """Cria um card premium usando HTML/CSS personalizado."""
    safe_label = escape_html(label)
    safe_value = escape_html(value)
    
    delta_html = ""
    if delta:
        safe_delta = escape_html(delta)
        # Tenta identificar se é positivo ou negativo para cor
        color_class = "delta-positive" if "+" in str(delta) or ("-" not in str(delta) and str(delta) != "0,00%") else "delta-negative"
        if str(delta) == "0,00%": color_class = ""
        delta_html = f'<div class="metric-delta {color_class}">{safe_delta}</div>'
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{safe_label}</div>
        <div class="metric-value">{safe_value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

def get_base64_image(image_path):
    """Lê uma imagem e retorna sua representação em base64."""
    try:
        import os
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        import logging
        logging.error(f"Erro ao carregar imagem {image_path}: {e}")
    return ""

def render_profile_popover():
    username_display = st.session_state.get('username', 'Perfil')
    
    label_suffix = "\u200b" * (st.session_state.get('pop_ctrl', 0) % 2)
    with st.popover(f"👤 {username_display}{label_suffix}", use_container_width=True):
        if st.session_state.get('is_admin', False):
            if st.button("Seu Perfil", use_container_width=True):
                st.session_state.trigger_dialog_perfil = True
                st.session_state.pop_ctrl = st.session_state.get('pop_ctrl', 0) + 1
                st.rerun()
            if st.button("Sair", type="primary", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        else:
            if st.button("Visão Geral", use_container_width=True):
                st.session_state.navigation_tab = "Visão Geral"
                st.session_state.viewing_history = None
                st.session_state.pop_ctrl = st.session_state.get('pop_ctrl', 0) + 1
                st.rerun()
            if st.button("Proventos", use_container_width=True):
                st.session_state.navigation_tab = "Proventos"
                st.session_state.viewing_history = None
                st.session_state.pop_ctrl = st.session_state.get('pop_ctrl', 0) + 1
                st.rerun()
            if st.button("Derivativos", use_container_width=True):
                st.session_state.navigation_tab = "Derivativos"
                st.session_state.viewing_history = None
                st.session_state.pop_ctrl = st.session_state.get('pop_ctrl', 0) + 1
                st.rerun()
            if st.button("Importar Ativos", use_container_width=True):
                st.session_state.trigger_dialog_ativos = True
                st.session_state.pop_ctrl = st.session_state.get('pop_ctrl', 0) + 1
                st.rerun()
            if st.button("Importar Proventos", use_container_width=True):
                st.session_state.trigger_dialog_proventos = True
                st.session_state.pop_ctrl = st.session_state.get('pop_ctrl', 0) + 1
                st.rerun()
            if st.button("Seu Perfil", use_container_width=True):
                st.session_state.trigger_dialog_perfil = True
                st.session_state.pop_ctrl = st.session_state.get('pop_ctrl', 0) + 1
                st.rerun()
            if st.button("Sair", type="primary", use_container_width=True):
                st.session_state.clear()
                st.rerun()

        try:
            version = "Versão 1.0.0"
            if os.path.exists(".version"):
                with open(".version", "r", encoding="utf-8") as f:
                    version = f.read().strip()
            safe_version = escape_html(version)
            st.markdown(f"<div style='text-align: center; font-size: 0.75rem; color: #a1a1aa; padding-top: 8px; margin-top: 8px; border-top: 1px solid #27272a;'>{safe_version}</div>", unsafe_allow_html=True)
        except Exception as e:
            import logging
            logging.error(f"Erro ao ler versão: {e}")

def render_top_header(title, subtitle):
    """Renderiza o cabeçalho superior unificado com o logo home, título e perfil."""
    
    col_logo, col_title, col_logout = st.columns([0.15, 0.7, 0.15], gap="small", vertical_alignment="center")
    with col_logo:
        # Resolve o caminho da imagem de forma robusta
        image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "logoHome.png")
        logo_b64 = get_base64_image(image_path)
        if logo_b64:
            st.markdown(
                f"""
                <style>
                .st-key-home_logo_btn button {{
                    background-image: url('data:image/png;base64,{logo_b64}');
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: left center;
                    background-color: transparent !important;
                    border: none !important;
                    width: 192px !important;
                    height: 64px !important;
                    box-shadow: none !important;
                    padding: 0 !important;
                    margin: 0 !important;
                    transition: transform 0.2s ease, filter 0.2s ease;
                }}
                .st-key-home_logo_btn button:hover {{
                    transform: scale(1.05);
                    filter: brightness(1.2);
                    background-color: transparent !important;
                    border: none !important;
                }}
                .st-key-home_logo_btn button p {{
                    display: none !important;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )
            if st.button("home", key="home_logo_btn", help="Voltar para Visão Geral"):
                st.session_state.navigation_tab = "Visão Geral"
                st.session_state.viewing_history = None
                st.rerun()
        else:
            # Fallback se a imagem não for encontrada
            if st.button("🏠", key="home_fallback_btn", help="Voltar para Visão Geral"):
                st.session_state.navigation_tab = "Visão Geral"
                st.session_state.viewing_history = None
                st.rerun()
                
    with col_title:
        safe_title = escape_html(title)
        safe_subtitle = escape_html(subtitle)
        st.markdown(f'''
            <div style="display: flex; flex-direction: column; justify-content: center;">
                <h1 style="color: #ffffff; font-size: 2.25rem; margin: 0; padding: 0; line-height: 1.1;">{safe_title}</h1>
                <p style="color: #a1a1aa; font-size: 1rem; margin: 0; padding: 0; line-height: 1.2; margin-top: 4px;">{safe_subtitle}</p>
            </div>
        ''', unsafe_allow_html=True)
    
    with col_logout:
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        render_profile_popover()
        st.markdown('</div>', unsafe_allow_html=True)
