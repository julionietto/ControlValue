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
*   **Geração de Relatórios Executivos Inteligentes por IA:** Um novo módulo `Report Executivo` foi introduzido, utilizando a IA (Gemini API) para realizar uma análise macroeconômica viva e personalizada do portfólio do investidor. Ele infere o perfil de risco do investidor, detecta os objetivos patrimoniais e identifica ativos sob pressão/desconto, gerando um relatório PDF profissional e detalhado com orientações estratégicas, pronto para download. **Esta funcionalidade foi aprimorada para incluir uma análise detalhada dos *aportes líquidos (compras - vendas) realizados no ano corrente*, visualização de *proventos recebidos e provisionados mês a mês*, e suporte à exibição de ativos e cotações em *múltiplas moedas* (e.g., USD), proporcionando uma visão mais completa e adaptada para investimentos internacionais.**
*   **Compatibilidade Aprimorada:** Inclui configurações para forçar a codificação UTF-8 no console, resolvendo potenciais problemas de caracteres em ambientes Windows.
*   **Processo de Deploy Robusto:** Automatiza `git add`, `git commit` e `git push` para simplificar o fluxo de trabalho do desenvolvedor.
*   **Análise Comparativa de Proventos:** A interface de histórico de proventos agora oferece uma funcionalidade de "Consulta Comparativa", permitindo aos usuários comparar os proventos recebidos por ativo entre dois períodos (mês/ano) selecionados, apresentando a diferença e totalizadores em uma tabela detalhada.

## Pré-requisitos

Para executar este projeto, você precisará ter instalado:

*   **Python 3.x:** Recomendado Python 3.8 ou superior.
*   **pip:** Gerenciador de pacotes do Python (geralmente incluído com o Python).
*   **Git:** Sistema de controle de versão.
*   **Chave de API do Google AI Studio (Gemini API):** Para a funcionalidade de IA.
*   **Pytest:** Usado pelo Agente de Testes para executar os testes do projeto (versão 8.0.0 ou superior).
*   **Streamlit:** Framework para criação de aplicações web interativas, utilizado para as interfaces do projeto.
*   **PostgreSQL:** O banco de dados PostgreSQL é utilizado para persistência de dados.
*   **psycopg2:** Driver Python para PostgreSQL, listado em `requirements.txt`.
*   **reportlab:** Biblioteca para geração de documentos PDF (versão 4.0.0 ou superior).
*   **matplotlib:** Biblioteca para criação de gráficos e visualizações de dados (versão 3.8.0 ou superior).
*   **google-generativeai:** Biblioteca oficial do Google para interagir com modelos generativos (versão 0.8.0 ou superior).

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

4.  **Configure sua chave de API do Gemini e outras variáveis de ambiente:**
    Crie um arquivo chamado `.env` na raiz do projeto e adicione sua chave de API do Google AI Studio (Gemini API) nele. Opcionalmente, você pode configurar um e-mail para relatórios de exceção:
    ```
    GEMINI_API_KEY=SUA_CHAVE_DE_API_DO_GEMINI_AQUI
    ADMIN_EMAIL=SEU_EMAIL_PARA_NOTIFICACOES_AQUI # Opcional, para relatórios de exceção
    ```

5.  **Inicialização do Banco de Dados (PostgreSQL):**
    Configure seu servidor PostgreSQL e crie um banco de dados conforme a necessidade do projeto. As credenciais de conexão (host, database, user, password) devem ser configuradas de forma segura (e.g., via variáveis de ambiente ou arquivo `.env`).
    *   **Gestão de Conexões (Neon.tech Auto-Suspend):** Este projeto utiliza um padrão de conexão direta ao banco de dados, onde cada operação abre e fecha sua conexão imediatamente. Isso é crucial para ambientes como a Neon.tech, que implementam "Auto-Suspend" para economizar recursos e evitar custos, suspendendo o banco quando não há conexões ativas. **Não há pool de conexões persistente.**
    *Nota:* Certifique-se de que as tabelas necessárias, como `users`, estejam criadas no banco de dados. A função `init_db()` em `db/connection.py` é responsável por criar as tabelas do sistema e realizar migrações de esquema, como a conversão de colunas de data para o tipo `DATE` na tabela `opcoes`. Para otimizar o desempenho em ambientes Streamlit, a chamada a `init_db()` foi ajustada em `app.py` para ocorrer apenas uma vez por sessão da aplicação, prevenindo reinicializações desnecessárias e garantindo um gerenciamento eficiente dos recursos.

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

