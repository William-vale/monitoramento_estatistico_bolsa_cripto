# 📚 Guia de Uso - Orquestrador de Dados

## O que cada função faz?

### 1️⃣ `buscar_ativos_b3()`

**Objetivo**: Buscar TODOS os ativos da bolsa de valores brasileira (B3)

**O que ela retorna?**
- Uma lista com todos os ativos da B3 (Ações, FIIs, ETFs, BDRs, Derivativos)
- Cada ativo tem as informações:
  - `ticker`: código da ação (ex: PETR4)
  - `ticker_yf`: ticker para usar no Yahoo Finance (ex: PETR4.SA)
  - `nome`: nome da empresa/fundo
  - `segmento`: qual tipo de ativo é (Ações, FII, etc)
  - `tipo`: descrição mais amigável
  - `ativo`: se o ativo está ativo ou não

**Onde os dados são salvos?**
- Arquivo: `backend/TRADE_B3/ativos_b3.json`

---

### 2️⃣ `buscar_cripto_bybit()`

**Objetivo**: Buscar TODAS as criptomoedas disponíveis na Bybit

**O que ela retorna?**
- Um dicionário com duas listas:
  - `spot`: pares para compra/venda imediata (ex: BTC/USDT)
  - `futuros`: contratos perpétuos e futuros (ex: BTC/USDT:USDT)
- Cada criptomoeda tem as informações:
  - `symbol`: nome do par/contrato
  - `base`: moeda base (ex: BTC)
  - `quote`: moeda cotada (ex: USDT)
  - `tipo`: "spot" ou "future"
  - `ativo`: se está disponível
  - `settlement`: moeda de liquidação
  - `expiracao`: data de expiração (se houver)

**Onde os dados são salvos?**
- Arquivo SPOT: `backend/TRADE_CRIPTO/bybit_spot.json`
- Arquivo FUTUROS: `backend/TRADE_CRIPTO/bybit_futuros.json`

---

### 3️⃣ `teste()`

**Objetivo**: Testar se as duas funções acima estão funcionando corretamente

**O que ela faz?**
- Executa as funções `buscar_ativos_b3()` e `buscar_cripto_bybit()`
- Verifica se retornaram dados válidos
- Mostra um relatório final

---

## 🚀 Como Usar?

### **Instalação das dependências**

Abra o terminal na pasta do projeto e execute:

```bash
pip install requests ccxt
```

Isso vai instalar as bibliotecas necessárias.

---

### **Opção 1: Buscar apenas ativos da B3**

```bash
python backend/orquestrador.py b3
```

**Resultado esperado:**
- Total de ativos B3: 8500+ (aprox)
- Os dados serão salvos em `backend/TRADE_B3/ativos_b3.json`

---

### **Opção 2: Buscar apenas criptomoedas da Bybit**

```bash
python backend/orquestrador.py cripto
```

**Resultado esperado:**
- SPOT: ~800+ pares
- FUTUROS: ~1500+ contratos
- Os dados serão salvos em:
  - `backend/TRADE_CRIPTO/bybit_spot.json`
  - `backend/TRADE_CRIPTO/bybit_futuros.json`

---

### **Opção 3: Executar os testes**

```bash
python backend/orquestrador.py teste
```

**Resultado esperado:**
- Ambas as funções são executadas
- Testes verificam se os dados são válidos
- Relatório mostrando status: ✓ OK ou ✗ FALHA

---

## 📂 Estrutura dos arquivos gerados

Após executar os comandos, a pasta `backend/` terá esta estrutura:

```
backend/
├── orquestrador.py
├── TRADE_B3/
│   └── ativos_b3.json           ← Ativos da B3
├── TRADE_CRIPTO/
│   ├── bybit_spot.json          ← Pares spot
│   └── bybit_futuros.json       ← Contratos futuros
└── ATIVO_LONGO_PRAZO/           ← (vazio por enquanto)
```

---

## 📋 Exemplo de dados retornados

### Ativo B3 (exemplo):

```json
{
  "ticker": "PETR4",
  "ticker_yf": "PETR4.SA",
  "nome": "PETROBRÁS - PETRÓLEO BRASILEIRO",
  "segmento": "ACOES",
  "tipo": "Ações",
  "ativo": true
}
```

### Criptomoeda Bybit SPOT (exemplo):

```json
{
  "symbol": "BTC/USDT",
  "base": "BTC",
  "quote": "USDT",
  "tipo": "spot",
  "contrato": "BTCUSDT",
  "ativo": true,
  "settlement": "",
  "expiracao": null
}
```

### Criptomoeda Bybit FUTUROS (exemplo):

```json
{
  "symbol": "BTC/USDT:USDT",
  "base": "BTC",
  "quote": "USDT",
  "tipo": "linear",
  "contrato": "BTCUSDT",
  "ativo": true,
  "settlement": "USDT",
  "expiracao": null
}
```

---

## ⚠️ Dicas Importantes

1. **Primeira execução pode demorar**: A primeira vez que rodar `b3` ou `cripto` pode levar alguns minutos, porque está fazendo download de MUITOS dados.

2. **Não é necessário salvar em JSON**: As funções têm um parâmetro `salvar_json=True` por padrão. Se você quiser apenas retornar os dados sem salvar em arquivo, chame assim:

```python
from backend.orquestrador import buscar_ativos_b3
ativos = buscar_ativos_b3(salvar_json=False)
print(f"Total: {len(ativos)} ativos")
```

3. **Usar em Python diretamente**:

```python
from backend.orquestrador import buscar_ativos_b3, buscar_cripto_bybit

# Buscar B3
ativos_b3 = buscar_ativos_b3()
print(f"Ativos B3: {len(ativos_b3)}")

# Buscar Bybit
cripto = buscar_cripto_bybit()
print(f"SPOT: {len(cripto['spot'])}")
print(f"FUTUROS: {len(cripto['futuros'])}")
```

---

## 📝 Próximos Passos

Agora que você tem os dados:

- **Frontend**: Você pode criar interfaces para visualizar estes dados
- **Análise**: Você pode processar estes dados para gerar análises
- **Filtros**: Você pode filtrar por tipo, segmento, etc.

Boa sorte! 🚀
