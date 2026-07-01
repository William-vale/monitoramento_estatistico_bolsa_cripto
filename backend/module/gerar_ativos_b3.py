import json

from buscar_acoes import buscar_acoes
from buscar_units import buscar_units
from buscar_fiis import buscar_fiis

def gerar_ativos_b3():
    ativos = []

    ativos.extend(buscar_acoes())
    ativos.extend(buscar_fiis())
    ativos.extend(buscar_units())

    # Remover duplicados
    ativos_unicos = {}

    for ativo in ativos: 
        ativos_unicos[ativo["ticker"]] = ativo
    
    resultado = list(ativos_unicos.values())
    resultado.sort(
        key=lambda x: x["ticker"]
    )

    with open(
        "data/ativos_b3.json",
        "w",
        encoding="utf-8"
    ) as arquivo: 

        json.dump(
            resultado,
            arquivo,
            indent=4,
            ensure_ascii=False
        )

    print(f"{len(resultado)} ativos encontrados" )

if __name__ == "__main__":
    gerar_ativos_b3()
