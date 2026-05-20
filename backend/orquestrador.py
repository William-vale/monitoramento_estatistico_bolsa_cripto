"""
╔══════════════════════════════════════════════════════════════════╗
║              ORQUESTRADOR PRINCIPAL — BACKEND                    ║
║                                                                  ║
║  Responsável por:                                                ║
║    • Buscar e listar todos os ativos da B3 (Ações, FIIs,        ║
║      ETFs, BDRs, Derivativos)                                    ║
║    • Buscar e listar todas as criptomoedas da Bybit              ║
║      (SPOT e FUTUROS/SWAP)                                       ║
║    • Persistir os dados em JSON para uso dos sub-módulos         ║
║    • Expor função de teste cobrindo todas as funções             ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json, time, base64, logging, requests, ccxt
import yfinance as yf
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------
# Configuração de LOG
# ----------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s %(message)s]",
    datefmt="%d-%m-%Y %H:%M:%S",
)
log = logging.getLogger("orquestrador")

# ----------------------------------------------------------------
# Caminhos base
# ----------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
TRADE_B3_DIR = BASE_DIR / "TRADE_B3"
TRADE_CRIPTO_DIR = BASE_DIR / "TRADE_CRIPTO"
LONGO_PRAZO_DIR = BASE_DIR / "ATIVO_LONGO_PRAZO"

for _dir in (TRADE_B3_DIR, TRADE_CRIPTO_DIR, LONGO_PRAZO_DIR): 
    _dir.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------
# LISTAS GLOBAIS (Preenchidas pelas funções abaixo)
# ----------------------------------------------------------------

B3_ATIVOS: list[dict] = [] # todos os ativos da B3
BYBIT_SPOT: list[dict] = [] # mercado spot da ByBit
BYBIT_FUTUROS: list[dict] = [] # contratos perpetuos/futuros da ByBit

# ----------------------------------------------------------------
# Constantes - B3 API
# ----------------------------------------------------------------

B3_BASE_URL = "https://sistemaswebb3-listados.fnet.com.br/listedCompaniesProxy/CompanyCall/GetInitialCompanies"
B3_PAGE_SIZE  = 120 # máximo aceito pela API da B3
B3_TIMEOUT    = 15  # segundos por request
B3_DELAY      = 0.3 # pausa entre páginas para não sobrecarregar

# Tipos de ativo que a B3 classifica internamente
B3_SEGMENT_MAP = {
    "ACOES"       : "Ações",
    "FII"         : "Fundo Imobiliário (FII)",
    "ETF-RENDA-VARIAVEL" : "ETF Renda Variável",
    "ETF-RENDA-FIXA"     : "ETF Renda Fixa",
    "BDR"         : "BDR",
    "DERIVATIVOS" : "Derivativos",
}

# ═════════════════════════════════════════════════════════════════
#  1. FUNÇÃO: BUSCAR ATIVOS B3
# ═════════════════════════════════════════════════════════════════

def buscar_ativos_b3(salvar_json: bool = True) -> list[dict]:
    """
    Busca todos os ativos listados na B3 usando a API pública de empresas listadas e complementa com yfinance para obter o ticker no formato aceito pelo Yahoo Finance ('<TICKER>.SA').
 
    Parâmetros ----------
    salvar_json : bool
        Se True, persiste o resultado em TRADE_B3/ativos_b3.json
 
    Retorno -------
    list[dict]  — lista de dicionários com os campos:
        {
            "ticker"       : str   # ex.: "PETR4"
            "ticker_yf"    : str   # ex.: "PETR4.SA"  (para uso no yfinance)
            "nome"         : str   # nome da empresa / fundo
            "segmento"     : str   # classificação B3
            "tipo"         : str   # descrição amigável do tipo
            "ativo"        : bool  # se o ativo ainda está listado
        }
    """

    global B3_ATIVOS

    log.info("====== Iniciando busca de ativos da B3 ======")
    ativos: list[dict] = []
    pagina = 1

    while True:
        payload = json.dumps({"language": "pt-br", "pageNumber": pagina, "pageSize": B3_PAGE_SIZE})
        token = base64.b64decode(payload.encode().decode())
        url = f"{B3_BASE_URL}/{token}"

        try: 
            resp = requests.get(url, timeout=B3_TIMEOUT)
            resp.raise_for_status()
            dados = resp.json()
        except requests.exceptions.Timeout:
            log.error(f"Timeout na página {pagina} da API B3")
            break
        except requests.exceptions.HTTPError as exc:
            log.error(f"Erro HTTP da API B3: {exc}")
            break
        except ValueError:
            log.error("Resposta da API B3 não é um JSON válido.")
            break

        empresas = dados.get("results", [])
        total    = dados.get("total", {})

        if not empresas:
            log.info(f"Nenhum resultado na página {pagina}. Encerrando paginação.")
            break

        for empresa in empresas:
            # O código de negociação pode ter vários tickers (ex.: PETR3, PETR4)
            codigos_brutos = empresa.get("codes", [empresa.get("code", "")])
            if isinstance(codigos_brutos, str):
                codigos_brutos = [codigos_brutos]
 
            for cod in codigos_brutos:
                if not cod:
                    continue
                segmento = empresa.get("segment", "").upper().replace(" ", "-")
                ativos.append({
                    "ticker"    : cod.strip(),
                    "ticker_yf" : f"{cod.strip()}.SA",
                    "nome"      : empresa.get("companyName", "").strip(),
                    "segmento"  : segmento,
                    "tipo"      : B3_SEGMENT_MAP.get(segmento, empresa.get("typeName", "—")),
                    "ativo"     : True,
                })
 
            log.info(f"  Página {pagina}: {len(empresas)} empresa(s). Acumulado: {len(ativos)} ativos.")

            # Verifica se há mais páginas
            total_registros = total.get("totalNumberOfCompanies", 0) if isinstance(total, dict) else 0
            if total_registros and len(ativos) >= total_registros:
                break
            if len(empresas) < B3_PAGE_SIZE:
                break
    
            pagina += 1
            time.sleep(B3_DELAY)

        # ── Remove duplicatas (mesmo ticker pode aparecer em segmentos diferentes)
        vistos: set[str] = set()
        unicos: list[dict] = []
        for item in ativos:
            if item["ticker"] not in vistos:
                vistos.add(item["ticker"])
            unicos.append(item)

        B3_ATIVOS = unicos

        log.info(f"✔  Total de ativos B3 coletados: {len(B3_ATIVOS)}")

        if salvar_json:
            _salvar_json(
                dados    = {"atualizado_em": _agora(), "total": len(B3_ATIVOS), "ativos": B3_ATIVOS},
                caminho  = TRADE_B3_DIR / "ativos_b3.json",
                descricao= "ativos B3",
            )
 
        return B3_ATIVOS

# ═════════════════════════════════════════════════════════════════
#  2. FUNÇÃO: BUSCAR CRIPTOMOEDAS BYBIT
# ═════════════════════════════════════════════════════════════════
 
def buscar_cripto_bybit(salvar_json: bool = True) -> dict[str, list[dict]]:
    """
    Busca todos os pares/contratos disponíveis na Bybit usando ccxt, separando entre mercado SPOT e mercado de FUTUROS (perpétuos + entrega).
 
    Parâmetros ----------
    salvar_json : bool
        Se True, persiste os resultados em:
          • TRADE_CRIPTO/bybit_spot.json
          • TRADE_CRIPTO/bybit_futuros.json
 
    Retorno -------
    dict com chaves "spot" e "futuros", cada uma com lista de dicionários:
        {
            "symbol"       : str   # ex.: "BTC/USDT"
            "base"         : str   # ex.: "BTC"
            "quote"        : str   # ex.: "USDT"
            "tipo"         : str   # "spot" | "swap" | "future"
            "contrato"     : str   # ex.: "BTC/USDT:USDT" (apenas futuros)
            "ativo"        : bool
            "settlement"   : str   # moeda de liquidação (futuros)
            "expiracao"    : str | None  # data de expiração (contratos com vencimento)
        }
    """
    global BYBIT_SPOT, BYBIT_FUTUROS
 
    log.info("═══ Iniciando busca de criptomoedas Bybit (SPOT + FUTUROS) ═══")
 
    spot_list:    list[dict] = []
    futuros_list: list[dict] = []
 
    # ── Inicializa a exchange
    try:
        exchange = ccxt.bybit({
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",      # ponto de partida; sobrescrito abaixo
            },
        })
    except Exception as exc:
        log.error(f"Falha ao inicializar ccxt.bybit: {exc}")
        return {"spot": [], "futuros": []}
 
    # ── Carrega todos os mercados de uma vez
    try:
        log.info("  Carregando todos os mercados da Bybit...")
        mercados: dict = exchange.load_markets(True)   # reload=True para garantir dados frescos
        log.info(f"  Total de mercados retornados pela Bybit: {len(mercados)}")
    except ccxt.NetworkError as exc:
        log.error(f"Erro de rede ao acessar Bybit: {exc}")
        return {"spot": [], "futuros": []}
    except ccxt.ExchangeError as exc:
        log.error(f"Erro da exchange Bybit: {exc}")
        return {"spot": [], "futuros": []}
    except Exception as exc:
        log.error(f"Erro inesperado ao carregar mercados Bybit: {exc}")
        return {"spot": [], "futuros": []}
 
    # ── Classifica cada mercado
    for symbol, market in mercados.items():
        is_spot   = market.get("spot",   False)
        is_swap   = market.get("swap",   False)   # perpétuos (sem vencimento)
        is_future = market.get("future", False)   # contratos com vencimento
 
        entrada = {
            "symbol"    : symbol,
            "base"      : market.get("base",  ""),
            "quote"     : market.get("quote", ""),
            "tipo"      : market.get("type",  "desconhecido"),
            "contrato"  : market.get("id",    symbol),
            "ativo"     : market.get("active", True),
            "settlement": market.get("settle", ""),
            "expiracao" : market.get("expiry", None),   # timestamp ms ou None
        }
 
        if is_spot:
            spot_list.append(entrada)
        elif is_swap or is_future:
            futuros_list.append(entrada)
        # Opções e outros tipos ignorados neste estágio
 
    BYBIT_SPOT    = spot_list
    BYBIT_FUTUROS = futuros_list
 
    log.info(f"✔  SPOT    : {len(BYBIT_SPOT)} pares")
    log.info(f"✔  FUTUROS : {len(BYBIT_FUTUROS)} contratos")
 
    if salvar_json:
        _salvar_json(
            dados    = {"atualizado_em": _agora(), "total": len(BYBIT_SPOT), "ativos": BYBIT_SPOT},
            caminho  = TRADE_CRIPTO_DIR / "bybit_spot.json",
            descricao= "Bybit SPOT",
        )
        _salvar_json(
            dados    = {"atualizado_em": _agora(), "total": len(BYBIT_FUTUROS), "ativos": BYBIT_FUTUROS},
            caminho  = TRADE_CRIPTO_DIR / "bybit_futuros.json",
            descricao= "Bybit FUTUROS",
        )
 
    return {"spot": BYBIT_SPOT, "futuros": BYBIT_FUTUROS}

# ═════════════════════════════════════════════════════════════════
#  3. FUNÇÃO: TESTE
# ═════════════════════════════════════════════════════════════════
 
def teste() -> dict:
    """
    Executa todas as funções do orquestrador e verifica seus retornos.
 
    ⚠️  As funções são totalmente independentes desta função — cada uma pode ser chamada diretamente em qualquer parte do projeto.
 
    Retorno -------
    dict  — relatório completo com status de cada função testada:
        {
            "timestamp"  : str,
            "resultados" : {
                "<nome_funcao>": {
                    "status"    : "OK" | "FALHA" | "AVISO",
                    "mensagem"  : str,
                    "detalhes"  : dict | None,
                }
            },
            "resumo": {"total": int, "ok": int, "falha": int, "aviso": int}
        }
    """
    log.info("══════════════════════════════════")
    log.info("  INICIANDO SUITE DE TESTES       ")
    log.info("══════════════════════════════════")
 
    relatorio: dict = {
        "timestamp" : _agora(),
        "resultados": {},
        "resumo"    : {"total": 0, "ok": 0, "falha": 0, "aviso": 0},
    }
 
    # ── Teste 1: buscar_ativos_b3 ──────────────────────────────
    _teste_funcao(
        relatorio  = relatorio,
        nome       = "buscar_ativos_b3",
        funcao     = buscar_ativos_b3,
        kwargs     = {"salvar_json": True},
        validacoes = [
            ("Retornou uma lista",        lambda r: isinstance(r, list)),
            ("Lista não está vazia",      lambda r: len(r) > 0),
            ("Itens têm campo 'ticker'",  lambda r: all("ticker"  in x for x in r[:5])),
            ("Itens têm campo 'ticker_yf'",lambda r: all("ticker_yf" in x for x in r[:5])),
            ("Itens têm campo 'nome'",    lambda r: all("nome"    in x for x in r[:5])),
        ],
    )
 
    # ── Teste 2: buscar_cripto_bybit ───────────────────────────
    _teste_funcao(
        relatorio  = relatorio,
        nome       = "buscar_cripto_bybit",
        funcao     = buscar_cripto_bybit,
        kwargs     = {"salvar_json": True},
        validacoes = [
            ("Retornou um dict",           lambda r: isinstance(r, dict)),
            ("Dict tem chave 'spot'",      lambda r: "spot"    in r),
            ("Dict tem chave 'futuros'",   lambda r: "futuros" in r),
            ("SPOT não está vazio",        lambda r: len(r.get("spot",    [])) > 0),
            ("FUTUROS não está vazio",     lambda r: len(r.get("futuros", [])) > 0),
            ("Itens SPOT têm 'symbol'",    lambda r: all("symbol" in x for x in r["spot"][:5])),
            ("Itens FUTUROS têm 'symbol'", lambda r: all("symbol" in x for x in r["futuros"][:5])),
        ],
    )
 
    # ── Resumo final ───────────────────────────────────────────
    _imprimir_relatorio(relatorio)
    return relatorio

# ═════════════════════════════════════════════════════════════════
#  UTILITÁRIOS INTERNOS
# ═════════════════════════════════════════════════════════════════
 
def _agora() -> str:
    """Retorna timestamp atual formatado."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 
 