**Para acessar o Report Executivo:**
*   Acesse o `Report Executivo` através do menu de perfil (ícone de usuário no canto superior direito da aplicação Streamlit), clicando no botão '📄 Report Executivo' para visualizar análises de IA e gerar relatórios em PDF.

Você verá o progresso e as decisões da IA sendo impressas no console.

## Arquitetura do Projeto

*   `auto_push.py`: O script principal e orquestrador do pipeline de CI/CD.
*   `.env`: Arquivo para variáveis de ambiente (como a chave da API do Gemini).
*   `.version`: Arquivo de controle de versão semântica.
*   `requirements.txt`: Lista de dependências Python.
*   `test_agent.py`: Responsável pela execução dos testes do projeto, utilizando `pytest`. Agora, além de executar os testes, ele gera um relatório detalhado em formato JUnit XML (`tests/report.xml`) e, a partir deste, um relatório HTML "ultra-premium" (`docs/test_report.html`) que é automaticamente aberto ao final do pipeline. Em caso de falha, a IA pode fornecer um diagnóstico e sugestões de correção.
*   `doc_agent.py`: Responsável pela criação e atualização automatizada da documentação do projeto. Ele agora emprega **diretrizes de contexto específicas** para gerar e refinar os conteúdos (como `README.md` para foco técnico, `docs/architecture.md` para detalhes arquiteturais e `docs/manual_do_usuario.md` para usuários leigos), assegurando que cada documento seja relevante e apropriado para seu público-alvo e sempre alinhado com as alterações de código.
*   `db/`: Diretório que contém módulos para interação com o banco de dados.
    *   `db/connection.py`: Este módulo é responsável por gerenciar a conexão com o banco de dados. Devido a uma **premissa arquitetural obrigatória para o Auto-Suspend da Neon.tech**, o sistema agora adota um padrão de conexão direta, onde **cada operação de banco de dados abre e fecha sua própria conexão imediatamente**. Isso garante que não haja conexões persistentes ou pools de conexões ativos que impeçam o banco de dados de entrar em modo de suspensão quando inativo, otimizando o uso de recursos e evitando custos. A função `get_db_connection` atua como um gerenciador de contexto (`context manager`), garantindo que a conexão seja criada ao entrar no bloco e, crucialmente, **fechada ao sair**, encapsulando de forma segura a aquisição e liberação de recursos. Para otimizar o desempenho em aplicações Streamlit, a função `clear_db_cache` foi introduzida aqui, permitindo invalidar o cache de dados do Streamlit (`st.cache_data`) de forma controlada após operações de escrita no banco de dados, garantindo que a interface sempre exiba dados atualizados sem reconsultar o DB desnecessariamente. As funções `init_connection_pool` e `close_pool` são mantidas como legadas para compatibilidade, mas não são mais utilizadas para gerenciamento ativo de pools de conexão persistentes. A função `init_db` continua sendo responsável por criar as tabelas do sistema e executar migrações de esquema (como a conversão de colunas de data para o tipo `DATE` na tabela `opcoes`), utilizando o `get_db_connection` para suas operações, garantindo a consistência e o correto manuseio de datas.
    *   `db/auth.py`: Módulo responsável pelas operações de autenticação e gerenciamento de usuários. A lógica de verificação de usuário (`verify_user`) foi significativamente aprimorada para permitir login tanto por e-mail quanto por nome de usuário, com tratamento case-insensitive e com remoção de espaços em branco. Funções como `create_user` e `admin_update_user` também foram ajustadas para limpar e padronizar as entradas de usuário e e-mail. Adicionalmente, a função `get_all_users` garante que os dados dos usuários sejam sempre retornados ordenados por `id` de forma ascendente, otimizando a consistência dos resultados. **Note que a funcionalidade de desbloqueio automático de contas, anteriormente gerenciada por uma thread em segundo plano, foi simplificada; o desbloqueio agora é avaliado e aplicado de forma síncrona durante as tentativas de login, baseando-se no timestamp de bloqueio, eliminando a necessidade de uma rotina assíncrona.**
    *   `db/assets.py`: Módulo que gerencia a persistência de dados e operações relacionadas aos ativos do portfólio. Funções de leitura de dados (`get_all_assets`, `get_asset_by_id`, `get_asset_history`, `get_all_asset_histories`, `get_user_allocations`) agora utilizam `st.cache_data` com um TTL (Time-To-Live) de 300 segundos, otimizando o desempenho ao armazenar resultados de consultas em cache. Todas as operações de escrita (adição, atualização e exclusão de ativos e suas operações) agora chamam `clear_db_cache()` para garantir a imediata invalidação do cache e a exibição de dados atualizados na interface.
    *   `db/dividends.py`: Este módulo lida com a gestão e recuperação de dados de proventos. Assim como outros módulos de dados, funções de leitura cruciais como `get_proventos`, `get_proventos_provisionados_calculados`, `get_total_proventos_by_ticker`, `get_total_proventos_all_tickers` e `get_all_total_proventos` foram aprimoradas com `st.cache_data(ttl=300)` para acelerar a recuperação de dados em ambientes Streamlit. As operações de escrita (salvar, excluir, adicionar proventos provisionados, importar) agora invocam `clear_db_cache()` para manter a consistência entre o banco de dados e o cache da aplicação.
    *   `db/options.py`: O módulo `db/options.py` agora inclui a função utilitária `_parse_date_to_iso`, que padroniza a conversão de diversas entradas de data (incluindo strings e objetos de data) para o formato ISO `YYYY-MM-DD`, fundamental para a correta persistência de dados no banco de dados. A função `get_opcoes` foi otimizada com `st.cache_data(ttl=300)` para cachear os resultados das consultas. A função `get_opcoes_import` foi atualizada para utilizar a nova lógica de data e, como todas as funções de escrita (inserção, atualização e exclusão de opções), agora inclui a chamada a `clear_db_cache()` para garantir que qualquer alteração nos dados reflita imediatamente na interface do usuário.
