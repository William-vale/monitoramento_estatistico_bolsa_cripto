import requests
import time

# Buscar informações de criptomoedas usando CoinGecko (API pública sem chave)

def buscar_ativos_coingecko(page=1, per_page=100):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": page,
        "sparkline": False,
        "price_change_percentage": "24h",
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            print(f"Erro HTTP {response.status_code} na API CoinGecko: {response.text.strip()[:200]}")
            return []

        try:
            dados = response.json()
        except ValueError as parse_error:
            print(f"Erro ao decodificar JSON da CoinGecko: {parse_error}")
            print(f"Resposta bruta: {response.text.strip()[:200]}")
            return []

        ativos = [
            {
                "id": item.get("id"),
                "symbol": item.get("symbol", "").upper(),
                "name": item.get("name"),
                "current_price": item.get("current_price"),
                "market_cap": item.get("market_cap"),
                "price_change_percentage_24h": item.get("price_change_percentage_24h"),
            }
            for item in dados
        ]

        return ativos
    except Exception as e:
        print(f"Erro ao buscar ativos da CoinGecko: {e}")
        return []


def imprimir_exemplos(ativos, titulo):
    print(f"--- {titulo} (Total: {len(ativos)}) ---")
    for ativo in ativos[:10]:
        print(
            f"{ativo['symbol']} - {ativo['name']} | Preço: ${ativo['current_price']} | "
            f"Market Cap: ${ativo['market_cap']} | 24h: {ativo['price_change_percentage_24h']}%"
        )
    print()


if __name__ == "__main__":
    print("Buscando informações de criptomoedas na CoinGecko...\n")

    ativos_mercado = buscar_ativos_coingecko(page=1, per_page=100)
    """ imprimir_exemplos(ativos_mercado, "Top 100 Criptomoedas por Market Cap") """

    # Buscar símbolos negociados na ByBit via CoinGecko
    def buscar_simbolos_bybit_via_coingecko():
        base = "https://api.coingecko.com/api/v3"
        # 1) localizar exchanges que contenham 'bybit' no nome ou id
        exchanges = []
        try:
            resp = requests.get(f"{base}/exchanges", params={"per_page": 250, "page": 1}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for ex in data:
                        if isinstance(ex, dict):
                            ex_id = ex.get("id", "")
                            ex_name = ex.get("name", "")
                            if "bybit" in ex_id.lower() or "bybit" in ex_name.lower():
                                exchanges.append(ex_id)
        except Exception as e:
            print(f"Erro ao listar exchanges na CoinGecko: {e}")

        if not exchanges:
            print("Nenhuma exchange com 'bybit' encontrada na lista da CoinGecko.")
            return []

        simbolos = set()
        for ex_id in exchanges:
            page = 1
            while True:
                try:
                    url = f"{base}/exchanges/{ex_id}/tickers"
                    resp = requests.get(url, params={"page": page}, timeout=10)
                    if resp.status_code != 200:
                        print(f"  ⊘ {ex_id} página {page}: HTTP {resp.status_code}")
                        break

                    dados = resp.json()
                    if not isinstance(dados, dict):
                        print(f"  ⊘ {ex_id}: resposta inesperada")
                        break
                    
                    tickers = dados.get("tickers", [])
                    if not tickers:
                        break

                    for t in tickers:
                        if isinstance(t, dict):
                            base_sym = t.get("base")
                            if base_sym:
                                simbolos.add(base_sym)

                    page += 1
                    time.sleep(0.2)
                except Exception as e:
                    print(f"  ⊘ {ex_id} página {page}: {str(e)[:50]}")
                    break

        return sorted(simbolos)

    ativos_bybit = buscar_simbolos_bybit_via_coingecko()
    print(f"--- Símbolos negociados na ByBit (via CoinGecko) (Total: {len(ativos_bybit)}) ---")
    print(f"Exemplos: {ativos_bybit[:50]}\n")

    # Mapear símbolos para IDs na CoinGecko (apenas principais)
    def mapear_simbolos_para_ids(simbolos):
        base = "https://api.coingecko.com/api/v3"
        mapping = {}
        
        try:
            print("Carregando lista de moedas da CoinGecko para mapeamento...")
            resp = requests.get(f"{base}/coins/list/include_platform_id", timeout=10)
            if resp.status_code == 200:
                coins = resp.json()
                # Criar dicionário com múltiplas entradas por símbolo
                sym_candidates = {}
                for coin in coins:
                    sym = coin.get("symbol", "").upper()
                    coin_id = coin.get("id")
                    if sym in simbolos:
                        if sym not in sym_candidates:
                            sym_candidates[sym] = []
                        sym_candidates[sym].append(coin_id)
                
                # Para cada símbolo, pegar o com melhor ranking (primeiros aparecem em melhor posição)
                for sym, ids in sym_candidates.items():
                    # Priorizar IDs que matcham com o símbolo (ex: BTC -> bitcoin)
                    main_id = next((id for id in ids if sym.lower() in id.lower()), ids[0])
                    mapping[sym] = main_id
                
                print(f"  ✓ Mapeados {len(mapping)} de {len(simbolos)} símbolos")
        except Exception as e:
            print(f"Erro ao mapear símbolos: {e}")
        
        return mapping

    # Buscar histórico de preços via CoinGecko
    def buscar_historico_precos(simbolos, dias=90, limite_simbolos=50):
        base = "https://api.coingecko.com/api/v3"
        
        # Limitar quantidade para evitar timeout
        simbolos_limitados = simbolos[:limite_simbolos]
        mapping = mapear_simbolos_para_ids(set(simbolos_limitados))
        
        historico = {}
        processados = 0
        erros = 0
        
        for simbolo in simbolos_limitados:
            if simbolo not in mapping:
                print(f"⊘ {simbolo}: não encontrado no mapeamento")
                continue
            
            coin_id = mapping[simbolo]
            try:
                url = f"{base}/coins/{coin_id}/market_chart"
                params = {
                    "vs_currency": "usd",
                    "days": dias,
                    "interval": "daily"
                }
                resp = requests.get(url, params=params, timeout=10)
                
                if resp.status_code == 200:
                    dados = resp.json()
                    prices = dados.get("prices", [])
                    
                    historico[simbolo] = {
                        "id": coin_id,
                        "timestamp_coleta": time.time(),
                        "dias": dias,
                        "prices": [{"timestamp": int(p[0]), "price_usd": float(p[1])} for p in prices]
                    }
                    processados += 1
                    print(f"✓ {simbolo:8} ({processados}/{len(mapping)}) - {len(prices)} pontos de preço")
                elif resp.status_code == 429:
                    print(f"⏱ {simbolo}: Rate limit (aguardando...)")
                    erros += 1
                    time.sleep(2)
                else:
                    print(f"✗ {simbolo}: HTTP {resp.status_code}")
                    erros += 1
                
                time.sleep(0.5)  # Rate limit mais conservador
            except Exception as e:
                print(f"✗ {simbolo}: {str(e)[:50]}")
                erros += 1
        
        print(f"\nResumo: {processados} sucesso, {erros} erros")
        return historico

    # Buscar histórico e salvar em JSON
    print("\nBuscando histórico de preços para ativos da ByBit (últimos 90 dias)...\n")
    historico_precos = buscar_historico_precos(ativos_bybit, dias=90)
    
    # Salvar em arquivo JSON
    import json
    output_file = "trade_data_cripto.json"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(historico_precos, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Dados salvos em {output_file} ({len(historico_precos)} ativos)")
    except Exception as e:
        print(f"Erro ao salvar arquivo JSON: {e}")
