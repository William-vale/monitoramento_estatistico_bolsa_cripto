# 📖 EXPLICAÇÃO PASSO A PASSO DO CÓDIGO

## 1. IMPORTS E CONFIGURAÇÕES INICIAIS

```python
import json, time, base64, logging, requests, ccxt
from datetime import datetime
from pathlib import Path
```

**O que cada um faz?**

- `json` → Para ler/escrever arquivos JSON
- `time` → Para pausar entre requisições (não sobrecarregar API)
- `base64` → Para codificar a requisição da API B3
- `logging` → Para imprimir mensagens legais no terminal
- `requests` → Para fazer requisições HTTP (falar com API B3)
- `ccxt` → Biblioteca para acessar várias exchanges de cripto
- `datetime` → Para registrar hora/data
- `Path` → Para trabalhar com caminhos de arquivos de forma segura

---

## 2. CONFIGURAÇÃO DE LOGS

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
)
log = logging.getLogger("orquestrador")
```

**O que faz?**

- Configura como as mensagens aparecem no terminal
- `level=INFO` → Mostra mensagens informativas e erros
- `format` → Define o padrão: `[hora] [tipo] mensagem`
- `log.info()` → Imprime mensagens informativas
- `log.error()` → Imprime erros

**Exemplo de saída:**
```
21-05-2026 14:30:45 [INFO] 🔄 Iniciando busca de ativos da B3...
21-05-2026 14:30:47 [INFO] ✅ Total de ativos B3: 8500
```

---

## 3. CAMINHOS DOS DIRETÓRIOS

```python
BASE_DIR = Path(__file__).resolve().parent  # Pasta do script
TRADE_B3_DIR = BASE_DIR / "TRADE_B3"
TRADE_CRIPTO_DIR = BASE_DIR / "TRADE_CRIPTO"
LONGO_PRAZO_DIR = BASE_DIR / "ATIVO_LONGO_PRAZO"

for _dir in (TRADE_B3_DIR, TRADE_CRIPTO_DIR, LONGO_PRAZO_DIR): 
    _dir.mkdir(parents=True, exist_ok=True)
```

**O que faz?**

- `Path(__file__)` → Pega o caminho do arquivo atual
- `.resolve().parent` → Pega a pasta onde o arquivo está
- `/` → Cria caminhos combinando pastas
- `mkdir()` → Cria as pastas se não existirem

**Resultado:**
```
backend/
  ├── TRADE_B3/
  ├── TRADE_CRIPTO/
  └── ATIVO_LONGO_PRAZO/
```

---

## 4. LISTAS GLOBAIS

```python
B3_ATIVOS: list[dict] = []
BYBIT_SPOT: list[dict] = []
BYBIT_FUTUROS: list[dict] = []
```

**O que são?**

- Variáveis que armazenam os dados buscados
- `list[dict]` → É uma lista com dicionários
- Inicializadas vazias, são preenchidas pelas funções

**Exemplo de conteúdo:**
```python
B3_ATIVOS = [
    {"ticker": "PETR4", "nome": "PETROBRÁS", ...},
    {"ticker": "VALE3", "nome": "VALE", ...},
]
```

---

## 5. CONSTANTES DA API B3

```python
B3_BASE_URL = "https://sistemaswebb3-listados.fnet.com.br/..."
B3_PAGE_SIZE = 120  # Máximo por página
B3_TIMEOUT = 15     # Segundos até dar timeout
B3_DELAY = 0.3      # Pausa entre páginas
```

**O que cada uma faz?**

- `BASE_URL` → Endereço da API
- `PAGE_SIZE` → Quantos ativos por página (B3 aceita máx 120)
- `TIMEOUT` → Tempo máximo para resposta (evita travamento)
- `DELAY` → Espera entre requisições (respeita a API)

---

## 6. MAPA DE SEGMENTOS B3

```python
B3_SEGMENT_MAP = {
    "ACOES": "Ações",
    "FII": "Fundo Imobiliário (FII)",
    "ETF-RENDA-VARIAVEL": "ETF Renda Variável",
    ...
}
```

**O que faz?**

Converte códigos da API em descrições legíveis:
- API retorna: `"ACOES"` 
- Convertemos para: `"Ações"`

---

## 7. FUNÇÃO: BUSCAR ATIVOS B3

```python
def buscar_ativos_b3(salvar_json: bool = True) -> list[dict]:
```

**O que significa?**

- `def` → Define uma função
- `salvar_json: bool = True` → Parâmetro com padrão (True)
- `-> list[dict]` → Retorna uma lista de dicionários

### Passo 1: Loop de Paginação

```python
ativos: list[dict] = []  # Lista vazia
vistos: set[str] = set()  # Conjunto para evitar duplicatas
pagina = 1  # Começa na página 1

