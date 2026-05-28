import os
import sys
# Força codificação UTF-8 no console para evitar UnicodeEncodeError no Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from google import genai
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

def run_tests():
    """Executa a suíte de testes usando pytest, exportando o resultado em XML, e retorna (sucesso, stdout, stderr)"""
    print("[Test Agent] Executando suíte de testes com pytest...")
    # Usa o python do ambiente virtual para rodar o pytest
    python_exe = os.path.join("venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = "python" # fallback
        
    # Garante que a pasta docs exista
    os.makedirs("docs", exist_ok=True)
    
    result = subprocess.run(
        [python_exe, "-m", "pytest", "-v", "--junitxml=tests/report.xml"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    sucesso = (result.returncode == 0)
    return sucesso, result.stdout, result.stderr

def generate_html_report(xml_path, html_path):
    """Lê o arquivo XML de JUnit gerado pelo pytest e monta um relatório HTML ultra-premium."""
    try:
        if not os.path.exists(xml_path):
            print(f"[Test Agent] [AVISO] XML de testes não encontrado em: {xml_path}")
            return False
            
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        if root.tag == "testsuites":
            testsuite = root.find("testsuite")
        else:
            testsuite = root
            
        if testsuite is None:
            print("[Test Agent] [AVISO] Nenhuma suite de testes encontrada no XML.")
            return False
            
        attrs = testsuite.attrib
        total = int(attrs.get("tests", 0))
        failures = int(attrs.get("failures", 0))
        errors = int(attrs.get("errors", 0))
        skipped = int(attrs.get("skipped", 0))
        passed = total - failures - errors - skipped
        duration = float(attrs.get("time", 0.0))
        timestamp = attrs.get("timestamp", datetime.now().isoformat())
        
        try:
            dt = datetime.fromisoformat(timestamp.split(".")[0])
            formatted_date = dt.strftime("%d/%m/%Y às %H:%M:%S")
        except Exception:
            formatted_date = timestamp
            
        test_cases = []
        for tc in testsuite.iter("testcase"):
            tc_name = tc.get("name")
            tc_class = tc.get("classname")
            tc_time = float(tc.get("time", 0.0))
            
            status = "PASSED"
            error_msg = ""
            traceback_text = ""
            
            failure = tc.find("failure")
            error = tc.find("error")
            skipped_node = tc.find("skipped")
            
            if failure is not None:
                status = "FAILED"
                error_msg = failure.get("message", "Falha no teste")
                traceback_text = failure.text or ""
            elif error is not None:
                status = "ERROR"
                error_msg = error.get("message", "Erro na execução")
                traceback_text = error.text or ""
            elif skipped_node is not None:
                status = "SKIPPED"
                error_msg = skipped_node.get("message", "Pulado")
                
            test_cases.append({
                "name": tc_name,
                "class": tc_class,
                "time": tc_time,
                "status": status,
                "error_msg": error_msg,
                "traceback": traceback_text
            })
            
        # Design ultra premium
        html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Execução de Testes - ControlValue</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 28, 45, 0.6);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent-pass: #10b981;
            --accent-fail: #ef4444;
            --accent-warn: #f59e0b;
            --glow-pass: rgba(16, 185, 129, 0.15);
            --glow-fail: rgba(239, 68, 68, 0.15);
            --shadow-premium: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 3rem 1.5rem;
            display: flex;
            justify-content: center;
            align-items: flex-start;
        }}
        
        .container {{
            width: 100%;
            max-width: 1000px;
            margin: 0 auto;
        }}
        
        header {{
            margin-bottom: 2.5rem;
            text-align: center;
        }}
        
        header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.025em;
            background: linear-gradient(135deg, #fff 0%, #a1a1aa 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        
        header p {{
            color: var(--text-secondary);
            font-size: 1.1rem;
        }}
        
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2.5rem;
        }}
        
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            backdrop-filter: blur(12px);
            border-radius: 18px;
            padding: 1.5rem;
            box-shadow: var(--shadow-premium);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}
        
        .card:hover {{
            transform: translateY(-4px);
            border-color: rgba(255, 255, 255, 0.15);
        }}
        
        .card-title {{
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }}
        
        .card-value {{
            font-size: 2.25rem;
            font-weight: 700;
            line-height: 1;
        }}
        
        .card.success {{
            border-color: rgba(16, 185, 129, 0.3);
            box-shadow: 0 8px 32px 0 var(--glow-pass);
        }}
        .card.success .card-value {{ color: var(--accent-pass); }}
        
        .card.failed {{
            border-color: rgba(239, 68, 68, 0.3);
            box-shadow: 0 8px 32px 0 var(--glow-fail);
        }}
        .card.failed .card-value {{ color: var(--accent-fail); }}
        
        .card.time .card-value {{ color: #60a5fa; }}
        
        .test-section {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            backdrop-filter: blur(12px);
            border-radius: 20px;
            box-shadow: var(--shadow-premium);
            padding: 2rem;
        }}
        
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .section-title {{
            font-size: 1.25rem;
            font-weight: 600;
        }}
        
        .timestamp {{
            font-size: 0.875rem;
            color: var(--text-secondary);
        }}
        
        .test-list {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}
        
        .test-item {{
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.25rem;
            background: rgba(15, 23, 42, 0.4);
            transition: all 0.2s ease;
        }}
        
        .test-item:hover {{
            background: rgba(15, 23, 42, 0.6);
        }}
        
        .test-info {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        
        .test-details {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }}
        
        .test-name {{
            font-weight: 600;
            font-size: 1.05rem;
        }}
        
        .test-class {{
            font-size: 0.825rem;
            color: var(--text-secondary);
        }}
        
        .test-meta {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }}
        
        .test-duration {{
            font-size: 0.875rem;
            color: var(--text-secondary);
            font-variant-numeric: tabular-nums;
        }}
        
        .badge {{
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        
        .badge.passed {{
            background-color: rgba(16, 185, 129, 0.15);
            color: var(--accent-pass);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}
        
        .badge.failed {{
            background-color: rgba(239, 68, 68, 0.15);
            color: var(--accent-fail);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}
        
        .badge.error {{
            background-color: rgba(239, 68, 68, 0.15);
            color: var(--accent-fail);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}
        
        .badge.skipped {{
            background-color: rgba(245, 158, 11, 0.15);
            color: var(--accent-warn);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}
        
        .error-details {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px dashed var(--border-color);
        }}
        
        .error-message {{
            font-size: 0.9rem;
            color: var(--accent-fail);
            font-weight: 500;
            margin-bottom: 0.75rem;
        }}
        
        .traceback {{
            background: #020617;
            padding: 1rem;
            border-radius: 8px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.85rem;
            line-height: 1.5;
            color: #ef4444;
            overflow-x: auto;
            white-space: pre-wrap;
            border: 1px solid rgba(239, 68, 68, 0.15);
            max-height: 300px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Relatório de Testes Automatizados</h1>
            <p>ControlValue Multiagent CI/CD Pipeline</p>
        </header>
        
        <div class="dashboard">
            <div class="card {'success' if failures + errors == 0 else 'failed'}">
                <div class="card-title">Resultado Geral</div>
                <div class="card-value">{'APROVADO' if failures + errors == 0 else 'REPROVADO'}</div>
            </div>
            <div class="card">
                <div class="card-title">Total de Testes</div>
                <div class="card-value">{total}</div>
            </div>
            <div class="card" style="border-color: rgba(16, 185, 129, 0.15);">
                <div class="card-title" style="color: var(--accent-pass);">Passaram</div>
                <div class="card-value" style="color: var(--accent-pass);">{passed}</div>
            </div>
            {f'''<div class="card" style="border-color: rgba(239, 68, 68, 0.15);">
                <div class="card-title" style="color: var(--accent-fail);">Falharam</div>
                <div class="card-value" style="color: var(--accent-fail);">{failures + errors}</div>
            </div>''' if failures + errors > 0 else ''}
            {f'''<div class="card" style="border-color: rgba(245, 158, 11, 0.15);">
                <div class="card-title" style="color: var(--accent-warn);">Pulados</div>
                <div class="card-value" style="color: var(--accent-warn);">{skipped}</div>
            </div>''' if skipped > 0 else ''}
            <div class="card time">
                <div class="card-title">Tempo Total</div>
                <div class="card-value">{duration:.2f}s</div>
            </div>
        </div>
        
        <div class="test-section">
            <div class="section-header">
                <h2 class="section-title">Detalhamento dos Testes</h2>
                <div class="timestamp">Executado em: <strong>{formatted_date}</strong></div>
            </div>
            
            <div class="test-list">
        """
        
        for tc in test_cases:
            badge_class = tc["status"].lower()
            error_section = ""
            if tc["status"] in ["FAILED", "ERROR"]:
                error_section = f"""
                <div class="error-details">
                    <div class="error-message">Erro: {escape_html(tc["error_msg"])}</div>
                    <pre class="traceback">{escape_html(tc["traceback"])}</pre>
                </div>
                """
                
            html_content += f"""
                <div class="test-item">
                    <div class="test-info">
                        <div class="test-details">
                            <span class="test-name">{tc["name"]}</span>
                            <span class="test-class">{tc["class"]}</span>
                        </div>
                        <div class="test-meta">
                            <span class="test-duration">{tc["time"]:.3f}s</span>
                            <span class="badge {badge_class}">{tc["status"]}</span>
                        </div>
                    </div>
                    {error_section}
                </div>
            """
            
        html_content += """
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"[Test Agent] [OK] Relatório HTML gerado em: {html_path}")
        return True
    except Exception as e:
        print(f"[Test Agent] [ERRO] Falha ao gerar relatório HTML: {e}")
        return False

def escape_html(text):
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")

def analyze_failures(stdout, stderr):
    """Envia os resultados de falha para o Gemini analisar e diagnosticar o erro."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[Test Agent] Aviso: GEMINI_API_KEY não configurada. Diagnóstico de IA ignorado.")
        return "GEMINI_API_KEY não encontrada no .env para diagnóstico por IA."
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Você é um agente de testes e depuração de IA sênior. 
    A execução dos testes unitários falhou no pytest. Analise a saída do erro e forneça um diagnóstico resumido.
    Aponte qual arquivo e linha causaram o erro, qual foi a exceção e dê uma sugestão direta de como corrigir o código.
    Seja breve, objetivo e escreva em Português (PT-BR).

    SAÍDA DOS TESTES (STDOUT):
    {stdout}

    SAÍDA DE ERRO (STDERR):
    {stderr}
    """
    
    try:
        print("[Test Agent] IA analisando a falha nos testes...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Erro ao comunicar com o Gemini para diagnóstico: {e}"

def main():
    print("[Test Agent] Iniciando verificação de testes...")
    sucesso, stdout, stderr = run_tests()
    
    # Gera o relatório HTML
    generate_html_report("tests/report.xml", "docs/test_report.html")
    
    if sucesso:
        print("[Test Agent] [OK] Todos os testes passaram com sucesso!")
        print(stdout)
        sys.exit(0)
    else:
        print("[Test Agent] [FALHA] Alguns testes falharam!")
        print(stdout)
        if stderr:
            print(stderr)
            
        diagnostico = analyze_failures(stdout, stderr)
        print("\n" + "="*50)
        print("[Test Agent] DIAGNÓSTICO E SUGESTÃO DA IA:")
        print(diagnostico)
        print("="*50 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
