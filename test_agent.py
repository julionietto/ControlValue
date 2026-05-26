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
from google import genai
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

def run_tests():
    """Executa a suíte de testes usando pytest e retorna (sucesso, stdout, stderr)"""
    print("[Test Agent] Executando suíte de testes com pytest...")
    # Usa o python do ambiente virtual para rodar o pytest
    python_exe = os.path.join("venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = "python" # fallback
        
    result = subprocess.run(
        [python_exe, "-m", "pytest", "-v"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    sucesso = (result.returncode == 0)
    return sucesso, result.stdout, result.stderr

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
