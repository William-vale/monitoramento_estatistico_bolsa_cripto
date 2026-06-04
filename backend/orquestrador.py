
# ==========================================================
# Orquestrador principal - implementação
# ==========================================================

# Variaveis

# Passo 1 - Listar API's bolsa de valores Disponiveis no Mercado

""" Yahoo Finance + BRAPI"""

#Lista de Variaveis e importações
import yfinance as yf
import requests
import json
import math
import time

# Busca dos ativos da Bolsa de Valores
URL_BRAPI = "https://brapi.dev/api/available?market=b3"

print("Buscando ativos da bolsa de valores B3... ")

acoes_filtradas = []
todos_tickers = []

try: 
	resposta = requests.get(URL_BRAPI, timeout=10)
	resposta.raise_for_status()

	dados = resposta.json()
	todos_tickers = dados.get("stocks", [])

	for ticker in todos_tickers:
		#remove espaços em branco nas pontas, se houver
		ticker = ticker.strip()

		# Filtra ações brasileiras com 4 letras + final 3 ou 4
		if len(ticker) == 5 and ticker[-1] in {"3", "4"} and ticker[:4].isalpha():
			acoes_filtradas.append(ticker)

	#ordena em ordem alfabética
	acoes_filtradas.sort()

	print(f"{len(acoes_filtradas)} \n")
except requests.exceptions.RequestException as erro:
    print(f"Erro ao conectar com a API: {erro}")

if not acoes_filtradas:
    raise SystemExit("Nenhum ativo filtrado foi encontrado. Verifique a disponibilidade da API e a lista de ativos.")

yfinance_infos = []
for index, ticker in enumerate(acoes_filtradas, start=1):
    symbol_sa = f"{ticker}.SA"
    try:
        info = yf.Ticker(symbol_sa).info
        yfinance_infos.append({
            "symbol": symbol_sa,
            "info": info
        })
    except Exception as erro:
        yfinance_infos.append({
            "symbol": symbol_sa,
            "error": str(erro)
        })

    if index % 50 == 0:
        print(f"Checkpoint: {index} ações buscadas. Aguardando 15s antes de continuar...")
        time.sleep(15)

# Construir a lista final de dados filtrados por ação
dados_filtrados = []
for item in yfinance_infos:
    if "info" not in item:
        dados_filtrados.append({
            "symbol": item["symbol"],
            "error": item.get("error")
        })
        continue

    info = item["info"]
    lpa = info.get("trailingEps")
    vpa = info.get("bookValue")
    preco_atual = info.get("currentPrice")

    if lpa and vpa and lpa > 0 and vpa > 0:
        preco_justo_grahan = round(math.sqrt(22.5 * lpa * vpa), 2)
        margem_seguranca = round(((preco_justo_grahan - preco_atual) / preco_justo_grahan) * 100, 2) if preco_atual else None
    else:
        preco_justo_grahan = "Não é possivel calcular!"
        margem_seguranca = None

    dados_filtrados.append({
        "empresa": info.get("longName") or info.get("shortName") or item["symbol"],
        "symbol": item["symbol"],
        "preco_atual": preco_atual,
        "p_l": info.get("trailingPE"),
        "p_vp": info.get("priceToBook"),
        "ev_ebtida": info.get("enterpriseToEbtida"),
        "DY": info.get("dividendYield"),
        "payout": info.get("payoutRatio"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "margem_lucro": info.get("profitMargins"),
        "divida_patrimonial": info.get("debtToEquity"),
        "Analise_Grahan": {
            "preco_justo_grahan": preco_justo_grahan,
            "margen_seguranca": margem_seguranca
        }
    })

# Criar arquivo JSON, para disponibilizar as informações de Ativos
with open("trade_data.json", "w", encoding="utf-8") as arquivo_json:
    json.dump(dados_filtrados, arquivo_json, indent=4, ensure_ascii=False)

print("Arquivo JSON salvo em trade_data.json")


# Passo 2 - Pegar Documentação da API da Bybit
