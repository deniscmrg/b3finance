import os
import sys
import django
import pandas as pd
import numpy as np
import joblib
import yfinance as yf
from django.db.models import Max
from django.db import models
from decimal import Decimal
from datetime import date

# Configuração do Django
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from cotacoes.models import Cotacao
from cotacoes.models import RecomendacaoDiaria, Acao


def gerar_recomendacoes(top_n=30):
    ultima_data = Cotacao.objects.aggregate(ultima=Max('data'))['ultima']
    if not ultima_data:
        print("❌ Nenhuma data disponível.")
        return

    print(f"📅 Usando dados até: {ultima_data}")

    qs = Cotacao.objects.filter(
        data__lte=ultima_data,
        fechamento__lt=models.F('wma602'),
        wma17__isnull=False,
        wma34__isnull=False,
        obv__isnull=False,
        rsi_14__isnull=False,
        media_volume_20d__isnull=False,
        fechamento_anterior__isnull=False,
        atr__isnull=False,
        volume__gt=0
    ).values(
        'data', 'acao__ticker', 'fechamento', 'atr', 'wma602', 'wma17', 'wma34',
        'obv', 'rsi_14', 'volume', 'media_volume_20d', 'fechamento_anterior'
    )

    df = pd.DataFrame.from_records(qs)
    if df.empty:
        print("❌ Nenhuma ação elegível.")
        return

    # Conversão de campos numéricos para float
    campos_float = [
        'atr', 'wma602', 'wma17', 'wma34', 'obv', 'rsi_14',
        'volume', 'media_volume_20d', 'fechamento_anterior'
    ]
    df[campos_float] = df[campos_float].astype(float)

    df.sort_values(by=['acao__ticker', 'data'], inplace=True)
    df['obv_5d'] = df.groupby('acao__ticker')['obv'].shift(5)
    df = df[df['data'] == ultima_data].copy()
    df['obv_5d'] = df['obv_5d'].astype(float)

    for col in ['wma34', 'wma602', 'media_volume_20d', 'fechamento_anterior', 'obv_5d', 'atr']:
        df[col] = df[col].replace(0, np.nan)

    # Buscar o preço mais recente (intraday) via yfinance
    print("\n🔄 Buscando cotações intraday...")
    precos_atuais = {}
    for ticker in df['acao__ticker'].unique():
        try:
            yf_ticker = yf.Ticker(ticker + '.SA')
            preco_atual = yf_ticker.history(period="1d", interval="1m")['Close'].dropna()
            if not preco_atual.empty:
                precos_atuais[ticker] = preco_atual.iloc[-1]
            else:
                precos_atuais[ticker] = np.nan
        except Exception as e:
            print(f"Erro ao buscar {ticker}: {e}")
            precos_atuais[ticker] = np.nan

    df['preco_atual'] = df['acao__ticker'].map(precos_atuais)
    df.dropna(subset=['preco_atual'], inplace=True)
    df['preco_compra'] = df['preco_atual'].astype(float)

    # Recalcular os indicadores com base no preço atual
    df['fechamento_div_wma602'] = df['preco_compra'] / df['wma602']
    df['wma17_div_wma34'] = df['wma17'] / df['wma34']
    df['obv_ratio'] = df['obv'] / df['obv_5d']
    df['volume_ratio'] = df['volume'] / df['media_volume_20d']
    df['candlestick'] = df['preco_compra'] / df['fechamento_anterior']
    df['potencial_alta'] = df['atr'] / df['preco_compra']

    df.dropna(subset=[
        'fechamento_div_wma602', 'wma17_div_wma34', 'obv_ratio',
        'rsi_14', 'volume_ratio', 'candlestick', 'potencial_alta', 'atr'
    ], inplace=True)

    if df.empty:
        print("⚠️ Nenhuma ação válida após limpeza dos dados.")
        return

    modelo_path = os.path.join(os.path.dirname(__file__), "..", "modelos", "modelo_random_forest.pkl")
    modelo_path = os.path.abspath(modelo_path)

    #modelo = joblib.load(r"C:\b3analise\modelos\modelo_random_forest.pkl")
    modelo = modelo_path
    X_pred = df[[
        'fechamento_div_wma602',
        'wma17_div_wma34',
        'obv_ratio',
        'rsi_14',
        'volume_ratio',
        'candlestick',
        'potencial_alta',
    ]]

    df['probabilidade'] = modelo.predict_proba(X_pred)[:, 1]
    df['valor_alvo'] = df['preco_compra'] + df['atr']
    df['lucro_perc'] = ((df['valor_alvo'] / df['preco_compra']) - 1) * 100
    df['probabilidade_pct'] = (df['probabilidade'] * 100).round(2)

    def faixa(p):
        if p >= 15:
            return 'forte'
        elif p >= 5:
            return 'média'
        else:
            return 'fraca'
    df['classificacao'] = df['probabilidade_pct'].apply(faixa)

    resultado = df[['acao__ticker', 'preco_compra', 'probabilidade_pct', 'classificacao', 'lucro_perc', 'valor_alvo']]
    resultado = resultado.rename(columns={
        'acao__ticker': 'ticker',
        'preco_compra': 'valor_compra',
        'probabilidade_pct': 'probabilidade (%)'
    }).sort_values(by='probabilidade (%)', ascending=False).head(top_n)

    # Impressão formatada
    print("\n📈 Recomendações com base no modelo (entrada = intraday, alvo = 1×ATR):\n")
    print(f"{'Ticker':<8} {'Compra':>8} {'Prob. (%)':>11} {'Faixa':>8} {'Lucro (%)':>11} {'Alvo':>10}")
    print("-" * 60)
    for _, row in resultado.iterrows():
        print(f"{row['ticker']:<8} "
              f"{row['valor_compra']:>8.2f} "
              f"{row['probabilidade (%)']:>11.2f} "
              f"{row['classificacao']:>8} "
              f"{row['lucro_perc']:>11.2f} "
              f"{row['valor_alvo']:>10.4f}")

    
    print("\n💾 Salvando recomendações no banco de dados...")
    for _, row in resultado.iterrows():
        try:
            acao_obj = Acao.objects.get(ticker=row['ticker'])
            rec, created = RecomendacaoDiaria.objects.update_or_create(
                acao=acao_obj,
                data=ultima_data,
                defaults={
                    'preco_compra': Decimal(row['valor_compra']),
                    'alvo_sugerido': Decimal(row['valor_alvo']),
                    'perc_alvo': Decimal(row['lucro_perc']).quantize(Decimal('0.01')),
                    'probabilidade': Decimal(row['probabilidade (%)']).quantize(Decimal('0.01')),
                    'abaixo_wma': True,
                    'wma602': Decimal(df.loc[df['acao__ticker'] == row['ticker'], 'wma602'].values[0]),
                    'cruzamento_medias': bool(
                        df.loc[df['acao__ticker'] == row['ticker'], 'wma17_div_wma34'].values[0] > 1
                    ),
                    'volume_acima_media': bool(
                        df.loc[df['acao__ticker'] == row['ticker'], 'volume_ratio'].values[0] > 1
                    ),
                    'obv_crescente': bool(
                        df.loc[df['acao__ticker'] == row['ticker'], 'obv_ratio'].values[0] > 1
                    ),
                    'origem': 'ia'
                }
            )
            status = "Criado" if created else "Atualizado"
            print(f"✅ {row['ticker']}: {status}")
        except Acao.DoesNotExist:
            print(f"⚠️ Ação não encontrada no banco: {row['ticker']}")
        except Exception as e:
            print(f"❌ Erro ao salvar {row['ticker']}: {e}")
    
    return resultado.to_dict(orient='records')


if __name__ == "__main__":
    gerar_recomendacoes()