*   `services/`: Novo diretório para encapsular a lógica de serviços de negócio.
    *   `services/executive_report_service.py`: É responsável pela lógica de recuperação de dados do portfólio, inferência de perfil e objetivos do investidor, análise de desempenho dos ativos e, crucialmente, pela integração com a Gemini API para gerar uma análise macroeconômica e estratégica inteligente, além de orquestrar a geração do relatório em PDF usando `reportlab`. **Este serviço agora calcula e inclui o *total de aportes líquidos (compras - vendas) realizados no ano corrente* na análise do portfólio. A lógica de análise de desempenho de ativos foi refinada para lidar com *múltiplas moedas* (exibindo valores em USD para ativos estrangeiros) e utiliza o campo `price_ceiling` de forma mais robusta. O relatório PDF foi atualizado para apresentar *cinco KPIs principais* (incluindo "Aportes Líquidos (Ano)") e para exibir corretamente os símbolos monetários (R$ ou U$) nas seções de ativos sob pressão.**
*   `views/`: Diretório que hospeda a lógica de apresentação e os controladores para diferentes interfaces.
    *   `views/auth.py`: Módulo aprimorado para oferecer uma experiência de login flexível e segura, adaptando-se às melhorias no backend de autenticação. O campo de senha agora mantém sempre a máscara de caracteres para maior segurança, focando na robustez da validação de credenciais. A implementação da interface de login foi refatorada para utilizar `st.form`, garantindo um manuseio mais robusto e consistente do estado dos campos e da submissão do formulário.
    *   `views/admin.py`: Módulo que gerencia a interface administrativa. A lógica de exibição de usuários agora inclui uma etapa explícita de ordenação do DataFrame de usuários por `id` de forma ascendente, complementando a ordenação do banco de dados e assegurando uma apresentação consistente dos dados.
    *   `views/asset_detail.py`: Módulo responsável por exibir a visão detalhada de um ativo específico, apresentando informações como histórico de transações, desempenho e métricas relevantes. **Foi aprimorado para incluir estilização condicional na tabela de histórico de operações: a lógica de coloração foi refinada, calculando um `raw_diff` para determinar o resultado da operação e aplicando destaque em verde (`#00CC96`) para lucros e vermelho (`#EF553B`) para prejuízos nas colunas '% Ganho', 'Vlr Atualizado' e 'Lucro/Prej'. A coluna auxiliar `raw_diff` é explicitamente ocultada na exibição, garantindo uma visualização limpa e focada no resultado financeiro.**
    *   `views/geral.py`: Módulo responsável pela visualização da "Visão Geral" do portfólio, incluindo gráficos de proventos e retorno total por ativo. A lógica de exibição de tickers em gráficos foi simplificada para utilizar diretamente o nome formatado do ativo, promovendo maior consistência visual nas representações de dados. **Foi aprimorada a categorização de ativos, agrupando 'ETF' e 'Cripto' sob a nova categoria 'ETF/Cripto' tanto para fins de filtragem quanto para visualização em gráficos, consolidando a apresentação dessas classes de ativos. Adicionalmente, foram implementados novos diálogos interativos para aprofundar a análise de ativos: `dialog_rv_assets_by_sector` (anteriormente `dialog_assets_by_sector`) permite visualizar ativos de Renda Variável por setor, e o novo `dialog_fii_assets_by_sector` oferece uma visão detalhada dos Fundos de Investimento Imobiliário (FIIs) por segmento, ambos exibindo ticker, quantidade e saldo atual de forma formatada. Além disso, a tabela de radar para "Ativos nos Estados Unidos" agora apresenta os valores dos ativos em dólar e, para os valores em Real, o nome da coluna é dinamicamente ajustado para "Valor em Real" (quando o dólar também é exibido) ou "Valor do Ativo", proporcionando uma visão mais direta e transparente para investimentos internacionais.**
    *   `views/proventos.py` e `views/proventos_historico.py`: Módulos responsáveis pela visualização e gerenciamento de dados de proventos. As tabelas de proventos, que anteriormente usavam `st.dataframe`, foram refatoradas para serem geradas diretamente como HTML customizado. Essa abordagem permite um controle granular sobre a estilização (cores condicionais, alinhamento, fontes), integração coesa de linhas de rodapé na mesma estrutura de tabela HTML, e melhorias de performance. Especificamente para a visualização histórica (`views/proventos_historico.py`), o processamento de dados foi aprimorado para construir uma tabela dinâmica (pivot_table) que organiza os proventos por ticker e mês, garantindo a inclusão de todos os meses, mesmo aqueles sem valores, e a ordenação consistente por ticker antes da exibição. As linhas de rodapé agora exibem "TOTAL", "CRESCIMENTO" (comparado ao ano anterior) e "VALOR MÉDIO" (anteriormente "MÉDIA ACUMULADA"). A coluna de "Valor Mensal" foi removida da exibição direta nas tabelas, focando em "Valor Anual". Uma legenda explicativa para "Crescimento" e "Valor Médio" foi adicionada na interface. A interação para edição e adição de ativos foi aprimorada, substituindo a seleção implícita de linhas por um `st.selectbox` explícito para "Editar Ativo" e um botão "➕ Adicionar Ativo", organizados em `st.columns` para uma melhor experiência do usuário e uso de `st.rerun()` para gerenciar o estado da aplicação de forma consistente. **Adicionalmente, o `views/proventos_historico.py` agora inclui uma funcionalidade de "Consulta Comparativa". A interface desta consulta foi aprimorada para oferecer uma experiência mais intuitiva, com a pré-seleção dos períodos otimizada para o ano anterior (Lado A) e o ano corrente (Lado B), ambos com o mês corrente, e garantindo que o ano corrente e o anterior estejam sempre disponíveis nas opções de seleção. A tabela de resultados apresenta uma comparação detalhada dos proventos recebidos por ativo entre dois períodos selecionados, exibindo a diferença (calculada como Período B - Período A, indicando crescimento ou declínio) e totalizadores em uma tabela HTML estilizada e responsiva. Para melhorar a visualização e a usabilidade, especialmente em conjuntos de dados maiores, a tabela foi projetada para ser rolavel com cabeçalhos e rodapés fixos (sticky). A ativação desta consulta agora garante uma atualização imediata da interface graças ao uso de `st.rerun()` após o clique no botão correspondente, proporcionando uma experiência de usuário mais fluida.**
    *   **`views/proventos_resumo.py`:** Um novo módulo dedicado à visualização consolidada e detalhada de proventos. A interface foi aprimorada com o uso de `st.tabs` para alternar entre "Evolução Anual" e "Distribuição por Classe". A aba "Evolução Anual" mantém o consolidado mensal e anual de proventos, com destaque para o maior valor recebido. Além disso, **introduz uma seção específica para "Proventos Dolarizados (Valores em R$)", apresentando o resumo anual de proventos oriundos de Stocks e Reits convertidos para BRL.** A nova aba "Distribuição por Classe" foi significativamente aprimorada: agora exibe dois totalizadores no topo ("Total Recebido no Mês" e "Total Recebido no Ano"), e a tabela detalhada apresenta os valores e porcentagens tanto mensais quanto anuais (`Valor Mês`, `% Mês`, `Valor Ano`, `% Ano`) para cada classe de ativo (ex: Ações, FIIs, Cripto), com estilização condicional de cores. Essa aba é complementada por dois gráficos de pizza interativos (`plotly.express`), "Distribuição do Mês" e "Acumulado do Ano", que ilustram a distribuição percentual das classes de ativos para o período selecionado e o ano corrente, respectivamente, com tratamento para ocultar valores quando a opção de privacidade está ativada e utilizando um mapeamento de cores consistente. **A visualização foi aprimorada com a adição de um diálogo interativo '🔍 Detalhamento por Ativo no Mês', que é acionado ao selecionar uma linha na tabela de distribuição por classe. Este diálogo permite uma exploração mais granular dos proventos, exibindo o detalhamento por ativo individualmente dentro da classe selecionada para o mês corrente, incluindo apenas lançamentos com valores maiores que zero, e com formatação e estilização condicional dos valores.** Para otimizar a usabilidade, os filtros de seleção de ano e mês agora são pré-selecionados por padrão para o ano e o mês correntes, respectivamente. Para aprimorar significativamente o desempenho e a reatividade da interface, a visualização de resumo de proventos (`views/proventos_resumo.py`) agora faz uso extensivo de `st.cache_data` para cachear os resultados das consultas de banco de dados (`db.get_proventos` e `db.get_all_assets`) por um período de 10 segundos. Essa otimização evita chamadas redundantes ao banco de dados em cada interação do usuário, garantindo uma experiência mais fluida. Além disso, o mapeamento de ativos (`full_assets_map`) é carregado e processado uma única vez no início da função, reduzindo o overhead computacional.
    *   **`views/report_executivo.py`:** Um novo módulo que implementa a interface Streamlit para a geração e visualização do Report Executivo, permitindo ao usuário interagir com a análise da IA e baixar o relatório em PDF. **A interface foi expandida para incluir um *novo card de KPI* que exibe o total de aportes líquidos (compras - vendas) do ano corrente. A seção de proventos foi significativamente aprimorada com uma *análise mais detalhada dos proventos YTD (Year-to-Date)* e um *gráfico combinado de barras e linha* que visualiza os proventos *recebidos e provisionados mês a mês* para o ano atual, juntamente com a média acumulada. A lógica de cálculo e exibição da evolução histórica de proventos e da média mensal foi refinada para o ano corrente, garantindo que o gráfico reflita com precisão os proventos acumulados YTD e a média mensal até o mês atual, proporcionando uma visão consistente com os dados mais recentes.** Além disso, os alertas de ativos sob pressão agora exibem as cotações com os *símbolos monetários correspondentes (R$ ou U$)*.
