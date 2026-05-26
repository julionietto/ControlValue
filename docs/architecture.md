# Arquitetura do Sistema de Deploy Multiagente

## 1. Introdução

Este documento detalha a arquitetura do sistema de auto-push, que evoluiu para um robusto pipeline de deploy multiagente. O objetivo principal do sistema é automatizar e inteligentemente orquestrar o processo de integração contínua (CI) e entrega contínua (CD), desde a detecção de mudanças no código até o push final para o repositório, garantindo qualidade, consistência e conformidade com as práticas de versionamento semântico.

A arquitetura atual integra múltiplos "agentes" autônomos, cada um com uma responsabilidade específica, coordenados por um orquestrador central. Essa abordagem visa aumentar a confiabilidade do deploy, automatizar tarefas repetitivas e incorporar inteligência artificial para decisões estratégicas, como o versionamento de releases e a geração de mensagens de commit. O sistema também incorpora melhorias para garantir sua robustez em diferentes ambientes operacionais, como a compatibilidade com a codificação UTF-8 em consoles do Windows.

## 2. Visão Geral da Arquitetura

O sistema é concebido como um orquestrador que coordena uma série de agentes especializados. Cada agente é responsável por uma etapa específica do pipeline de deploy, garantindo modularidade e capacidade de extensão. A inteligência artificial, através da API do Google Gemini, é um componente central para a tomada de decisões e geração de conteúdo, e também para o diagnóstico proativo de problemas.

```
+---------------------+
|     Orquestrador    |
|   (auto_push.py)    |
+----------+----------+
           |
           | 1. Detecção de Mudanças (git diff inicial)
           |    e Staging Temporário
           |
+----------V----------+
| Agente de Testes    |<-----+   Pytest          |
|  (test_agent.py)    |      |   (Execução)      |
|                     |<-----+   Google Gemini   |
|                     |      |   (Diagnóstico)   |
+----------+----------+      +-------------------+
           |
           | 2. Validação de Código (com IA para diagnóstico)
           |
+----------V----------+
| Agente de Docs      |<-----+   Google Gemini   |
|  (doc_agent.py)     |      |   (Modelo GenAI)  |
+----------+----------+      +-------------------+
           |
           | 3. Atualização de Documentação (README.md, docs/architecture.md)
           |    e Re-staging de todas as mudanças
           |
+----------V----------+
| Agente de Version.  |<-----+   Google Gemini   |
| (via Orquestrador)  |      |   (Modelo GenAI)  |
+----------+----------+      +-------------------+
           |
           | 4. Decisão e Atualização da Versão (.version)
           |
+----------V----------+
| Agente de Commit    |<-----+   Google Gemini   |
| (via Orquestrador)  |      |   (Modelo GenAI)  |
+----------+----------+      +-------------------+
           |
           | 5. Commit e Push (Git)
           |
+----------V----------+
|  Repositório Remoto |
|      (GitHub)       |
+---------------------+
```

### 2.1. Componentes Principais

