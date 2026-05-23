
# ==========================================================
# Orquestrador principal - implementação
# ==========================================================
# Observação: todo o código e os comentários abaixo seguem o
# pedido do usuário: todo o trabalho deve ocorrer somente neste
# arquivo `orquestrador.py`. Os comentários funcionam como
# passo a passo explicativo (passo 1, passo 2, ...).
# As funções usam variáveis globais sempre que possível e
# minimizam variáveis locais conforme solicitado.
# ==========================================================

# -------------------- Passo 1: Imports e variáveis globais --------------------
import os
import json
import time
from typing import Any, Dict, List, Optional

import requests
import re

# Variáveis globais: sessão HTTP, bases de API, chaves e arquivos de saída
# (usar variáveis globais para facilitar o acesso em múltiplas funções)
HTTP_SESSION: requests.Session = requests.Session()

# Base URL para a API pública de trades (brapi.dev)
BRAPI_BASE: str = os.getenv("BRAPI_BASE", "https://brapi.dev/api")

# Base URL para a API de fundamentalistas (dadosdemercado.com.br).
# A URL e a chave devem ser definidas como variáveis de ambiente.
# Se a variável `PARTNR_API_KEY` já estiver em uso, ela é aceita como fallback.
DADOS_BASE: str = os.getenv("DADOS_BASE", "https://api.dadosdemercado.com.br/v1")
DADOS_API_KEY: Optional[str] = os.getenv("DADOS_API_KEY") or os.getenv("PARTNR_API_KEY")

# Arquivos de saída (persistência simples em JSON)
OUTPUT_TRADE_FILE: str = os.getenv("OUTPUT_TRADE_FILE", "backend/trade_data.json")
OUTPUT_FUND_FILE: str = os.getenv("OUTPUT_FUND_FILE", "backend/fundamental_data.json")


# -------------------- Passo 2: Cliente HTTP genérico --------------------
def http_get(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 10) -> Any:
	"""
	Passo 2 (cliente HTTP): função genérica para realizar requisições GET.

	- Usa a sessão HTTP global `HTTP_SESSION` para reaproveitar conexões.
	- Retorna JSON decodificado em caso de sucesso.
	- Em caso de erro de rede ou resposta inválida, lança exceção com
	  mensagem descritiva.

	Minimiza variáveis locais: apenas usa `resp` e `rjson` localmente.
	"""
	# Cabeçalhos default — permitem sobrepor via parâmetro
	default_headers = {"Accept": "application/json"}
	if headers:
		default_headers.update(headers)

	resp = HTTP_SESSION.get(url, params=params, headers=default_headers, timeout=timeout)
	# Lança para status codes 4xx/5xx — será capturado nas camadas superiores
	resp.raise_for_status()

	# Converter resposta para JSON (poderia falhar se a API devolver texto)
	rjson = resp.json()
	return rjson


# -------------------- Passo 3: Buscar dados de Trade via brapi.dev --------------------
def fetch_trade_data_brapi(symbols: List[str]) -> Dict[str, Any]:
	"""
	Passo 3: busca dados de Trade das ações usando a API da brapi.dev.

	- `symbols`: lista de tickers no formato suportado (ex: PETR4.SA, VALE3.SA)
	- Retorna um dicionário mapeando ticker -> dados retornados pela API

	Observações de implementação:
	- Usa a variável global `BRAPI_BASE` como base da URL.
	- Usa o cliente `http_get` para centralizar tratamento de erros.
	- Mantém poucas variáveis locais para alinhar com a solicitação do usuário.
	"""
	results: Dict[str, Any] = {}

	# Vamos buscar o histórico diário de 1 ano para cada símbolo usando
	# o endpoint /quote/{symbol}?range=1y&interval=1d que retorna
	# um campo `historicalDataPrice` em `results[0]`.
	for symbol in symbols:
		# limpar sufixos de exchange para a consulta se necessário
		query_symbol = symbol.split(".")[0]
		url = f"{BRAPI_BASE}/quote/{query_symbol}"
		try:
			# Passamos parâmetros para obter 1 ano diário
			resp = http_get(url, params={"range": "1y", "interval": "1d"})
			# Normalizar saída: extrair histórico se presente
			entry = None
			if isinstance(resp, dict) and resp.get("results"):
				entry = resp.get("results")[0]
			elif isinstance(resp, dict):
				entry = resp

			hist = None
			if entry and isinstance(entry, dict):
				hist = entry.get("historicalDataPrice") or entry.get("historical") or entry.get("historicalPrices")

			# Guardar histórico explícito no arquivo de trade
			results[symbol] = {"historical": hist or [], "meta": entry}
		except requests.HTTPError as e:
			results[symbol] = {"error": str(e)}
		except Exception as e:
			results[symbol] = {"error": f"unexpected: {e}"}

		time.sleep(0.2)

	return results


