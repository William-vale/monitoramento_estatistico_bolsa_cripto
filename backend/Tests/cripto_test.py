import requests

def buscar_pares_bybit():
    # URL da API do CoinGecko para listar os tickers da exchange Bybit
    url = "https://api.coingecko.com/api/v3/exchanges/bybit_spot/tickers"
    
    try:
        # Faz a requisição para a API
        resposta = requests.get(url)
        resposta.raise_for_status()
        dados = resposta.json()
        
        lista_pares_usdt = []
        
        # Filtra apenas os tickers cujo alvo (target) seja USDT
        for ticker in dados.get('tickers', []):
            base = ticker.get('base')    # Símbolo da cripto (ex: BTC)
            target = ticker.get('target') # Símbolo do alvo (ex: USDT)
            
            if target == 'USDT':
                # Cria o formato do par (ex: BTC/USDT ou BTCUSDT)
                par = f"{base}/{target}"
                if par not in lista_pares_usdt:
                    lista_pares_usdt.append(par)
                    
        return lista_pares_usdt

    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar na API: {e}")
        return []

# Executa a função e exibe o resultado
pares_filtrados = buscar_pares_bybit()

print(f"Total de pares encontrados: {len(pares_filtrados)}")
print("Lista de pares:")
print(pares_filtrados)