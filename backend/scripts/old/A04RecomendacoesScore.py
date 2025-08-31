#     analisar_potencial_reversao()
import os
import sys
import django
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP

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

        ultimos_fech = df['fechamento'].iloc[-3:]
        subindo = ultimos_fech.is_monotonic_increasing

        cruzamento = atual['wma17'] > atual['wma34'] or atual['wma17'] > atual['fechamento']

        volume_medio = df['volume'].mean()
        volume_ok = atual['volume'] > volume_medio

        obv_ok = df['obv'].iloc[-3:].is_monotonic_increasing

        score = int(subindo) + int(cruzamento) + int(volume_ok) + int(obv_ok)

        if score > 0:
            fechamento = Decimal(atual['fechamento'])
            wma602 = Decimal(atual['wma602'])
            alvo_sugerido = (fechamento * Decimal('1.05')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            perc_alvo = ((alvo_sugerido / fechamento - 1) * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            resultado = {
                'ticker': acao.ticker,
                'fechamento': float(fechamento),
                'wma602': float(wma602),
                'score': score,
            }
            resultados.append(resultado)

            RecomendacaoDiaria.objects.update_or_create(
                acao=acao,
                data=atual['data'],
                origem='score',
                defaults={
                    'fechamento': fechamento,
                    'wma602': wma602,
                    'abaixo_wma': True,
                    'percentual_diferenca': ((wma602 - fechamento) / wma602 * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                    'score_reversao': Decimal(score),
                    'comentario': 'Potencial de reversão com OBV positivo',
                    'subindo_3dias': bool(subindo),
                    'cruzamento_medias': bool(cruzamento),
                    'volume_acima_media': bool(volume_ok),
                    'obv_crescente': bool(obv_ok),
                    'origem': 'score',
                    'alvo_sugerido': alvo_sugerido,
                    'perc_alvo': perc_alvo,
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


