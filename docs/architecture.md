Aqui está a documentação `docs/architecture.md` atualizada, integrando as alterações do `git diff` e focando na perspectiva técnica.

```markdown
# Arquitetura do Sistema de Deploy Multiagente

## 1. Introdução

Este documento detalha a arquitetura do sistema de auto-push, que evoluiu para um robusto pipeline de deploy multiagente, agora formalmente identificado como **Push Agent (Orquestrador)**. O objetivo principal do sistema é automatizar e inteligentemente orquestrar o processo de integração contínua (CI) e entrega contínua (CD), desde a detecção de mudanças no código até o push final para o repositório, garantindo qualidade, consistência e conformidade com as práticas de versionamento semântico. As regras para a execução automática deste pipeline são agora explicitamente definidas no arquivo `.agents/AGENTS.md`, servindo como um guia para o comportamento dos agentes.

A arquitetura atual integra múltiplos "agentes" autônomos, cada um com uma responsabilidade específica, coordenados por um orquestrador central (o Push Agent). Essa abordagem visa aumentar a confiabilidade do deploy, automatizar tarefas repetitivas e incorporar inteligência artificial para decisões estratégicas, como o versionamento de releases e a geração de mensagens de commit. O sistema também incorpora melhorias para garantir sua robustez em diferentes ambientes operacionais, como a compatibilidade com a codificação UTF-8 em consoles do Windows, e agora oferece uma visão clara e imediata dos resultados dos testes através de relatórios HTML.

## 2. Visão Geral da Arquitetura

O sistema é concebido como um orquestrador que coordena uma série de agentes especializados. Cada agente é responsável por uma etapa específica do pipeline de deploy, garantindo modularidade e capacidade de extensão. A inteligência artificial, através da API do Google Gemini, é um componente central para a tomada de decisões e geração de conteúdo, e também para o diagnóstico proativo de problemas.

```
+---------------------+
|     Orquestrador    |
|   (agent_push.py)   |
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

*   **Orquestrador (`agent_push.py`):** Renomeado de `auto_push.py` para melhor refletir seu papel como o agente principal de push e orquestração. É o coração do sistema, gerenciando o fluxo de execução completo, *invocando* os agentes externos em sequência, lidando com a lógica central de versionamento e interagindo diretamente com o Git para operações de commit e push. As diretrizes para a execução automática deste orquestrador e do pipeline são definidas no arquivo `.agents/AGENTS.md`. Em seus logs, ele agora se identifica explicitamente com o prefixo "[Push Agent]", aumentando a clareza do fluxo de execução. Implementa a lógica para determinar o tipo de incremento de versão (major, minor, patch) e gerar a mensagem de commit, utilizando a IA. Possui tratamento para forçar a codificação UTF-8 na saída do console, melhorando a compatibilidade em diferentes sistemas operacionais. **Após a conclusão do pipeline, ele tenta abrir o relatório de testes HTML gerado em `docs/test_report.html` preferencialmente no Microsoft Edge (em sistemas Windows), ou no navegador padrão como fallback, proporcionando feedback imediato sobre a qualidade do código.**
*   **Agente de Testes (`test_agent.py`):** Um agente externo invocado pelo orquestrador. Responsável por executar os testes automatizados do projeto (`pytest`). O pipeline só prossegue se todos os testes forem aprovados, garantindo a qualidade e estabilidade do código. **Agora, o agente de testes não só executa os testes, mas também gera um relatório detalhado em formato JUnit XML (`tests/report.xml`) e, subsequentemente, um relatório HTML visualmente rico (`docs/test_report.html`), utilizando as funções `generate_html_report` e `escape_html` para este propósito.** Em caso de falha, ele utiliza a API do Google Gemini para analisar os logs de erro e fornecer um diagnóstico resumido e sugestões de correção. A cobertura de testes foi expandida para incluir módulos críticos como o de autenticação (`tests/test_auth.py`), assegurando a robustez das funcionalidades centrais. **Novos testes foram adicionados para validar a flexibilidade e a robustez do sistema de autenticação, incluindo login por nome de usuário e tratamento de case-insensitivity e espaços em branco nos identificadores, e para a nova funcionalidade de consulta comparativa de proventos (`tests/test_consulta_comparativa.py`), elevando o total de testes para 24.**
*   **Agente de Documentação (`doc_agent.py`):** Um agente externo invocado pelo orquestrador. Encarregado de atualizar e/ou criar diversos arquivos de documentação do projeto (como `README.md`, `docs/architecture.md`, `docs/manual_do_usuario.md` e outros guias), baseando-se nas mudanças de código. Este agente assegura que a documentação esteja sempre sincronizada com o estado atual do software, utilizando a inteligência artificial para gerar e integrar o conteúdo de forma contextual, agora com diretrizes contextuais específicas para cada arquivo (e.g., perspectiva técnica para `architecture.md`, manual de usuário leigo) que guiam a IA na geração de conteúdo mais preciso e direcionado.
*   **Agente de Versionamento (Lógica `determine_version_increment` e `increment_version` no Orquestrador):** A função `determine_version_increment` utiliza a inteligência artificial (Google Gemini) para analisar o `git diff` das alterações de código *originais* (antes da geração de documentação) e decidir qual parte do versionamento semântico (`major`, `minor`, `patch`) deve ser incrementada. Em caso de falha da IA ou chave de API não configurada, o incremento padrão é `patch`. A função `increment_version` então aplica esta decisão, realizando incrementos `major` e `minor` que resetam as partes seguintes (ex: `1.2.3` com `minor` vira `1.3.0`). Ele também inicializa o arquivo `.version` para "1.0.0" se não existir.
*   **Agente de Geração de Mensagem de Commit (Função `generate_commit_message` no Orquestrador):** Emprega a inteligência artificial (Google Gemini) para gerar mensagens de commit claras e concisas. A mensagem é formatada para iniciar obrigatoriamente com a nova versão do projeto (ex: `[vX.Y.Z] Adiciona...`), baseando-se no `git diff` *completo* (incluindo as alterações de código, documentação e versão).
*   **Integração com Git:** A comunicação com o sistema de controle de versão é feita através de comandos `subprocess`, utilizando `text=True`, `encoding='utf-8'` e `errors='replace'` para garantir operações como `add`, `diff`, `commit` e `push` com robustez de codificação em diferentes sistemas operacionais.
*   **Serviço de Geração de Relatório Executivo (`services/executive_report_service.py`):** Este é um novo serviço, movido para o diretório `services` para uma melhor organização modular. É responsável por orquestrar a geração de relatórios executivos personalizados em formato PDF. Utiliza o banco de dados PostgreSQL para buscar dados do portfólio do usuário, `pandas` para manipulação de dados, `ReportLab` para a renderização do PDF e a API do Google Gemini para aprimorar a análise com inteligência artificial. Suas funções incluem a inferência do perfil de risco e objetivo do investidor, análise de ativos sob pressão ou com desconto e a geração de uma narrativa macroeconômica dinâmica e estratégica, oferecendo insights preditivos.
*   **API do Google Gemini:** Utilizada como o motor de inteligência artificial generativa para:
    *   Análise de `git diff` para decisão de versionamento (`major`, `minor`, `patch`).
    *   Geração de mensagens de commit.
    *   Criação/atualização de documentos (no `doc_agent.py`).
    *   Diagnóstico e sugestão de correção para falhas em testes (no `test_agent.py`).
    *   Análise do portfólio do investidor, inferência de perfil e objetivo, e geração de narrativas macroeconômicas e recomendações estratégicas para o Relatório Executivo (no `services/executive_report_service.py`).