while True:  # Loop infinito (até quebrar)
```

**O que faz?**

- Cria lista para armazenar ativos
- `set()` é mais rápido para verificar duplicatas que listas
- Loop paginado (vai de página em página)

### Passo 2: Montar Requisição

```python
payload = json.dumps({"language": "pt-br", "pageNumber": pagina, "pageSize": B3_PAGE_SIZE})
token = base64.b64decode(payload.encode().decode())
url = f"{B3_BASE_URL}/{token}"
```

**O que faz?**

- Cria um dicionário com os parâmetros
- Converte para JSON
- Codifica em base64 (API B3 exige isso)
- Adiciona à URL

### Passo 3: Fazer Requisição HTTP

```python
resp = requests.get(url, timeout=B3_TIMEOUT)
resp.raise_for_status()
dados = resp.json()
```

**O que faz?**

- `requests.get()` → Faz requisição GET
- `raise_for_status()` → Lança erro se status != 200-299
- `resp.json()` → Converte resposta em dicionário

### Passo 4: Processar Dados

```python
empresas = dados.get("results", [])

if not empresas:
    log.info(f"Fim da paginação na página {pagina}")
    break
```

**O que faz?**

- Extrai lista de empresas da resposta
- Se não há empresas, para o loop (chegou ao final)

### Passo 5: Adicionar Ativos à Lista

```python
for empresa in empresas:
    codigos = empresa.get("codes", [empresa.get("code", "")])
    
    for cod in codigos:
        if not cod or cod in vistos:
            continue
        
        vistos.add(cod)
        segmento = empresa.get("segment", "").upper().replace(" ", "-")
        
        ativos.append({
            "ticker": cod.strip(),
            "ticker_yf": f"{cod.strip()}.SA",
            "nome": empresa.get("companyName", "").strip(),
            "segmento": segmento,
            "tipo": B3_SEGMENT_MAP.get(segmento, "Desconhecido"),
            "ativo": True,
        })
```

**O que faz?**

- Para cada empresa:
  - Pega lista de códigos (um ativo pode ter múltiplos)
  - Para cada código:
    - Verifica se já foi visto (pula duplicata)
    - Marca como visto
    - Formata segmento (ACOES → ACOES)
    - Cria dicionário com dados
    - Adiciona à lista

### Passo 6: Próxima Página

```python
log.info(f"Página {pagina}: {len(empresas)} empresa(s) → Total: {len(ativos)} ativos")
pagina += 1
time.sleep(B3_DELAY)
```

**O que faz?**

- Loga progresso
- Incrementa número da página
- Pausa 0.3 segundos (respeita API)

### Passo 7: Salvar em JSON

```python
B3_ATIVOS = ativos

if salvar_json:
    _salvar_json(
        dados     = {"atualizado_em": _agora(), "total": len(B3_ATIVOS), "ativos": B3_ATIVOS},
        caminho   = TRADE_B3_DIR / "ativos_b3.json",
        descricao = "ativos B3",
    )