# -------------------- Passo 4: Buscar dados fundamentalistas via Google Finance --------------------
def fetch_fundamental_dados(symbols: List[str]) -> Dict[str, Any]:
	"""
	Passo 4 (atualizado): busca dados fundamentalistas usando o Google Finance.

	- Para cada `symbol` constrói a URL do Google Finance e faz um GET.
	- Tenta extrair os indicadores solicitados diretamente do HTML do Google Finance.
	- Usa `brapi.dev` como fallback para completar campos numéricos que não são
	  expostos diretamente pelo scraping.
	- Aplica os filtros solicitados e ordena os resultados por P/L ascendente.
	"""
	results: Dict[str, Any] = {}

	headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/html"}

	def _parse_float(value: Any, field_name: Optional[str] = None) -> Optional[float]:
		if value is None:
			return None
		if isinstance(value, (int, float)):
			float_value = float(value)
			if field_name in ("ROE", "Margem Líquida", "DY") and float_value <= 1:
				return float_value * 100
			return float_value
		text = str(value).strip()
		if not text:
			return None
		percent = text.endswith("%")
		if percent:
			text = text[:-1].strip()
		text = text.replace(',', '.').replace('−', '-').replace('–', '-')
		m = re.search(r'([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', text)
		if not m:
			return None
		float_value = float(m.group(1))
		if percent:
			return float_value
		if field_name in ("ROE", "Margem Líquida", "DY") and float_value <= 1:
			return float_value * 100
		return float_value

	def _parse_google_finance(text: str) -> Dict[str, str]:
		found: Dict[str, str] = {}
		label_map = {
			"Dividend": "DY",
			"P/E ratio": "P/L",
			"Mkt. cap": "Market cap",
			"EPS": "EPS",
			"Beta": "Beta",
		}
		for label, target in label_map.items():
			pattern = rf'<div class="KxsRFb">\s*<div class="SwQK7">{re.escape(label)}</div>\s*<div class="dO6ijd">([^<]+)</div>'
			m = re.search(pattern, text, re.I)
			if m:
				found[target] = m.group(1).strip()

		m = re.search(r'<div class="sp5q4e">Net profit margin</div>.*?<div class="CNzF7d">([^<]+)</div>', text, re.S | re.I)
		if m:
			found["Margem Líquida"] = m.group(1).strip()

		return found

	def _apply_filters(found: Dict[str, Any]) -> Dict[str, Any]:
		metrics = {
			"DY": _parse_float(found.get("DY"), "DY"),
			"P/L": _parse_float(found.get("P/L"), "P/L"),
			"P/VPA": _parse_float(found.get("P/VPA"), "P/VPA"),
			"ROE": _parse_float(found.get("ROE"), "ROE"),
			"Margem Líquida": _parse_float(found.get("Margem Líquida"), "Margem Líquida"),
			"Dívida Líquida / EBITDA": _parse_float(found.get("Dívida Líquida / EBITDA"), "Dívida Líquida / EBITDA"),
			"Liquidez Corrente": _parse_float(found.get("Liquidez Corrente"), "Liquidez Corrente"),
		}

		passes = True
		reasons: List[str] = []
		filters = [
			("DY", 6.0, 30.0, False),
			("P/L", 1.0, 15.0, False),
			("P/VPA", 0.5, 1.5, False),
			("ROE", 15.0, None, False),
			("Margem Líquida", 10.0, None, True),
			("Dívida Líquida / EBITDA", 0.5, 2.5, False),
			("Liquidez Corrente", 1.0, 2.0, False),
		]
		for key, minimum, maximum, strict in filters:
			value = metrics.get(key)
			if value is None:
				passes = False
				reasons.append(f"{key} ausente")
				continue
			if minimum is not None:
				if strict:
					if value <= minimum:
						passes = False
						reasons.append(f"{key}={value} <= {minimum}")
				else:
					if value < minimum:
						passes = False
						reasons.append(f"{key}={value} < {minimum}")
			if maximum is not None and value > maximum:
				passes = False
				reasons.append(f"{key}={value} > {maximum}")
		return {"metrics": metrics, "passes_filters": passes, "filter_reasons": reasons}

	for symbol in symbols:
		clean = symbol.split(".")[0]
		exchange = "BMFBOVESPA"
		url = f"https://finance.google.com/finance?q={clean}:{exchange}"
		found: Dict[str, Any] = {}
		try:
			resp = HTTP_SESSION.get(url, headers=headers, timeout=15)
			resp.raise_for_status()
			text = resp.text
			found.update(_parse_google_finance(text))
			if "P/L" not in found:
				m = re.search(r'<div class="SwQK7">P/E ratio</div>\s*<div class="dO6ijd">([^<]+)</div>', text, re.I)
				if m:
					found["P/L"] = m.group(1).strip()
			m_roe = re.search(r'ROE\s*[:\-–]?\s*([0-9]+\.?[0-9]*%?)', text, re.I)
			if m_roe and "ROE" not in found:
				found["ROE"] = m_roe.group(1).strip()
		except Exception:
			pass

		try:
			brapi_url = f"{BRAPI_BASE}/quote/{clean}"
			br = http_get(brapi_url, params={"modules": "financialData,defaultKeyStatistics"})
			br_entry = None
			if isinstance(br, dict) and br.get("results"):
				br_entry = br.get("results")[0]
			elif isinstance(br, dict):
				br_entry = br
			if br_entry:
				financial = br_entry.get("financialData") or {}
				stats = br_entry.get("defaultKeyStatistics") or {}
				if "P/L" not in found and br_entry.get("priceEarnings") is not None:
					found["P/L"] = str(br_entry.get("priceEarnings"))
				if "P/VPA" not in found and stats.get("priceToBook") is not None:
					found["P/VPA"] = str(stats.get("priceToBook"))
				if "ROE" not in found and financial.get("returnOnEquity") is not None:
					found["ROE"] = str(financial.get("returnOnEquity"))
				if "Margem Líquida" not in found and financial.get("profitMargins") is not None:
					found["Margem Líquida"] = str(financial.get("profitMargins"))
				if "Liquidez Corrente" not in found and financial.get("currentRatio") is not None:
					found["Liquidez Corrente"] = str(financial.get("currentRatio"))
				if financial.get("totalDebt") is not None and financial.get("totalCash") is not None and financial.get("ebitda") is not None:
					total_debt = financial.get("totalDebt")
					total_cash = financial.get("totalCash")
					ebitda = financial.get("ebitda")
					if isinstance(total_debt, (int, float)) and isinstance(total_cash, (int, float)) and isinstance(ebitda, (int, float)) and ebitda != 0:
						found["Dívida Líquida / EBITDA"] = str((total_debt - total_cash) / ebitda)
				if "Beta" not in found and stats.get("beta") is not None:
					found["Beta"] = str(stats.get("beta"))
				if "Market cap" not in found and br_entry.get("marketCap") is not None:
					found["Market cap"] = str(br_entry.get("marketCap"))
		except Exception:
			pass

		for required_key in ["DY", "P/L", "P/VPA", "ROE", "Margem Líquida", "Dívida Líquida / EBITDA", "Liquidez Corrente"]:
			found.setdefault(required_key, None)

		filter_info = _apply_filters(found)
		found.update(filter_info)
		results[symbol] = found
		time.sleep(0.2)

	filtered_symbols = [s for s, v in results.items() if v.get("passes_filters")]
	filtered_symbols.sort(key=lambda s: (_parse_float(results[s].get("P/L"), "P/L") if _parse_float(results[s].get("P/L"), "P/L") is not None else float("inf")))
	return {"symbols": results, "filtered_symbols": filtered_symbols, "filtered_data": [results[s] for s in filtered_symbols]}