## 3. Fluxo de Execução do Pipeline Multiagente

O orquestrador (`agent_push.py`) executa as seguintes etapas para cada deploy:

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
    *   Inferência do perfil de investidor, análise de cenário macroeconômico e geração de orientações estratégicas para o Relatório Executivo (no `services/executive_report_service.py`).
*   **Pytest:** Framework de testes unitários e de integração em Python, utilizado pelo Agente de Testes para garantir a qualidade do código. A cobertura de testes foi ampliada, incluindo agora testes robustos para o módulo de autenticação (`tests/test_auth.py`) e para a nova funcionalidade de consulta comparativa de proventos (`tests/test_consulta_comparativa.py`).
*   **SQLite:** Um banco de dados leve, sem servidor e embarcável, utilizado para persistência de dados em arquivos como `db/controlvalue.db`.
*   **PostgreSQL (`psycopg2`):** Banco de dados relacional robusto e de código aberto, utilizado para persistência dos dados da aplicação principal, como ativos, proventos e usuários, com acesso através do driver `psycopg2`.
*   **`python-dotenv`:** Para o gerenciamento de variáveis de ambiente, como a chave da API do Gemini.
*   **`subprocess`:** Módulo Python para a execução de comandos externos (ex: comandos Git, invocação de agentes e abertura de aplicativos específicos como o Microsoft Edge), com tratamento robusto de codificação (`errors='replace'`).
*   **`xml.etree.ElementTree` (Python):** Módulo padrão do Python utilizado pelo Agente de Testes para parsear os resultados JUnit XML gerados pelo Pytest e construir o relatório HTML.
*   **`webbrowser` (Python):** Módulo padrão do Python utilizado pelo Orquestrador como um mecanismo de fallback para abrir automaticamente o relatório de testes HTML no navegador web padrão do sistema, caso a abertura direta com o Microsoft Edge falhe.
*   **`pandas`:** Biblioteca amplamente utilizada para manipulação e análise de dados, essencial em módulos como `db/options.py`, `utils/formatters.py` e **agora no `services/executive_report_service.py` para tratamento eficiente de tabelas, dados financeiros e preparação para gráficos/relatórios.**
*   **`plotly.express`:** Biblioteca de visualização de dados em Python, integrada para gerar gráficos interativos (como gráficos de pizza) na interface de usuário, especialmente para a distribuição de proventos por classe de ativos.
*   **`streamlit`:** Framework utilizado para construir a interface de usuário interativa do sistema, facilitando a criação de dashboards e aplicações web complexas com Python.
*   **`ReportLab`:** Uma biblioteca Python para criar documentos PDF de forma programática. Utilizada no `services/executive_report_service.py` para gerar relatórios executivos profissionais, permitindo controle granular sobre layout, estilos, tabelas e parágrafos.

## 5. Princípios de Design

*   **Automação Inteligente:** Redução da intervenção manual em tarefas de deploy através da automação e uso de IA para decisões estratégicas (versionamento, commit, documentação) e diagnóstico de problemas. As regras para esta automação, incluindo a execução obrigatória do pipeline, são formalmente definidas em `.agents/AGENTS.OD`. **A introdução do Relatório Executivo reforça este princípio ao automatizar a análise de portfólio, a inferência de perfil de investidor e a geração de uma narrativa macroeconômica e estratégica, transformando dados brutos em insights acionáveis e preditivos.**
*   **Qualidade Assegurada:** Integração de uma etapa obrigatória de testes com `pytest` para garantir a estabilidade e funcionalidade do software antes do deploy. A inteligência artificial auxilia no diagnóstico e sugestão de correção para falhas, agilizando o desenvolvimento. A suíte de testes foi fortalecida com a adição de testes para funcionalidades críticas como autenticação (`tests/test_auth.py`), que agora incluem verificações para login por nome de usuário e tratamento de case-insensitivity/whitespace para e-mails e nomes de usuário, elevando o total de testes para 24. A cobertura de testes foi estendida para incluir a nova funcionalidade de consulta comparativa de proventos, com testes dedicados em `tests/test_consulta_comparativa.py` que verificam a ordenação alfabética, cálculos de diferença e o comportamento em cenários com dados parciais ou vazios, assegurando a precisão e confiabilidade da comparação histórica. **Testes adicionais foram implementados em `tests/test_consulta_comparativa.py` para validar a nova lógica de cálculo da diferença (`Lado B - Lado A`) e assegurar sua precisão em diversos cenários, incluindo casos com dados parciais ou nulos, reforçando a confiabilidade da comparação histórica de proventos.** A introdução de relatórios de testes em HTML detalhados e visualmente atraentes (`docs/test_report.html`), que agora são abertos automaticamente após o deploy (com preferência pelo Microsoft Edge em Windows), melhora significativamente a transparência e a facilidade de análise dos resultados dos testes, fornecendo um feedback imediato e compreensível sobre a qualidade do código após cada execução do pipeline. **Além disso, a cobertura de testes foi expandida para incluir a nova lógica de inferência de tipos de ativos, garantindo que a classificação de ETFs de Criptomoedas e outros ativos seja precisa e consistente (`tests/test_formatters.py`). Testes adicionais em `tests/test_formatters.py` agora verificam a exatidão do cálculo do resumo anual de proventos, assegurando que o 'Valor Mensal' seja corretamente ponderado pelo número de meses decorridos para o ano corrente e por 12 para anos anteriores.** **A funcionalidade do Relatório Executivo contribui para este princípio ao oferecer diagnósticos proativos sobre ativos sob pressão e orientações estratégicas, ajudando a manter a saúde e o alinhamento do portfólio com os objetivos do investidor.**
*   **Documentação Contínua:** Automação da atualização e geração de diversos documentos (`README.md`, `docs/architecture.md`, `docs/manual_do_usuario.md`, etc.) através do `doc_agent.py`, garantindo que ela esteja sempre alinhada com o código e sem a necessidade de intervenção manual, agora com a capacidade de direcionar a IA com contextos específicos para cada tipo de documento.
*   **Versionamento Semântico Automatizado:** Aplicação automática das regras de SemVer (`major`, `minor`, `patch`) com base na análise do impacto das mudanças de código pela IA, com a lógica de incremento completa implementada no orquestrador.
*   **Modularidade e Extensibilidade:** A arquitetura baseada em orquestrador e agentes externos permite adicionar novos passos ou modificar existentes com relativa facilidade, sem impactar o fluxo principal. **A criação de um novo serviço (`services/executive_report_service.py`) e uma nova view (`views/report_executivo.py`) para o Relatório Executivo demonstra a capacidade de estender a aplicação com novas funcionalidades complexas de forma modular, sem alterar o core do sistema.**
*   **Robustez:** Melhorias no tratamento de codificação de caracteres (UTF-8 com `errors='replace'`) e no gerenciamento de arquivos, garantindo a execução e logs claros em diferentes ambientes, incluindo sistemas Windows. **Para otimizar o desempenho e evitar re-inicializações desnecessárias, a função `db.init_db()` agora é invocada condicionalmente apenas uma vez por sessão da aplicação Streamlit (`app.py`), utilizando `st.session_state` para controlar o estado da inicialização do banco de dados.**

