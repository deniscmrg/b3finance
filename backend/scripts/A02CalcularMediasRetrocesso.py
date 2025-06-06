import django
import os
import sys
import pandas as pd
from decimal import Decimal, InvalidOperation

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import Cotacao, Acao

def wilder_moving_average(series, period):
    return series.ewm(alpha=1/period, adjust=False).mean()

def calcular_rsi(series, period=14):
    delta = series.diff()
    ganho = delta.where(delta > 0, 0)
    perda = -delta.where(delta < 0, 0)
    media_ganho = ganho.ewm(alpha=1/period, adjust=False).mean()
    media_perda = perda.ewm(alpha=1/period, adjust=False).mean()
    rs = media_ganho / media_perda
    return 100 - (100 / (1 + rs))

def to_decimal_safe(value):
    try:
        if pd.isna(value):
            return None
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None

def calcular_medias_para_acao(acao_id):
    cotacoes = Cotacao.objects.filter(acao_id=acao_id).order_by('data')

    if cotacoes.count() < 602:
        print(f"⚠ {acao_id} não possui dados suficientes para calcular WMA602")
        return

    df = pd.DataFrame.from_records(
        cotacoes.values('id', 'data', 'fechamento', 'maxima', 'minima', 'volume'),
        index='data'
    ).sort_index()

    # Cálculo das WMA
    for periodo in [17, 34, 72, 144, 602]:
        df[f'wma{periodo}'] = wilder_moving_average(df['fechamento'], periodo)

    # OBV
    obv = [0]
    for i in range(1, len(df)):
        if df['fechamento'].iloc[i] > df['fechamento'].iloc[i - 1]:
            obv.append(obv[-1] + df['volume'].iloc[i])
        elif df['fechamento'].iloc[i] < df['fechamento'].iloc[i - 1]:
            obv.append(obv[-1] - df['volume'].iloc[i])
        else:
            obv.append(obv[-1])
    df['obv'] = obv

    # RSI 14
    df['rsi_14'] = calcular_rsi(df['fechamento'], 14)

    # Retorno 5 dias
    df['retorno_5d'] = df['fechamento'].pct_change(periods=5) * 100

    # Média de volume 20 dias
    df['media_volume_20d'] = df['volume'].rolling(window=20).mean()

    # Atualiza os dados no banco
    for idx, row in df.iterrows():
        cotacao = Cotacao.objects.get(id=row['id'])
        cotacao.wma17 = to_decimal_safe(row.get('wma17'))
        cotacao.wma34 = to_decimal_safe(row.get('wma34'))
        cotacao.wma72 = to_decimal_safe(row.get('wma72'))
        cotacao.wma144 = to_decimal_safe(row.get('wma144'))
        cotacao.wma602 = to_decimal_safe(row.get('wma602'))
        cotacao.ad = to_decimal_safe(row.get('ad'))
        cotacao.obv = to_decimal_safe(row.get('obv'))
        cotacao.rsi_14 = to_decimal_safe(row.get('rsi_14'))
        cotacao.retorno_5d = to_decimal_safe(row.get('retorno_5d'))
        cotacao.media_volume_20d = to_decimal_safe(row.get('media_volume_20d'))
        cotacao.save()

    print(f"✅ Indicadores calculados para {cotacoes[0].acao.ticker}")

def calcular_todas():
    for acao in Acao.objects.all():
        calcular_medias_para_acao(acao.id)

if __name__ == '__main__':
    calcular_todas()
