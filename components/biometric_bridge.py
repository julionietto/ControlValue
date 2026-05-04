import streamlit as st
import streamlit.components.v1 as components
import json

def biometric_register_component(options_json):
    """Componente para capturar o registro biométrico do navegador."""
    js_code = f"""
    <script>
    const options = {options_json};
    
    // Converte campos base64url de volta para Uint8Array
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

    navigator.credentials.create({{ publicKey: options }})
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
            window.parent.postMessage({{
                type: 'webauthn_register_success',
                data: JSON.stringify(response)
            }}, '*');
        }})
        .catch(function(err) {{
            window.parent.postMessage({{
                type: 'webauthn_error',
                data: err.message
            }}, '*');
        }});
    </script>
    """
    components.html(js_code, height=0)

def biometric_authenticate_component(options_json):
    """Componente para capturar a autenticação biométrica do navegador."""
    js_code = f"""
    <script>
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

    navigator.credentials.get({{ publicKey: options }})
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
            window.parent.postMessage({{
                type: 'webauthn_auth_success',
                data: JSON.stringify(response)
            }}, '*');
        }})
        .catch(function(err) {{
            window.parent.postMessage({{
                type: 'webauthn_error',
                data: err.message
            }}, '*');
        }});
    </script>
    """
    components.html(js_code, height=0)

def listen_webauthn_events():
    """Script para capturar as mensagens do iframe e salvar no session_state."""
    js_listener = """
    <script>
    window.addEventListener('message', function(event) {
        if (event.data.type === 'webauthn_register_success') {
            const params = new URLSearchParams(window.location.search);
            params.set('webauthn_reg_data', event.data.data);
            window.parent.location.search = params.toString();
        }
        if (event.data.type === 'webauthn_auth_success') {
            const params = new URLSearchParams(window.location.search);
            params.set('webauthn_auth_data', event.data.data);
            window.parent.location.search = params.toString();
        }
        if (event.data.type === 'webauthn_error') {
            console.error('WebAuthn Error:', event.data.data);
            // Poderíamos passar o erro via query param se necessário
        }
    });
    </script>
    """
    # Usamos o streamlit_javascript se disponível, ou components.html no parent
    # Para simplificar, vamos usar st.query_params no Python para ler o resultado
    # Mas precisamos que o JS injete isso na URL ou use um truque.
    # O Streamlit 1.30+ tem st.query_params.
    
    # Truque para injetar na URL sem recarregar a página inteira se possível, 
    # mas o Streamlit recarrega ao mudar query params.
    components.html(js_listener, height=0)