## 6. Considerações Futuras

*   Implementação de *rollbacks* automatizados em caso de falha no pós-deploy.
*   Suporte para múltiplos branches além do `master`.
*   Relatórios mais detalhados sobre o desempenho dos agentes e o resultado do pipeline.
*   Adição de mais agentes especializados (ex: Agente de Linting, Agente de Segurança, Agente de Deploy em Ambiente).

## 7. Componentes e Fluxo de Dados da Aplicação Principal

Esta seção descreve a arquitetura de módulos chave da aplicação principal, focando no fluxo de dados e na consistência das informações, em particular no gerenciamento de usuários e na interface administrativa.

### 7.1. Gerenciamento de Usuários e Consistência de Dados

A gestão de dados de usuários e sua apresentação em interfaces administrativas são pontos críticos para a integridade e usabilidade do sistema. As recentes alterações visam aprimorar a consistência e a previsibilidade na recuperação e exibição dessas informações, bem como a experiência do usuário na autenticação, tornando-la mais flexível e robusta.

*   **Camada de Acesso a Dados (`db/auth.py`):**
    *   A função `get_all_users` no módulo `db/auth.py` é responsável por recuperar todos os registros de usuários do banco de dados. Foi introduzida uma cláusula `ORDER BY id ASC` na consulta SQL. Essa modificação garante que os usuários sejam sempre retornados em uma ordem ascendente consistente, baseada em seus IDs, diretamente da fonte de dados. Isso é fundamental para manter a uniformidade na ordenação dos dados em todas as partes da aplicação que consomem essa função.
    *   A função `verify_user` foi significativamente aprimorada. Agora, ela permite a autenticação de usuários tanto pelo **email** quanto pelo **nome de usuário**, tornando o processo de login mais flexível. A busca é realizada de forma **case-insensitive** para ambos (email e nome de usuário) e **remove espaços em branco** das extremidades do identificador de login fornecido, aumentando a robustez contra erros de digitação e variações de capitalização.
    *   Outras funções de gerenciamento de usuários, como `create_user`, `get_user_by_email` e `admin_update_user`, também foram ajustadas para lidar com emails e nomes de usuário de forma **case-insensitive** e com **limpeza de espaços** (`strip()`), assegurando consistência e robustez em todo o ciclo de vida do usuário no sistema.
    *   A robustez desta camada é agora reforçada por testes unitários dedicados em `tests/test_auth.py`, que verificam cenários de login bem-sucedido, falhas por usuário não encontrado ou senha inválida, o fluxo de logout, e agora também cenários de login por nome de usuário e a tolerância a case-insensitivity e espaços em branco nos identificadores.

*   **Camada de Apresentação (`views/admin.py`):**
    *   Na função `render_admin_view` do módulo `views/admin.py`, que é responsável por preparar os dados para a interface administrativa, foi adicionado um passo de validação e ordenação explícita. Após a recuperação dos dados de usuários via `db.get_all_users()` e sua conversão para um `pandas.DataFrame`, o código agora verifica se o DataFrame não está vazio (`if not users_df.empty:`). Em caso afirmativo, ele aplica uma ordenação adicional `users_df.sort_values(by='id', ascending=True).reset_index(drop=True)`. Embora a camada de acesso a dados já forneça uma ordenação, esta etapa na camada de apresentação age como um reforço, garantindo que a visualização administrativa sempre exiba os usuários em ordem consistente por ID, independentemente de potenciais variações ou transformações intermediárias. Essa redundância controlada contribui para a robustez do fluxo de dados até o usuário final.

*   **Camada de Autenticação na Interface (`views/auth.py`):**
    *   O módulo `views/auth.py` recebeu atualizações para simplificar a interface de login. O `st.checkbox("Mostrar senha")` e a lógica associada de alteração dinâmica do tipo do campo de senha foram **removidos**. O campo de entrada de senha (`st.text_input("Senha", type="password")`) agora é sempre do tipo "password" por padrão, priorizando a segurança e uma experiência de usuário mais concisa. **Além disso, a interface de login foi refatorada para utilizar `st.form` e `st.form_submit_button`. Essa alteração encapsula os campos de entrada e o botão de submissão dentro de um formulário Streamlit, melhorando o gerenciamento de estado e a forma como as interações do usuário são processadas, garantindo que a lógica de autenticação seja acionada de forma explícita e controlada após a submissão do formulário.**

### 7.2. Visualização e Análise de Proventos (`views/proventos.py`, `views/proventos_historico.py`, `views/proventos_resumo.py`)

A apresentação de dados financeiros, como proventos, exige um alto grau de controle sobre a formatação e a interação para garantir clareza e usabilidade. As recentes modificações nos módulos `views/proventos.py`, `views/proventos_historico.py` e `views/proventos_resumo.py` refletem uma evolução na estratégia de renderização de tabelas, na interação com os dados e na granularidade da análise, visando uma experiência do usuário mais rica e consistente.

