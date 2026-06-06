#!/usr/bin/env python3
"""
Teste isolado para debugar o orquestrador_cripto.py
"""
import sys
import os
import requests
import time
import json

# Adicionar caminho do backend ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("TESTE 1: Buscar ativos CoinGecko")
print("=" * 80)

try:
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 5,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h",
    }
    response = requests.get(url, params=params, timeout=10)
    print(f"✓ Status: {response.status_code}")
    dados = response.json()
    print(f"✓ Ativos retornados: {len(dados)}")
    for item in dados[:3]:
        print(f"  - {item['symbol'].upper()}: ${item['current_price']}")
except Exception as e:
    print(f"✗ Erro: {e}")

print("\n" + "=" * 80)
print("TESTE 2: Listar exchanges da CoinGecko")
print("=" * 80)

try:
    url = "https://api.coingecko.com/api/v3/exchanges"
    params = {"per_page": 250, "page": 1}
    response = requests.get(url, params=params, timeout=10)
    print(f"✓ Status: {response.status_code}")
    exchanges = response.json()
    print(f"✓ Total de exchanges: {len(exchanges)}")
    
    bybit_exchanges = [ex for ex in exchanges if "bybit" in ex.get("id", "").lower()]
    print(f"✓ Exchanges com 'bybit': {len(bybit_exchanges)}")
    for ex in bybit_exchanges:
        print(f"  - {ex['id']}: {ex['name']}")
except Exception as e:
    print(f"✗ Erro: {e}")

print("\n" + "=" * 80)
print("TESTE 3: Buscar tickers de um exchange ByBit")
print("=" * 80)

try:
    url = "https://api.coingecko.com/api/v3/exchanges/bybit_spot/tickers"
    params = {"page": 1}
    response = requests.get(url, params=params, timeout=10)
    print(f"✓ Status: {response.status_code}")
    data = response.json()
    tickers = data.get("tickers", [])
    print(f"✓ Tickers retornados: {len(tickers)}")
    
    symbols = [t.get("base") for t in tickers[:5] if t.get("base")]
    print(f"✓ Primeiros símbolos: {symbols}")
except Exception as e:
    print(f"✗ Erro: {e}")

print("\n" + "=" * 80)
print("TESTE 4: Mapear símbolo para ID")
print("=" * 80)

try:
    url = "https://api.coingecko.com/api/v3/coins/list"
    response = requests.get(url, timeout=10)
    print(f"✓ Status: {response.status_code}")
    coins = response.json()
    print(f"✓ Total de moedas: {len(coins)}")
    
    # Buscar BTC, ETH, SOL
    for sym in ["BTC", "ETH", "SOL"]:
        coin = next((c for c in coins if c.get("symbol", "").upper() == sym), None)
        if coin:
            print(f"  ✓ {sym} -> {coin['id']}")
        else:
            print(f"  ✗ {sym} não encontrado")
except Exception as e:
    print(f"✗ Erro: {e}")

print("\n" + "=" * 80)
print("TESTE 5: Buscar histórico de preços (BTC)")
print("=" * 80)

try:
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {
        "vs_currency": "usd",
        "days": 7,
        "interval": "daily"
    }
    response = requests.get(url, params=params, timeout=10)
    print(f"✓ Status: {response.status_code}")
    data = response.json()
    prices = data.get("prices", [])
    print(f"✓ Pontos de preço retornados: {len(prices)}")
    
    for price_data in prices[:3]:
        timestamp, price = price_data
        from datetime import datetime
        dt = datetime.fromtimestamp(timestamp / 1000)
        print(f"  - {dt.date()}: ${price}")
except Exception as e:
    print(f"✗ Erro: {e}")

print("\n" + "=" * 80)
print("TESTE 6: Função completa (primeiros 5 símbolos ByBit)")
print("=" * 80)

try:
    # Simular a função completa com apenas 5 símbolos
    base = "https://api.coingecko.com/api/v3"
    
    # Buscar exchanges
    resp = requests.get(f"{base}/exchanges", params={"per_page": 250, "page": 1}, timeout=10)
    data = resp.json()
    
    # Verificar tipo de resposta
    if isinstance(data, list):
        exchanges = [ex['id'] for ex in data if isinstance(ex, dict) and "bybit" in ex.get("id", "").lower()]
    else:
        print(f"⊘ Tipo de resposta inesperado: {type(data)}")
        exchanges = []
    
    print(f"✓ Exchanges ByBit encontradas: {len(exchanges)}")
    
    # Coletar símbolos
    simbolos = set()
    for ex_id in exchanges[:2]:  # Testar com 2 exchanges
        try:
            url = f"{base}/exchanges/{ex_id}/tickers"
            resp = requests.get(url, params={"page": 1}, timeout=10)
            if resp.status_code == 200:
                tickers = resp.json().get("tickers", [])
                for t in tickers[:20]:  # Apenas primeiros 20
                    base_sym = t.get("base")
                    if base_sym:
                        simbolos.add(base_sym)
            time.sleep(0.2)
        except Exception as e:
            print(f"  ✗ Erro em {ex_id}: {e}")
    
    print(f"✓ Símbolos únicos coletados: {len(simbolos)}")
    print(f"  Exemplos: {sorted(list(simbolos))[:10]}")
    
    # Agora mapear para IDs e buscar histórico de 3 deles
    resp = requests.get(f"{base}/coins/list", timeout=10)
    all_coins = resp.json()
    
    test_symbols = sorted(list(simbolos))[:3]
    print(f"\n✓ Testando histórico para: {test_symbols}")
    
    for sym in test_symbols:
        coin = next((c for c in all_coins if c.get("symbol", "").upper() == sym), None)
        if coin:
            coin_id = coin['id']
            url = f"{base}/coins/{coin_id}/market_chart"
            params = {"vs_currency": "usd", "days": 7, "interval": "daily"}
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                prices = resp.json().get("prices", [])
                print(f"  ✓ {sym} ({coin_id}): {len(prices)} pontos de preço")
            else:
                print(f"  ✗ {sym}: HTTP {resp.status_code}")
            time.sleep(0.3)
        else:
            print(f"  ✗ {sym}: não encontrado em /coins/list")

except Exception as e:
    print(f"✗ Erro geral: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("FIM DOS TESTES")
print("=" * 80)
