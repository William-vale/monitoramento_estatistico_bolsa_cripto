import requests
import time
from datetime import datetime, timedelta

COINGECKO_BASE = "https://coingecko.com"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; monitoramento-estatistico/1.0)"
}
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN_REQUESTS = 1.0  # Aumentado levemente para evitar bloqueios por IP


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
        max_pages = 5  # Reduzido para evitar atingir o limite da API rapidamente

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
    """
    Divide 1 ano em 4 blocos de 90 dias usando o endpoint de range
    para garantir dados individuais por dia.
    """
    # Usa o endpoint /range dedicado para intervalos de tempo customizados
    url = f"{COINGECKO_BASE}/coins/{coin_id}/ohlc/range"
    historico_completo = []
    datas_processadas = set()

    fim_atual = datetime.utcnow()

    # Executa 4 ciclos de 90 dias (360 dias no total)
    for ciclo in range(4):
        inicio_atual = fim_atual - timedelta(days=90)
        
        # Converte para timestamp Unix inteiro requerido pela API do CoinGecko
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
                
                # Evita duplicar registros nas bordas dos blocos de 90 dias
                if data_formatada not in datas_processadas:
                    datas_processadas.add(data_formatada)
                    historico_completo.append({
                        "data": data_formatada,
                        "entrada": open_price,
                        "minimo": low_price,
                        "maximo": high_price,
                        "fechamento": close_price,
                    })
        
        # O fim do próximo bloco (passado) será o início deste bloco atual
        fim_atual = inicio_atual
        time.sleep(1.5)  # Pausa de segurança extra entre os blocos do mesmo ativo

    # Ordena o histórico do dia mais antigo para o mais recente
    historico_completo.sort(key=lambda x: x["data"])
    return historico_completo


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
                "erro": "ID CoinGecko nao encontrado para o simbolo",
                "historico": [],
            })
            continue

        print(f"[Processando] {par} (ID: {coin_id})")
        historico = buscar_historico_ohlc_por_ano_em_blocos(coin_id)
        resultados.append({
            "par": par,
            "coin_id": coin_id,
            "historico": historico,
        })

    return resultados


if __name__ == "__main__":
    resultados = obter_historico_diario_bybit(limit=1)
    print("\n--- RESULTADO FINAL ---")
    for item in resultados:
        print(f"PAR: {item['par']}")
        if item.get("erro"):
            print(f"  Erro: {item['erro']}")
            continue
        print(f"  CoinGecko ID: {item.get('coin_id')}")
        print(f"  Registros Totais: {len(item['historico'])}")
        
        # Exibe apenas os primeiros 5 e os ultimos 5 para nao poluir o terminal
        if len(item['historico']) > 10:
            for dia in item["historico"][:5]:
                print(f"    {dia['data']} -> entrada={dia['entrada']}, min={dia['minimo']}, max={dia['maximo']}, fechamento={dia['fechamento']}")
            print("    ...")
            for dia in item["historico"][-5:]:
                print(f"    {dia['data']} -> entrada={dia['entrada']}, min={dia['minimo']}, max={dia['maximo']}, fechamento={dia['fechamento']}")
        else:
            for dia in item["historico"]:
                print(f"    {dia['data']} -> entrada={dia['entrada']}, min={dia['minimo']}, max={dia['maximo']}, fechamento={dia['fechamento']}")
        print()