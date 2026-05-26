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

def run_git_command(command):
    """Executa um comando git no terminal."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"[Doc Agent] Erro ao executar comando git: {e}")
        return ""

def generate_or_update_doc(diff_text, file_path, doc_context=""):
    """Usa o Gemini para gerar ou atualizar a documentação com base no diff."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[Doc Agent] [ERRO] GEMINI_API_KEY não configurada no arquivo .env.")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    
    file_exists = os.path.exists(file_path)
    current_content = ""
    if file_exists:
        with open(file_path, "r", encoding="utf-8") as f:
            current_content = f.read()
            
    prompt = f"""
    Você é um redator técnico e arquiteto de software de IA. 
    Seu objetivo é criar ou atualizar a documentação do projeto baseando-se nas alterações de código fornecidas pelo git diff.
    
    Caminho do arquivo de documentação a ser escrito: {file_path}
    O arquivo existe atualmente? {'Sim' if file_exists else 'Não'}
    
    DIRETRIZ DE CONTEXTO ADICIONAL PARA ESTE ARQUIVO:
    {doc_context or 'Nenhuma diretriz especial.'}
    
    CONTEÚDO ATUAL DA DOCUMENTAÇÃO (se aplicável):
    \"\"\"
    {current_content}
    \"\"\"

    GIT DIFF DE ALTERAÇÕES RECENTES:
    \"\"\"
    {diff_text}
    \"\"\"
    
    INSTRUÇÕES:
    1. Se o arquivo NÃO existia, crie um documento markdown completo, profissional e estruturado para o arquivo: {file_path}.
    2. Se o arquivo já existia, atualize-o integrando as novas alterações do git diff de forma fluida nas seções correspondentes, sem apagar informações válidas pré-existentes.
    3. Escreva em Português (PT-BR).
    4. NÃO inclua explicações extras ou blocos de código markdown contendo o arquivo de saída (ex: ```markdown). Retorne APENAS o conteúdo markdown limpo para ser gravado diretamente no arquivo.
    """
    
    try:
        print(f"[Doc Agent] Gerando/Atualizando documentação para: {os.path.basename(file_path)}...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        content = response.text.strip()
        
        # Limpeza rápida de marcadores markdown extras se a IA colocar
        if content.startswith("```markdown"):
            content = content[11:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Garante que a pasta pai exista
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content + "\n")
            
        print(f"[Doc Agent] [OK] Arquivo gravado com sucesso: {file_path}")
        return True
    except Exception as e:
        print(f"[Doc Agent] [ERRO] Erro ao comunicar com o Gemini: {e}")
        return False

def main():
    print("[Doc Agent] Iniciando geração de documentação...")
    
    # 1. Obter staged diff
    diff = run_git_command("git diff --cached")
    if not diff:
        print("[Doc Agent] Nenhuma alteração staged detectada. Verificando unstaged diff...")
        diff = run_git_command("git diff")
        if not diff:
            print("[Doc Agent] [AVISO] Nenhuma alteração detectada para documentar.")
            sys.exit(0)
            
    # Criar pasta /docs se não existir
    os.makedirs("docs", exist_ok=True)
    
    # 2. Atualizar README.md principal (Técnico / Setup)
    generate_or_update_doc(
        diff, 
        "README.md",
        doc_context="Foque na perspectiva técnica do projeto, incluindo requisitos de ambiente, inicialização de banco de dados e execução dos scripts de pipeline."
    )
    
    # 3. Atualizar docs/architecture.md (Técnico / Arquitetural)
    generate_or_update_doc(
        diff, 
        "docs/architecture.md",
        doc_context="Foque na perspectiva técnica da arquitetura, incluindo fluxo de dados, estrutura de diretórios e o funcionamento dos agentes autônomos."
    )
    
    # 4. Atualizar docs/manual_do_usuario.md (Usuário Leigo / Negócio)
    generate_or_update_doc(
        diff, 
        "docs/manual_do_usuario.md", 
        doc_context="Este é um Manual do Usuário voltado para pessoas leigas. NÃO inclua termos de programação, instalações de console, scripts ou banco de dados. Foque em explicar novas funcionalidades ou mudanças visuais na perspectiva do usuário final de negócio do app Streamlit."
    )
    
    print("[Doc Agent] Processo de documentação concluído com sucesso!")

if __name__ == "__main__":
    main()
