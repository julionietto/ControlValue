import streamlit as st
import streamlit.components.v1 as components
import json

def biometric_register_component(options_json):
    """Componente para capturar o registro biométrico escapando do iframe do Streamlit."""
    js_code = f"""
        (function() {{
            const options = {options_json};
            
            function base64urlToUint8Array(base64url) {{
                const padding = '='.repeat((4 - base64url.length % 4) % 4);
                const base64 = (base64url + padding).replace(/-/g, '+').replace(/_/g, '/');
                const rawData = window.atob(base64);
                return Uint8Array.from([...rawData].map(char => char.charCodeAt(0)));
            }}

            options.challenge = base64urlToUint8Array(options.challenge);
            options.user.id = base64urlToUint8Array(options.user.id);
            if (options.excludeCredentials) {{
                options.excludeCredentials.forEach(c => c.id = base64urlToUint8Array(c.id));
            }}

            window.navigator.credentials.create({{ publicKey: options }})
                .then(function(credential) {{
                    const response = {{
                        id: credential.id,
                        rawId: btoa(String.fromCharCode.apply(null, new Uint8Array(credential.rawId))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, ''),
                        type: credential.type,
                        response: {{
                            attestationObject: btoa(String.fromCharCode.apply(null, new Uint8Array(credential.response.attestationObject))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, ''),
                            clientDataJSON: btoa(String.fromCharCode.apply(null, new Uint8Array(credential.response.clientDataJSON))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
                        }}
                    }};
                    const params = new URLSearchParams(window.location.search);
                    params.set('webauthn_reg_data', JSON.stringify(response));
                    window.location.search = params.toString();
                }})
                .catch(function(err) {{
                    alert('Erro de Biometria: ' + err.message);
                }});
        }})();
    """.replace('\n', ' ').replace('"', "'")

    # Hack de injeção no nível superior (escapa do iframe)
    st.markdown(f'<img src="x" onerror="{js_code}" style="display:none;">', unsafe_allow_html=True)

def biometric_authenticate_component(options_json):
    """Componente para capturar a autenticação biométrica escapando do iframe do Streamlit."""
    js_code = f"""
        (function() {{
            const options = {options_json};
            
            function base64urlToUint8Array(base64url) {{
                const padding = '='.repeat((4 - base64url.length % 4) % 4);
                const base64 = (base64url + padding).replace(/-/g, '+').replace(/_/g, '/');
                const rawData = window.atob(base64);
                return Uint8Array.from([...rawData].map(char => char.charCodeAt(0)));
            }}

            options.challenge = base64urlToUint8Array(options.challenge);
            if (options.allowCredentials) {{
                options.allowCredentials.forEach(c => c.id = base64urlToUint8Array(c.id));
            }}

            window.navigator.credentials.get({{ publicKey: options }})
                .then(function(assertion) {{
                    const response = {{
                        id: assertion.id,
                        rawId: btoa(String.fromCharCode.apply(null, new Uint8Array(assertion.rawId))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, ''),
                        type: assertion.type,
                        response: {{
                            authenticatorData: btoa(String.fromCharCode.apply(null, new Uint8Array(assertion.response.authenticatorData))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, ''),
                            clientDataJSON: btoa(String.fromCharCode.apply(null, new Uint8Array(assertion.response.clientDataJSON))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, ''),
                            signature: btoa(String.fromCharCode.apply(null, new Uint8Array(assertion.response.signature))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, ''),
                            userHandle: assertion.response.userHandle ? btoa(String.fromCharCode.apply(null, new Uint8Array(assertion.response.userHandle))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '') : null
                        }}
                    }};
                    const params = new URLSearchParams(window.location.search);
                    params.set('webauthn_auth_data', JSON.stringify(response));
                    window.location.search = params.toString();
                }})
                .catch(function(err) {{
                    alert('Erro de Biometria: ' + err.message);
                }});
        }})();
    """.replace('\n', ' ').replace('"', "'")

    # Hack de injeção no nível superior (escapa do iframe)
    st.markdown(f'<img src="x" onerror="{js_code}" style="display:none;">', unsafe_allow_html=True)

def listen_webauthn_events():
    """Inativo nesta versão, pois a injeção via Markdown já lida com a URL diretamente."""
    pass
