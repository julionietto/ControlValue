import streamlit as st
import streamlit.components.v1 as components

def inject_pwa():
    """
    Injeta as tags do PWA (manifest e service worker) no documento principal do Streamlit.
    Como o Streamlit roda dentro de um iframe, precisamos acessar window.parent.
    """
    pwa_js = """
    <script>
    const parentDoc = window.parent.document;
    
    // 1. Injetar o link do Manifest
    if (!parentDoc.querySelector('link[rel="manifest"]')) {
        const manifestLink = parentDoc.createElement('link');
        manifestLink.rel = 'manifest';
        manifestLink.href = '/app/static/manifest.json';
        parentDoc.head.appendChild(manifestLink);
    }
    
    // 2. Registrar o Service Worker
    if ('serviceWorker' in window.parent.navigator) {
        window.parent.navigator.serviceWorker.register('/app/static/sw.js', { scope: '/' })
            .then(function(registration) {
                console.log('PWA: ServiceWorker registrado com sucesso:', registration.scope);
            })
            .catch(function(err) {
                console.log('PWA: Falha ao registrar o ServiceWorker:', err);
            });
    }
    </script>
    """
    # Injeta o componente invisível
    components.html(pwa_js, height=0, width=0)
