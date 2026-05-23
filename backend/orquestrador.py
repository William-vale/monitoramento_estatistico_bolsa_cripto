
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


# -------------------- Passo 4: Buscar dados fundamentalistas via dadosdemercado --------------------
def fetch_fundamental_dados(symbols: List[str]) -> Dict[str, Any]:
	"""
	Passo 4 (atualizado): busca dados fundamentalistas usando Google Finance.

	- Para cada `symbol` constrói a URL do Google Finance e faz um GET.
	- Tenta extrair valores comuns (Market cap, P/E, P/B, Dividend yield, Beta, EPS).
	- Retorna um mapeamento symbol -> dicionário de campos encontrados.

	Observação: o Google Finance não oferece uma API pública estável; esta
	função realiza scraping leve e *best-effort* do HTML/JS da página. Os
	valores extraídos são trechos textuais próximos aos rótulos encontrados.
	"""
	results: Dict[str, Any] = {}

	headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/html"}

	# Rótulos que tentamos capturar — organizar em ordem de importância
	labels = [
		"Market cap",
		"P/E",
		"P/E ratio",
		"Price/Book",
		"P/B",
		"Dividend yield",
		"Dividend yield %",
		"Beta",
		"EPS (TTM)",
		"EPS",
	]

	for symbol in symbols:
		clean = symbol.split(".")[0]
		# Presume B3 quando símbolo termina em .SA, senão usa BMFBOVESPA por padrão
		exchange = "BMFBOVESPA"
		if symbol.upper().endswith(".SA"):
			exchange = "BMFBOVESPA"

		url = f"https://www.google.com/finance/quote/{clean}:{exchange}"
		try:
			resp = HTTP_SESSION.get(url, headers=headers, timeout=15)
			resp.raise_for_status()
			text = resp.text

			found: Dict[str, str] = {}
			# 1) Procura por padrões diretos no HTML comum gerado
			for label in labels:
				# tenta padrões com blocos div/span (observação: estrutura pode variar)
				m = re.search(rf'{re.escape(label)}\s*</[^>]+>\s*<[^>]+>\s*([^<\n]+)', text, re.I)
				if not m:
					m = re.search(rf'{re.escape(label)}\s*[:\-–]?\s*([^<\n]{{1,80}})', text, re.I)
				if m:
					val = m.group(1).strip()
					found[label] = val

			# 2) Se nada foi encontrado, captura trechos AF_initDataCallback relevantes
			if not found:
				blocks = re.findall(r'AF_initDataCallback\((\{.*?\})\);', text, re.S)
				matches = []
				for b in blocks:
					if clean in b or symbol in b:
						matches.append(b[:2000])
				# salva ao menos um bloco bruto para investigação posterior
				found["raw_matches"] = matches or (blocks[:1] if blocks else [])

			# 3) Consultar o brapi.dev como fallback para preencher/ajustar
			#    principalmente os campos numéricos/estruturados.
			try:
				qsym = clean
				brapi_url = f"{BRAPI_BASE}/quote/{qsym}"
				br = http_get(brapi_url)
				br_entry = None
				if isinstance(br, dict) and br.get("results"):
					br_entry = br.get("results")[0]
				elif isinstance(br, dict):
					br_entry = br

				if br_entry:
					# Preferir valores numéricos do brapi quando disponíveis
					if "marketCap" in br_entry and br_entry.get("marketCap") is not None:
						found["Market cap"] = str(br_entry.get("marketCap"))
					if "priceEarnings" in br_entry and br_entry.get("priceEarnings") is not None:
						found["P/E"] = str(br_entry.get("priceEarnings"))
					if "earningsPerShare" in br_entry and br_entry.get("earningsPerShare") is not None:
						found["EPS"] = str(br_entry.get("earningsPerShare"))
					if "longName" in br_entry and br_entry.get("longName"):
						found.setdefault("Name", br_entry.get("longName"))
					if "fiftyTwoWeekLow" in br_entry and br_entry.get("fiftyTwoWeekLow") is not None:
						found["52WeekLow"] = str(br_entry.get("fiftyTwoWeekLow"))
					if "fiftyTwoWeekHigh" in br_entry and br_entry.get("fiftyTwoWeekHigh") is not None:
						found["52WeekHigh"] = str(br_entry.get("fiftyTwoWeekHigh"))
			except Exception:
				pass

			# Sanitizar números básicos (tentar extrair numeric/percent)
			def _extract_number(s: str) -> Optional[str]:
				if not isinstance(s, str):
					return None
				# procurar porcentagem
				m = re.search(r"([-+]?[0-9]+\.?[0-9]*)%", s)
				if m:
					return m.group(1) + "%"
				m = re.search(r"([-+]?[0-9]+\.?[0-9]*(?:e[-+]?[0-9]+)?)", s.replace(',',''), re.I)
				if m:
					return m.group(1)
				return None

			numeric_keys = ["Market cap", "P/E", "EPS", "P/B", "52WeekLow", "52WeekHigh", "Dividend yield", "Beta"]
			for k in list(found.keys()):
				if k in numeric_keys:
					val = found.get(k)
					num = _extract_number(val) if isinstance(val, str) else None
					if num:
						found[k] = num
					else:
						# remover valores estranhos
						if isinstance(val, str) and len(val) > 200:
							found[k] = val[:200]

				# Extrair Beta do HTML se o valor atual não for numérico
				if "Beta" not in found or (isinstance(found.get("Beta"), str) and not re.search(r"[-+]?[0-9]+\.?[0-9]*", found.get("Beta"))):
					m_beta = re.search(r"Beta\s*[:\-–]?\s*([-+]?[0-9]+\.?[0-9]*)", text, re.I)
					if m_beta:
						found["Beta"] = m_beta.group(1)
					else:
						# remover Beta inválido se presente
						if "Beta" in found:
							del found["Beta"]
			# Marcar origem simples
			if "raw_matches" in found and br_entry:
				found.setdefault("_source", "google+brapi_fallback")
			elif "raw_matches" in found:
				found.setdefault("_source", "google")
			else:
				found.setdefault("_source", "brapi")

			results[symbol] = found
		except requests.HTTPError as e:
			results[symbol] = {"error": str(e)}
		except Exception as e:
			results[symbol] = {"error": f"unexpected: {e}"}

		time.sleep(0.2)

	return results


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