
# IA05_faixa_mais_provavel.py
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

FAIXAS = {
    '1a2': (1, 2),
    '2a3': (2, 3),
    '3a4': (3, 4),
    '4a5': (4, 5)
}

MODELOS = {nome: joblib.load(f'modelo_faixa_{nome}.pkl') for nome in FAIXAS}

def faixa_mais_provavel():
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
            continue  # restrição: somente ações abaixo da WMA602

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

        probabilidades = {
            faixa: round(float(modelo.predict_proba(X)[0][1]) * 100, 2)
            for faixa, modelo in MODELOS.items()
        }

        faixa_max = max(probabilidades, key=probabilidades.get)
        prob_max = probabilidades[faixa_max]
        faixa_base = FAIXAS[faixa_max][0]

        fechamento = float(cotacao.fechamento)
        alvo_em_valor = fechamento * (1 + faixa_base / 100)

        resultados.append({
            'Ticker': acao.ticker,
            'Fechamento atual': round(fechamento, 2),
            'Faixa mais provável': faixa_max,
            'Probabilidade (%)': prob_max,
            'Alvo (R$)': round(alvo_em_valor, 2)
        })

    df = pd.DataFrame(resultados).sort_values(by='Probabilidade (%)', ascending=False)
    csv_path = 'c:/b3analise_docs/faixa_mais_provavel.csv'
    df.to_csv(csv_path, index=False)
    print(f"✅ Arquivo gerado: {csv_path}")
    return csv_path

if __name__ == '__main__':
    faixa_mais_provavel()