*   `utils/`: Diretório para funções utilitárias.
    *   `utils/formatters.py`: O módulo `utils/formatters.py` agora centraliza a função `parse_currency`, responsável por converter strings monetárias em diversos formatos (incluindo `R$`, `$`, separadores de milhar e decimal variados) para valores `float`, garantindo a correta interpretação numérica em todo o sistema. **Adicionalmente, inclui a função `get_annual_proventos_summary`, que calcula o resumo anual e mensal de proventos, ajustando o cálculo da média mensal para o ano corrente com base nos meses já decorridos, proporcionando uma análise financeira mais precisa.**
*   `scratch/`: Diretório que hospeda scripts e arquivos temporários ou de experimentação, que podem ser removidos conforme o desenvolvimento avança.
*   `docs/architecture.md`: Documentação detalhada da arquitetura do sistema multi-agente, incluindo o fluxo do pipeline e os componentes.
*   `docs/manual_do_usuario.md`: Documentação abrangente para o usuário final, explicando como interagir com o sistema e suas funcionalidades.
*   `docs/test_report.html`: Relatório HTML gerado automaticamente pelo `test_agent.py` contendo os resultados detalhados da execução dos testes.
*   **`docs/relatorio_investimentos_bruna_nietto.pdf`**: Exemplo de relatório executivo em PDF gerado pelo sistema.
*   **`docs/relatorio_investimentos_julio_nietto.pdf`**: Exemplo de relatório executivo em PDF gerado pelo sistema.
*   **`docs/relatorio_investimentos_tatiana_domiciano.pdf`**: Exemplo de relatório executivo em PDF gerado pelo sistema.
*   `tests/`: Diretório contendo os testes unitários e de integração do projeto, executados pelo `test_agent.py`. A suíte de testes de autenticação (`tests/test_auth.py`) foi expandida com novos testes para cenários de login por nome de usuário e e-mail (case-insensitive e com tratamento de espaços), garantindo a robustez do processo de login e logout. **A cobertura de testes foi estendida para incluir validações da função `get_annual_proventos_summary` em `tests/test_formatters.py`, assegurando a precisão dos cálculos de resumo anual e mensal de proventos, especialmente o ajuste da média mensal para o ano corrente. Um novo arquivo de testes, `tests/test_consulta_comparativa.py`, foi adicionado para validar a funcionalidade de comparação de proventos entre períodos, garantindo que os dados sejam corretamente obtidos, agrupados e ordenados, e que a lógica de cálculo da diferença (Período B - Período A) seja precisa.** O número total de testes foi atualizado para **24**, reforçando a cobertura do sistema.

## Contribuição

Contribuições são bem-vindas! Se você tiver ideias para melhorias, novas funcionalidades ou correção de bugs, sinta-se à vontade para abrir uma issue ou enviar um pull request.

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.