return B3_ATIVOS
```

**O que faz?**

- Atribui dados à variável global
- Se `salvar_json=True`, salva em arquivo JSON
- Retorna a lista

---

## 8. FUNÇÃO: BUSCAR CRIPTO BYBIT

```python
def buscar_cripto_bybit(salvar_json: bool = True) -> dict[str, list[dict]]:
```

**Estrutura similar à B3, mas:**

### Conectar à Exchange

```python
exchange = ccxt.bybit({"enableRateLimit": True})
mercados = exchange.load_markets(reload=True)
```

**O que faz?**

- Cria conexão com Bybit via CCXT
- Carrega todos os mercados (símbolos, informações, etc)
- `reload=True` força download dos dados mais recentes

### Classificar Mercados

```python
for symbol, market in mercados.items():
    is_spot   = market.get("spot", False)
    is_swap   = market.get("swap", False)
    is_future = market.get("future", False)
    
    entrada = {
        "symbol": symbol,
        "base": market.get("base", ""),
        "quote": market.get("quote", ""),
        ...
    }
    
    if is_spot:
        spot_list.append(entrada)
    elif is_swap or is_future:
        futuros_list.append(entrada)
```

**O que faz?**

- Para cada mercado na exchange:
  - Verifica se é SPOT, SWAP ou FUTURE
  - Cria dicionário com dados
  - Adiciona à lista correta

---

## 9. FUNÇÕES AUXILIARES

### _agora()

```python
def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

**O que faz?**

- Retorna a hora/data atual formatada
- Exemplo: `"2026-05-21 14:30:45"`

### _salvar_json()

```python
def _salvar_json(dados: dict, caminho: Path, descricao: str = "") -> None:
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        log.info(f"  💾 {descricao} salvo em: {caminho}")
    except OSError as exc:
        log.error(f"  Falha ao salvar {descricao}: {exc}")
```

**O que faz?**

- Abre arquivo em modo escrita
- Salva dicionário como JSON formatado
- Se erro, loga mensagem de erro
- `ensure_ascii=False` → Permite caracteres especiais (acentos)
- `indent=2` → Indenta para ler melhor

**Resultado:**
```json
{
  "atualizado_em": "2026-05-21 14:30:45",
  "total": 8500,
  "ativos": [...]
}
```

### _teste_funcao()

```python
def _teste_funcao(relatorio: dict, nome: str, funcao, kwargs: dict, validacoes: list) -> None:
```

**O que faz?**

- Executa uma função
- Aplica validações (checagens)
- Registra resultado no relatório

**Fluxo:**
1. Tenta executar a função com os parâmetros
2. Para cada validação:
   - Executa a validação
   - Se passou: marca como ✓
   - Se falhou: marca como ✗ e adiciona a falhas
3. Registra resultado no relatório

---

## 10. PONTO DE ENTRADA (main)

```python
if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
```

**O que faz?**

- `if __name__ == "__main__"` → Só executa se for rodado direto (não importado)
- `sys.argv[1:]` → Pega argumentos da linha de comando

### Comando: teste

```python
if "teste" in args:
    resultado = teste()
    sys.exit(0 if resultado["resumo"]["falha"] == 0 else 1)
```

**O que faz?**

- Executa função teste()
- Se falhou alguma coisa: `exit(1)` (erro)
- Se tudo ok: `exit(0)` (sucesso)

---

## 🎯 RESUMO DO FLUXO COMPLETO

```
python backend/orquestrador.py teste
        ↓
    → Executa teste()
        ↓
    → Chama buscar_ativos_b3()
        ├─ Faz paginação na API B3
        ├─ Coleta 8500+ ativos
        └─ Salva em TRADE_B3/ativos_b3.json
        ↓
    → Chama buscar_cripto_bybit()
        ├─ Conecta em CCXT Bybit
        ├─ Coleta SPOT + FUTUROS
        ├─ Salva em TRADE_CRIPTO/bybit_spot.json
        └─ Salva em TRADE_CRIPTO/bybit_futuros.json
        ↓
    → Valida os dados
    → Imprime relatório
        ↓
    → exit(0) se sucesso
```

---

Pronto! Agora você entende cada linha do código! 🚀
