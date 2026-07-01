import requests

BASE_URL = "https://brapi.dev/api/quote/list"

def buscar_units():

    ativos = []
    pagina = 1

    while True:

        response = requests.get(
            BASE_URL,
            params={
                "subType": "unit",
                "page": pagina,
                "limit": 100
            }
        )

        dados = response.json()

        for item in dados.get("stocks", []):

            ativos.append({
                "ticker": item["stock"],
                "tipo": "UNIT"
            })

        if not dados.get("hasNextPage"):
            break

        pagina += 1

    return ativos