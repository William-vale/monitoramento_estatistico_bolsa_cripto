
# ==========================================================
# Orquestrador principal - implementação
# ==========================================================

# Variaveis

# Passo 1 - Listar API's bolsa de valores Disponiveis no Mercado e buscar informações das ações (Um arquivo para Fundamentalista e outra para Trade)

""" Yahoo Finance + BRAPI"""

#Lista de Variaveis e importações
import os
import yfinance as yf
import requests
import json
import math
import time

# Diretório de saída para os arquivos JSON
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

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
fundamental_path = os.path.join(OUTPUT_DIR, "fundamental_data.json")
with open(fundamental_path, "w", encoding="utf-8") as arquivo_json:
    json.dump(dados_filtrados, arquivo_json, indent=4, ensure_ascii=False)
print(f"Arquivo JSON salvo em {fundamental_path}")

# Busca de informações de Trade (histórico de Preços)
historico_precos = []

print("\n\nBuscando histórico de 1 ano dos preços para as ações filtradas... ")

for index, ticker in enumerate(acoes_filtradas, start=1):
    symbol_sa = f"{ticker}.SA"
    try: 
        ##inicializa o ticker no yfinance
        ativo = yf.Ticker(symbol_sa)

        #Busca histórico de 1 ano com intervalo de 1 hora
        dados_historicos = ativo.history(period="1y", interval="1h")

        if not dados_historicos.empty:
            historico_precos.append({
                "symbol": symbol_sa,
                "historico": dados_historicos
            })
            print(f"[{index}] Histórico de {symbol_sa} coletado com sucesso ({len(dados_historicos)} registros).")
        else: 
            historico_precos.append({
                "symbol": symbol_sa,
                "error": "Nenhum dado histórico encontrado"
            })
            print(f"[{index}] {symbol_sa}:  Nenhum dado encontrado.")
    except Exception as erro:
        historico_precos.append({
            "symbol": symbol_sa,
            "error": str(erro)
        })
        print(f"[{index}] Erro ao buscar {symbol_sa}: {erro}")

    # Timeout a cada 10 ações buscadas, pausa de 5 segundos
    if index % 10 == 0 and index < len(acoes_filtradas):
        print(f"Checkpoint: {index} ações processadas. Aguardando 5s antes de continuar...")
        time.sleep(5)

print("\nBusca finalizada." )

# Processamento estatístico simplificado para o arquivo JSON
analise_trade_b3 = []

print("\nIniciando análise dos padrões de preço...")

for item in historico_precos:
    symbol_sa = item["symbol"]
    
    # Se houver erro na coleta, mantém o registro do erro
    if "historico" not in item or hasattr(item["historico"], "empty") and item["historico"].empty:
        analise_trade_b3.append({
            "symbol": symbol_sa,
            "error": item.get("error", "Sem dados históricos disponíveis")
        })
        continue

    df = item["historico"]
    total_horas = len(df)
    vezes_padrao_atingido = 0

    # Varre cada linha (hora) do histórico para identificar o padrão
    for _, row in df.iterrows():
        open_price = row["Open"]
        low_price = row["Low"]
        close_price = row["Close"]

        if open_price > 0:
            # 1. Queda: Mínima caiu pelo menos 5% em relação à abertura, mas no máximo 8%
            queda_minima = open_price * 0.95   # -5% 
            queda_maxima = open_price * 0.92   # -8%
            
            # 2. Alta: Fechamento subiu cerca de 10% (ou mais) em relação à abertura
            alta_esperada = open_price * 1.10  # +10%

            if (low_price <= queda_minima) and (low_price >= queda_maxima) and (close_price >= alta_esperada):
                vezes_padrao_atingido += 1

    # Cálculos de porcentagem e projeções com base no último preço disponível
    porcentagem_acerto = (vezes_padrao_atingido / total_horas * 100) if total_horas > 0 else 0.0
    
    preco_atual = float(df["Close"].iloc[-1]) if total_horas > 0 else 0.0
    preco_menos_5 = preco_atual * 0.95
    preco_menos_5_mais_10 = preco_menos_5 * 1.10

    # Estruturação limpa na ordem exata solicitada
    analise_trade_b3.append({
        "symbol": symbol_sa,
        "padrao_atingido_vezes": vezes_padrao_atingido,
        "total_horas_analisadas": total_horas,
        "porcentagem_acerto": round(porcentagem_acerto, 2),
        "preco_atual": round(preco_atual, 2),
        "preco_entrada_menos_5": round(preco_menos_5, 2),
        "preco_alvo_mais_10": round(preco_menos_5_mais_10, 2)
    })

# Salva o arquivo final otimizado e leve
trade_data_path = os.path.join(OUTPUT_DIR, "trade_data_b3.json")
with open(trade_data_path, "w", encoding="utf-8") as arquivo_json:
    json.dump(analise_trade_b3, arquivo_json, indent=4, ensure_ascii=False)

print(f"\nAnálise estatística concluída com sucesso! Arquivo compacto salvo em: {trade_data_path}")

# Passo 2 - Pegar Documentação da API da Bybit
