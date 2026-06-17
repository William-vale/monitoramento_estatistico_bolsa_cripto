import json
import os
import requests
import time
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
#  URLs das APIs
# ─────────────────────────────────────────────
BYBIT_BASE      = "https://api.bybit.com"          # API da Bybit (pares de futuros)
COINGECKO_BASE  = "https://api.coingecko.com/api/v3"  # API do CoinGecko (histórico OHLC)

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; monitoramento-estatistico/1.0)"
}
REQUEST_TIMEOUT        = 15
SLEEP_BETWEEN_REQUESTS = 2.0   # Respeita o rate limit do CoinGecko (30 req/min)


# ─────────────────────────────────────────────
#  Requisição com retry e tratamento de rate limit
# ─────────────────────────────────────────────
def safe_get(url, params=None, max_retries=5):
    session = requests.Session()
    session.headers.update(HEADERS)

    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and str(retry_after).isdigit() else 60.0
                print(f"    [Rate limit] Aguardando {wait + attempt:.1f}s...")
                time.sleep(wait + attempt)
                continue

            response.raise_for_status()
            time.sleep(SLEEP_BETWEEN_REQUESTS)
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"    [Erro na requisição] Tentativa {attempt}/{max_retries}: {e}")
            if attempt == max_retries:
                raise
            time.sleep(2.0 * attempt)


# ─────────────────────────────────────────────
#  Busca pares de FUTUROS USDT Perpetual na Bybit
#  Usa a API oficial da Bybit (sem autenticação)
#  Fallback: CoinGecko exchange bybit_futures
# ─────────────────────────────────────────────
def buscar_pares_futuros_bybit():
    """
    Busca todos os contratos LinearPerpetual com quoteCoin=USDT e status=Trading
    diretamente da API da Bybit.
    Fallback automático para o CoinGecko (exchange bybit_futures) se a Bybit falhar.
    """
    print("  Tentando API da Bybit (fonte primária)...")
    try:
        url = f"{BYBIT_BASE}/v5/market/instruments-info"
        params = {"category": "linear", "limit": 1000}
        dados = safe_get(url, params=params)

        if isinstance(dados, dict) and dados.get("retCode") == 0:
            instrumentos = dados.get("result", {}).get("list", [])
            pares = []
            for inst in instrumentos:
                if (inst.get("contractType") == "LinearPerpetual"
                        and inst.get("quoteCoin") == "USDT"
                        and inst.get("status") == "Trading"):
                    base = inst.get("baseCoin")
                    if base:
                        par = f"{base}/USDT"
                        if par not in pares:
                            pares.append(par)

            if pares:
                print(f"  [Bybit API] {len(pares)} pares de futuros USDT Perpetual encontrados.")
                return pares

    except Exception as e:
        print(f"  [Bybit API] Falhou: {e}")

    # ── Fallback: CoinGecko com exchange bybit_futures ──
    print("  Usando fallback: CoinGecko exchange 'bybit_futures'...")
    return _buscar_pares_via_coingecko_futures()


def _buscar_pares_via_coingecko_futures():
    """Fallback: coleta pares USDT da exchange bybit_futures no CoinGecko."""
    url = f"{COINGECKO_BASE}/exchanges/bybit_futures/tickers"
    pares = []
    page = 1

    while True:
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
            if base:
                par = f"{base}/USDT"
                if par not in pares:
                    pares.append(par)

        print(f"    Página {page}: {len(tickers)} tickers | Total acumulado: {len(pares)}")
        page += 1

    print(f"  [CoinGecko fallback] {len(pares)} pares encontrados.")
    return pares


# ─────────────────────────────────────────────
#  CoinGecko: lista de moedas e busca de coin_id
# ─────────────────────────────────────────────
def buscar_coingecko_coin_list():
    url = f"{COINGECKO_BASE}/coins/list"
    dados = safe_get(url)
    return dados if isinstance(dados, list) else []


def encontrar_coin_id_por_symbol(symbol, coins_list):
    symbol_upper = symbol.upper()
    candidatos = [c for c in coins_list if c.get("symbol", "").upper() == symbol_upper]
    if not candidatos:
        return None
    return candidatos[0].get("id")


# ─────────────────────────────────────────────
#  Histórico OHLC (~1 ano em 4 blocos de 90 dias)
# ─────────────────────────────────────────────
def buscar_historico_ohlc_por_ano_em_blocos(coin_id, vs_currency="usd"):
    url = f"{COINGECKO_BASE}/coins/{coin_id}/ohlc/range"
    historico_completo = []
    datas_processadas = set()
    fim_atual = datetime.utcnow()

    for ciclo in range(4):
        inicio_atual = fim_atual - timedelta(days=90)
        params = {
            "vs_currency": vs_currency,
            "from": int(inicio_atual.timestamp()),
            "to":   int(fim_atual.timestamp())
        }

        print(f"    -> Bloco {ciclo + 1}/4: {inicio_atual.strftime('%Y-%m-%d')} até {fim_atual.strftime('%Y-%m-%d')}")
        dados = safe_get(url, params=params)

        if isinstance(dados, list):
            for registro in dados:
                if len(registro) != 5:
                    continue
                timestamp, open_price, high_price, low_price, close_price = registro
                data_fmt = datetime.utcfromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")
                if data_fmt not in datas_processadas:
                    datas_processadas.add(data_fmt)
                    historico_completo.append({
                        "data":       data_fmt,
                        "entrada":    open_price,
                        "minimo":     low_price,
                        "maximo":     high_price,
                        "fechamento": close_price,
                    })

        fim_atual = inicio_atual
        time.sleep(1.5)

    historico_completo.sort(key=lambda x: x["data"])
    return historico_completo