def _salvar_json(dados: dict, caminho: Path, descricao: str = "") -> None:
    """Persiste um dicionário em arquivo JSON com indentação."""
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        log.info(f"  💾 {descricao} salvo em: {caminho}")
    except OSError as exc:
        log.error(f"  Falha ao salvar {descricao}: {exc}")
 
 
def _teste_funcao(
    relatorio: dict,
    nome: str,
    funcao,
    kwargs: dict,
    validacoes: list[tuple],
) -> None:
    """
    Executa uma função, aplica validações sobre o retorno e
    registra o resultado no relatório de testes.
    """
    log.info(f"  ▶  Testando: {nome}")
    relatorio["resumo"]["total"] += 1
 
    try:
        resultado = funcao(**kwargs)
    except Exception as exc:
        relatorio["resultados"][nome] = {
            "status"  : "FALHA",
            "mensagem": f"Exceção durante execução: {type(exc).__name__}: {exc}",
            "detalhes": None,
        }
        relatorio["resumo"]["falha"] += 1
        log.error(f"    ✘ FALHA — {exc}")
        return
 
    falhas  = []
    avisos  = []
    detalhes = {}
 
    for descricao, validacao in validacoes:
        try:
            passou = validacao(resultado)
        except Exception as exc:
            passou = False
            avisos.append(f"Erro ao avaliar validação '{descricao}': {exc}")
 
        detalhes[descricao] = "✔" if passou else "✘"
        if not passou:
            falhas.append(descricao)
 
    # Informações extras sobre o resultado
    if isinstance(resultado, list):
        detalhes["total_itens"] = len(resultado)
    elif isinstance(resultado, dict):
        for k, v in resultado.items():
            if isinstance(v, list):
                detalhes[f"total_{k}"] = len(v)
 
    if falhas:
        status   = "FALHA"
        mensagem = f"Validações reprovadas: {'; '.join(falhas)}"
        relatorio["resumo"]["falha"] += 1
        log.warning(f"    ✘ {status} — {mensagem}")
    elif avisos:
        status   = "AVISO"
        mensagem = f"Avisos: {'; '.join(avisos)}"
        relatorio["resumo"]["aviso"] += 1
        log.warning(f"    ⚠  {status} — {mensagem}")
    else:
        status   = "OK"
        mensagem = "Todas as validações passaram."
        relatorio["resumo"]["ok"] += 1
        log.info(f"    ✔ {status} — {mensagem}")
 
    relatorio["resultados"][nome] = {
        "status"  : status,
        "mensagem": mensagem,
        "detalhes": detalhes,
    }
 
 
