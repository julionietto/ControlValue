# Agente de Auto Deploy e Orquestrador de CI/CD (Multi-Agente)

Este projeto apresenta um sistema avançado de Continuous Integration/Continuous Deployment (CI/CD) orquestrado por um agente principal, `auto_push.py`. Utilizando inteligência artificial (Gemini API) e uma arquitetura multi-agente, ele automatiza o processo de versionamento semântico, geração de mensagens de commit, execução de testes e atualização de documentação antes de realizar o commit e o push das alterações para o repositório.

## Funcionalidades Principais

*   **Orquestração de Pipeline Multi-Agente:** O `auto_push.py` atua como um orquestrador, coordenando a execução de outros agentes especializados (como um Agente de Testes e um Agente de Documentação) para garantir a qualidade e a atualização do projeto em cada deploy.
*   **Versionamento Semântico Automatizado (SemVer):**
    *   Utiliza a IA (Gemini) para analisar o `git diff` e determinar de forma inteligente o tipo de incremento de versão (major, minor ou patch) conforme as boas práticas do Versionamento Semântico.
    *   Cria e gerencia o arquivo `.version` automaticamente, iniciando em `1.0.0` se não existir.
*   **Geração de Mensagens de Commit por IA:** A inteligência artificial é empregada para gerar mensagens de commit concisas, claras e padronizadas, que incluem a nova versão do projeto.
*   **Integração com Agente de Testes:** Antes de qualquer commit, o orquestrador invoca um `test_agent.py` para executar os testes do projeto. Se os testes falharem, o processo de deploy é abortado, garantindo a integridade do código. A cobertura de testes foi expandida para incluir verificações robustas nas funcionalidades de autenticação, agora abrangendo cenários de login por nome de usuário e e-mail, com tratamento case-insensitive e de espaços em branco, além da capacidade de realizar testes de interface de usuário (UI) para aplicações Streamlit, assegurando a estabilidade e a qualidade das interações do usuário. Além disso, o `test_agent.py` agora gera um relatório detalhado dos testes em formato HTML, que é automaticamente aberto no navegador ao final da execução do pipeline.
*   **Integração com Agente de Documentação:** Após os testes, um `doc_agent.py` é executado para criar ou atualizar automaticamente a documentação do projeto. Este agente agora utiliza **diretrizes de contexto específicas** para cada tipo de documento, garantindo que o `README.md` mantenha um foco técnico, `docs/architecture.md` detalhe a estrutura e o fluxo do sistema, e `docs/manual_do_usuario.md` seja adaptado para um público leigo, explicando funcionalidades e mudanças visuais de forma acessível. Isso assegura que a documentação esteja sempre alinhada, precisa e adequada ao seu público-alvo.
*   **Compatibilidade Aprimorada:** Inclui configurações para forçar a codificação UTF-8 no console, resolvendo potenciais problemas de caracteres em ambientes Windows.
*   **Processo de Deploy Robusto:** Automatiza `git add`, `git commit` e `git push` para simplificar o fluxo de trabalho do desenvolvedor.

## Pré-requisitos

Para executar este projeto, você precisará ter instalado:

*   **Python 3.x:** Recomendado Python 3.8 ou superior.
*   **pip:** Gerenciador de pacotes do Python (geralmente incluído com o Python).
*   **Git:** Sistema de controle de versão.
*   **Chave de API do Google AI Studio (Gemini API):** Para a funcionalidade de IA.
*   **Pytest:** Usado pelo Agente de Testes para executar os testes do projeto.
*   **Streamlit:** Framework para criação de aplicações web interativas, utilizado para as interfaces do projeto.
*   **PostgreSQL:** O banco de dados PostgreSQL é utilizado para persistência de dados.
*   **psycopg2:** Driver Python para PostgreSQL, listado em `requirements.txt`.

## Instalação

Siga os passos abaixo para configurar o ambiente e começar a usar o agente:

