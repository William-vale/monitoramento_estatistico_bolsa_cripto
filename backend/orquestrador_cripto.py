import json
import os
import requests
import time
from datetime import datetime, timedelta

# Corrigido para incluir a rota /api/v3 correta
COINGECKO_BASE = "https://coingecko.com"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; monitoramento-estatistico/1.0)"
}
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN_REQUESTS = 1.0


def safe_get(url, params=None, max_retries=5):
    session = requests.Session()
    session.headers.update(HEADERS)

    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else 2.0
                time.sleep(wait + attempt)
                continue

            response.raise_for_status()
            time.sleep(SLEEP_BETWEEN_REQUESTS)
            return response.json()
        except requests.exceptions.RequestException:
            if attempt == max_retries:
                raise
            time.sleep(1.0 * attempt)


def buscar_pares_bybit():
    url_exchanges = f"{COINGECKO_BASE}/exchanges"
    dados_exchanges = safe_get(url_exchanges, params={"per_page": 250, "page": 1})
    if not isinstance(dados_exchanges, list):
        return []

    bybit_exchanges = [ex.get("id") for ex in dados_exchanges if isinstance(ex, dict) and "bybit" in ex.get("id", "").lower()]
    pares = []

    for ex_id in bybit_exchanges:
        url = f"{COINGECKO_BASE}/exchanges/{ex_id}/tickers"
        page = 1
        max_pages = 5

        while page <= max_pages:
            dados = safe_get(url, params={"page": page})
            if not isinstance(dados, dict):
                break

            tickers = dados.get("tickers", [])
            if not tickers:
                break

            for ticker in tickers:
                if ticker.get("target") != "USDT":
                    continue

                base = ticker.get("base")
                if not base:
                    continue

                par = f"{base}/USDT"
                if par not in pares:
                    pares.append(par)
            page += 1

    return pares


def buscar_coingecko_coin_list():
    url = f"{COINGECKO_BASE}/coins/list"
    dados = safe_get(url)
    return dados if isinstance(dados, list) else []


def encontrar_coin_id_por_symbol(symbol, coins_list):
    symbol_upper = symbol.upper()
    candidatos = [coin for coin in coins_list if coin.get("symbol", "").upper() == symbol_upper]
    if not candidatos:
        return None
    return candidatos[0].get("id")


def buscar_historico_ohlc_por_ano_em_blocos(coin_id, vs_currency="usd"):
    url = f"{COINGECKO_BASE}/coins/{coin_id}/ohlc/range"
    historico_completo = []
    datas_processadas = set()

    fim_atual = datetime.utcnow()

    for ciclo in range(4):
        inicio_atual = fim_atual - timedelta(days=90)
        from_timestamp = int(inicio_atual.timestamp())
        to_timestamp = int(fim_atual.timestamp())

        params = {
            "vs_currency": vs_currency,
            "from": from_timestamp,
            "to": to_timestamp
        }

        print(f"    -> Buscando bloco {ciclo + 1}: {inicio_atual.strftime('%Y-%m-%d')} ate {fim_atual.strftime('%Y-%m-%d')}")
        dados = safe_get(url, params=params)

        if isinstance(dados, list):
            for registro in dados:
                if len(registro) != 5:
                    continue
                timestamp, open_price, high_price, low_price, close_price = registro
                data_formatada = datetime.utcfromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")
                
                if data_formatada not in datas_processadas:
                    datas_processadas.add(data_formatada)
                    historico_completo.append({
                        "data": data_formatada,
                        "entrada": open_price,
                        "minimo": low_price,
                        "maximo": high_price,
                        "fechamento": close_price,
                    })
        
        fim_atual = inicio_atual
        time.sleep(1.5)

    historico_completo.sort(key=lambda x: x["data"])
    return historico_completo


def calculo_historico(historico):
    """
    Realiza os calculos estatisticos e de simulacao com base no historico OHLC.
    """
    acertos = 0
    total_trades = len(historico)

    for dia in historico:
        entrada = dia["entrada"]
        minimo = dia["minimo"]
        maximo = dia["maximo"]

        # Calcula as variacoes percentuais do dia em relacao a abertura (entrada)
        variacao_minima = ((minimo - entrada) / entrada) * 100
        variacao_maxima = ((maximo - entrada) / entrada) * 100

        # Criterio: Variou negativamente entre -5% e -8% (ou mais abaixo) E depois subiu +10%
        if variacao_minima <= -5.0 and variacao_maxima >= 10.0:
            acertos += 1

    # Porcentagem de acerto baseada nos criterios atendidos vs total de trades do ano
    porcentagem_acerto = (acertos / total_trades * 100) if total_trades > 0 else 0.0

    # Simulacao com o preco atualizado mais recente (ultimo registro do historico)
    preco_atual = historico[-1]["fechamento"] if historico else 0.0
    preco_menos_5 = preco_atual * 0.95
    preco_menos_5_mais_10 = preco_menos_5 * 1.10

    return {
        "trades_com_criterio_atendido": acertos,
        "total_trades_ano": total_trades,
        "porcentagem_acerto": round(porcentagem_acerto, 2),
        "simulacao_precos": {
            "preco_atual": preco_atual,
            "preco_com_queda_5_porcento": round(preco_menos_5, 4),
            "preco_com_queda_5_e_alta_10_porcento": round(preco_menos_5_mais_10, 4)
        }
    }


def obter_historico_diario_bybit(limit=1):
    pares = buscar_pares_bybit()[:limit]
    if not pares:
        return []

    coins_list = buscar_coingecko_coin_list()
    resultados = []

    for par in pares:
        simbolo = par.split("/")[0]
        coin_id = encontrar_coin_id_por_symbol(simbolo, coins_list)
        if not coin_id:
            resultados.append({
                "par": par,
                "erro": "ID CoinGecko nao encontrado para o simbolo"
            })
            continue

        print(f"[Processando] {par} (ID: {coin_id})")
        historico = buscar_historico_ohlc_por_ano_em_blocos(coin_id)
        
        if not historico:
            resultados.append({
                "par": par,
                "erro": "Nenhum dado historico retornado"
            })
            continue

        # Executa os calculos solicitados
        metricas = calculo_historico(historico)

        resultados.append({
            "par": par,
            "coin_id": coin_id,
            "analise": metricas
        })

    return resultados


if __name__ == "__main__":
    resultados_finais = obter_historico_diario_bybit(limit=1)
    
    # Garante a existencia do diretorio backend
    pasta_backend = "backend"
    if not os.path.exists(pasta_backend):
        os.makedirs(pasta_backend)
        
    caminho_arquivo = os.path.join(pasta_backend, "resultado_analise.json")
    
    # Salva o arquivo em formato JSON formatado
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(resultados_finais, f, indent=4, ensure_ascii=False)
        
    print(f"\n[Sucesso] Analise concluida! Resultados salvos em: {caminho_arquivo}")
