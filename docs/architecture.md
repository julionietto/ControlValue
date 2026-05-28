# Arquitetura do Sistema de Deploy Multiagente

## 1. Introdução

Este documento detalha a arquitetura do sistema de auto-push, que evoluiu para um robusto pipeline de deploy multiagente. O objetivo principal do sistema é automatizar e inteligentemente orquestrar o processo de integração contínua (CI) e entrega contínua (CD), desde a detecção de mudanças no código até o push final para o repositório, garantindo qualidade, consistência e conformidade com as práticas de versionamento semântico.

A arquitetura atual integra múltiplos "agentes" autônomos, cada um com uma responsabilidade específica, coordenados por um orquestrador central. Essa abordagem visa aumentar a confiabilidade do deploy, automatizar tarefas repetitivas e incorporar inteligência artificial para decisões estratégicas, como o versionamento de releases e a geração de mensagens de commit. O sistema também incorpora melhorias para garantir sua robustez em diferentes ambientes operacionais, como a compatibilidade com a codificação UTF-8 em consoles do Windows, e agora oferece uma visão clara e imediata dos resultados dos testes através de relatórios HTML.

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
|                     |      |   (Geração de     |
|                     |      |    Relatório HTML)|
+----------+----------+      +-------------------+
           |
           | 2. Validação de Código (com IA para diagnóstico)
           |    e Geração de Relatório de Testes HTML
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
+----------+----------+
           |
           | 6. Abertura do Relatório de Testes HTML
           |    (docs/test_report.html) no navegador
           |
           V
