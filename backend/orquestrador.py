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

import json
import time
import base64
import logging
import requests
import ccxt
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------
# Configuração de LOG
# ----------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
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
    Busca todos os ativos listados na B3 usando a API pública.
    
    A função pagina automaticamente até obter todos os ativos disponíveis
    e formata os dados em um padrão consistente.
 
    Parâmetros ----------
    salvar_json : bool
        Se True, salva o resultado em TRADE_B3/ativos_b3.json
 
    Retorno -------
    list[dict]  — lista com os campos:
        {
            "ticker"       : str   # ex.: "PETR4"
            "ticker_yf"    : str   # ex.: "PETR4.SA"
            "nome"         : str   # nome da empresa/fundo
            "segmento"     : str   # classificação B3
            "tipo"         : str   # descrição amigável
            "ativo"        : bool
        }
    """
    global B3_ATIVOS

    log.info("🔄 Iniciando busca de ativos da B3...")
    
    ativos: list[dict] = []
    vistos: set[str] = set()  # para evitar duplicatas
    pagina = 1

    while True:
        try:
            # Monta a requisição para a API da B3
            payload = json.dumps({"language": "pt-br", "pageNumber": pagina, "pageSize": B3_PAGE_SIZE})
            token = base64.b64decode(payload.encode().decode())
            url = f"{B3_BASE_URL}/{token}"
            
            resp = requests.get(url, timeout=B3_TIMEOUT)
            resp.raise_for_status()
            dados = resp.json()
            
        except requests.exceptions.RequestException as e:
            log.error(f"Erro ao buscar página {pagina}: {e}")
            break

        empresas = dados.get("results", [])
        
        # Se não há empresas, chegou ao final
        if not empresas:
            log.info(f"✓ Fim da paginação na página {pagina}")
            break

        # Processa cada empresa
        for empresa in empresas:
            codigos = empresa.get("codes", [empresa.get("code", "")])
            if isinstance(codigos, str):
                codigos = [codigos]
 
            for cod in codigos:
                if not cod or cod in vistos:
                    continue
                    
                vistos.add(cod)
                segmento = empresa.get("segment", "").upper().replace(" ", "-")
                
                ativos.append({
                    "ticker"    : cod.strip(),
                    "ticker_yf" : f"{cod.strip()}.SA",
                    "nome"      : empresa.get("companyName", "").strip(),
                    "segmento"  : segmento,
                    "tipo"      : B3_SEGMENT_MAP.get(segmento, "Desconhecido"),
                    "ativo"     : True,
                })

        log.info(f"  Página {pagina}: {len(empresas)} empresa(s) → Total: {len(ativos)} ativos")
        pagina += 1
        time.sleep(B3_DELAY)

    B3_ATIVOS = ativos
    log.info(f"✅ Total de ativos B3: {len(B3_ATIVOS)}")

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
    Busca todos os pares/contratos disponíveis na Bybit (SPOT e FUTUROS).
    
    A função se conecta à exchange através da biblioteca ccxt e classifica
    automaticamente cada mercado como SPOT, SWAP (perpétuo) ou FUTURE.
 
    Parâmetros ----------
    salvar_json : bool
        Se True, salva em arquivos JSON separados para SPOT e FUTUROS
 
    Retorno -------
    dict com estrutura:
        {
            "spot"    : [ {...}, {...} ],
            "futuros" : [ {...}, {...} ]
        }
        
    Cada item contém:
        {
            "symbol"       : str   # ex.: "BTC/USDT"
            "base"         : str   # ex.: "BTC"
            "quote"        : str   # ex.: "USDT"
            "tipo"         : str   # "spot" | "swap" | "future"
            "contrato"     : str   # ID do contrato
            "ativo"        : bool
            "settlement"   : str   # moeda de liquidação
            "expiracao"    : str | None
        }
    """
    global BYBIT_SPOT, BYBIT_FUTUROS
 
    log.info("🔄 Buscando criptomoedas da Bybit (SPOT + FUTUROS)...")
 
    spot_list: list[dict] = []
    futuros_list: list[dict] = []
 
    try:
        # Conecta à exchange
        exchange = ccxt.bybit({"enableRateLimit": True})
        
        # Carrega todos os mercados
        log.info("  Carregando mercados da Bybit...")
        mercados = exchange.load_markets(reload=True)
        log.info(f"  Total de mercados retornados: {len(mercados)}")
        
    except Exception as exc:
        log.error(f"Erro ao conectar com Bybit: {exc}")
        return {"spot": [], "futuros": []}
 
    # Classifica cada mercado em SPOT ou FUTUROS
    for symbol, market in mercados.items():
        is_spot   = market.get("spot", False)
        is_swap   = market.get("swap", False)
        is_future = market.get("future", False)
 
        entrada = {
            "symbol"     : symbol,
            "base"       : market.get("base", ""),
            "quote"      : market.get("quote", ""),
            "tipo"       : market.get("type", "desconhecido"),
            "contrato"   : market.get("id", symbol),
            "ativo"      : market.get("active", True),
            "settlement" : market.get("settle", ""),
            "expiracao"  : market.get("expiry", None),
        }
 
        if is_spot:
            spot_list.append(entrada)
        elif is_swap or is_future:
            futuros_list.append(entrada)
 
    BYBIT_SPOT    = spot_list
    BYBIT_FUTUROS = futuros_list
 
    log.info(f"✅ SPOT    : {len(BYBIT_SPOT)} pares")
    log.info(f"✅ FUTUROS : {len(BYBIT_FUTUROS)} contratos")
 
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
    Executa um teste completo de todas as funções do orquestrador.
    
    ⚠️ As funções são totalmente independentes — cada uma pode ser
       chamada diretamente sem precisar desta função de teste.
 
    Retorno -------
    dict — relatório com o resultado de cada teste
    """
    log.info("\n" + "="*50)
    log.info("  ▶ INICIANDO TESTES DO ORQUESTRADOR")
    log.info("="*50 + "\n")
 
    relatorio: dict = {
        "timestamp" : _agora(),
        "resultados": {},
        "resumo"    : {"total": 0, "ok": 0, "falha": 0},
    }
 
    # Teste 1: B3
    _teste_funcao(
        relatorio  = relatorio,
        nome       = "buscar_ativos_b3",
        funcao     = buscar_ativos_b3,
        kwargs     = {"salvar_json": True},
        validacoes = [
            ("Retorna lista",        lambda r: isinstance(r, list)),
            ("Lista não vazia",      lambda r: len(r) > 0),
            ("Tem campo 'ticker'",   lambda r: all("ticker" in x for x in r[:3])),
            ("Tem campo 'ticker_yf'",lambda r: all("ticker_yf" in x for x in r[:3])),
        ],
    )
 
    # Teste 2: Bybit
    _teste_funcao(
        relatorio  = relatorio,
        nome       = "buscar_cripto_bybit",
        funcao     = buscar_cripto_bybit,
        kwargs     = {"salvar_json": True},
        validacoes = [
            ("Retorna dict",         lambda r: isinstance(r, dict)),
            ("Tem chave 'spot'",     lambda r: "spot" in r),
            ("Tem chave 'futuros'",  lambda r: "futuros" in r),
            ("SPOT não vazio",       lambda r: len(r.get("spot", [])) > 0),
            ("FUTUROS não vazio",    lambda r: len(r.get("futuros", [])) > 0),
        ],
    )
 
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
 
 
def _teste_funcao(relatorio: dict, nome: str, funcao, kwargs: dict, validacoes: list) -> None:
    """
    Executa uma função e valida o resultado.
    
    Registra o status (OK/FALHA) no relatório de testes.
    """
    log.info(f"  Testando: {nome}")
    relatorio["resumo"]["total"] += 1
 
    try:
        resultado = funcao(**kwargs)
    except Exception as exc:
        relatorio["resultados"][nome] = {
            "status"  : "FALHA",
            "mensagem": f"Erro: {type(exc).__name__}: {exc}",
            "detalhes": {},
        }
        relatorio["resumo"]["falha"] += 1
        log.error(f"    ✘ Erro na execução: {exc}")
        return
 
    falhas = []
    detalhes = {}
 
    # Valida cada critério
    for descricao, validacao in validacoes:
        try:
            passou = validacao(resultado)
            detalhes[descricao] = "✓" if passou else "✗"
            if not passou:
                falhas.append(descricao)
        except Exception as e:
            detalhes[descricao] = f"erro: {e}"
            falhas.append(descricao)
 
    # Adiciona informações extras
    if isinstance(resultado, list):
        detalhes["total_itens"] = len(resultado)
    elif isinstance(resultado, dict):
        for k, v in resultado.items():
            if isinstance(v, list):
                detalhes[f"total_{k}"] = len(v)
 
    if falhas:
        status = "FALHA"
        relatorio["resumo"]["falha"] += 1
        log.error(f"    ✘ {', '.join(falhas)}")
    else:
        status = "OK"
        relatorio["resumo"]["ok"] += 1
        log.info(f"    ✓ Todas as validações passaram")
 
    relatorio["resultados"][nome] = {
        "status"  : status,
        "detalhes": detalhes,
    }
 
 
def _imprimir_relatorio(relatorio: dict) -> None:
    """Imprime o relatório de testes formatado."""
    log.info("\n" + "="*50)
    log.info("  RELATÓRIO FINAL")
    log.info("="*50)
    
    for nome, res in relatorio["resultados"].items():
        icone = "✓" if res["status"] == "OK" else "✗"
        log.info(f"  {icone} {nome}: {res['status']}")
        
    r = relatorio["resumo"]
    log.info("─"*50)
    log.info(f"  Total: {r['total']} | OK: {r['ok']} | Falha: {r['falha']}")
    log.info("="*50 + "\n")
 
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
        if ativos:
            print("Primeiros 3:", json.dumps(ativos[:3], ensure_ascii=False, indent=2))

    elif "cripto" in args:
        resultado = buscar_cripto_bybit()
        print(f"\nSPOT   : {len(resultado['spot'])} pares")
        print(f"FUTUROS: {len(resultado['futuros'])} contratos")
        if resultado["spot"]:
            print("Primeiros 2 SPOT:", json.dumps(resultado["spot"][:2], ensure_ascii=False, indent=2))

    else:
        print("\n" + "="*60)
        print("USO:  python orquestrador.py [comando]")
        print("="*60)
        print("\nComandos disponíveis:")
        print("  b3     → Busca todos os ativos da B3 e salva em JSON")
        print("  cripto → Busca todos os pares/contratos da Bybit e salva em JSON")
        print("  teste  → Executa testes em todas as funções")
        print("\n")
