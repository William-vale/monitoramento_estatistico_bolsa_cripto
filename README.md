# monitoramento_estatistico_bolsa_cripto

<!-- PROMPT'S USADOS -->

<!-- 1) Olá, preciso de auxilio para a criação de uma aplicação voltada para monitoramente da bolsa de valores, B3 Brasil, e do mercado de CriptoMoedas, usando API's, imagens, sites e etc. 

Vou separar minha aplicação em duas pastas diferentes, backend e frontend. A pasta FrontEnd vai ter acesso a algumas pastas e/ou arquivos do backend, pois essa parte de backend vai ser responsavel pela busca de todas as informações dos ativos, seja Ações, Fii's, ETFs, BDRs, Derivativos no caso da bolsa, e CriptoMoedas no caso do mercado cripto, tanto no mercado futuro como no Spot. Dentro do BackEnd, terão 3 pastas diferentes, TRADE_B3, TRADE_CRIPTO, ATIVOS_LONGO_PRAZO, que terão informações/dados diferentes. 

Pra começar, desejo que você, dentro da Pasta backend (na linguagem Python) crie um arquivo orquestrador. Usando o a biblioteca yfinance e a biblioteca ccxt crie duas funções diferentes, uma que busca todas os ativos existentes na bolsa do brasil e outra que busque todas as criptomoedas existentes no mercado na bybit (SPOT E FUTUROS). Essas duas funções desejo que você grave todas essas informações, no caso em cada uma, em uma lista, cada uma, para facil acesso posterior.

Por ultimo crie uma função test dentro do orquestrador que vai servir para testar todas as funções que serão criadas daqui pra frente, só peço que as funções não sejam dependentes da função teste para funcionar, mas que elas deem um retorno. 

Apenas construa isso primeiro, vamos fazer bem devagar esse projeto para que possamos no final ter exito.  -->

<!-- 2) 
Veja pra mim todo o código feito no backend, e tente enxugar o máximo e ótimiza-lo. Após isso explique passo a passo o código com comentários nele para que eu entenda de forma simples. 

Após isso preciso que você crie uma pasta chamada frontend no diretório principal, pois lá irei montar a parte de front do projeto. 
Por hora faça apenas isso, e por favor mostre um passo a passo em como usar o código, ativa-lo e assim buscar os dados e guarda-los. 

-->

<!-- Adicionar no git as modificações
    git status
    git add .
    git commit -m "..."
    git push -u origin main
 -->

 <!-- 3)
    Crie pra mim uma tela frontend que monitore o mercado da bolsa de valores e mostre na tela 3 formas de informações: 

    1) O usuário escolhe uma das 4 Formas: Cripto (Futuros), Cripto (Spot), Bolsa (trade), Bolsa (BuyAndHold)
    2) Após a Escolha do usuário aparecer na tela informações sobre cada escolha: 
      a) Cripto (Futuros), aparecer uma tabela com informações da seguinte forma nas colunas: NomeParCripto (Lembre-se, sempre par CriptoUsdt), Valor atual, qtd de quedas (quantas vezes o valor caiu 5% e aumentou para 15% no final do dia. Essas informações serão pegas no JSON com histórico de preços de 1 ano, de hoje a um ano atrás, e horarios durante o dia (horario inicial 9h ate as 23h)), valor descrescimo (5% a menos), valor futuro (valor descrescimo*15%) e % de vezes que que caiu 5% e subiu 15% durante um ano diariamente(% acerto).
      b) Cripto (Spot), mesma coisa do a) mas com os ativos de SPOT apenas, sem mercados futuros. Faça a mesma coisa do a).
      c) Bolsa (trade), aparecer na tela informações da seguinte forma nas colunas: Nome de Ativo, Valor atual, qtd de quedas, valor descrescimo (5% a menos do valor atual), valor futuro (15% sobre o valor descrescimo) e % de acerto.
      d) Bolsa(BuyAndHold), se comparta da seguinte forma as colunas: Ativo, Valor atual, DY, P/L, P/VPA, ROE, Margem Líquida, Dívida Líquida / EBITDA, Liquidez Corrente e % de filtros aceitos (colocar em ordem do que estiver maior).
   3) Colocar abaixo dessa tabela acima, apenas no Bolsa(BuyAndHold), a seguinte tabela e os 10 ativos mais vantajosos, segundo a tabela acima: 
      Ativo,  Valor justo (Formula de graham), % de valorizaçao dos ultimos 5 anos.

   Lembrando, segundo esse repositório aqui (https://github.com/William-vale/monitoramento_estatistico_bolsa_cripto) onde está todas as informações do projeto, as informações no front end devem ser preparadas para receber os dados do backend

   Faça apenas isso, por favor. O Projeto é em React, usando o Vite e Typescript, use nesse padrão.
 -->