# ─────────────────────────────────────────────
#  Cálculo estatístico e simulação de preços
# ─────────────────────────────────────────────
def calculo_historico(historico):
    """
    Critério de acerto: candle em que o preço caiu >= 5% abaixo da abertura
                        E subiu >= 10% acima da abertura no mesmo dia.
    """
    acertos = 0
    total_trades = len(historico)

    for dia in historico:
        entrada = dia["entrada"]
        var_min = ((dia["minimo"] - entrada) / entrada) * 100
        var_max = ((dia["maximo"] - entrada) / entrada) * 100
        if var_min <= -5.0 and var_max >= 10.0:
            acertos += 1

    pct_acerto  = (acertos / total_trades * 100) if total_trades > 0 else 0.0
    preco_atual = historico[-1]["fechamento"] if historico else 0.0
    p_menos_5   = preco_atual * 0.95
    p_menos5_mais10 = p_menos_5 * 1.10

    return {
        "trades_com_criterio_atendido": acertos,
        "total_trades_ano":             total_trades,
        "porcentagem_acerto":           round(pct_acerto, 2),
        "simulacao_precos": {
            "preco_atual":                       preco_atual,
            "preco_com_queda_5_porcento":        round(p_menos_5, 4),
            "preco_com_queda_5_e_alta_10_porcento": round(p_menos5_mais10, 4)
        }
    }


# ─────────────────────────────────────────────
#  Orquestrador principal
# ─────────────────────────────────────────────
def obter_historico_futuros_bybit(caminho_arquivo):
    print("=" * 60)
    print("[1/3] Buscando pares de FUTUROS USDT Perpetual da Bybit...")
    print("=" * 60)
    pares = buscar_pares_futuros_bybit()

    if not pares:
        print("  [Erro] Nenhum par de futuros encontrado.")
        return []

    print(f"\n  Total de pares de futuros encontrados: {len(pares)}")

    print("\n[2/3] Buscando lista de moedas do CoinGecko...")
    coins_list = buscar_coingecko_coin_list()
    print(f"  {len(coins_list)} moedas carregadas.")

    # Retomada de execução anterior
    resultados = []
    pares_ja_processados = set()
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            try:
                resultados = json.load(f)
                pares_ja_processados = {r["par"] for r in resultados}
                print(f"\n  [Retomada] {len(pares_ja_processados)} pares já processados, serão pulados.")
            except json.JSONDecodeError:
                print("\n  [Aviso] Arquivo corrompido, iniciando do zero.")

    restantes = len(pares) - len(pares_ja_processados)
    print(f"\n[3/3] Processando {restantes} pares restantes...")
    print("=" * 60)

    for i, par in enumerate(pares, start=1):
        if par in pares_ja_processados:
            print(f"  [{i}/{len(pares)}] {par} — já processado, pulando.")
            continue

        simbolo  = par.split("/")[0]
        coin_id  = encontrar_coin_id_por_symbol(simbolo, coins_list)

        if not coin_id:
            print(f"  [{i}/{len(pares)}] [Aviso] coin_id não encontrado para: {simbolo}")
            resultados.append({"par": par, "erro": "ID CoinGecko nao encontrado para o simbolo"})
        else:
            print(f"  [{i}/{len(pares)}] Processando {par} (ID: {coin_id})...")
            historico = buscar_historico_ohlc_por_ano_em_blocos(coin_id)

            if not historico:
                print(f"    [Aviso] Nenhum histórico retornado para {par}")
                resultados.append({"par": par, "erro": "Nenhum dado historico retornado"})
            else:
                metricas = calculo_historico(historico)
                resultados.append({"par": par, "coin_id": coin_id, "analise": metricas})
                print(f"    Concluído: {metricas['total_trades_ano']} candles | "
                      f"Acertos: {metricas['trades_com_criterio_atendido']} "
                      f"({metricas['porcentagem_acerto']}%)")

        # Salva progressivamente a cada par
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=4, ensure_ascii=False)

    return resultados


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    pasta_backend = "backend"
    os.makedirs(pasta_backend, exist_ok=True)

    caminho_arquivo = os.path.join(pasta_backend, "resultado_analise.json")
    resultados_finais = obter_historico_futuros_bybit(caminho_arquivo)

    print(f"\n{'=' * 60}")
    print(f"[Sucesso] Análise concluída!")
    print(f"  Total de pares processados: {len(resultados_finais)}")
    print(f"  Resultados salvos em: {caminho_arquivo}")
    print(f"{'=' * 60}")