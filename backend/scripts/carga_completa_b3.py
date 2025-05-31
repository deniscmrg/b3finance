# backend/scripts/carga_completa_b3.py

from decimal import Decimal
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
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

def carregar_lista_tickers():
    with open(r"C:\b3analise\tickersb3.txt", "r") as f:
        tickers = [linha.strip() + ".SA" for linha in f if linha.strip()]
    return tickers

def safe_decimal(value):
    try:
        if pd.isna(value) or value in [None, '', '-', 'nan', 'NaN', float('inf'), float('-inf')]:
            return None
        return Decimal(str(value))
    except:
        return None

def carregar_cotacoes():
    tickers = carregar_lista_tickers()
    hoje = datetime.today()
    inicio = hoje - timedelta(days=2500)

    for ticker in tickers:
        try:
            print(f"\n📥 Processando {ticker}...")
            acao, _ = Acao.objects.get_or_create(ticker=ticker.replace('.SA', ''))

            # df = yf.download(ticker, start=inicio.strftime('%Y-%m-%d'), end=hoje.strftime('%Y-%m-%d'))

            df = yf.download(ticker, start=inicio.strftime('%Y-%m-%d'), end=hoje.strftime('%Y-%m-%d'), group_by="ticker")

            # Corrige colunas se vierem com MultiIndex
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(0)

            if df.empty:
                print(f"⚠️  Sem dados: {ticker}")
                continue

            for data, row in df.iterrows():
                try:
                    print(row)
                    if pd.isna(row[['Open', 'Close', 'Low', 'High', 'Volume']]).any():
                        continue

                    abertura = safe_decimal(row['Open'])
                    fechamento = safe_decimal(row['Close'])
                    minima = safe_decimal(row['Low'])
                    maxima = safe_decimal(row['High'])
                    volume = int(row['Volume']) if pd.notna(row['Volume']) else 0

                    if None in [abertura, fechamento, minima, maxima]:
                        continue

                    Cotacao.objects.update_or_create(
                        acao=acao,
                        data=data.date(),
                        defaults={
                            'abertura': abertura,
                            'fechamento': fechamento,
                            'minima': minima,
                            'maxima': maxima,
                            'volume': volume
                        }
                    )
                    print(f"✔️  {ticker} - {data.date()} salva")
                except Exception as e:
                    print(f"❌ Erro ao salvar {ticker} ({data.date()}): {e}")

        except Exception as e:
            print(f"❌ Erro ao processar {ticker}: {e}")
            continue

if __name__ == '__main__':
    carregar_cotacoes()
