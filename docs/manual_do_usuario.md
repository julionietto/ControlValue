# Manual do Usuário - ControlValue 📈

Bem-vindo ao **ControlValue**, a sua plataforma pessoal para consolidação, acompanhamento e análise de investimentos! Este guia foi feito para ajudar você a navegar e utilizar todos os recursos do sistema, mesmo se você não tiver conhecimento técnico em informática.

---

## 1. Como Acessar o Sistema

### 🔑 Criando sua Conta e Fazendo Login
1. Ao abrir o ControlValue, você verá a tela de **Acesso**.
2. Se for seu primeiro acesso, clique na aba **Cadastrar** (ou botão de cadastro), preencha seu e-mail e crie uma senha segura.
3. Se já tiver cadastro, basta preencher seu **e-mail ou nome de usuário** e sua senha cadastrados na aba **Entrar**. O sistema é inteligente: ele reconhece seu e-mail ou nome de usuário independentemente de letras maiúsculas ou minúsculas e também ignora espaços extras no início ou fim do que você digitar, facilitando o seu acesso.
4. **Recuperação de Senha:** Caso esqueça sua senha, clique no link de recuperação. Você receberá um e-mail com instruções e um link seguro para cadastrar uma nova senha (o link é válido por 30 minutos).

### 🛡️ Segurança: Desconexão Automática (Timeout)
Para a segurança dos seus dados financeiros, caso você deixe a página aberta e fique **10 minutos sem interagir** (sem clicar em nada), o sistema encerrará sua sessão automaticamente. Se isso acontecer, basta fazer o login novamente.

---

## 2. Conhecendo a Tela Principal (Dashboard)

Ao fazer o login, você será direcionado para a **Visão Geral** da sua carteira.

*   **Cards de Resumo:** Na parte superior, você verá indicadores rápidos do seu patrimônio total, rentabilidade acumulada e os últimos proventos (dividendos) recebidos.
*   **Gráficos Interativos:** Veja visualmente como seu dinheiro está dividido entre diferentes classes de ativos (Ações, Fundos Imobiliários, Renda Fixa, Reits, etc.) e setores da economia. **Para simplificar a visualização, os ativos do tipo ETF (Exchange Traded Funds) e Criptomoedas agora são agrupados em uma única categoria chamada "ETF/Cripto" nos gráficos de alocação.** Passando o mouse por cima dos gráficos, você verá os detalhes e porcentagens de cada fatia. A categorização dos Fundos Imobiliários (FIIs) por setor é continuamente atualizada para garantir que seus gráficos de alocação estejam sempre precisos, incluindo os ativos mais recentes.
*   **Menu de Navegação:** Localizado na barra superior ou lateral, ele permite alternar entre as diferentes visões do sistema.

---

## 3. Como Importar seus Investimentos (Ativos e Proventos)

Em vez de cadastrar operação por operação manualmente, você pode importar seus dados em lote de forma muito simples.

### 📥 Importando Ativos (Suas Compras e Vendas)
1. Clique no menu de perfil ou no botão de importação no topo da tela e selecione **Importar Ativos (CSV)**.
2. O sistema disponibiliza um modelo de arquivo para download. Baixe o modelo para ver como as colunas devem ser preenchidas (ex: ticker do ativo, quantidade, preço de compra, data).
3. Preencha seus dados de acordo com o modelo, salve o arquivo no formato **CSV** e faça o envio (upload) na tela.
4. O sistema processará as informações e atualizará seu saldo patrimonial instantaneamente.

### 💰 Importando Proventos (Dividendos e JCP Recebidos)
1. No mesmo menu, selecione **Importar Proventos (CSV)**.
2. Assim como nos ativos, siga o modelo de arquivo fornecido (data de pagamento, ativo, tipo de provento e valor recebido).
3. Faça o upload do arquivo CSV correspondente para registrar todo o histórico de rendimentos da sua carteira.

**Importação Mais Flexível de Valores:** O ControlValue agora aceita uma variedade maior de formatos para valores monetários nas suas planilhas (CSV), como "R$ 1.250,50", "1.250,50", "38,50" ou simplesmente números. Isso torna a importação de ativos e proventos (e também de opções, se você as importa) ainda mais simples e com menos chance de erros de formatação.

---

## 4. Navegando Pelas Abas do Sistema

