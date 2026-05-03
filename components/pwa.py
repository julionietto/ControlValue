import streamlit as st
import streamlit.components.v1 as components

def inject_pwa():
    """
    Injeta as tags do PWA (manifest e service worker) no documento principal do Streamlit.
    Remove as tags padrão do Streamlit para evitar que o ícone 'Streamlit' apareça.
    """
    pwa_js = """
    <script>
    const parentDoc = window.parent.document;
    
    // 1. Função para remover tags existentes que conflitam
    function removeDefaultTags() {
        const selectors = [
            'link[rel="manifest"]',
            'link[rel="icon"]',
            'link[rel="apple-touch-icon"]',
            'meta[name="apple-mobile-web-app-title"]'
        ];
        selectors.forEach(sel => {
            const tags = parentDoc.querySelectorAll(sel);
            tags.forEach(t => t.remove());
        });
    }

    removeDefaultTags();

    // 2. Injetar Manifest Próprio (com versão para quebrar cache)
    const manifestLink = parentDoc.createElement('link');
    manifestLink.rel = 'manifest';
    manifestLink.href = './app/static/manifest.json?v=2';
    parentDoc.head.appendChild(manifestLink);
    
    // 3. Injetar Ícone para iPhone (Apple Touch Icon)
    const appleIcon = parentDoc.createElement('link');
    appleIcon.rel = 'apple-touch-icon';
    appleIcon.href = './app/static/icon-192x192.png';
    parentDoc.head.appendChild(appleIcon);

    // 4. Injetar Favicon Padrão
    const favicon = parentDoc.createElement('link');
    favicon.rel = 'icon';
    favicon.href = './app/static/icon-192x192.png';
    parentDoc.head.appendChild(favicon);

    // 5. Definir Título para Web App no iOS
    const metaTitle = parentDoc.createElement('meta');
    metaTitle.name = 'apple-mobile-web-app-title';
    metaTitle.content = 'ControlValue';
    parentDoc.head.appendChild(metaTitle);

    // 6. Registrar o Service Worker
    if ('serviceWorker' in window.parent.navigator) {
        window.parent.navigator.serviceWorker.register('./app/static/sw.js')
            .then(function(registration) {
                console.log('PWA: ServiceWorker registrado com sucesso.');
            })
            .catch(function(err) {
                console.error('PWA: Falha ao registrar o ServiceWorker:', err);
            });
    }
    </script>
    """
    # Injeta o componente invisível
    components.html(pwa_js, height=0, width=0)
