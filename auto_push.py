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

# Carrega as variáveis do arquivo .env
load_dotenv()

def increment_version(part="patch", version_path=".version"):
    """Lê o arquivo de versão, incrementa a parte correspondente (major, minor, patch) e salva."""
    try:
        if not os.path.exists(version_path):
            with open(version_path, "w") as f:
                f.write("1.0.0\n")
            print(f"[OK] Arquivo {version_path} criado com versão inicial 1.0.0")
            return "1.0.0"
            
        with open(version_path, "r") as f:
            version_str = f.read().strip()
            
        parts = version_str.split('.')
        if len(parts) != 3:
            print(f"Formato de versão inválido no arquivo {version_path}: {version_str}")
            sys.exit(1)
            
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        if part == "major":
            major += 1
            minor = 0
            patch = 0
        elif part == "minor":
            minor += 1
            patch = 0
        else: # patch
            patch += 1
            
        new_version = f"{major}.{minor}.{patch}"
        
        with open(version_path, "w") as f:
            f.write(new_version + "\n")
            
        print(f"[OK] Versão atualizada ({part}): {version_str} -> {new_version}")
        return new_version
    except Exception as e:
        print(f"Erro ao atualizar versão: {e}")
        sys.exit(1)

def run_git_command(command, check=True, capture_output=True):
    """Executa um comando git no terminal."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=check, 
            capture_output=capture_output, 
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.stdout:
            return result.stdout.strip()
        return ""
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Erro ao executar: {command}")
        print(e.stderr)
        sys.exit(1)

def determine_version_increment(diff_text):
    """Usa o Gemini para decidir se a mudança é 'major', 'minor' ou 'patch' baseando-se no diff."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "patch"
        
    client = genai.Client(api_key=api_key)
    prompt = f"""
    Você é um gerente de release sênior. 
    Analise o git diff abaixo e classifique as alterações em uma das seguintes categorias de versionamento semântico (SemVer):
    
    - 'major': Alterações incompatíveis com versões anteriores ou refatorações de grande escala na arquitetura do banco/sistema.
    - 'minor': Novas funcionalidades adicionadas (ex: novas páginas, novos componentes, novas rotinas de teste ou agentes) que são compatíveis com versões anteriores.
    - 'patch': Correções de bugs, ajustes de layout/CSS, documentação, ou refatorações pequenas.
    
    Retorne APENAS uma das três palavras: 'major', 'minor' ou 'patch'. Não inclua explicações, aspas ou markdown.
    
    GIT DIFF:
    {diff_text}
    """
    try:
        print("[IA] Analisando o diff para determinar o nível de incremento da versão...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        decision = response.text.strip().lower()
        if decision in ['major', 'minor', 'patch']:
            return decision
        return "patch"
    except Exception as e:
        print(f"[AVISO] Falha ao determinar o incremento por IA ({e}). Usando padrão 'patch'.")
        return "patch"

def generate_commit_message(diff_text, new_version):
    """Gera a mensagem de commit usando a API do Gemini."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERRO] Chave de API 'GEMINI_API_KEY' não encontrada no arquivo .env.")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Você é um desenvolvedor sênior. Baseado no git diff abaixo, gere uma mensagem de commit em Português (PT-BR) clara, concisa e direta.
    A mensagem deve iniciar citando a nova versão [v{new_version}] no início, seguida por uma descrição curta das alterações principais.
    Siga as boas práticas de commit (ex: '[v{new_version}] Adiciona testes para formatters e documenta a arquitetura').
    NÃO inclua explicações, markdown, aspas ou prefixos como 'Commit:'. Retorne APENAS a string da mensagem.
    
    GIT DIFF:
    {diff_text}
    """
    
    try:
        print("[IA] Gerando mensagem de commit com a Inteligência Artificial...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        message = response.text.strip()
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]
        if message.startswith("'") and message.endswith("'"):
            message = message[1:-1]
            
        return message
    except Exception as e:
        print(f"[ERRO] Erro ao comunicar com a API do Gemini: {e}")
        sys.exit(1)

def main():
    print("[START] Iniciando Auto Push Agent (Orquestrador)...")
    
    # 1. Adicionar arquivos ao staging temporariamente para ver o diff
    print("[GIT] Verificando modificações...")
    run_git_command("git add .")
    
    diff = run_git_command("git diff --cached")
    if not diff:
        print("[AVISO] Nenhuma alteração detectada para commitar.")
        sys.exit(0)
        
    # Limita o tamanho do diff se for gigante para não estourar o limite de tokens
    if len(diff) > 30000:
        diff_for_ai = diff[:30000] + "\n...[diff truncado devido ao tamanho]"
    else:
        diff_for_ai = diff
        
    # 2. Chamar o Agente de Testes
    print("\n" + "="*40)
    print("[Pipeline] Invocando o Agente de Testes...")
    python_exe = os.path.join("venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = "python"
        
    test_result = subprocess.run([python_exe, "test_agent.py"])
    if test_result.returncode != 0:
        print("[Pipeline] [ERRO] O Agente de Testes reportou falhas. O deploy foi abortado!")
        sys.exit(1)
    print("[Pipeline] [OK] Agente de Testes passou.")
    print("="*40 + "\n")
    
    # 3. Chamar o Agente de Documentação
    print("="*40)
    print("[Pipeline] Invocando o Agente de Documentação...")
    doc_result = subprocess.run([python_exe, "doc_agent.py"])
    if doc_result.returncode != 0:
        print("[Pipeline] [ERRO] O Agente de Documentação falhou. O deploy foi abortado!")
        sys.exit(1)
    print("[Pipeline] [OK] Agente de Documentação concluiu a atualização.")
    print("="*40 + "\n")
    
    # 4. Adicionar as documentações criadas/alteradas ao staging
    run_git_command("git add .")
    
    # Recalcula o diff completo (incluindo as documentações novas)
    full_diff = run_git_command("git diff --cached")
    if len(full_diff) > 30000:
        full_diff_for_ai = full_diff[:30000] + "\n...[diff truncado]"
    else:
        full_diff_for_ai = full_diff
        
    # 5. Decidir o incremento de versão por IA
    increment_type = determine_version_increment(diff_for_ai) # decide com base nas alterações originais de código
    
    # 6. Incrementa a versão no arquivo
    new_version = increment_version(increment_type)
    
    # Adiciona a atualização de versão ao staging
    run_git_command("git add .version")
    
    # 7. Gerar mensagem de commit por IA contendo a nova versão
    commit_message = generate_commit_message(full_diff_for_ai, new_version)
    print(f"[MSG] Mensagem gerada: {commit_message}")
    
    # 8. Commit
    print("[GIT] Realizando commit...")
    # Usa array para evitar problemas com aspas na linha de comando
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    
    # 9. Push
    print("[GIT] Enviando para o GitHub (git push origin master)...")
    run_git_command("git push origin master", capture_output=False) # Exibe o output no terminal
    
    # 10. Abrir Relatório no Navegador
    try:
        import webbrowser
        report_path = os.path.abspath("docs/test_report.html")
        if os.path.exists(report_path):
            print(f"\n[Pipeline] Abrindo relatório de testes no navegador: {report_path}")
            webbrowser.open("file://" + report_path)
        else:
            print(f"\n[Pipeline] [AVISO] Relatório HTML não encontrado em: {report_path}")
    except Exception as e:
        print(f"\n[Pipeline] Erro ao tentar abrir o navegador: {e}")
        
    print("\n" + "="*50)
    print("[OK] PIPELINE MULTIAGENTE CONCLUÍDO COM SUCESSO!")
    print(f"Versão de Deploy: {new_version} ({increment_type})")
    print(f"Mensagem de Commit: {commit_message}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