*   **Renderização de Tabelas Customizadas em HTML (`views/proventos.py`, `views/proventos_historico.py`):**
    *   Anteriormente, a visualização de proventos utilizava o componente nativo `st.dataframe` do Streamlit, com estilização aplicada via métodos `.style.apply()`. Esta abordagem foi substituída pela geração direta de tabelas HTML customizadas.
    *   Agora, as tabelas são construídas programaticamente em HTML (usando listas de strings que são unidas e passadas para `st.write(..., unsafe_allow_html=True)`). Isso permite um controle granular sobre cada aspecto visual da tabela, incluindo cabeçalhos, linhas de dados, e as linhas de rodapé (TOTAL, CRESCIMENTO, VALOR MÉDIO), que agora são integradas de forma coesa na mesma estrutura de tabela HTML. Foi removida a coluna explícita de "Média Mensal" para focar a apresentação nos valores mensais e no total anual dos ativos.
    *   A estilização é aplicada diretamente nos atributos `style` do HTML e através de classes CSS (`.custom-table`), utilizando variáveis CSS (`var(--border-color)`, `var(--table-header-bg)`, etc.) para garantir a compatibilidade e consistência com o tema global da aplicação. Isso proporciona maior flexibilidade para aplicar cores condicionais (ex: verde para valores positivos, vermelho para negativos), alinhamentos específicos e fontes personalizadas, melhorando a legibilidade e a inteligência visual dos dados financeiros. As linhas de sumário "TOTAL", "CRESCIMENTO" e "VALOR MÉDIO" receberam melhorias visuais para maior destaque e clareza.
    *   Para melhorar a compreensão das métricas exibidas, uma legenda foi adicionada abaixo das tabelas, explicando os termos "Crescimento" (comparado ao mesmo mês do ano anterior) e "Valor Médio" (valor médio acumulado até o mês atual).
    *   Esta mudança resultou em uma visualização mais performática e com maior fidelidade ao design desejado, especialmente para tabelas complexas que requerem cálculos de totais, médias e percentuais de crescimento em suas linhas de sumário.

*   **Interação de Edição e Adição de Ativos (`views/proventos.py`, `views/proventos_historico.py`):**
    *   No módulo `views/proventos.py`, a seleção de ativos para edição, que antes era realizada implicitamente através da seleção de linhas no `st.dataframe`, foi refatorada para um componente `st.selectbox` explícito ("Editar Ativo"). Isso proporciona um controle mais direto e claro para o usuário ao iniciar o processo de edição.
    *   Ambos os módulos (`views/proventos.py` e `views/proventos_historico.py`) agora apresentam uma interface mais consistente e intuitiva para adicionar ou editar proventos. Um botão "➕ Adicionar Ativo" e um `st.selectbox` para "Editar Ativo" (ou "Selecionar Ativo para Editar/Excluir...") são utilizados, encapsulados em colunas (`st.columns`) para melhor organização do layout. Esta abordagem separa claramente a visualização da tabela das ações de gerenciamento de dados, melhorando a usabilidade.
    *   A lógica de `st.rerun()` é utilizada para reprocessar a visualização após a seleção de uma ação de adição ou edição, garantindo que o estado da aplicação seja atualizado e o formulário de edição/adição seja exibido conforme necessário.

*   **Consulta Comparativa de Proventos (`views/proventos_historico.py`):**
    *   A funcionalidade de **"Consulta Comparativa"** permite aos usuários comparar os proventos recebidos por ativo entre dois períodos (mês/ano) distintos.
    *   Esta funcionalidade agora é mais acessível, sendo acionada por um botão "📊 Consulta Comparativa" localizado **contextualmente para cada grupo anual de proventos**. Ao ser clicado, este botão define uma variável de estado de sessão (`st.session_state.show_consulta_comparativa = True`) e aciona um `st.rerun()`, **garantindo que o diálogo interativo (`st.dialog`) para a consulta seja exibido imediatamente para uma experiência de usuário mais responsiva e fluida.**
    *   Dentro do diálogo, o usuário pode selecionar o ano e o mês para o "Lado A" e o "Lado B" da comparação. **Para maior conveniência, os filtros de seleção de ano e mês agora vêm com padrões inteligentes: o "Lado A" é pré-selecionado para o ano anterior e o "Lado B" para o ano corrente, ambos com o mês atual, se esses períodos estiverem disponíveis nos dados. Além disso, a lista de anos disponíveis foi ampliada para sempre incluir o ano corrente e o ano anterior, garantindo opções de comparação relevantes mesmo na ausência de dados para esses anos.**
    *   A função `obter_dados_consulta_comparativa` é responsável por processar os dados, agrupando os proventos por ticker para cada período selecionado e calculando os valores (`valor_a`, `valor_b`) e a diferença (`diferenca`), **que agora representa a variação do Lado A para o Lado B (`valor_b - valor_a`).** Os resultados são então ordenados alfabeticamente pelo nome do ativo para uma visualização consistente.
    *   Os dados comparativos são exibidos em uma tabela HTML customizada, similar às outras tabelas de proventos, com colunas para "Ativo", "Lado A", "Lado B" e "Diferença". **A renderização desta tabela foi aprimorada para incluir um container com rolagem vertical (`overflow-y: auto`), além de cabeçalhos e a linha de totalizadores que permanecem "fixos" ou "sticky" durante a rolagem (usando `position: sticky`), melhorando significativamente a usabilidade para comparações com muitos ativos.** A coluna "Diferença" utiliza estilização condicional (verde para positivo, vermelho para negativo) e a tabela inclui linhas de totalizadores para os valores totais e a diferença total entre os períodos.
    *   A funcionalidade suporta a opção de ocultar valores para privacidade e inclui um botão de fechamento para o diálogo.

