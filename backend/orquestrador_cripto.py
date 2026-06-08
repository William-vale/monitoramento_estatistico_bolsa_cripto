import time
import requests


# 1. BUSCA LISTA DE FUTUROS DA BYBIT
def obter_criptos_futuros_bybit():
    url = "https://coingecko.com"
    nome_exchange_alvo = "Bybit (Futures)"
    lista_futuros = set()
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        for item in resposta.json():
            if item.get("market") == nome_exchange_alvo:
                ativo_base = item.get("index_id")
                if ativo_base:
                    lista_futuros.add(ativo_base.upper())
    except Exception:
        return []
    return sorted(list(lista_futuros))


# 2. MAPEIA SÍMBOLOS PARA IDS DO COINGECKO
def obter_mapeamento_ids():
    url = "https://coingecko.com"
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        return {coin["symbol"].upper(): coin["id"] for coin in resposta.json()}
    except Exception:
        return {}


# 3. NOVO MÉTODO: BUSCA PREÇOS DE HORA EM HORA DIVIDIDO EM 4 BLOCOS
def buscar_historico_horario_completo_1ano(coin_id):
    url = f"https://coingecko.com{coin_id}/market_chart/range"

    agora = int(time.time())
    um_dia_segundos = 86400
    noventa_dias_segundos = 90 * um_dia_segundos

    # Dividimos o ano (360 dias) em 4 janelas de 90 dias para forçar a API a mandar dados horários
    janelas_tempo = []
    for i in range(4):
        fim = agora - (i * noventa_dias_segundos)
        inicio = fim - noventa_dias_segundos
        janelas_tempo.append((inicio, fim))

    # Inverte para processar do passado para o presente
    janelas_tempo.reverse()

    todos_precos_horarios = []

    for inicio, fim in janelas_tempo:
        parametros = {"vs_currency": "usd", "from": inicio, "to": fim}

        try:
            resposta = requests.get(url, params=parametros)

            # Se bater no limite, aguarda 1 minuto inteiro conforme solicitado
            if resposta.status_code == 429:
                print(
                    " -> Limite atingido. Aguardando 60 segundos para continuar..."
                )
                time.sleep(60)
                resposta = requests.get(url, params=parametros)

            resposta.raise_for_status()
            dados = resposta.json()
            precos_bloco = dados.get("prices", [])

            # Concatena os preços horários deste trimestre na lista geral
            todos_precos_horarios.extend(precos_bloco)

            # Pausa de segurança entre blocos para não estressar a API pública
            time.sleep(3.0)

        except Exception as e:
            print(f" -> Erro ao buscar bloco de tempo para {coin_id}: {e}")
            time.sleep(5.0)

    return todos_precos_horarios


# --- EXECUÇÃO DO FLUXO ---

minha_lista_futuros_bybit = obter_criptos_futuros_bybit()
mapa_ids = obter_mapeamento_ids()
lista_dados_historicos = []

# Testando estritamente com a primeira moeda para demonstrar o volume de dados horários
moedas_para_teste = minha_lista_futuros_bybit[:1]

print(
    f"Iniciando busca de preços de hora em hora (1 ano inteiro) para: {moedas_para_teste}..."
)

for cripto in moedas_para_teste:
    coin_id = mapa_ids.get(cripto)
    if coin_id:
        print(f"\nProcessando {cripto}... Isso fará 4 requisições com pausas.")
        precos_horarios_ano = buscar_historico_horario_completo_1ano(coin_id)

        lista_dados_historicos.append(
            {
                "cripto": cripto,
                "par": f"{cripto}/USDT",
                "precos_horarios_1ano": precos_horarios_ano,
            }
        )

# --- SAÍDA ESPERADA NO SEU TERMINAL ---
print("\n--- Resultado do Teste Real ---")
for item in lista_dados_historicos:
    print(f"Par de Negociação: {item['par']}")
    print(
        f"Total de registros de preços salvos (de hora em hora): {len(item['precos_horarios_1ano'])} pontos de dados."
    )
    if len(item["precos_horarios_1ano"]) > 0:
        print(
            f"Exemplo do primeiro registro (Há 1 ano): {item['precos_horarios_1ano'][0]}"
        )
        print(
            f"Exemplo do último registro (Agora): {item['precos_horarios_1ano'][-1]}"
        )