### 📊 Visão Geral
Exibe a consolidação de toda a sua carteira de investimentos, gráficos de alocação e desempenho histórico acumulado comparado a índices de mercado (como o IBOVESPA ou CDI).

### 🔍 Detalhes do Ativo
Quer analisar um investimento específico? Selecione o ativo (ex: PETR4, WEGE3) para ver um raio-x completo:
*   Preço médio de compra vs. preço atual de mercado.
*   Lucro ou prejuízo (nominal e percentual).
*   Histórico de dividendos pagos exclusivamente por aquele ativo.
*   Lista de todas as compras e vendas realizadas daquele papel. Para facilitar a sua análise, a tabela de histórico agora utiliza cores. Se você tem uma posição aberta (aúnão vendeu tudo) e essa operação está gerando **lucro**, a linha correspondente mostrará o **percentual de ganho, valor atualizado e lucro/prejuízo em verde**. Se estiver gerando **prejuízo**, esses mesmos valores aparecerão em **vermelho**, permitindo uma identificação rápida do desempenho de cada operação.

### 💵 Proventos (Rendimentos)
Esta aba é dedicada a quem busca viver de renda, permitindo um controle detalhado sobre seus recebimentos. As tabelas de proventos foram aprimoradas para uma visualização ainda mais clara e consistente, apresentando todos os dados de forma unificada e fácil de ler.

Para garantir uma experiência ainda mais fluida e rápida, otimizamos o carregamento de todas as informações de proventos. Isso significa que, ao navegar pelas diferentes abas e gráficos desta seção, os dados serão exibidos mais rapidamente, proporcionando uma análise mais ágil da sua renda passiva.

Para garantir a máxima precisão, o sistema agora registra proventos provisionados (que são valores a receber, mas ainda não pagos) **somente para os investimentos que você realmente possuía na data em que o direito ao provento foi estabelecido (a "data com")**. Isso assegura que sua contabilidade de rendimentos seja sempre exata, refletindo apenas o que lhe é devido.

A aba de Proventos está organizada em três seções principais para facilitar sua análise:

1.  **Histórico:** Veja mês a mês ou ano a ano quanto você já recebeu de dividendos, juros sobre capital próprio (JCP) ou rendimentos.

2.  **Resumo de Recebimentos:** Esta seção foi aprimorada e agora conta com duas abas para diferentes perspectivas de análise:
    *   **Aba "📅 Evolução Anual":**
        *   Aqui você encontrará a tabela consolidada dos seus proventos, exibindo os valores mensais de cada ativo e um **Total Anual**.
        *   Uma nova linha **"Crescimento"** mostra a porcentagem de crescimento dos proventos de cada mês em relação ao mesmo mês do ano anterior, ajudando a identificar tendências na sua renda passiva.
        *   A linha **"Valor Médio"** (anteriormente conhecida como "Média Acumulada") agora apresenta o valor médio acumulado dos proventos recebidos até o mês atual, oferecendo uma perspectiva clara do seu recebimento médio ao longo do tempo.
        *   **Proventos Dolarizados:** Se você possui investimentos internacionais (como Stocks e Reits) que pagam proventos em dólar, você encontrará um resumo separado desses valores, já convertidos para Reais (R$), nesta mesma aba.

    *   **Aba "📂 Distribuição por Classe":**
        *   Esta aba oferece uma visão detalhada de como seus proventos estão distribuídos entre as diferentes classes de ativos (Ações, Fundos Imobiliários, Renda Fixa, etc.) para um mês e ano específicos.
        *   **Filtros de Período:** Use as opções de seleção para escolher o **Ano** e o **Mês** que deseja analisar. Para sua conveniência, o sistema agora preenche automaticamente esses filtros com o **ano e o mês atual**, mostrando os dados mais recentes logo de cara. Você pode facilmente ajustá-los para explorar outros períodos.
        *   **Visão Geral dos Recebimentos:** Agora, na parte superior, você encontrará **dois painéis destacados**: um mostrando o **Total Recebido no Mês** (para o mês e ano selecionados) e outro exibindo o **Total Acumulado no Ano** (todos os proventos recebidos até o momento no ano selecionado). Isso facilita a comparação rápida do seu rendimento mensal com o total anual.
        *   **Valores por Classe Detalhados:** A tabela de "Valores por Classe" foi aprimorada para oferecer uma análise mais completa. Ela agora exibe, para cada classe de ativo (Ações, FIIs, etc.), tanto o **valor e a porcentagem de proventos recebidos no mês selecionado** quanto o **valor e a porcentagem acumulados no ano selecionado**. Isso permite uma visão clara da contribuição de cada tipo de investimento tanto no período mensal quanto no anual.
        *   **Dupla Análise Gráfica:** Em vez de um único gráfico, agora você terá **dois gráficos de pizza** para uma análise visual mais aprofundada:
            *   **"Distribuição do Mês":** Mostra como seus proventos estão divididos entre as classes de ativos para o **mes selecionado**.
            *   **"Acumulado do Ano":** Apresenta a distribuição dos proventos por classe de ativo considerando o **total acumulado no ano selecionado**.
            Ambos os gráficos permitem entender rapidamente quais investimentos mais contribuíram para sua renda passiva em cada período.