*   **Resumo de Proventos por Ano e Classe (`views/proventos_resumo.py`):**
    *   A tela de resumo de proventos foi significativamente aprimorada para oferecer uma análise mais granular e visualmente rica. O título foi alterado para **"📊 Resumo de Proventos"**, com subtítulo expandido para "Consolidado histórico de proventos recebidos por ano, moeda e classe de ativos."
    *   Agora, a visualização é dividida em duas abas (`st.tabs`):
        *   **"📅 Evolução Anual":** Mantém a funcionalidade de "Consolidado por Ano", exibindo os proventos mensais e anuais. Para garantir a precisão nas métricas de performance anual, a lógica de cálculo do 'Valor Mensal' para o resumo de proventos foi aprimorada: para anos passados, o valor total anual é dividido por 12 meses, enquanto para o ano corrente, o valor total acumulado é dividido pelo número de meses já decorridos, refletindo de forma mais fidedigna a média mensal até o momento. Também inclui a tabela de "Proventos Dolarizados (Valores em R$)" para ativos dos EUA, se aplicável, fornecendo uma visão contínua da evolução histórica.
        *   **"📂 Distribuição por Classe":** Esta é uma aba avançada que permite ao usuário analisar a distribuição dos proventos recebidos por classe de ativo, oferecendo tanto uma visão mensal quanto anual.
            *   **Otimização de Desempenho:** Para aprimorar a performance, as funções `db.get_proventos` e `db.get_all_assets` agora são encapsuladas por decoradores `@st.cache_data(ttl=10)` dentro de funções auxiliares (`get_cached_proventos`, `get_cached_assets`). Isso garante que os dados de proventos e ativos sejam carregados e mapeados para `full_assets_map` apenas uma vez no início da renderização da view, e armazenados em cache por 10 segundos, reduzindo chamadas redundantes ao banco de dados e processamento de dados em reruns do Streamlit.
            *   **Filtros de Data:** O usuário pode selecionar o ano e o mês específicos através de `st.selectbox` para focar a análise. **Esses filtros agora vêm com uma seleção padrão inteligente, pré-definindo o ano e o mês correntes, se disponíveis nos dados, para uma experiência de usuário mais conveniente.**
            *   **Mapeamento de Ativos:** Utiliza os dados de ativos carregados e cacheados (`full_assets_map`) para classificar os tickers dos proventos no mês selecionado por seu respectivo tipo de ativo (Classe), tanto para a agregação mensal quanto para a anual.
            *   **Totalizadores (Mensal e Anual):** Na parte superior, são exibidos dois totalizadores, organizados lado a lado usando `st.columns`, para o "💰 Total Recebido no Mês" e "📅 Total Recebido no Ano". Ambos são apresentados em um formato estilizado em HTML, com a opção de ocultar valores, fornecendo um resumo financeiro imediato.
            *   **Tabela de Valores por Classe:** Apresenta um `st.dataframe` que consolida o sumário dos proventos recebidos por cada classe de ativo, mostrando tanto o "Valor Mês" quanto o "Valor Ano", acompanhados dos seus respectivos percentuais ("% Mês" e "% Ano") sobre o total. A tabela é ordenada por "Valor Ano" de forma decrescente para facilitar a visualização das maiores contribuições anuais. A estilização agora diferencia visualmente os valores mensais (verde) dos anuais (azul). **Para aprimorar a interatividade, esta tabela agora permite a seleção de uma única linha (`selection_mode="single-row"`). Ao selecionar uma classe de ativo na tabela, um novo diálogo (`st.dialog`) intitulado "🔍 Detalhamento por Ativo no Mês" é acionado. Este diálogo exibe um detalhamento interativo dos proventos recebidos, por ativo, dentro da classe selecionada, focando exclusivamente nos valores mensais e mostrando apenas ativos com proventos positivos no mês. Essa alteração proporciona uma visão mais granular e focada dos rendimentos mensais por ativo dentro de cada classe. A função utilitária `format_provento` foi promovida para o escopo global do módulo para padronizar a formatação de valores monetários, incluindo a funcionalidade de ocultar valores para privacidade, sendo reutilizada tanto na tabela principal quanto no novo diálogo de detalhamento.**
            *   **Gráficos de Distribuição Percentual (Mensal e Anual):** Em vez de um único gráfico, a aba agora exibe dois gráficos de pizza interativos (`plotly.express.pie`), organizados em colunas (`st.columns`), para visualizar a distribuição percentual das classes de ativos:
                *   **"📊 Distribuição do Mês":** Reflete a composição dos proventos para o mês selecionado.
                *   **"📊 Acumulado do Ano":** Mostra a composição dos proventos acumulados ao longo do ano selecionado.
                Ambos os gráficos utilizam uma paleta de cores consistente (`color_map`) para as classes de ativos e são interativos, ajustando a exibição com base no estado `hide_values`, oferecendo uma compreensão rápida e aprofundada da origem e distribuição dos rendimentos financeiros ao longo do tempo.

Esta refatoração da camada de apresentação para proventos exemplifica o compromisso com a criação de interfaces de usuário altamente otimizadas e ricas em dados, mantendo a flexibilidade e a extensibilidade da arquitetura.

### 7.3. Gerenciamento de Operações com Opções e Tratamento de Dados Financeiros

A gestão de operações financeiras com opções requer uma manipulação precisa de dados, especialmente datas e valores monetários. Recentemente, foram implementadas melhorias significativas nas camadas de acesso a dados e de utilitários para garantir a integridade, consistência e robustez no tratamento dessas informações.

*   **Camada de Conexão e Migração de Banco de Dados (`db/connection.py`):**
    *   A definição da tabela `opcoes` foi atualizada para alterar os tipos de dados das colunas `dt_operacao` e `dt_vencimento` de `TEXT` para `DATE`. Essa mudança otimiza o armazenamento, a indexação e a manipulação de datas no banco de dados, garantindo que operações de data e hora sejam realizadas de forma nativa e eficiente pelo PostgreSQL.
    *   Foi introduzido um script de migração na função `init_db()` que verifica o tipo atual dessas colunas. Se ainda estiverem como `text` ou `character varying`, um `ALTER TABLE` é executado para convertê-las para `DATE`, tratando strings vazias (`NULLIF(dt_operacao, '')`) para evitar erros de conversão. Este mecanismo de migração automática assegura a compatibilidade retroativa e a transição suave para o novo esquema de dados.
    *   **Estratégia de Conexão com Banco de Dados para Ambientes de Nuvem (Neon.tech Auto-Suspend):**
        *   Uma premissa arquitetural crucial foi adotada devido à hospedagem do banco de dados PostgreSQL na **Neon.tech**. Para garantir que o serviço possa entrar em **Auto-Suspend** quando o sistema estiver ocioso – evitando o estouro do limite mensal de horas de computação – o sistema **não pode** manter conexões ativas ou em pool de forma permanente.
        *   Consequentemente, a arquitetura de gerenciamento de conexões foi refeita, abandonando o modelo de *connection pooling* persistente. As funções `init_connection_pool` e `close_pool` foram mantidas como legado, mas não gerenciam mais um pool persistente.
        *   O gerenciador de contexto `get_db_connection()` foi fundamentalmente refatorado: agora, ele estabelece uma conexão `psycopg2.connect` **diretamente** ao banco de dados ao entrar no contexto. Mais importante, ele garante que `conn.close()` seja invocado no bloco `finally` ao sair do contexto, assegurando que a conexão física com o banco de dados seja **terminada imediatamente após cada uso**. Essa abordagem de conexões efêmeras e diretas prioriza a eficiência de custo e o gerenciamento de recursos em ambientes de banco de dados de nuvem "serverless-like".
    *   **Refatoração do Inicializador de Banco de Dados (`init_db`):**
        *   A função `init_db()` continua a utilizar o *context manager* `with get_db_connection() as conn:`. Esta abordagem, agora com o novo modelo de conexão direta e efêmera, melhora a robustez na aquisição e liberação de conexões para tarefas de inicialização e migração, garantindo que o banco de dados seja configurado de forma segura e que as conexões sejam apropriadamente encerradas.
        *   **Controle de Inicialização da Aplicação (`app.py`):** A chamada a `db.init_db()` na função principal da aplicação (`app.py`) foi otimizada para ser executada apenas uma vez por sessão do Streamlit. Isso é feito verificando o estado `st.session_state.db_initialized`, garantindo que o banco de dados seja inicializado de forma eficiente e evitando re-inicializações redundantes que podem impactar o desempenho e a estabilidade da aplicação em ambientes interativos como o Streamlit.

