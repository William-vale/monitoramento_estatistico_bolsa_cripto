"""Testes rápidos para o orquestrador.

Coloque esta parte à vista para remover depois.
"""

import yfinance as yf
import pandas as pd


def contar_padrao_atingido(df):
    """Conta quantas barras de candles respeitam o padrão definido no orquestrador."""
    vezes = 0
    for _, row in df.iterrows():
        open_price = row["Open"]
        print(f"Open Price: {open_price}")
        low_price = row["Low"]
        print(f"Low Price: {low_price}")
        print(f"Média de cada: {(low_price/open_price)*100:.2f}% ")
        close_price = row["Close"]
        print(f"Close Price: {close_price} ")
        print(f"Média de subida: {100-(low_price/close_price)*100:.2f}% \n")

        if open_price <= 0:
            continue

        queda_minima = open_price * 0.995
        queda_maxima = open_price * 0.985
        alta_esperada = open_price * 1.007 

        if ((low_price <= queda_minima) or (low_price >= queda_maxima)) and (close_price >= alta_esperada):
            vezes += 1
    return vezes


def teste_sintetico():
    print("\n=== TESTE SINTÉTICO ===")
    dados = [
        {"Open": 100.0, "Low": 99.0, "Close": 104.94},
        {"Open": 100.0, "Low": 94.0, "Close": 110.0},
        {"Open": 100.0, "Low": 97.0, "Close": 109.0},
        {"Open": 100.0, "Low": 99.0, "Close": 108.0},
    ]
    df = pd.DataFrame(dados)
    vezes = contar_padrao_atingido(df)
    print("Esperado 1, encontrado:", vezes)


def teste_historico_real(symbol="ITSA4.SA"):
    print(f"\n=== TESTE HISTÓRICO REAL ({symbol}) ===")
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1mo", interval="1h")
    if hist.empty:
        print("Nenhum dado histórico retornado.")
        return
    print("Linhas retornadas:", len(hist))
    vezes = contar_padrao_atingido(hist)
    print("padrao_atingido_vezes:", vezes)
    print("Amostra de primeiros registros:")
    print(hist[["Open", "Low", "Close"]].head(5).to_string())


def teste_parte_fundamental(symbol="ITSA4.SA"):
    print(f"\n=== TESTE FUNDAMENTAL ({symbol}) ===")
    ticker = yf.Ticker(symbol)
    info = ticker.info
    keys = ["currentPrice", "trailingPE", "priceToBook", "trailingEps", "bookValue"]
    for key in keys:
        print(f"{key}:", info.get(key))


if __name__ == "__main__":
    print("ATENÇÃO: testes de validação do orquestrador. Apague este arquivo quando quiser.")
    teste_sintetico()
    teste_historico_real("PETR4.SA")
    teste_parte_fundamental("PETR4.SA")
