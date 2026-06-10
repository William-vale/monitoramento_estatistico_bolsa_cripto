import time
import requests

API_COINGECKO = "https://coingecko.com"
API_BINANCE = "https://binance.com"

# 1. BUSCA LISTA DE FUTUROS DA BYBIT (CoinGecko)
def obter_criptos_futuros_bybit():
    print("Buscando lista de contratos futuros na Bybit...")
    url = f"{API_COINGECKO}/derivatives/exchanges/bybit"
    lista_futuros = set()
    try:
        headers = {"accept": "application/json"}
        resposta = requests.get(url, headers=headers)
        resposta.raise_for_status()
        tickers = resposta.json().get("tickers", [])
        
        for item in tickers:
            ativo_base = item.get("base")  # Ex: 'BTC', 'ETH'
            if ativo_base:
                lista_futuros.add(ativo_base.upper())
    except Exception as e:
        print(f"Erro ao buscar futuros da Bybit: {e}")
        return []
    return sorted(list(lista_futuros))


# 2. BUSCA HISTÓRICO DE 1 ANO EM CANDLES DIÁRIOS (Binance)
def buscar_historico_diario_binance_1ano(symbol):
    url = f"{API_BINANCE}/klines"
    
    # Pegamos os últimos 365 dias
    parametros = {
        "symbol": f"{symbol}USDT",
        "interval": "1d",
        "limit": 365
    }
    try:
        resposta = requests.get(url, params=parametros)
        if resposta.status_code == 429:
            print(" -> Rate limit Binance atingido. Aguardando 10s...")
            time.sleep(10)
            return buscar_historico_diario_binance_1ano(symbol)
            
        resposta.raise_for_status()
        return resposta.json()
    except Exception:
        # Retorna vazio se o par não existir na Binance (ex: moedas exclusivas da Bybit)
        return []


# --- EXECUÇÃO DO FLUXO DE COLETA ---

criptos_filtradas = obter_criptos_futuros_bybit()
historico_precos = []

print(f"\nBuscando histórico diário de 1 ano para as {len(criptos_filtradas)} criptos encontradas... ")

for index, cripto in enumerate(criptos_filtradas, start=1):
    par_usdt = f"{cripto}/USDT"
    try:
        # Busca os candles diários consolidados (Open, High, Low, Close de cada dia)
        dados_historicos = buscar_historico_diario_binance_1ano(cripto)

        if len(dados_historicos) > 0:
            historico_precos.append({
                "symbol": par_usdt,
                "historico": dados_historicos
            })
            print(f"[{index}] Histórico diário de {par_usdt} coletado com sucesso ({len(dados_historicos)} dias).")
        else:
            historico_precos.append({
                "symbol": par_usdt,
                "error": "Par não disponível ou sem histórico na Binance"
            })
            print(f"[{index}] {par_usdt}: Não encontrado na Binance.")
            
    except Exception as erro:
        historico_precos.append({
            "symbol": par_usdt,
            "error": str(erro)
        })
        print(f"[{index}] Erro ao buscar {par_usdt}: {erro}")

    # Checkpoint de segurança a cada 10 moedas (Igual ao seu modelo original)
    if index % 10 == 0 and index < len(criptos_filtradas):
        print(f"Checkpoint: {index} criptos processadas. Aguardando 5s antes de continuar...")
        time.sleep(5)

print("\nBusca finalizada.")


# --- PROCESSAMENTO ESTATÍSTICO (LÓGICA DIÁRIA PERFEITA) ---

analise_trade_cripto = []
print("\nIniciando análise dos padrões baseados nos Candles Diários (Queda: 5% a 8% | Subida: 10%)...")

for item in historico_precos:
    par_usdt = item["symbol"]
    
    if "historico" not in item or len(item["historico"]) == 0:
        analise_trade_cripto.append({
            "symbol": par_usdt,
            "error": item.get("error", "Sem dados históricos disponíveis")
        })
        continue

    dados = item["historico"]
    total_dias = len(dados)
    vezes_padrao_atingido = 0

    # Varre cada dia do ano
    for row in dados:
        # Índices oficiais do Candlestick da Binance:
        # 1 = Preço de Abertura (Open)
        # 3 = Preço Mínimo do Dia (Low)
        # 4 = Preço de Fechamento (Close)
        open_price = float(row[1])
        low_price = float(row[3])
        close_price = float(row[4])

        if open_price > 0:
            # Suas Regras Próprias:
            # 1. Queda: Mínima do dia caiu entre 5% e 8% em relação à abertura daquele dia
            queda_minima = open_price * 0.95   # -5%
            queda_maxima = open_price * 0.92   # -8%
            
            # 2. Alta: Fechamento do dia subiu 10% ou mais em relação à abertura daquele dia
            alta_esperada = open_price * 1.10  # +10%

            # Validação cirúrgica do padrão usando os dados oficiais da Binance
            if (low_price <= queda_minima) and (low_price >= queda_maxima) and (close_price >= alta_esperada):
                vezes_padrao_atingido += 1

    # Porcentagem de acerto baseada nos dias reais analisados
    porcentagem_acerto = (vezes_padrao_atingido / total_dias * 100) if total_dias > 0 else 0.0
    
    # Pega o fechamento do último candle (Preço Atual de Mercado)
    preco_atual = float(dados[-1][4]) if total_dias > 0 else 0.0
    
    # Projeções matemáticas baseadas no último preço
    preco_entrada_menos_5 = preco_atual * 0.95
    preco_alvo_mais_10 = preco_entrada_menos_5 * 1.10

    # Estruturação limpa na ordem e chaves originais do seu modelo da B3
    analise_trade_cripto.append({
        "symbol": par_usdt,
        "padrao_atingido_vezes": vezes_padrao_atingido,
        "total_horas_analisadas": total_dias,  # Mantido o nome da chave do seu modelo para não quebrar integrações
        "porcentagem_acerto": round(porcentagem_acerto, 2),
        "preco_atual": round(preco_atual, 6) if preco_atual < 1 else round(preco_atual, 2),
        "preco_entrada_menos_05": round(preco_entrada_menos_5, 6) if preco_entrada_menos_5 < 1 else round(preco_entrada_menos_5, 2),
        "preco_alvo_mais_075": round(preco_alvo_mais_10, 6) if preco_alvo_mais_10 < 1 else round(preco_alvo_mais_10, 2)
    })

print("\n--- Análise Finalizada com Sucesso ---")

# Exibe os 3 primeiros resultados para conferência
print("\nAmostra dos primeiros resultados gerados:")
for r in analise_trade_cripto[:3]:
    print(r)
