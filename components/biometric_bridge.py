import streamlit as st
import streamlit.components.v1 as components
import json

def biometric_register_component(options_json):
    """Componente de diagnóstico para verificar execução de JS."""
    js_code = f"""
        (function() {{
            alert('DIAGNÓSTICO: Script de Registro Iniciado!');
            try {{
                const options = {options_json};
                // ... resto do código ...
                alert('DIAGNÓSTICO: Navigator detectado: ' + !!window.navigator.credentials);
                
                // Tenta o registro
                // ... (mantendo a lógica mas com alertas)
            }} catch(e) {{
                alert('ERRO NO SCRIPT: ' + e.message);
            }}
        }})();
    """.replace('\n', ' ').replace('"', "'")
    st.markdown(f'<img src="x" onerror="{js_code}" style="display:none;">', unsafe_allow_html=True)

def biometric_authenticate_component(options_json):
    """Componente de diagnóstico para verificar execução de JS."""
    js_code = f"""
        (function() {{
            alert('DIAGNÓSTICO: Script de Autenticação Iniciado!');
            try {{
                const options = {options_json};
                // ... resto do código ...
            }} catch(e) {{
                alert('ERRO NO SCRIPT: ' + e.message);
            }}
        }})();
    """.replace('\n', ' ').replace('"', "'")
    st.markdown(f'<img src="x" onerror="{js_code}" style="display:none;">', unsafe_allow_html=True)

def listen_webauthn_events():
    """Inativo nesta versão, pois a injeção via Markdown já lida com a URL diretamente."""
    pass