3.  **Ranking:** Veja quais empresas ou fundos imobiliários mais pagaram dividendos para você no período selecionado.

#### Gerenciando Ativos e Proventos
*   **Adicionar Novo Ativo:** Para registrar proventos de um ativo que ainda não está na sua lista ou para um novo ano, clique no botão "➕ Adicionar Ativo".
*   **Editar ou Excluir Ativo Existente:** Se precisar ajustar os proventos de um ativo já cadastrado ou remover seus registros para um ano específico, utilize o menu suspenso "Editar Ativo" que aparece ao lado do botão de adicionar. Selecione o ativo desejado na lista para abrir a tela de edição. Lá, você poderá fazer as alterações necessárias. **Atenção:** Se optar por remover os proventos de um ativo para um ano específico, uma **janela de confirmação** será exibida. Isso garante que a exclusão seja intencional. Você precisará confirmar sua escolha para que a exclusão seja efetivada ou poderá cancelar a operação, se desejar.

---

**💡 Legenda:**
*   **Crescimento:** Indica a porcentagem de crescimento dos proventos em comparação com o mesmo mês do ano anterior.
*   **Valor Médio:** Representa o valor médio acumulado dos proventos recebidos até o mês atual, fornecendo uma visão da sua renda passiva mensal projetada.

---

### 📉 Derivativos (Opções)
Para usuários que realizam operações de proteção (hedge) ou rentabilização de carteira utilizando opções, o ControlValue agora oferece um acompanhamento ainda mais detalhado:

*   **Rastreamento Completo de Operações:** Além de acompanhar suas opções de Compra (Call) ou Venda (Put) abertas, você pode agora visualizar os **detalhes completos de abertura e encerramento** de cada operação. Isso inclui a quantidade, valor da opção e prêmio inicial, bem como os mesmos dados no momento do encerramento.
*   **Resultados por Operação:** Monitore o **lucro ou prejuízo (resultado)** de cada operação de opção, proporcionando uma visão clara do desempenho de suas estratégias com derivativos.
*   **Detalhes de Vencimento:** Continue a acompanhar os preços de exercício (*strikes*) e as datas de vencimento das operações para um controle preciso.
*   **Importação de Dados de Opções:** Para quem importa suas operações de opções através de planilhas (CSV), o sistema agora é mais flexível ao reconhecer as datas. Ele aceita e converte automaticamente diferentes formatos, como `DD/MM/AAAA`, `DD/MM/AA` (dia/mês/ano) e `AAAA-MM-DD` (ano-mês-dia), facilitando o registro das suas operações.

---

## 5. Personalizando sua Experiência (Temas)

Você pode mudar a aparência do ControlValue para o estilo que mais lhe agrada:
1.  Acesse as **Preferências** (no menu superior ou ícone de engrenagem).
2.  Escolha entre as opções de estilo disponíveis:
    *   **Cyberpunk:** Aparência futurista com cores neon vibrantes.
    *   **Glassmorphism:** Efeito moderno de vidro fosco e translúcido.
    *   **Minimalista:** Layout limpo, focado em alta legibilidade.
    *   **Padrão:** O estilo clássico e elegante do sistema.
3.  A alteração é aplicada imediatamente e fica salva para seus próximos acessos.

---

*Se tiver alguma dúvida sobre preenchimento de planilhas ou erro no processamento de cotações, entre em contato com o administrador do sistema através do e-mail de suporte.*
