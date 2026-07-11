# Regras de Automação do Projeto ControlValue

Você é instruído a seguir as seguintes diretrizes automáticas de encerramento de tarefas neste projeto:

## Execução Automática do Pipeline de Versionamento e Testes

Sempre que você concluir com sucesso qualquer alteração de código ou modificação solicitada pelo usuário no projeto:
1. **Você não deve encerrar a conversa sem antes executar o pipeline de agentes local.**
2. Execute obrigatoriamente o script `agent_push.py` no terminal usando o interpretador do ambiente virtual:
   ```powershell
   .\venv\Scripts\python.exe agent_push.py
   ```
3. O script `agent_push.py` é o orquestrador que automaticamente:
   - Invoca o `test_agent.py` para rodar e validar todos os testes (`pytest`) e gerar os relatórios em `docs/test_report.html`.
   - Invoca o `doc_agent.py` para analisar as mudanças no código e gerar ou atualizar as documentações em `README.md`, `docs/architecture.md` e `docs/manual_do_usuario.md`.
   - Incrementa o versionamento semântico (`.version`) utilizando IA para julgar a relevância da mudança.
   - Gera a mensagem de commit por IA e faz o commit e push das alterações para o repositório remoto.
4. **Nota de Consentimento:** O usuário já concedeu aprovação permanente para a execução deste pipeline ao fim de cada tarefa. Portanto, você **deve propor e rodar este comando diretamente**, sem necessidade de pedir permissão explícita em chat para o início de sua execução.
