# pyrefly: ignore[missing-import]
import streamlit as st  # type: ignore
# pyrefly: ignore [missing-import]
import streamlit.components.v1 as components

def inject_pwa():
    """
    Injeta as tags do PWA (manifest e service worker) no documento principal do Streamlit.
    Remove as tags padrão do Streamlit para evitar que o ícone 'Streamlit' apareça.
    """
    pwa_js = """
    <script>
    function forceIdentity() {
        const parentDoc = window.parent.document;
        if (!parentDoc) return;

        // 1. Sobrescrever o Título (Remove o "- Streamlit")
        if (parentDoc.title.includes("Streamlit")) {
            parentDoc.title = "ControlValue";
        }

        // 2. Limpar tags conflitantes
        const selectors = [
            'link[rel="manifest"]', 
            'link[rel="icon"]', 
            'link[rel="apple-touch-icon"]',
            'meta[name="apple-mobile-web-app-title"]',
            'meta[name="application-name"]'
        ];
        
        selectors.forEach(sel => {
            parentDoc.querySelectorAll(sel).forEach(t => t.remove());
        });

        // 3. Injetar nossas tags no TOPO (Prioridade)
        const timestamp = Date.now();
        
        const manifest = parentDoc.createElement('link');
        manifest.rel = 'manifest';
        manifest.href = './app/static/manifest.json?v=' + timestamp;
        parentDoc.head.prepend(manifest);

        const appleIcon = parentDoc.createElement('link');
        appleIcon.rel = 'apple-touch-icon';
        appleIcon.href = './app/static/icon-192x192.png?v=' + timestamp;
        parentDoc.head.prepend(appleIcon);

        const favicon = parentDoc.createElement('link');
        favicon.rel = 'icon';
        favicon.href = './app/static/icon-192x192.png?v=' + timestamp;
        parentDoc.head.prepend(favicon);
        
        const metaTitle = parentDoc.createElement('meta');
        metaTitle.name = 'apple-mobile-web-app-title';
        metaTitle.content = 'ControlValue';
        parentDoc.head.prepend(metaTitle);

        const appName = parentDoc.createElement('meta');
        appName.name = 'application-name';
        appName.content = 'ControlValue';
        parentDoc.head.prepend(appName);
    }

    // Executa imediatamente e repete para vencer o carregamento assíncrono do Streamlit
    forceIdentity();
    setTimeout(forceIdentity, 500);
    setTimeout(forceIdentity, 1500);
    setTimeout(forceIdentity, 3000);

    // Registrar Service Worker
    if ('serviceWorker' in window.parent.navigator) {
        window.parent.navigator.serviceWorker.register('./app/static/sw.js?v=2')
            .then(function(reg) { console.log('PWA: OK'); })
            .catch(function(err) { console.log('PWA: Erro SW'); });
    }
    </script>
    """
    # Injeta o componente invisível
    components.html(pwa_js, height=0, width=0)
