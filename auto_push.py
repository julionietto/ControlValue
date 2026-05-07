import os
import sys
import subprocess
from google import genai
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

def increment_version(version_path=".version"):
    """Lê o arquivo de versão, incrementa o patch e salva."""
    try:
        with open(version_path, "r") as f:
            version_str = f.read().strip()
            
        parts = version_str.split('.')
        if len(parts) != 3:
            print(f"Formato de versão inválido no arquivo {version_path}: {version_str}")
            sys.exit(1)
            
        # Incrementa o último número (patch)
        parts[2] = str(int(parts[2]) + 1)
        new_version = ".".join(parts)
        
        with open(version_path, "w") as f:
            f.write(new_version + "\n")
            
        print(f"[OK] Versão atualizada: {version_str} -> {new_version}")
        return new_version
    except FileNotFoundError:
        print(f"Erro: Arquivo {version_path} não encontrado.")
        sys.exit(1)
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
            encoding='utf-8'
        )
        if result.stdout:
            return result.stdout.strip()
        return ""
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Erro ao executar: {command}")
        print(e.stderr)
        sys.exit(1)

def generate_commit_message(diff_text):
    """Gera a mensagem de commit usando a API do Gemini."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERRO] Chave de API 'GEMINI_API_KEY' não encontrada no arquivo .env.")
        print("Por favor, adicione sua chave de API do Google AI Studio no arquivo .env para usar este script.")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Você é um desenvolvedor sênior. Baseado no git diff abaixo, gere uma mensagem de commit em Português (PT-BR) clara, concisa e direta.
    Siga as boas práticas de commit (ex: 'Adiciona funcionalidade X', 'Corrige erro Y', 'Atualiza estilo Z').
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
        # Remove aspas se a IA ainda assim as colocar
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]
        if message.startswith("'") and message.endswith("'"):
            message = message[1:-1]
            
        return message
    except Exception as e:
        print(f"[ERRO] Erro ao comunicar com a API do Gemini: {e}")
        sys.exit(1)

def main():
    print("[START] Iniciando Auto Push Agent...")
    
    # 1. Atualizar a versão
    increment_version()
    
    # 2. Fazer o Git Add
    print("[GIT] Adicionando arquivos (git add .)...")
    run_git_command("git add .")
    
    # 3. Obter o Diff
    diff = run_git_command("git diff --cached")
    if not diff:
        print("[AVISO] Nenhuma alteração detectada para commitar.")
        # Reverte a versão se não houver mudanças (opcional)
        sys.exit(0)
        
    # Limita o tamanho do diff se for gigante para não estourar o limite de tokens
    if len(diff) > 30000:
        diff = diff[:30000] + "\n...[diff truncado devido ao tamanho]"
        
    # 4. Gerar Mensagem
    commit_message = generate_commit_message(diff)
    print(f"[MSG] Mensagem gerada: {commit_message}")
    
    # 5. Commit
    print("[GIT] Realizando commit...")
    # Usa array de argumentos para lidar com espaços e aspas na mensagem de forma segura
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    
    # 6. Push
    print("[GIT] Enviando para o GitHub (git push origin master)...")
    run_git_command("git push origin master", capture_output=False) # Exibe o output no terminal
    
    print("[OK] Processo concluído com sucesso!")

if __name__ == "__main__":
    main()
