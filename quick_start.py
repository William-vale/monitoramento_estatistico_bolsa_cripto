#!/usr/bin/env python3
"""
🚀 QUICK START - Exemplo de como usar o orquestrador

Este arquivo mostra exemplos práticos de como usar as funções
do orquestrador em seu próprio código.

Uso:
    python quick_start.py
"""

# Importar as funções do orquestrador
from backend.orquestrador import buscar_ativos_b3, buscar_cripto_bybit, teste
import json

print("\n" + "="*60)
print("  🚀 QUICK START - EXEMPLOS DE USO")
print("="*60 + "\n")

# ════════════════════════════════════════════════════════════════
# EXEMPLO 1: Buscar ativos da B3
# ════════════════════════════════════════════════════════════════

print("1️⃣  BUSCANDO ATIVOS DA B3...")
print("-" * 60)

try:
    ativos_b3 = buscar_ativos_b3(salvar_json=True)
    
    print(f"\n✅ Ativos coletados: {len(ativos_b3)}")
    
    # Mostrar alguns exemplos
    print("\n📋 Primeiros 3 ativos:")
    for i, ativo in enumerate(ativos_b3[:3], 1):
        print(f"\n  {i}. {ativo['nome']}")
        print(f"     Ticker: {ativo['ticker']}")
        print(f"     Tipo: {ativo['tipo']}")
        print(f"     Segmento: {ativo['segmento']}")
    
    # Contar por tipo
    tipos = {}
    for ativo in ativos_b3:
        tipo = ativo['tipo']
        tipos[tipo] = tipos.get(tipo, 0) + 1
    
    print("\n📊 Ativos por tipo:")
    for tipo, count in sorted(tipos.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   • {tipo}: {count}")

except Exception as e:
    print(f"❌ Erro: {e}")

# ════════════════════════════════════════════════════════════════
# EXEMPLO 2: Buscar criptomoedas da Bybit
# ════════════════════════════════════════════════════════════════

print("\n\n2️⃣  BUSCANDO CRIPTOMOEDAS DA BYBIT...")
print("-" * 60)

try:
    cripto = buscar_cripto_bybit(salvar_json=True)
    
    spot = cripto['spot']
    futuros = cripto['futuros']
    
    print(f"\n✅ SPOT: {len(spot)} pares")
    print(f"✅ FUTUROS: {len(futuros)} contratos")
    
    # Mostrar alguns pares SPOT
    print("\n📋 Primeiros 3 pares SPOT:")
    for i, par in enumerate(spot[:3], 1):
        print(f"\n  {i}. {par['symbol']}")
        print(f"     Base: {par['base']}")
        print(f"     Quote: {par['quote']}")
        print(f"     Ativo: {'Sim' if par['ativo'] else 'Não'}")
    
    # Mostrar alguns contratos FUTUROS
    print("\n📋 Primeiros 3 contratos FUTUROS:")
    for i, contrato in enumerate(futuros[:3], 1):
        print(f"\n  {i}. {contrato['symbol']}")
        print(f"     Base: {contrato['base']}")
        print(f"     Settlement: {contrato['settlement']}")
        print(f"     Ativo: {'Sim' if contrato['ativo'] else 'Não'}")
    
    # Contar moedas base
    bases_spot = {}
    for par in spot:
        base = par['base']
        bases_spot[base] = bases_spot.get(base, 0) + 1
    
    print("\n📊 Top 10 moedas mais comuns no SPOT:")
    for base, count in sorted(bases_spot.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   • {base}: {count} pares")

except Exception as e:
    print(f"❌ Erro: {e}")

# ════════════════════════════════════════════════════════════════
# EXEMPLO 3: Executar testes
# ════════════════════════════════════════════════════════════════

print("\n\n3️⃣  EXECUTANDO TESTES...")
print("-" * 60 + "\n")

try:
    resultado = teste()
    
    # Mostrar resumo
    resumo = resultado['resumo']
    print(f"\n✅ Total de testes: {resumo['total']}")
    print(f"✅ Sucesso: {resumo['ok']}")
    if resumo['falha'] > 0:
        print(f"❌ Falhas: {resumo['falha']}")

except Exception as e:
    print(f"❌ Erro: {e}")

# ════════════════════════════════════════════════════════════════
# EXEMPLO 4: Filtrar e processar dados
# ════════════════════════════════════════════════════════════════

print("\n\n4️⃣  FILTRANDO E PROCESSANDO DADOS...")
print("-" * 60)

try:
    ativos_b3 = buscar_ativos_b3(salvar_json=False)
    
    # Filtrar apenas ações
    acoes = [a for a in ativos_b3 if a['tipo'] == 'Ações']
    print(f"\n📊 Total de ações: {len(acoes)}")
    
    # Filtrar apenas FIIs
    fiis = [a for a in ativos_b3 if 'FII' in a['tipo']]
    print(f"📊 Total de FIIs: {len(fiis)}")
    
    # Filtrar apenas ETFs
    etfs = [a for a in ativos_b3 if 'ETF' in a['tipo']]
    print(f"📊 Total de ETFs: {len(etfs)}")
    
    # Mostrar 5 ETFs aleatórios
    print("\n📋 Alguns ETFs disponíveis:")
    for etf in etfs[:5]:
        print(f"   • {etf['ticker']} - {etf['nome']}")

except Exception as e:
    print(f"❌ Erro: {e}")

# ════════════════════════════════════════════════════════════════
# EXEMPLO 5: Acessar dados dos arquivos JSON
# ════════════════════════════════════════════════════════════════

print("\n\n5️⃣  LENDO DADOS DOS ARQUIVOS JSON...")
print("-" * 60)

try:
    from pathlib import Path
    
    # Arquivo B3
    arquivo_b3 = Path("backend/TRADE_B3/ativos_b3.json")
    if arquivo_b3.exists():
        with open(arquivo_b3, 'r', encoding='utf-8') as f:
            dados_b3 = json.load(f)
        print(f"\n✅ Arquivo B3 carregado")
        print(f"   Data de atualização: {dados_b3['atualizado_em']}")
        print(f"   Total de ativos: {dados_b3['total']}")
    else:
        print(f"\n⚠️  Arquivo B3 não encontrado. Execute primeiro:")
        print(f"   python backend/orquestrador.py b3")
    
    # Arquivo Cripto SPOT
    arquivo_spot = Path("backend/TRADE_CRIPTO/bybit_spot.json")
    if arquivo_spot.exists():
        with open(arquivo_spot, 'r', encoding='utf-8') as f:
            dados_spot = json.load(f)
        print(f"\n✅ Arquivo Bybit SPOT carregado")
        print(f"   Data de atualização: {dados_spot['atualizado_em']}")
        print(f"   Total de pares: {dados_spot['total']}")
    else:
        print(f"\n⚠️  Arquivo Bybit não encontrado. Execute primeiro:")
        print(f"   python backend/orquestrador.py cripto")

except Exception as e:
    print(f"❌ Erro: {e}")

# ════════════════════════════════════════════════════════════════
# FIM
# ════════════════════════════════════════════════════════════════

print("\n" + "="*60)
print("  ✅ QUICK START CONCLUÍDO!")
print("="*60)
print("\n📚 Para mais informações, consulte:")
print("   • GUIA_DE_USO.md - Guia completo")
print("   • backend/EXPLICACAO_DETALHADA.md - Detalhes técnicos")
print("\n")
