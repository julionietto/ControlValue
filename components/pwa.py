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
    
    // 1. Injetar o link do Manifest se não existir
    if (!parentDoc.querySelector('link[rel="manifest"]')) {
        const manifestLink = parentDoc.createElement('link');
        manifestLink.rel = 'manifest';
        // Tentativa de caminho relativo para maior compatibilidade
        manifestLink.href = './app/static/manifest.json';
        parentDoc.head.appendChild(manifestLink);
        console.log('PWA: Manifest link injetado via ./app/static/');
    }
    
    // 2. Registrar o Service Worker
    if ('serviceWorker' in window.parent.navigator) {
        window.parent.navigator.serviceWorker.register('./app/static/sw.js')
            .then(function(registration) {
                console.log('PWA: ServiceWorker registrado com sucesso no escopo:', registration.scope);
            })
            .catch(function(err) {
                console.error('PWA: Falha ao registrar o ServiceWorker:', err);
            });
    } else {
        console.log('PWA: Service Worker não é suportado neste navegador.');
    }
    </script>
    """
    # Injeta o componente invisível
    components.html(pwa_js, height=0, width=0)
