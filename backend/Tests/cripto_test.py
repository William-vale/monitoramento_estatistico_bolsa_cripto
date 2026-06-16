import requests
import time
from datetime import datetime

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; monitoramento-estatistico/1.0)"
}
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN_REQUESTS = 0.4


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
    # Buscar todas as exchanges Bybit (spot e futuros) no CoinGecko
    url_exchanges = f"{COINGECKO_BASE}/exchanges"
    dados_exchanges = safe_get(url_exchanges, params={"per_page": 250, "page": 1})
    if not isinstance(dados_exchanges, list):
        return []

    bybit_exchanges = [ex.get("id") for ex in dados_exchanges if isinstance(ex, dict) and "bybit" in ex.get("id", "").lower()]
    pares = []

    for ex_id in bybit_exchanges:
        url = f"{COINGECKO_BASE}/exchanges/{ex_id}/tickers"
        page = 1
        max_pages = 100

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

                    if len(pares) % 5 == 0:
                        print(f"[checkpoint] coletados {len(pares)} pares; aguardando 5 segundos antes da próxima busca...")
                        time.sleep(5)

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


def buscar_historico_ohlc(coin_id, dias=365, vs_currency="usd"):
    url = f"{COINGECKO_BASE}/coins/{coin_id}/ohlc"
    params = {
        "vs_currency": vs_currency,
        "days": dias,
    }
    dados = safe_get(url, params=params)
    if not isinstance(dados, list):
        return []

    historico = []
    for registro in dados:
        if len(registro) != 5:
            continue
        timestamp, open_price, high_price, low_price, close_price = registro
        historico.append({
            "data": datetime.utcfromtimestamp(timestamp / 1000).strftime("%Y-%m-%d"),
            "entrada": open_price,
            "minimo": low_price,
            "maximo": high_price,
            "fechamento": close_price,
        })
    return historico


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
                "erro": "ID CoinGecko não encontrado para o símbolo",
                "historico": [],
            })
            continue

        historico = buscar_historico_ohlc(coin_id, dias=365)
        resultados.append({
            "par": par,
            "coin_id": coin_id,
            "historico": historico,
        })

    return resultados


if __name__ == "__main__":
    resultados = obter_historico_diario_bybit(limit=1)
    for item in resultados:
        print(f"PAR: {item['par']}")
        if item.get("erro"):
            print(f"  Erro: {item['erro']}")
            continue
        print(f"  CoinGecko ID: {item.get('coin_id')}")
        print(f"  Registros: {len(item['historico'])}")
        for dia in item["historico"]:
            print(f"    {dia['data']} -> entrada={dia['entrada']}, min={dia['minimo']}, max={dia['maximo']}, fechamento={dia['fechamento']}")
        print()
