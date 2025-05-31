#     analisar_potencial_reversao()
import os
import sys
import django
import pandas as pd
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import Cotacao, Acao, RecomendacaoDiaria
from datetime import date

def wilder_moving_average(series, period):
    return series.ewm(alpha=1/period, adjust=False).mean()

def analisar_potencial_reversao():
    resultados = []

    for acao in Acao.objects.all():
        cotacoes = Cotacao.objects.filter(acao=acao).order_by('-data')[:90]

        if cotacoes.count() < 60:
            continue

        df = pd.DataFrame.from_records(
            cotacoes.values('data', 'fechamento', 'wma602', 'wma17', 'wma34', 'volume', 'obv')
        ).sort_values('data')

        atual = df.iloc[-1]

        if not atual['wma602'] or atual['fechamento'] >= atual['wma602']:
            continue

        # Sinal 1: tendência de alta nos últimos 3 dias
        ultimos_fech = df['fechamento'].iloc[-3:]
        subindo = ultimos_fech.is_monotonic_increasing

        # Sinal 2: cruzamento de médias ou wma17 acima do fechamento
        cruzamento = atual['wma17'] > atual['wma34'] or atual['wma17'] > atual['fechamento']

        # Sinal 3: volume acima da média
        volume_medio = df['volume'].mean()
        volume_ok = atual['volume'] > volume_medio

        # Sinal 4: OBV crescente nos últimos 3 dias
        obv_ok = df['obv'].iloc[-3:].is_monotonic_increasing

        score = int(subindo) + int(cruzamento) + int(volume_ok) + int(obv_ok)

        if score > 0:
            resultado = {
                'ticker': acao.ticker,
                'fechamento': float(atual['fechamento']),
                'wma602': float(atual['wma602']),
                'score': score,
            }
            resultados.append(resultado)

            RecomendacaoDiaria.objects.update_or_create(
                acao=acao,
                data=atual['data'],
                defaults={
                    'fechamento': atual['fechamento'],
                    'wma602': atual['wma602'],
                    'abaixo_wma': True,
                    'percentual_diferenca': (atual['wma602'] - atual['fechamento']) / atual['wma602'] * 100,
                    'score_reversao': score,
                    'comentario': 'Potencial de reversão com OBV positivo',
                    'subindo_3dias': bool(subindo),
                    'cruzamento_medias': bool(cruzamento),
                    'volume_acima_media': bool(volume_ok),
                    'obv_crescente': bool(obv_ok)
                }
            )

    df_resultado = pd.DataFrame(resultados)
    if not df_resultado.empty:
        df_resultado = df_resultado.sort_values(['score', 'ticker'], ascending=[False, True]).head(20)
        print(df_resultado.to_string(index=False))
        df_resultado.to_csv('relatorio_reversao.csv', index=False)
    else:
        print("Nenhuma ação com potencial de reversão encontrada.")

    return df_resultado

if __name__ == '__main__':
    analisar_potencial_reversao()
