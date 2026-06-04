
# ==========================================================
# Orquestrador principal - implementação
# ==========================================================

# Variaveis

# Passo 1 - Listar API's bolsa de valores Disponiveis no Mercado

""" Yahoo Finance + BRAPI"""

#Lista de Variaveis e importações
import yfinance as yf
import json
import math

# Busca dos ativos da Bolsa de Valores
URL_BRAPI = "https://brapi.dev"

print("Buscando ativos da bolsa de valores B3... ")

try: 
	resposta = requests.get(URL_BRAPI)
	resposta.raise_for_status()

	dados = resposta.json()
	todos_tickers = dados.get("stocks", [])

	acoes_filtradas = []

	for ticker in todos_tickers:
		#remove espaços em branco nas pontas, se houver
		ticker = ticker.strip()

		# Filtra ações que terminam em 3 e 4
		if ticker.endswith("3") or ticker.endswith("4"):
			acoes_filtradas.append(ticker)

	#ordena em ordem alfabética
	acoes_filtradas.sort()

	print(f"{len(acoes_filtradas)} \n")
except requests.exceptions.RequestException as erro:
    print(f"Erro ao conectar com a API: {erro}")


acao = yf.Ticker(symbol)

#Dados Fundamentalistas e Calculo da Formula de Graham
lpa = acao.info.get("trailingEps")
vpa = acao.info.get("bookValue")
preco_atual = acao.info.get("currentPrice")

#Calcular a formula de Graham
if lpa and vpa and lpa > 0 and vpa > 0:
	preco_justo_grahan = round(math.sqrt(22.5 * lpa * vpa), 2)
	margem_seguranca = round(((preco_justo_grahan - preco_atual)/ preco_justo_grahan) *100, 2) if preco_atual else None
else:
	preco_justo_grahan = "Não é possivel calcular!"
	margem_seguranca = None


dados_filtrados = {
	"empresa": acao.info.get("longName"),
	"symbol": acao.info.get("symbol"),
	"preco_atual": preco_atual,

	# Indicadores Fundamentalistas
	"p_l": acao.info.get("trailingPE"), #Preco sobre o Lucro, P/L
	"p_vp": acao.info.get("priceToBook"), #Preco sobre o Valor patrimonial, P/VP
	"ev_ebtida": acao.info.get("enterpriseToEbtida"), # EV / Ebtida

	"DY": acao.info.get("dividendYield"), #Dividend Yield (em porcentagem 0,12 = 12%)
	"payout": acao.info.get("payoutRatio"), # Payout (Percentual do lucro distribuído)

	"roe": acao.info.get("returnOnEquity"), # ROE (Retorno sobre o Patrimônio Líquido)
	"roa": acao.info.get("returnOnAssets"), # ROA (Retorno sobre o Ativo)
	"margem_lucro": acao.info.get("profitMargins"), # Margem Liquida

	"divida_patrimonial": acao.info.get("debtToEquity"), # Divida Bruta / Patrimonio Liquido (em %)

	# Formula de Grahan
	"Analise_Grahan": {
		"preco_justo_grahan": preco_justo_grahan,
		"margen_seguranca": margem_seguranca
	}
}

# Dados em JSON
dados_json = json.dumps(dados_filtrados, indent=4, ensure_ascii=False)
print(dados_json)

# Criar arquivo JSON, para disponibilizar as informações de Ativos


# Passo 2 - Pegar Documentação da API da Bybit