# -------------------- Passo 5: Orquestração e persistência --------------------
def orchestrate(symbols: List[str]) -> Dict[str, Any]:
	"""
	Passo 5: função principal que orquestra as chamadas e persiste os dados.

	- Executa `fetch_trade_data_brapi` e `fetch_fundamental_dados`.
	- Persiste os resultados em JSON usando os caminhos globais.
	- Retorna um resumo contendo caminhos e contagens básicas.
	"""
	# Buscar dados de trade
	trade_data = fetch_trade_data_brapi(symbols)

	# Buscar dados fundamentalistas
	fund_data = fetch_fundamental_dados(symbols)

	# Persistência simples em arquivos JSON (usando variáveis globais de caminho)
	try:
		with open(OUTPUT_TRADE_FILE, "w", encoding="utf-8") as f:
			json.dump(trade_data, f, ensure_ascii=False, indent=2)
	except Exception as e:
		# Em caso de falha de I/O, registrar no resultado retornado
		return {"error": f"Falha ao escrever o arquivo de negociação: {e}"}

	try:
		with open(OUTPUT_FUND_FILE, "w", encoding="utf-8") as f:
			json.dump(fund_data, f, ensure_ascii=False, indent=2)
	except Exception as e:
		return {"error": f"Falha ao gravar o arquivo de fundos: {e}"}

	# Retornar um resumo simples
	summary = {
		"trade_file": OUTPUT_TRADE_FILE,
		"fund_file": OUTPUT_FUND_FILE,
		"symbols_processed": len(symbols),
	}
	return summary


# -------------------- Passo 6: Função de teste que executa tudo --------------------
def run_full_test():
	"""
	Passo 6: função de teste de alto nível que demonstra o uso do orquestrador.

	- Define uma lista de símbolos de exemplo (B3) e chama `orchestrate`.
	- Imprime o resumo retornado para verificação rápida.
	- Essa função funciona como um 'smoke test' local.
	"""
	# Símbolos exemplo (usados normalmente na B3). O usuário pode editar
	# diretamente a variável global `OUTPUT_*` ou as variáveis de ambiente.
	example_symbols = ["PETR4.SA", "VALE3.SA"]

	# Executa a orquestração
	result = orchestrate(example_symbols)

	# Saída simples para diagnóstico
	print("Orquestrador - resumo:", result)


# -------------------- Passo 7: Ponto de entrada opcional --------------------
if __name__ == "__main__":
	# Executa o teste apenas quando o arquivo for executado diretamente.
	run_full_test()