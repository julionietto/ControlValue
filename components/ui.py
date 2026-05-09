# pyrefly: ignore [missing-import]
import streamlit as st
import base64
import os
from utils.formatters import escape_html

def create_card(label, value, delta=None, small_font=False):
    """Cria um card premium usando HTML/CSS personalizado."""
    is_hidden = st.session_state.get('hide_values', False)
    if is_hidden:
        value = "R$ ••••••" if isinstance(value, str) and "R$" in value else "••••••"
        if delta:
            delta = "••••••"
            
    safe_label = escape_html(label)
    safe_value = escape_html(value)
    
    delta_html = ""
    if delta:
        safe_delta = escape_html(delta)
        # Tenta identificar se é positivo ou negativo para cor
        color_class = "delta-positive" if "+" in str(delta) or ("-" not in str(delta) and str(delta) != "0,00%") else "delta-negative"
        if str(delta) == "0,00%": color_class = ""
        delta_html = f'<div class="metric-delta {color_class}">{safe_delta}</div>'
    
    value_class = "metric-value-small" if small_font else "metric-value"
    label_class = "metric-label-small" if small_font else "metric-label"
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="{label_class}">{safe_label}</div>
        <div class="{value_class}">{safe_value}</div>
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
            if st.button("Alocação de Ativos", use_container_width=True):
                st.session_state.trigger_dialog_alocacao = True
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
    
    # Colunas: Logo (15%), Prefs (12%), Eye (5%), Título (48%), Ações/Login (20%)
    col_logo, col_prefs, col_eye, col_title, col_logout = st.columns([0.15, 0.12, 0.05, 0.48, 0.20], gap="small", vertical_alignment="center")
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
                
    with col_prefs:
        if st.button("Preferências", key="btn_prefs_header", help="Preferências de Tema"):
            st.session_state.trigger_dialog_preferencias = True
            st.rerun()
            
    with col_eye:
        is_hidden = st.session_state.get('hide_values', False)
        eye_img_name = "logoClosedEye.png" if is_hidden else "logoOpenEye.png"
        eye_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", eye_img_name)
        eye_b64 = get_base64_image(eye_path)
        if eye_b64:
            st.markdown(
                f"""
                <style>
                .st-key-eye_btn button {{
                    background-image: url('data:image/png;base64,{eye_b64}');
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: center;
                    background-color: transparent !important;
                    border: none !important;
                    width: 28px !important;
                    height: 28px !important;
                    box-shadow: none !important;
                    padding: 0 !important;
                    margin: 0 !important;
                    transition: transform 0.2s ease, filter 0.2s ease;
                }}
                .st-key-eye_btn button:hover {{
                    transform: scale(1.1);
                    filter: brightness(1.2);
                    background-color: transparent !important;
                    border: none !important;
                }}
                .st-key-eye_btn button p {{
                    display: none !important;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )
            if st.button("eye", key="eye_btn", help="Ocultar/Mostrar Valores"):
                st.session_state.hide_values = not is_hidden
                st.rerun()

    with col_title:
        safe_title = escape_html(title)
        safe_subtitle = escape_html(subtitle)
        st.markdown(f'''
            <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;">
                <h1 style="color: #ffffff; font-size: 2.25rem; margin: 0; padding: 0; line-height: 1.1;">{safe_title}</h1>
                <p style="color: #a1a1aa; font-size: 1rem; margin: 0; padding: 0; line-height: 1.2; margin-top: 4px;">{safe_subtitle}</p>
            </div>
        ''', unsafe_allow_html=True)
    
    with col_logout:
        st.markdown('<div class="social-header-container">', unsafe_allow_html=True)
        
        # Resolve caminhos
        img_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")
        ig_path = os.path.join(img_dir, "logo-instagram.jpg")
        em_path = os.path.join(img_dir, "logo-email.png")
        
        # Converte para Base64
        ig_b64 = get_base64_image(ig_path)
        em_b64 = get_base64_image(em_path)
        
        # HTML dos Ícones com tamanhos forçados
        ig_img = f'<img src="data:image/jpeg;base64,{ig_b64}" width="28" height="28" style="object-fit: contain;">' if ig_b64 else "IG"
        em_img = f'<img src="data:image/png;base64,{em_b64}" width="28" height="28" style="object-fit: contain;">' if em_b64 else "EM"

        st.markdown(
            f"""
            <div style="display: flex; gap: 10px; align-items: center; margin-right: 15px;">
                <span style="color: var(--text-secondary); font-size: 0.85rem; font-weight: 500; margin-right: 5px; opacity: 0.8;">Fale conosco:</span>
                <a href="https://www.instagram.com/controlvalueoficial/" target="_blank" class="social-link" title="Instagram">
                    {ig_img}
                </a>
                <a href="mailto:controlvalueoficial@gmail.com" class="social-link" title="E-mail">
                    {em_img}
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        render_profile_popover()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
