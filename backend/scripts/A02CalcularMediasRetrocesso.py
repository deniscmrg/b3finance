# import django
# import os
# import sys
# import pandas as pd
# from decimal import Decimal
# # Caminho até a raiz do projeto
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
# django.setup()
# from cotacoes.models import Cotacao, Acao


# def wilder_moving_average(series, period):
#     return series.ewm(alpha=1/period, adjust=False).mean()

# def calcular_medias_para_acao(acao_id):
#     cotacoes = Cotacao.objects.filter(acao_id=acao_id).order_by('data')
    
#     if cotacoes.count() < 602:
#         print(f"⚠ {acao_id} não possui dados suficientes para calcular WMA602")
#         return

#     df = pd.DataFrame.from_records(
#         cotacoes.values('id', 'data', 'fechamento'),
#         index='data'
#     ).sort_index()

#     for periodo in [17, 34, 72, 144, 602]:
#         df[f'wma{periodo}'] = wilder_moving_average(df['fechamento'], periodo)

#     # Atualiza no banco
#     for idx, row in df.iterrows():
#         cotacao = Cotacao.objects.get(id=row['id'])
#         cotacao.wma17 = row.get('wma17', None)
#         cotacao.wma34 = row.get('wma34', None)
#         cotacao.wma72 = row.get('wma72', None)
#         cotacao.wma144 = row.get('wma144', None)
#         cotacao.wma602 = row.get('wma602', None)
#         cotacao.save()

#     print(f"✅ Médias calculadas para {cotacoes[0].acao.ticker}")

# def calcular_todas():
#     for acao in Acao.objects.all():
#         calcular_medias_para_acao(acao.id)

# if __name__ == '__main__':
#     calcular_todas()

import django
import os
import sys
import pandas as pd
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import Cotacao, Acao

def wilder_moving_average(series, period):
    return series.ewm(alpha=1/period, adjust=False).mean()

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

    # Atualiza os dados no banco
    for idx, row in df.iterrows():
        cotacao = Cotacao.objects.get(id=row['id'])
        cotacao.wma17 = row.get('wma17', None)
        cotacao.wma34 = row.get('wma34', None)
        cotacao.wma72 = row.get('wma72', None)
        cotacao.wma144 = row.get('wma144', None)
        cotacao.wma602 = row.get('wma602', None)
        cotacao.ad = row.get('ad', None)
        cotacao.obv = row.get('obv', None)
        cotacao.save()

    print(f"✅ Indicadores calculados para {cotacoes[0].acao.ticker}")

def calcular_todas():
    for acao in Acao.objects.all():
        calcular_medias_para_acao(acao.id)

if __name__ == '__main__':
    calcular_todas()