*   **Camada de Acesso a Dados de Opções (`db/options.py`):**
    *   Foi adicionada uma nova função utilitária interna, `_parse_date_to_iso`, para padronizar a conversão de strings e objetos de data em vários formatos (`YYYY-MM-DD`, `DD/MM/YYYY`, `DD/MM/YY`) para o formato `YYYY-MM-DD` exigido pelas colunas `DATE` do banco de dados. Esta função é robusta e lida com valores nulos ou vazios, retornando `None` quando a conversão não é possível.
    *   A função `get_opcoes_import`, responsável pela importação de dados de opções de arquivos, foi atualizada para utilizar `_parse_date_to_iso` nas colunas `dt_operacao` e `dt_vencimento`. Isso garante que as datas importadas sejam consistentemente formatadas e validadas antes da inserção no banco de dados, prevenindo erros de tipo de dado e assegurando a integridade dos registros. Um `ValueError` explícito é levantado se as datas parseadas forem inválidas.
    *   A forma de acesso aos dados de linhas de DataFrame foi ajustada de `row[index]` para `row.iloc[index]` para maior clareza e robustez.

*   **Utilitários de Formatação (`utils/formatters.py`):**
    *   A função `parse_currency`, crucial para a conversão robusta de valores monetários em diversos formatos de string (com ou sem símbolos de moeda, separadores de milhar/decimal variados) para o tipo `float`, foi centralizada neste módulo. Isso promove a reutilização de código e garante uma abordagem unificada para o tratamento de valores financeiros em toda a aplicação. A função lida com valores nulos, vazios e diferentes convenções de formatação (e.g., `,` como separador decimal).
    *   **Adicionalmente, inclui a função `get_annual_proventos_summary`, que calcula o resumo anual e mensal de proventos, ajustando o cálculo da média mensal para o ano corrente com base nos meses já decorridos, proporcionando uma análise financeira mais precisa.**

Essas alterações em `db/connection.py`, `db/options.py` e `utils/formatters.py` reforçam a arquitetura da aplicação com uma manipulação de dados financeiros mais segura, padronizada e à prova de erros, essencial para a confiabilidade de um sistema de gestão de investimentos.

### 7.4. Processamento de Proventos e Validação de Custódia (`sync_job.py`)

O módulo `sync_job.py`, responsável pela sincronização e provisionamento de proventos, recebeu uma importante melhoria para garantir a precisão e a integridade na atribuição de rendimentos aos usuários.

*   **Verificação de Quantidade em Custódia na Data-Com:**
    *   Foi introduzida uma lógica no `run_sync()` que, antes de salvar (upsert) um provento provisionado, verifica se o usuário possuía uma quantidade positiva do ativo em custódia na `data_com` (data ex-dividendo).
    *   A `data_com`, que pode vir como `date` ou `string` (em formatos `DD/MM/YYYY` ou `YYYY-MM-DD`), é parseada para o formato `YYYY-MM-DD` (`d_com_iso`) para garantir compatibilidade com a consulta SQL.
    *   Uma consulta SQL é executada na tabela `asset_history` para somar a quantidade (`SUM(h.quantity)`) que o usuário (`user_id`) possuía do `db_ticker` até a `data_com`.
    *   Se a quantidade em custódia na `data_com` for `0` ou negativa (`qty_on_date <= 0`), o provento não é provisionado para aquele usuário (`continue`), prevenindo a atribuição indevida de rendimentos a quem não era elegível.
    *   Esta validação crítica garante que os registros de proventos sejam baseados na posse efetiva do ativo, aumentando a confiabilidade dos dados financeiros da aplicação.

### 7.5. Otimização da Visualização e Interação de Dados para a Visão Geral

No módulo `views/geral.py`, responsável pela renderização da "Visão Geral", foram implementadas otimizações na preparação de dados para gráficos que exibem proventos e retornos totais de Fundos de Investimento Imobiliário (FIIs), juntamente com melhorias na interação para exploração detalhada dos ativos.

*   **Simplificação da Preparação de Dados para Gráficos:** As funções `render_visao_geral_view` foram refatoradas para simplificar a manipulação de dados antes da plotagem. A coluna temporária `Ativo_display`, que antes era utilizada para formatar os tickers dos ativos (`fii_prov_df['Ativo'].apply(format_ticker_for_display)`) e então usada nos eixos dos gráficos `px.bar`, foi eliminada. Agora, a formatação é aplicada diretamente à coluna `Ativo` original do DataFrame, e esta coluna já formatada é utilizada nos gráficos. Esta mudança reduz a criação de colunas intermediárias, otimizando levemente o consumo de memória e a clareza do código na camada de apresentação, sem alterar o fluxo de dados fundamental ou a lógica de cálculo dos proventos e retornos.
*   **Diálogos Interativos para Detalhamento de Ativos por Setor/Segmento:** Para aprimorar a capacidade de exploração dos dados na Visão Geral, foram introduzidos e refatorados diálogos (`st.dialog`) que permitem ao usuário visualizar os ativos pertencentes a um setor ou segmento específico, selecionado a partir dos gráficos de distribuição.
    *   A função `dialog_assets_by_sector` foi renomeada para `dialog_rv_assets_by_sector`, focando agora especificamente nos ativos de **Renda Variável (RV)**.
    *   Uma nova função, `dialog_fii_assets_by_sector`, foi criada para lidar com o detalhamento dos **Fundos de Investimento Imobiliário (FIIs)** por segmento. Essa separação garante lógica e apresentação específicas para cada tipo de ativo.
    *   Ambos os diálogos são acionados interativamente por cliques nos gráficos de pizza de distribuição (Setores de RV e Segmentos de FIIs), utilizando `plotly_events`. Eles filtram os ativos ativos (`quantity > 1e-5`) pertencentes ao setor/segmento selecionado e os exibem em um `st.dataframe` estilizado.
    *   Para o `st.dataframe` dentro desses diálogos, foi implementada uma formatação customizada para a coluna 'Quantidade' (`format_qty_hist`), que ajusta a exibição para ativos de criptomoedas (maior precisão decimal) e outros ativos (inteiros), além de formatar o 'Saldo Atual' em BRL.
    *   O gerenciamento do estado dos diálogos é feito através de chaves no `st.session_state` (`rv_sector_dialog_handled` e `fii_sector_dialog_handled`), garantindo que os diálogos sejam abertos e reabertos de forma controlada após a interação do usuário. Botões de fechamento específicos (`key="btn_close_rv_sector_dialog"` e `key="btn_close_fii_sector_dialog"`) foram adicionados para cada diálogo, permitindo um control mais preciso da interação.