*   **Orquestrador (`auto_push.py`):** O coração do sistema. Ele gerencia o fluxo de execução completo, *invocando* os agentes externos em sequência, lida com a lógica central de versionamento e interage diretamente com o Git para operações de commit e push. Implementa a lógica para determinar o tipo de incremento de versão (major, minor, patch) e gerar a mensagem de commit, utilizando a IA. Possui tratamento para forçar a codificação UTF-8 na saída do console, melhorando a compatibilidade em diferentes sistemas operacionais.
*   **Agente de Testes (`test_agent.py`):** Um agente externo invocado pelo orquestrador. Responsável por executar os testes automatizados do projeto (`pytest`). O pipeline só prossegue se todos os testes forem aprovados, garantindo a qualidade e estabilidade do código. Em caso de falha, ele utiliza a API do Google Gemini para analisar os logs de erro e fornecer um diagnóstico resumido e sugestões de correção.
*   **Agente de Documentação (`doc_agent.py`):** Um agente externo invocado pelo orquestrador. Encarregado de atualizar e/ou criar diversos arquivos de documentação do projeto (como `README.md`, `docs/architecture.md`, `docs/manual_do_usuario.md` e outros guias), baseando-se nas mudanças de código. Este agente assegura que a documentação esteja sempre sincronizada com o estado atual do software, utilizando a inteligência artificial para gerar e integrar o conteúdo de forma contextual, agora com diretrizes contextuais específicas para cada arquivo (e.g., perspectiva técnica, manual de usuário leigo) que guiam a IA na geração de conteúdo mais preciso e direcionado.
*   **Agente de Versionamento (Lógica `determine_version_increment` e `increment_version` no Orquestrador):** A função `determine_version_increment` utiliza a inteligência artificial (Google Gemini) para analisar o `git diff` das alterações de código *originais* (antes da geração de documentação) e decidir qual parte do versionamento semântico (`major`, `minor`, `patch`) deve ser incrementada. Em caso de falha da IA ou chave de API não configurada, o incremento padrão é `patch`. A função `increment_version` então aplica esta decisão, realizando incrementos `major` e `minor` que resetam as partes seguintes (ex: `1.2.3` com `minor` vira `1.3.0`). Ele também inicializa o arquivo `.version` para "1.0.0" se não existir.
*   **Agente de Geração de Mensagem de Commit (Função `generate_commit_message` no Orquestrador):** Emprega a inteligência artificial (Google Gemini) para gerar mensagens de commit claras e concisas. A mensagem é formatada para iniciar obrigatoriamente com a nova versão do projeto (ex: `[vX.Y.Z] Adiciona...`), baseando-se no `git diff` *completo* (incluindo as alterações de código, documentação e versão).
*   **Integração com Git:** A comunicação com o sistema de controle de versão é feita através de comandos `subprocess`, utilizando `text=True`, `encoding='utf-8'` e `errors='replace'` para garantir operações como `add`, `diff`, `commit` e `push` com robustez de codificação em diferentes sistemas operacionais.
*   **API do Google Gemini:** Utilizada como o motor de inteligência artificial generativa para:
    *   Análise de `git diff` para decisão de versionamento (`major`, `minor`, `patch`).
    *   Geração de mensagens de commit.
    *   Criação/atualização de documentos (no `doc_agent.py`).
    *   Diagnóstico e sugestão de correção para falhas em testes (no `test_agent.py`).

## 3. Fluxo de Execução do Pipeline Multiagente

O orquestrador (`auto_push.py`) executa as seguintes etapas para cada deploy:

1.  **Detecção Inicial de Mudanças e Staging Temporário:**
    *   O sistema primeiro adiciona todas as modificações atuais ao *staging area* (`git add .`) para uma análise preliminar.
    *   Em seguida, gera um `git diff --cached` para identificar as alterações pendentes. Este `diff` inicial é crucial para as análises subsequentes da IA (para versionamento) e para o Agente de Documentação.
    *   Se não houver mudanças detectadas, o processo é abortado.
2.  **Invocação do Agente de Testes (`test_agent.py`):**
    *   O orquestrador invoca o `test_agent.py` de forma síncrona.
    *   O `test_agent.py` executa a suíte de testes (`pytest`).
    *   Se os testes falharem (código de retorno diferente de zero), o `test_agent.py` utiliza a IA para diagnosticar a falha e o pipeline é interrompido imediatamente, reportando o erro e o diagnóstico da IA.
    *   Se os testes forem aprovados, o pipeline continua, garantindo a qualidade do código.
3.  **Invocação do Agente de Documentação (`doc_agent.py`):**
    *   O orquestrador invoca o `doc_agent.py`.
    *   O `doc_agent.py` utiliza o `git diff` inicial para analisar as alterações de código e, com o auxílio da IA, atualiza ou gera diversos arquivos de documentação, incluindo `README.md`, `docs/architecture.md` e outros guias ou manuais (ex: `docs/manual_do_usuario.md`). Para cada tipo de documento, o agente recebe diretrizes contextuais explícitas que orientam a IA a focar na perspectiva e público-alvo apropriados (e.g., foco técnico para `architecture.md`, manual para usuário leigo para `manual_do_usuario.md`).
    *   Se o agente de documentação reportar falha, o pipeline é abortado.
4.  **Re-staging e Recálculo do Diff Completo:**
    *   Após a potencial atualização da documentação pelo `doc_agent.py`, todas as mudanças (incluindo quaisquer novos ou modificados arquivos de documentação) são novamente adicionadas ao *staging area* (`git add .`).
    *   Um novo `git diff --cached` completo é gerado, que agora reflete todas as alterações, incluindo as da documentação e quaisquer outros arquivos modificados por agentes. Este `diff` completo será usado para a geração final da mensagem de commit.