1.  **Clone o repositório:**
    ```bash
    git clone <URL_DO_SEU_REPOSITORIO>
    cd <nome_do_seu_repositorio>
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    # No Windows:
    venv\Scripts\activate
    # No macOS/Linux:
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure sua chave de API do Gemini:**
    Crie um arquivo chamado `.env` na raiz do projeto e adicione sua chave de API do Google AI Studio (Gemini API) nele:
    ```
    GEMINI_API_KEY=SUA_CHAVE_DE_API_DO_GEMINI_AQUI
    ```

5.  **Inicialização do Banco de Dados (PostgreSQL):**
    Configure seu servidor PostgreSQL e crie um banco de dados conforme a necessidade do projeto. As credenciais de conexão (host, database, user, password) devem ser configuradas de forma segura (e.g., via variáveis de ambiente ou arquivo `.env`).
    *Nota:* Certifique-se de que as tabelas necessárias, como `users`, estejam criadas no banco de dados. A função `init_db()` em `db/connection.py` é responsável por criar as tabelas do sistema e realizar migrações de esquema, como a conversão de colunas de data para o tipo `DATE` na tabela `opcoes`.

## Uso

Para utilizar o Agente de Auto Deploy, siga este fluxo de trabalho:

1.  **Faça suas alterações no código.**
2.  **Execute o script principal:**
    ```bash
    python auto_push.py
    ```

O `auto_push.py` irá então:
*   Verificar as alterações em staging.
*   Invocar o `test_agent.py`. Se houver falhas, o processo será interrompido.
*   Invocar o `doc_agent.py` para atualizar a documentação.
*   Adicionar quaisquer arquivos de documentação alterados/criados ao staging.
*   Utilizar a IA para determinar o incremento de versão (major, minor, patch).
*   Atualizar o arquivo `.version` e adicioná-lo ao staging.
*   Utilizar a IA para gerar uma mensagem de commit detalhada, incluindo a nova versão.
*   Realizar o `git commit` com a mensagem gerada.
*   Executar o `git push` para o branch `master` (ou o branch configurado por padrão).
*   Abrir o relatório de testes HTML gerado (`docs/test_report.html`) no navegador. O sistema prioriza a abertura no Microsoft Edge (especialmente em ambientes Windows) e, caso não seja possível, tentará abrir no navegador padrão configurado.

Você verá o progresso e as decisões da IA sendo impressas no console.

## Arquitetura do Projeto

*   `auto_push.py`: O script principal e orquestrador do pipeline de CI/CD.
*   `.env`: Arquivo para variáveis de ambiente (como a chave da API do Gemini).
*   `.version`: Arquivo de controle de versão semântica.
*   `requirements.txt`: Lista de dependências Python.
*   `test_agent.py`: Responsável pela execução dos testes do projeto, utilizando `pytest`. Agora, além de executar os testes, ele gera um relatório detalhado em formato JUnit XML (`tests/report.xml`) e, a partir deste, um relatório HTML "ultra-premium" (`docs/test_report.html`) que é automaticamente aberto ao final do pipeline. Em caso de falha, a IA pode fornecer um diagnóstico e sugestões de correção.
*   `doc_agent.py`: Responsável pela criação e atualização automatizada da documentação do projeto. Ele agora emprega **diretrizes de contexto específicas** para gerar e refinar os conteúdos (como `README.md` para foco técnico, `docs/architecture.md` para detalhes arquiteturais e `docs/manual_do_usuario.md` para usuários leigos), assegurando que cada documento seja relevante e apropriado para seu público-alvo e sempre alinhado com as alterações de código.
*   `db/`: Diretório que contém módulos para interação com o banco de dados.
    *   `db/connection.py`: Módulo para gerenciamento da conexão com o banco de dados. A função `init_db` foi aprimorada para incluir uma migração automática de esquema para a tabela `opcoes`, convertendo as colunas `dt_operacao` e `dt_vencimento` de `TEXT` para o tipo `DATE` do PostgreSQL, garantindo a consistência e o correto manuseio de datas.
    *   `db/auth.py`: Módulo responsável pelas operações de autenticação e gerenciamento de usuários. A lógica de verificação de usuário (`verify_user`) foi significativamente aprimorada para permitir login tanto por e-mail quanto por nome de usuário, com tratamento case-insensitive e remoção de espaços em branco. Funções como `create_user` e `admin_update_user` também foram ajustadas para limpar e padronizar as entradas de usuário e e-mail. Adicionalmente, a função `get_all_users` garante que os dados dos usuários sejam sempre retornados ordenados por `id` de forma ascendente, otimizando a consistência dos resultados.
    *   `db/options.py`: O módulo `db/options.py` agora inclui a função utilitária `_parse_date_to_iso`, que padroniza a conversão de diversas entradas de data (incluindo strings e objetos de data) para o formato ISO `YYYY-MM-DD`, fundamental para a correta persistência de dados no banco de dados. A função `get_opcoes_import` foi atualizada para utilizar essa nova lógica, garantindo a robustez na importação de dados de opções, com validação explícita para datas de operação e vencimento.
*   `views/`: Diretório que hospeda a lógica de apresentação e os controladores para diferentes interfaces.
    *   `views/auth.py`: Módulo aprimorado para oferecer uma experiência de login flexível e segura, adaptando-se às melhorias no backend de autenticação. O campo de senha agora mantém sempre a máscara de caracteres para maior segurança, focando na robustez da validação de credenciais. A implementação da interface de login foi refatorada para utilizar `st.form`, garantindo um manuseio mais robusto e consistente do estado dos campos e da submissão do formulário.
    *   `views/admin.py`: Módulo que gerencia a interface administrativa. A lógica de exibição de usuários agora inclui uma etapa explícita de ordenação do DataFrame de usuários por `id` de forma ascendente, complementando a ordenação do banco de dados e assegurando uma apresentação consistente dos dados.
    *   `views/geral.py`: Módulo responsável pela visualização da "Visão Geral" do portfólio, incluindo gráficos de proventos e retorno total por ativo. A lógica de exibição de tickers em gráficos foi simplificada para utilizar diretamente o nome formatado do ativo, promovendo maior consistência visual nas representações de dados. **Foi aprimorada a categorização de ativos, agrupando 'ETF' e 'Cripto' sob a nova categoria 'ETF/Cripto' tanto para fins de filtragem quanto para visualização em gráficos, consolidando a apresentação dessas classes de ativos.**
    *   `views/proventos.py` e `views/proventos_historico.py`: Módulos responsáveis pela visualização e gerenciamento de dados de proventos. As tabelas de proventos, que anteriormente usavam `st.dataframe`, foram refatoradas para serem geradas diretamente como HTML customizado. Essa abordagem permite um controle granular sobre a estilização (cores condicionais, alinhamento, fontes), integração coesa de linhas de rodapé na mesma estrutura de tabela HTML, e melhorias de performance. Especificamente para a visualização histórica (`views/proventos_historico.py`), o processamento de dados foi aprimorado para construir uma tabela dinâmica (pivot_table) que organiza os proventos por ticker e mês, garantindo a inclusão de todos os meses, mesmo aqueles sem valores, e a ordenação consistente por ticker antes da exibição. As linhas de rodapé agora exibem "TOTAL", "CRESCIMENTO" (comparado ao ano anterior) e "VALOR MÉDIO" (anteriormente "MÉDIA ACUMULADA"). A coluna de "Valor Mensal" foi removida da exibição direta nas tabelas, focando em "Valor Anual". Uma legenda explicativa para "Crescimento" e "Valor Médio" foi adicionada na interface. A interação para edição e adição de ativos foi aprimorada, substituindo a seleção implícita de linhas por um `st.selectbox` explícito para "Editar Ativo" e um botão "➕ Adicionar Ativo", organizados em `st.columns` para uma melhor experiência do usuário e uso de `st.rerun()` para gerenciar o estado da aplicação de forma consistente.
*   `utils/`: Diretório para funções utilitárias.
    *   `utils/formatters.py`: O módulo `utils/formatters.py` agora centraliza a função `parse_currency`, responsável por converter strings monetárias em diversos formatos (incluindo `R$`, `$`, separadores de milhar e decimal variados) para valores `float`, garantindo a correta interpretação numérica em todo o sistema.
*   `docs/architecture.md`: Documentação detalhada da arquitetura do sistema multi-agente, incluindo o fluxo do pipeline e os componentes.
*   `docs/manual_do_usuario.md`: Documentação abrangente para o usuário final, explicando como interagir com o sistema e suas funcionalidades.
*   `docs/test_report.html`: Relatório HTML gerado automaticamente pelo `test_agent.py` contendo os resultados detalhados da execução dos testes.
*   `tests/`: Diretório contendo os testes unitários e de integração do projeto, executados pelo `test_agent.py`. A suíte de testes de autenticação (`tests/test_auth.py`) foi expandida com novos testes para cenários de login por nome de usuário e e-mail (case-insensitive e com tratamento de espaços), garantindo a robustez do processo de login e logout. O número total de testes passou de 16 para 17, reforçando a cobertura do sistema.

## Contribuição

Contribuições são bem-vindas! Se você tiver ideias para melhorias, novas funcionalidades ou correção de bugs, sinta-se à vontade para abrir uma issue ou enviar um pull request.

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.
