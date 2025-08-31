from decimal import Decimal
import requests
import pandas as pd
from datetime import timedelta
import os
import sys

# Caminho absoluto da pasta raiz do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Aponta para o settings.py correto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from cotacoes.models import Acao, Cotacao


def get_dia_util(offset=0):
    hoje = pd.Timestamp.today(tz='America/Sao_Paulo').normalize()
    dias_uteis = pd.date_range(end=hoje, periods=700, freq='B').to_list()

    index = -1 + offset  # offset 0 -> ontem (último dia útil), -1 -> anteontem
    if abs(index) >= len(dias_uteis):
        raise ValueError("Offset fora do intervalo de dias úteis")

    return dias_uteis[index].date()


def buscar_cotacao_brapi(ticker):
    url = f"https://brapi.dev/api/quote/{ticker}?range=1d&interval=1d"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Erro {response.status_code} na API Brapi para {ticker}")
            return None
        dados = response.json()
        resultados = dados.get("results", [])
        if not resultados:
            print(f"⚠️ Nenhum dado retornado pela Brapi para {ticker}")
            return None

        r = resultados[0]
        return {
            'abertura': Decimal(str(r.get("open", 0) or 0)),
            'fechamento': Decimal(str(r.get("regularMarketPrice", 0) or 0)),
            'minima': Decimal(str(r.get("low", 0) or 0)),
            'maxima': Decimal(str(r.get("high", 0) or 0)),
            'volume': int(r.get("volume", 0) or 0)
        }
    except Exception as e:
        print(f"❌ Erro na Brapi para {ticker}: {e}")
        return None


def atualizar_cotacoes_brapi(dia_offset):
    data = get_dia_util(dia_offset)
    acoes = Acao.objects.all()

    for acao in acoes:
        print(f"\n📥 Buscando {acao.ticker} via Brapi para {data}...")

        if Cotacao.objects.filter(acao=acao, data=data).exists():
            print(f"✔️ Cotação de {acao.ticker} em {data} já está salva")
            continue

        dados = buscar_cotacao_brapi(acao.ticker)
        if not dados:
            continue

        if any(v == 0 for v in dados.values()):
            print(f"⚠️ Dados inválidos para {acao.ticker}: {dados}")
            continue

        Cotacao.objects.update_or_create(
            acao=acao,
            data=data,
            defaults=dados
        )
        print(f"✅ Cotação de {acao.ticker} salva com sucesso")


if __name__ == '__main__':
    DIA_OFFSET = 0  # 0 = ontem (último pregão)
    atualizar_cotacoes_brapi(DIA_OFFSET)
