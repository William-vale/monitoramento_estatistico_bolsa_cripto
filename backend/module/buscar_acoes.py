import requests

BASE_URL = "https://brapi.dev/api/quote/list"

def buscar_acoes():

    ativos = []
    pagina = 1

    while True:

        response = requests.get(
            BASE_URL,
            params={
                "subType": "stock",
                "page": pagina,
                "limit": 100
            }
        )

        dados = response.json()

        for item in dados.get("stocks", []):

            ticker = item["stock"]

            if ticker.endswith(("3", "4")):

                ativos.append({
                    "ticker": ticker,
                    "tipo": "ACAO"
                })

        if not dados.get("hasNextPage"):
            break

        pagina += 1

    return ativos