5.  **Decisão de Versionamento (Agente de Versionamento - no Orquestrador):**
    *   O `git diff` **inicial** (focado nas alterações de código antes da geração da documentação) é enviado à API do Google Gemini através da função `determine_version_increment`.
    *   A IA classifica as mudanças como `major`, `minor` ou `patch` com base nas diretrizes do Versionamento Semântico.
    *   Se a chave de API não estiver disponível ou a IA falhar na determinação, o incremento padrão é `patch`.
6.  **Atualização da Versão:**
    *   O arquivo `.version` é lido. Se não existir, é criado com a versão inicial "1.0.0".
    *   A versão é então incrementada (`major`, `minor` ou `patch`) conforme a decisão da IA. Incrementos `major` e `minor` resetam as partes seguintes (ex: `1.2.3` com `minor` vira `1.3.0`).
    *   O arquivo `.version` atualizado é adicionado ao *staging area*.
7.  **Geração da Mensagem de Commit (Agente de Geração de Mensagem de Commit - no Orquestrador):**
    *   O `git diff` **completo** (incluindo documentação e atualização de versão) e a nova versão são enviados à API do Google Gemini através da função `generate_commit_message`.
    *   A IA gera uma mensagem de commit em português, concisa e formatada, iniciando obrigatoriamente com a nova versão (ex: `[vX.Y.Z] Adiciona...`).
8.  **Commit das Alterações:**
    *   Um `git commit` é realizado com a mensagem gerada pela IA, contendo a nova versão do projeto.
9.  **Push para o Repositório Remoto:**
    *   Finalmente, um `git push origin master` é executado para enviar todas as mudanças (código, documentação, atualização de versão) para o repositório remoto.

## 4. Tecnologias e Ferramentas

*   **Python:** Linguagem principal para o desenvolvimento do orquestrador e dos agentes.
*   **Git:** Sistema de controle de versão utilizado para gerenciar o código-fonte e as operações de deploy.
*   **Google Gemini API (GenAI):** Plataforma de inteligência artificial generativa, utilizada para:
    *   Análise de `git diff` para decisão de versionamento (`major`, `minor`, `patch`).
    *   Geração de mensagens de commit.
    *   Criação/atualização de documentos (no `doc_agent.py`).
    *   Diagnóstico inteligente de falhas em testes (no `test_agent.py`).
*   **Pytest:** Framework de testes unitários em Python, utilizado pelo Agente de Testes para garantir a qualidade do código.
*   **`python-dotenv`:** Para o gerenciamento de variáveis de ambiente, como a chave da API do Gemini.
*   **`subprocess`:** Módulo Python para a execução de comandos externos (ex: comandos Git e invocação de agentes), com tratamento robusto de codificação (`errors='replace'`).

## 5. Princípios de Design

*   **Automação Inteligente:** Redução da intervenção manual em tarefas de deploy através da automação e uso de IA para decisões estratégicas (versionamento, commit, documentação) e diagnóstico de problemas.
*   **Qualidade Assegurada:** Integração de uma etapa obrigatória de testes com `pytest` para garantir a estabilidade e funcionalidade do software antes do deploy. A inteligência artificial auxilia no diagnóstico e sugestão de correção para falhas, agilizando o desenvolvimento.
*   **Documentação Contínua:** Automação da atualização e geração de diversos documentos (`README.md`, `docs/architecture.md`, `docs/manual_do_usuario.md`, etc.) através do `doc_agent.py`, garantindo que ela esteja sempre alinhada com o código e sem a necessidade de intervenção manual, agora com a capacidade de direcionar a IA com contextos específicos para cada tipo de documento.
*   **Versionamento Semântico Automatizado:** Aplicação automática das regras de SemVer (`major`, `minor`, `patch`) com base na análise do impacto das mudanças de código pela IA, com a lógica de incremento completa implementada no orquestrador.
*   **Modularidade e Extensibilidade:** A arquitetura baseada em orquestrador e agentes externos permite adicionar novos passos ou modificar existentes com relativa facilidade, sem impactar o fluxo principal.
*   **Robustez:** Melhorias no tratamento de codificação de caracteres (UTF-8 com `errors='replace'`) e no gerenciamento de arquivos, garantindo a execução e logs claros em diferentes ambientes, incluindo sistemas Windows.

## 6. Considerações Futuras

*   Implementação de *rollbacks* automatizados em caso de falha no pós-deploy.
*   Suporte para múltiplos branches além do `master`.
*   Relatórios mais detalhados sobre o desempenho dos agentes e o resultado do pipeline.
*   Adição de mais agentes especializados (ex: Agente de Linting, Agente de Segurança, Agente de Deploy em Ambiente).