def _imprimir_relatorio(relatorio: dict) -> None:
    """Imprime um relatório formatado no log."""
    log.info("══════════════════════════════════")
    log.info("  RELATÓRIO DE TESTES             ")
    log.info("══════════════════════════════════")
    for nome, res in relatorio["resultados"].items():
        icone = {"OK": "✔", "FALHA": "✘", "AVISO": "⚠"}.get(res["status"], "?")
        log.info(f"  {icone}  {nome:<30} [{res['status']}]")
        if res.get("detalhes"):
            for k, v in res["detalhes"].items():
                log.info(f"       • {k}: {v}")
    r = relatorio["resumo"]
    log.info("──────────────────────────────────")
    log.info(f"  Total: {r['total']}  |  OK: {r['ok']}  |  Falha: {r['falha']}  |  Aviso: {r['aviso']}")
    log.info("══════════════════════════════════")
 
# ═════════════════════════════════════════════════════════════════
#  PONTO DE ENTRADA DIRETO
# ═════════════════════════════════════════════════════════════════
 
if __name__ == "__main__":
    import sys
 
    args = sys.argv[1:]
 
    if "teste" in args:
        resultado = teste()
        sys.exit(0 if resultado["resumo"]["falha"] == 0 else 1)
 
    elif "b3" in args:
        ativos = buscar_ativos_b3()
        print(f"\nTotal de ativos B3: {len(ativos)}")
        print("Primeiros 5:", json.dumps(ativos[:5], ensure_ascii=False, indent=2))
 
    elif "cripto" in args:
        resultado = buscar_cripto_bybit()
        print(f"\nSPOT   : {len(resultado['spot'])} pares")
        print(f"FUTUROS: {len(resultado['futuros'])} contratos")
        print("Primeiros 3 SPOT:", json.dumps(resultado["spot"][:3], ensure_ascii=False, indent=2))
 
    else:
        print("\nUso:  python orquestrador.py [b3 | cripto | teste]\n")
        print("  b3     → busca todos os ativos da B3")
        print("  cripto → busca todos os pares/contratos da Bybit")
        print("  teste  → executa a suite de testes completa")
 
