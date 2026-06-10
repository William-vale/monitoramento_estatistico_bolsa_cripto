import time
import requests

# URL Base da API oficial do CoinGecko
API_BASE_URL = "https://api.coingecko.com/api/v3"

# 1. BUSCA LISTA DE FUTUROS DA BYBIT (USANDO ENDPOINT DE DERIVATIVOS)
def obter_criptos_futuros_bybit():
    url = f"{API_BASE_URL}/derivatives/exchanges/bybit"
    lista_futuros = set()
    try:
        # Nota: A API gratuita pode exigir User-Agent para evitar bloqueios básicos
        headers = {"accept": "application/json"}
        resposta = requests.get(url, headers=headers)
        resposta.raise_for_status()
        
        dados = resposta.json()
        # O endpoint da Bybit retorna tickers de derivativos na chave 'tickers'
        tickers = dados.get("tickers", [])
        
        for item in tickers:
            # Filtra apenas por contratos futuros/perpétuos se necessário, ou pega o ativo base
            ativo_base = item.get("base")  # Ex: 'BTC', 'ETH'
            if ativo_base:
                lista_futuros.add(ativo_base.upper())
    except Exception as e:
        print(f"Erro ao buscar futuros da Bybit: {e}")
        return []
    return sorted(list(lista_futuros))


# 2. MAPEIA SÍMBOLOS PARA IDS DO COINGECKO (USANDO LISTA OFICIAL)
def obter_mapeamento_ids():
    url = f"{API_BASE_URL}/coins/list"
    try:
        headers = {"accept": "application/json"}
        resposta = requests.get(url, headers=headers)
        resposta.raise_for_status()
        
        # Cria um dicionário vinculando o SYMBOL ao ID da API (ex: 'btc': 'bitcoin')
        return {coin["symbol"].upper(): coin["id"] for coin in resposta.json()}
    except Exception as e:
        print(f"Erro ao mapear IDs do CoinGecko: {e}")
        return {}


# 3. BUSCA PREÇOS DE HORA EM HORA DIVIDIDO EM 4 BLOCOS
def buscar_historico_horario_completo_1ano(coin_id):
    url = f"{API_BASE_URL}/coins/{coin_id}/market_chart/range"

    agora = int(time.time())
    um_dia_segundos = 86400
    noventa_dias_segundos = 90 * um_dia_segundos

    # Dividimos o ano (360 dias) em 4 janelas de 90 dias
    janelas_tempo = []
    for i in range(4):
        fim = agora - (i * noventa_dias_segundos)
        inicio = fim - noventa_dias_segundos
        janelas_tempo.append((inicio, fim))

    janelas_tempo.reverse()
    todos_precos_horarios = []

    for inicio, fim in janelas_tempo:
        parametros = {"vs_currency": "usd", "from": inicio, "to": fim}
        headers = {"accept": "application/json"}

        try:
            resposta = requests.get(url, params=parametros, headers=headers)

            # Tratamento de Rate Limit (Código 429)
            if resposta.status_code == 429:
                print(" -> Limite atingido. Aguardando 60 segundos para continuar...")
                time.sleep(60)
                resposta = requests.get(url, params=parametros, headers=headers)

            resposta.raise_for_status()
            dados = resposta.json()
            precos_bloco = dados.get("prices", [])

            todos_precos_horarios.extend(precos_bloco)
            
            # Pausa curta para não estressar a API pública/gratuita
            time.sleep(3.0)

        except Exception as e:
            print(f" -> Erro ao buscar bloco de tempo para {coin_id}: {e}")
            time.sleep(5.0)

    return todos_precos_horarios


# --- EXECUÇÃO DO FLUXO ---

print("Buscando dados iniciais na API do CoinGecko...")
minha_lista_futuros_bybit = obter_criptos_futuros_bybit()
mapa_ids = obter_mapeamento_ids()
lista_dados_historicos = []

# Pega apenas a primeira moeda da lista para o teste
moedas_para_teste = minha_lista_futuros_bybit[:1]

print(f"Iniciando busca de preços de hora em hora (1 ano inteiro) para: {moedas_para_teste}...")

for cripto in moedas_para_teste:
    coin_id = mapa_ids.get(cripto)
    if coin_id:
        print(f"\nProcessando {cripto} (ID: {coin_id})... Isso fará 4 requisições com pausas.")
        precos_horarios_ano = buscar_historico_horario_completo_1ano(coin_id)

        lista_dados_historicos.append(
            {
                "cripto": cripto,
                "par": f"{cripto}/USDT",
                "precos_horarios_1ano": precos_horarios_ano,
            }
        )
    else:
        print(f"\nNão foi possível encontrar o ID do CoinGecko para a moeda: {cripto}")

# Resultado Final
print("\n--- Resultado do Teste Real ---")
for item in lista_dados_historicos:
    print(f"Par de Negociação: {item['par']}")
    print(f"Total de registros salvos: {len(item['precos_horarios_1ano'])} pontos de dados.")
    if len(item["precos_horarios_1ano"]) > 0:
        print(f"Exemplo do primeiro registro (Há 1 ano): {item['precos_horarios_1ano'][0]}")
        print(f"Exemplo do último registro (Agora): {item['precos_horarios_1ano'][-1]}")