```

### 2.1. Componentes Principais

*   **Orquestrador (`auto_push.py`):** O coração do sistema. Ele gerencia o fluxo de execução completo, *invocando* os agentes externos em sequência, lida com a lógica central de versionamento e interage diretamente com o Git para operações de commit e push. Implementa a lógica para determinar o tipo de incremento de versão (major, minor, patch) e gerar a mensagem de commit, utilizando a IA. Possui tratamento para forçar a codificação UTF-8 na saída do console, melhorando a compatibilidade em diferentes sistemas operacionais. **Após a conclusão do pipeline, ele tenta abrir o relatório de testes HTML gerado em `docs/test_report.html` preferencialmente no Microsoft Edge (em sistemas Windows), ou no navegador padrão como fallback, proporcionando feedback imediato sobre a qualidade do código.**
*   **Agente de Testes (`test_agent.py`):** Um agente externo invocado pelo orquestrador. Responsável por executar os testes automatizados do projeto (`pytest`). O pipeline só prossegue se todos os testes forem aprovados, garantindo a qualidade e estabilidade do código. **Agora, o agente de testes não só executa os testes, mas também gera um relatório detalhado em formato JUnit XML (`tests/report.xml`) e, subsequentemente, um relatório HTML visualmente rico (`docs/test_report.html`), utilizando as funções `generate_html_report` e `escape_html` para este propósito.** Em caso de falha, ele utiliza a API do Google Gemini para analisar os logs de erro e fornecer um diagnóstico resumido e sugestões de correção. A cobertura de testes foi expandida para incluir módulos críticos como o de autenticação (`tests/test_auth.py`), assegurando a robustez das funcionalidades centrais.
*   **Agente de Documentação (`doc_agent.py`):** Um agente externo invocado pelo orquestrador. Encarregado de atualizar e/ou criar diversos arquivos de documentação do projeto (como `README.md`, `docs/architecture.md`, `docs/manual_do_usuario.md` e outros guias), baseando-se nas mudanças de código. Este agente assegura que a documentação esteja sempre sincronizada com o estado atual do software, utilizando a inteligência artificial para gerar e integrar o conteúdo de forma contextual, agora com diretrizes contextuais específicas para cada arquivo (e.g., perspectiva técnica para `architecture.md`, manual de usuário leigo) que guiam a IA na geração de conteúdo mais preciso e direcionado.
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
    *   O `test_agent.py` executa a suíte de testes (`pytest`), **agora com a opção `--junitxml=tests/report.xml` para gerar um arquivo XML de resultados.**
    *   **Após a execução dos testes, o `test_agent.py` processa este arquivo XML e gera um relatório HTML completo (`docs/test_report.html`), que oferece uma visão detalhada e formatada dos resultados dos testes, incluindo sumarização e pormenores de cada caso de teste.**
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
10. **Abertura do Relatório de Testes (no Orquestrador):**
    *   Após o push bem-sucedido, o orquestrador verifica a existência do relatório HTML de testes (`docs/test_report.html`).
    *   Se o relatório for encontrado, ele tenta abri-lo automaticamente. Em sistemas Windows, o sistema prioriza a abertura no **Microsoft Edge** através de um comando `subprocess.Popen` com `start msedge`.
    *   Caso a abertura no Microsoft Edge falhe, ou em outros sistemas operacionais, o orquestrador tenta abrir o relatório no navegador padrão do sistema, oferecendo um feedback visual e instantâneo sobre a saúde do projeto após o deploy.

## 4. Tecnologias e Ferramentas

*   **Python:** Linguagem principal para o desenvolvimento do orquestrador e dos agentes.
*   **Git:** Sistema de controle de versão utilizado para gerenciar o código-fonte e as operações de deploy.
*   **Google Gemini API (GenAI):** Plataforma de inteligência artificial generativa, utilizada para:
    *   Análise de `git diff` para decisão de versionamento (`major`, `minor`, `patch`).
    *   Geração de mensagens de commit.
    *   Criação/atualização de documentos (no `doc_agent.py`).
    *   Diagnóstico inteligente de falhas em testes (no `test_agent.py`).
*   **Pytest:** Framework de testes unitários e de integração em Python, utilizado pelo Agente de Testes para garantir a qualidade do código. A cobertura de testes foi ampliada, incluindo agora testes robustos para o módulo de autenticação (`tests/test_auth.py`). Adicionalmente, `streamlit.testing.v1.AppTest` está sendo explorado para testes funcionais da interface do usuário (`scratch/test_apptest.py`), visando garantir a estabilidade e usabilidade da aplicação Streamlit.
*   **`python-dotenv`:** Para o gerenciamento de variáveis de ambiente, como a chave da API do Gemini.
*   **`subprocess`:** Módulo Python para a execução de comandos externos (ex: comandos Git, invocação de agentes e abertura de aplicativos específicos como o Microsoft Edge), com tratamento robusto de codificação (`errors='replace'`).
*   **`xml.etree.ElementTree` (Python):** Módulo padrão do Python utilizado pelo Agente de Testes para parsear os resultados JUnit XML gerados pelo Pytest e construir o relatório HTML.
*   **`webbrowser` (Python):** Módulo padrão do Python utilizado pelo Orquestrador como um mecanismo de fallback para abrir automaticamente o relatório de testes HTML no navegador web padrão do sistema, caso a abertura direta com o Microsoft Edge falhe.

## 5. Princípios de Design

*   **Automação Inteligente:** Redução da intervenção manual em tarefas de deploy através da automação e uso de IA para decisões estratégicas (versionamento, commit, documentação) e diagnóstico de problemas.
*   **Qualidade Assegurada:** Integração de uma etapa obrigatória de testes com `pytest` para garantir a estabilidade e funcionalidade do software antes do deploy. A inteligência artificial auxilia no diagnóstico e sugestão de correção para falhas, agilizando o desenvolvimento. A suíte de testes foi fortalecida com a adição de testes para funcionalidades críticas como autenticação (`tests/test_auth.py`) e a exploração de testes de interface do usuário com `streamlit.testing.v1` (`scratch/test_apptest.py`) reforça o compromisso com a qualidade em todas as camadas da aplicação. **A introdução de relatórios de testes em HTML detalhados e visualmente atraentes (`docs/test_report.html`), que agora são abertos automaticamente após o deploy (com preferência pelo Microsoft Edge em Windows), melhora significativamente a transparência e a facilidade de análise dos resultados dos testes, fornecendo um feedback imediato e compreensível sobre a qualidade do código após cada execução do pipeline.**
*   **Documentação Contínua:** Automação da atualização e geração de diversos documentos (`README.md`, `docs/architecture.md`, `docs/manual_do_usuario.md`, etc.) através do `doc_agent.py`, garantindo que ela esteja sempre alinhada com o código e sem a necessidade de intervenção manual, agora com a capacidade de direcionar a IA com contextos específicos para cada tipo de documento.
*   **Versionamento Semântico Automatizado:** Aplicação automática das regras de SemVer (`major`, `minor`, `patch`) com base na análise do impacto das mudanças de código pela IA, com a lógica de incremento completa implementada no orquestrador.
*   **Modularidade e Extensibilidade:** A arquitetura baseada em orquestrador e agentes externos permite adicionar novos passos ou modificar existentes com relativa facilidade, sem impactar o fluxo principal.
*   **Robustez:** Melhorias no tratamento de codificação de caracteres (UTF-8 com `errors='replace'`) e no gerenciamento de arquivos, garantindo a execução e logs claros em diferentes ambientes, incluindo sistemas Windows.

## 6. Considerações Futuras

*   Implementação de *rollbacks* automatizados em caso de falha no pós-deploy.
*   Suporte para múltiplos branches além do `master`.
*   Relatórios mais detalhados sobre o desempenho dos agentes e o resultado do pipeline.
*   Adição de mais agentes especializados (ex: Agente de Linting, Agente de Segurança, Agente de Deploy em Ambiente).

## 7. Componentes e Fluxo de Dados da Aplicação Principal

Esta seção descreve a arquitetura de módulos chave da aplicação principal, focando no fluxo de dados e na consistência das informações, em particular no gerenciamento de usuários e na interface administrativa.

### 7.1. Gerenciamento de Usuários e Consistência de Dados

A gestão de dados de usuários e sua apresentação em interfaces administrativas são pontos críticos para a integridade e usabilidade do sistema. As recentes alterações visam aprimorar a consistência e a previsibilidade na recuperação e exibição dessas informações, bem como a experiência do usuário na autenticação.

*   **Camada de Acesso a Dados (`db/auth.py`):**
    *   A função `get_all_users` no módulo `db/auth.py` é responsável por recuperar todos os registros de usuários do banco de dados. Foi introduzida uma cláusula `ORDER BY id ASC` na consulta SQL. Essa modificação garante que os usuários sejam sempre retornados em uma ordem ascendente consistente, baseada em seus IDs, diretamente da fonte de dados. Isso é fundamental para manter a uniformidade na ordenação dos dados em todas as partes da aplicação que consomem essa função.
    *   A robustez desta camada é agora reforçada por testes unitários dedicados em `tests/test_auth.py`, que verificam cenários de login bem-sucedido, falhas por usuário não encontrado ou senha inválida, e o fluxo de logout.

*   **Camada de Apresentação (`views/admin.py`):**
    *   Na função `render_admin_view` do módulo `views/admin.py`, que é responsável por preparar os dados para a interface administrativa, foi adicionado um passo de validação e ordenação explícita. Após a recuperação dos dados de usuários via `db.get_all_users()` e sua conversão para um `pandas.DataFrame`, o código agora verifica se o DataFrame não está vazio (`if not users_df.empty:`). Em caso afirmativo, ele aplica uma ordenação adicional `users_df.sort_values(by='id', ascending=True).reset_index(drop=True)`. Embora a camada de acesso a dados já forneça uma ordenação, esta etapa na camada de apresentação age como um reforço, garantindo que a visualização administrativa sempre exiba os usuários em ordem consistente por ID, independentemente de potenciais variações ou transformações intermediárias. Essa redundância controlada contribui para a robustez do fluxo de dados até o usuário final.

*   **Camada de Autenticação na Interface (`views/auth.py`):**
    *   O módulo `views/auth.py` recebeu atualizações para melhorar a usabilidade da tela de login. A estrutura de `st.form` foi removida, permitindo maior flexibilidade na interação dos componentes. Foi adicionado um checkbox "Mostrar senha" (`st.checkbox("Mostrar senha")`) que, quando ativado, altera dinamicamente o tipo do campo de senha de `type="password"` para `type="default"`. Isso oferece aos usuários a opção de visualizar sua senha digitada, melhorando a experiência e reduzindo erros de digitação. O botão de submissão do login agora é um `st.button` padrão, alinhando-se à nova abordagem de gerenciamento de estado.
