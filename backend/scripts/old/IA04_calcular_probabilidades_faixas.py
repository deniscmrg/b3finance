
# IA04_calcular_probabilidades_faixas.py
import sys, os, django
import pandas as pd
import joblib
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import Acao, Cotacao

FEATURES = [
    'score_reversao', 'percentual_diferenca', 'obv_crescente',
    'subindo_3dias', 'volume_acima_media', 'cruzamento_medias',
    'rsi_14', 'retorno_5d', 'media_volume_20d'
]

FAIXAS = ['1a2', '2a3', '3a4', '4a5']
MODELOS = {nome: joblib.load(f'modelo_faixa_{nome}.pkl') for nome in FAIXAS}

def prever_faixas_para_hoje():
    from django.db.models import Max
    dia_ref = Cotacao.objects.aggregate(ultima=Max('data'))['ultima']
    print(f"📅 Usando dados de {dia_ref}\n")

    resultados = []

    for acao in Acao.objects.all():
        try:
            cotacao = Cotacao.objects.get(acao=acao, data=dia_ref)
        except Cotacao.DoesNotExist:
            continue

        if not cotacao.wma602 or cotacao.fechamento >= cotacao.wma602:
            continue

        dados = {
            'score_reversao': getattr(cotacao, 'score_reversao', 0) or 0,
            'percentual_diferenca': ((cotacao.fechamento - cotacao.wma602) / cotacao.wma602) * 100,
            'obv_crescente': int(getattr(cotacao, 'obv_crescente', False) or False),
            'subindo_3dias': int(getattr(cotacao, 'subindo_3dias', False) or False),
            'volume_acima_media': int(getattr(cotacao, 'volume_acima_media', False) or False),
            'cruzamento_medias': int(getattr(cotacao, 'cruzamento_medias', False) or False),
            'rsi_14': getattr(cotacao, 'rsi_14', None),
            'retorno_5d': getattr(cotacao, 'retorno_5d', None),
            'media_volume_20d': getattr(cotacao, 'media_volume_20d', None),
        }

        if any(v is None for v in dados.values()):
            continue

        X = pd.DataFrame([[dados[feat] for feat in FEATURES]], columns=FEATURES)

        probabilidades = {}
        for faixa, modelo in MODELOS.items():
            prob = modelo.predict_proba(X)[0][1]
            probabilidades[faixa] = round(Decimal(prob * 100), 2)

        resultados.append({
            'ticker': acao.ticker,
            **probabilidades
        })

    resultados_ordenados = sorted(resultados, key=lambda x: x['4a5'], reverse=True)
    for r in resultados_ordenados[:20]:
        print(f"{r['ticker']:<8} | 1-2%: {r['1a2']}% | 2-3%: {r['2a3']}% | 3-4%: {r['3a4']}% | 4-5%: {r['4a5']}%")

if __name__ == '__main__':
    prever_faixas_para_hoje()