*   **Exibição de Valores em Dólar para Ativos dos EUA:**
    *   A função `format_usd_custom` foi introduzida para padronizar a formatação de valores monetários em dólar (`$ X.XXX,XX`), garantindo consistência na apresentação.
    *   A tabela "Ativos nos Estados Unidos", localizada na seção "Radar de Balanceamento" da Visão Geral, agora exibe uma nova coluna "Valor em Dólar". Além disso, o nome da coluna para o valor em BRL é dinamicamente ajustado: "Valor em Real" quando a visualização em dólar está ativa (`show_usd`), ou "Valor do Ativo" em outros contextos. Esta coluna calcula o valor atual dos ativos dos EUA em USD, utilizando o `original_current_price` (preço original do ativo em dólar, se disponível) ou, como fallback, convertendo o `current_value` em BRL usando a taxa de câmbio USD/BRL. Essa funcionalidade oferece uma visão mais direta e contextualizada do patrimônio em moeda estrangeira, aprimorando a clareza e a utilidade da Visão Geral para portfólios globais.

### 7.6. Mapeamento de Ativos Financeiros

O módulo `services.py` atua como um repositório central para lógicas de negócio e mapeamentos de dados que são utilizados em diversas partes da aplicação.

*   **Atualização do Mapeamento de Setores de FIIs:** O dicionário `FII_TICKER_OVERRIDE` em `services.py`, que define o setor de um Fundo de Investimento Imobiliário (FII) a partir de seu ticker, foi atualizado. Especificamente, o ticker `'KNUQ11.SA'` foi adicionado e associado ao setor `'Recebíveis'`. Essa atualização garante que novos ativos sejam corretamente classificados e exibidos conforme sua categoria, mantendo a integridade e precisão das informações financeiras apresentadas na aplicação.

### 7.7. Gerenciamento e Classificação de Ativos Financeiros

A robustez na classificação de ativos é crucial para a precisão dos cálculos de portfólio, balanceamento e relatórios. Recentemente, a arquitetura de gerenciamento de ativos foi estendida para incluir uma categorização mais granular, especificamente para **ETFs de Criptomoedas**, e para garantir que essa nova categoria seja tratada corretamente em toda a aplicação.

*   **Definição Centralizada de ETFs de Criptomoedas (`db/assets.py`):**
    *   O módulo `db/assets.py` agora hospeda uma constante global, `CRYPTO_ETFS`, que é um `set` contendo os *tickers* (símbolos de negociação) de ETFs de criptomoedas, tanto listados na B3 (ex: `HASH11.SA`, `QBTC11.SA`, `DEFI11.SA`) quanto em bolsas dos EUA (ex: `IBIT`, `FBTC`, `ARKB`). Esta lista serve como a fonte de verdade centralizada para identificar esses ativos específicos.
    *   A função `infer_asset_type(ticker)` em `db/assets.py` foi atualizada para, antes de outras verificações, consultar `CRYPTO_ETFS`. Se o *ticker* fornecido estiver presente neste conjunto, o tipo de ativo é inferido como `'ETF'`, garantindo uma classificação precisa para esses instrumentos e a integração adequada com o ecossistema de ETFs.

*   **Classificação Unificada de Tipos de Ativos (`utils/formatters.py` e `db/assets.py`):**
    *   A função `infer_asset_type(ticker)`, também presente em `utils/formatters.py` (para uso em contextos de formatação e exibição), foi alinhada com a lógica central. Ela agora importa `CRYPTO_ETFS` de `db/assets.py` e aplica a mesma lógica de identificação, garantindo consistência na inferência do tipo de ativo em diferentes camadas da aplicação. Este padrão reforça o reuso de definições chave e a precisão da classificação em todo o sistema.

*   **Impacto no Balanceamento e Diversificação de Portfólio (`views/geral.py`):**
    *   No módulo `views/geral.py`, que renderiza a "Visão Geral" do portfólio, a lógica de cálculo das **alocações percentuais atuais por classe (`current_allocs_pct`)** foi ajustada para acomodar os ETFs de Criptomoedas:
        *   A soma para a categoria **'Ações'** agora exclui explicitamente os ETFs de criptomoedas (identificados através de `db.CRYPTO_ETFS`), garantindo que estes não sejam contados como 'Ações' para fins de balanceamento.
        *   A soma para a categoria **'Criptos'** agora inclui não apenas os ativos classificados diretamente como 'Cripto', mas também os ETFs identificados como de criptomoedas, consolidando-os sob a alocação de criptoativos para uma representação mais fiel do portfólio.
    *   A função interna `get_target_class_key`, utilizada para mapear o tipo de ativo à sua respectiva chave de target de usuário (para recomendações de rebalanceamento), também foi aprimorada. Ela agora aceita a linha completa do DataFrame (`row`) e verifica se um ativo é um ETF de criptomoeda (usando `db.CRYPTO_ETFS`) e, se for, o associa à categoria **'Criptos'** para o cálculo do balanceamento ideal. Isso assegura que as recomendações de compra/venda reflitam corretamente a alocação desejada para criptoativos, independentemente de estarem em formato de criptomoeda direta ou ETF.

Essas modificações garantem que a aplicação principal categorize, visualize e forneça recomendações de balanceamento de portfólio para ETFs de Criptomoedas de forma inteligente e consistente, refletindo sua natureza híbrida entre ETFs e criptoativos e aprimoramento a precisão da gestão de portfólio.

### 7.8. Detalhe do Ativo e Visualização Histórica de Operações

O módulo `views/asset_detail.py` é responsável por apresentar a visão detalhada de um ativo específico, incluindo seu histórico de operações. Melhorias foram implementadas para aprimorar a inteligência visual e a legibilidade da tabela de histórico de operações, permitindo que o usuário identifique rapidamente o desempenho de cada transação.

