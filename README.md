# Agente de Auto Deploy e Orquestrador de CI/CD (Multi-Agente)

Este projeto apresenta um sistema avançado de Continuous Integration/Continuous Deployment (CI/CD) orquestrado por um agente principal, `auto_push.py`. Utilizando inteligência artificial (Gemini API) e uma arquitetura multi-agente, ele automatiza o processo de versionamento semântico, geração de mensagens de commit, execução de testes e atualização de documentação antes de realizar o commit e o push das alterações para o repositório.

## Funcionalidades Principais

*   **Orquestração de Pipeline Multi-Agente:** O `auto_push.py` atua como um orquestrador, coordenando a execução de outros agentes especializados (como um Agente de Testes e um Agente de Documentação) para garantir a qualidade e a atualização do projeto em cada deploy.
*   **Versionamento Semântico Automatizado (SemVer):**
    *   Utiliza a IA (Gemini) para analisar o `git diff` e determinar de forma inteligente o tipo de incremento de versão (major, minor ou patch) conforme as boas práticas do Versionamento Semântico.
    *   Cria e gerencia o arquivo `.version` automaticamente, iniciando em `1.0.0` se não existir.
*   **Geração de Mensagens de Commit por IA:** A inteligência artificial é empregada para gerar mensagens de commit concisas, claras e padronizadas, que incluem a nova versão do projeto.
*   **Integração com Agente de Testes:** Antes de qualquer commit, o orquestrador invoca um `test_agent.py` para executar os testes do projeto. Se os testes falharem, o processo de deploy é abortado, garantindo a integridade do código.
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
    *Nota:* Certifique-se de que as tabelas necessárias, como `users`, estejam criadas no banco de dados.

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

Você verá o progresso e as decisões da IA sendo impressas no console.

## Arquitetura do Projeto

*   `auto_push.py`: O script principal e orquestrador do pipeline de CI/CD.
*   `.env`: Arquivo para variáveis de ambiente (como a chave da API do Gemini).
*   `.version`: Arquivo de controle de versão semântica.
*   `requirements.txt`: Lista de dependências Python.
*   `test_agent.py`: Responsável pela execução dos testes do projeto, utilizando `pytest`. Em caso de falha, a IA pode fornecer um diagnóstico e sugestões de correção.
*   `doc_agent.py`: Responsável pela criação e atualização automatizada da documentação do projeto. Ele agora emprega **diretrizes de contexto específicas** para gerar e refinar os conteúdos (como `README.md` para foco técnico, `docs/architecture.md` para detalhes arquiteturais e `docs/manual_do_usuario.md` para usuários leigos), assegurando que cada documento seja relevante e apropriado para seu público-alvo e sempre alinhado com as alterações de código.
*   `db/`: Diretório que contém módulos para interação com o banco de dados.
    *   `db/auth.py`: Módulo responsável pelas operações de autenticação e gerenciamento de usuários. A função `get_all_users` foi aprimorada para garantir que os dados dos usuários sejam sempre retornados ordenados por `id` de forma ascendente, otimizando a consistência dos resultados.
*   `views/`: Diretório que hospeda a lógica de apresentação e os controladores para diferentes interfaces.
    *   `views/admin.py`: Módulo que gerencia a interface administrativa. A lógica de exibição de usuários agora inclui uma etapa explícita de ordenação do DataFrame de usuários por `id` de forma ascendente, complementando a ordenação do banco de dados e assegurando uma apresentação consistente dos dados.
*   `docs/architecture.md`: Documentação detalhada da arquitetura do sistema multi-agente, incluindo o fluxo do pipeline e os componentes.
*   `docs/manual_do_usuario.md`: Documentação abrangente para o usuário final, explicando como interagir com o sistema e suas funcionalidades.
*   `tests/`: Diretório contendo os testes unitários do projeto, executados pelo `test_agent.py`.

## Contribuição

Contribuições são bem-vindas! Se você tiver ideias para melhorias, novas funcionalidades ou correção de bugs, sinta-se à vontade para abrir uma issue ou enviar um pull request.

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.