*   **Estilização Condicional da Tabela de Histórico de Operações (`views/asset_detail.py`):**
    *   A lógica para aplicar estilos CSS condicionalmente às linhas do DataFrame que exibe o histórico de operações do ativo foi refatorada para maior clareza e eficiência.
    *   Primeiro, uma nova coluna temporária, `raw_diff`, é adicionada ao DataFrame `display_hist`. Esta coluna pré-calcula o lucro ou prejuízo bruto de cada operação (ajustando para ativos dos EUA ou considerando o `lucro_prejuizo` nativo), mas apenas para operações com quantidade positiva (`quantity > 0`). Esta centralização do cálculo otimiza o processamento.
    *   A função auxiliar `color_cols` (anteriormente `color_row`) foi atualizada para utilizar este valor pré-calculado de `raw_diff`. Se o `diff` for positivo, as colunas de desempenho (`% Ganho`, `Vlr Atualizado`, `Lucro/Prej`) recebem a cor verde (`#00CC96`). Se for negativo, a cor é definida como vermelho (`#EF553B`).
    *   Esta função `color_cols` é então aplicada ao DataFrame `display_hist` usando `styled_hist = display_hist.style.apply(color_cols, axis=1)`.
    *   Finalmente, a coluna `raw_diff` é ocultada do `st.dataframe` final através da configuração `column_config={"op_idx": None, "raw_diff": None}`, garantindo que ela sirva apenas como um auxiliar interno para a estilização, sem poluir a interface do usuário. Essa abordagem melhora significativamente a usabilidade e a interpretação dos dados históricos do ativo, destacando visualmente as operações lucrativas e deficitárias de forma mais performática.

### 7.9. Geração de Relatório Executivo e Análise Preditiva

Uma nova funcionalidade foi integrada à aplicação para fornecer aos usuários um relatório executivo detalhado e preditivo de seus investimentos. Esta funcionalidade é impulsionada por inteligência artificial para oferecer insights estratégicos e personalizados.

*   **Serviço de Geração de Relatório (`services/executive_report_service.py`):**
    *   Este serviço foi **movido do diretório raiz para o subdiretório `services` (`executive_report_service.py -> services/executive_report_service.py`)** para organizar melhor a arquitetura de serviços da aplicação, garantindo que a lógica de negócios complexa seja encapsulada e reutilizável.
    *   É o coração da funcionalidade, responsável por buscar, processar e analisar os dados do portfólio.
    *   **Fluxo de Dados:**
        1.  **Coleta de Dados:** `get_user_portfolio_data(user_id)` se conecta ao banco de dados PostgreSQL (`psycopg2`) para buscar todos os ativos, proventos históricos e informações do usuário. Utiliza `pandas` para manipular os DataFrames.
        2.  **Inferência de Perfil e Objetivo:** `infer_investor_profile_and_goal(active_df)` analisa a composição da carteira (`asset_type` e `invested_brl_est`) para determinar o perfil de risco (Conservador, Moderado, Arrojado) e o objetivo principal do investidor (Renda Passiva, Crescimento, Misto).
        3.  **Análise de Desempenho de Ativos:** `analyze_asset_performance(active_df)` identifica ativos que estão com preço médio acima do valor justo ou preço teto (`fair_value`, `price_ceiling`), ou que estão sob pressão setorial específica (ex: FIIs de escritório por vacância, REITs por juros altos nos EUA, commodities por desaceleração chinesa).
        4.  **Geração de Narrativa por IA:** `generate_ai_macro_narrative(...)` utiliza a API do Google Gemini para compilar uma análise executiva estruturada. Esta análise inclui:
            *   Um panorama macroeconômico atual para Brasil (Selic, IPCA, fiscal) e EUA (Fed Funds, câmbio USD/BRL).
            *   Uma explicação dos fatos relevantes setoriais que afetam os ativos sob pressão/desconto.
            *   Uma orientação estratégica para o investidor, alinhada ao seu perfil e objetivo.
            *   Possui um robusto *fallback* em caso de falha ou indisponibilidade da API do Gemini, garantindo que o relatório ainda seja gerado com uma análise genérica.
        5.  **Geração de PDF:** `generate_executive_pdf_report(user_id)` integra todos os dados coletados e as análises da IA para construir um documento PDF profissional usando a biblioteca `ReportLab`. O relatório inclui:
            *   Um cabeçalho estilizado.
            *   Cartões de KPI (Patrimônio Investido, Perfil, Objetivo, Média Mensal de Proventos).
            *   A narrativa da IA, formatada em tópicos claros.
            *   Uma tabela de alertas para ativos sob pressão/desconto, com estilização condicional (vermelho).
            *   É retornado em `bytes` para permitir o download direto na interface Streamlit.
*   **Interface do Usuário (`views/report_executivo.py`):**
    *   Uma nova view, `render_report_executivo_view()`, foi adicionada para apresentar a interface do Relatório Executivo.
    *   Esta view é acessível através de uma nova opção "📄 Report Executivo" no popover de perfil do usuário (`components/ui.py`).
    *   Utiliza `st.session_state` para armazenar o relatório gerado em cache (`report_data`) e o ID do usuário (`report_user_id`), evitando re-gerações desnecessárias e otimizando a experiência do usuário.
    *   Apresenta um cabeçalho informativo e um botão "🚀 Emitir Report Executivo Atualizado" para iniciar o processo de análise.
    *   Oferece um botão "📥 Baixar Report Executivo em PDF" para download do relatório gerado.
    *   Exibe KPIs resumidos (Patrimônio Investido, Perfil de Risco Inferido, Objetivo Detectado, Saúde do Portfólio).
    *   Organiza o conteúdo em abas (`st.tabs`): "🌐 Panorama Macroeconômico & Estratégia", "⚠️ Análise Setorial & Ativos sob Desconto" e "📊 Detalhamento dos Ativos em Carteira".
    *   Integra diretamente a narrativa da IA e a lista de ativos sob pressão ou com desconto para uma visão clara na interface.
*   **Integração na Aplicação (`app.py`):**
    *   A nova view `render_report_executivo_view` é importada e renderizada condicionalmente no `app.py` quando `st.session_state.navigation_tab == "Report_Executivo"`.
*   **Navegação (`components/ui.py`):**
    *   Um novo botão "📄 Report Executivo" foi adicionado ao menu de navegação (`st.popover`) em `components/ui.py`, permitindo fácil acesso à funcionalidade.

Esta nova capacidade de relatório executivo demonstra um avanço significativo na inteligência da aplicação, movendo-a de uma ferramenta de gestão de portfólio para um assistente de investimentos preditivo, que fornece análises contextualizadas e recomendações estratégicas acionáveis.
