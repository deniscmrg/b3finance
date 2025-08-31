# IA07_prever_percentual_maximo.py
import sys, os, django
import pandas as pd
import joblib
from decimal import Decimal
from django.db.models import Max

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import Acao, Cotacao, RecomendacaoDiaria

FEATURES = [
    'score_reversao', 'percentual_diferenca', 'obv_crescente',
    'subindo_3dias', 'volume_acima_media', 'cruzamento_medias',
    'rsi_14', 'retorno_5d', 'media_volume_20d'
]

modelo = joblib.load('modelo_regressao_alvo.pkl')
MAE = 2.66  # margem conservadora

def prever_e_salvar():
    dia_ref = Cotacao.objects.aggregate(ultima=Max('data'))['ultima']
    print(f"🗕️ Dia referência: {dia_ref}")

    total_salvos = 0

    for acao in Acao.objects.all():
        try:
            cot = Cotacao.objects.get(acao=acao, data=dia_ref)
        except Cotacao.DoesNotExist:
            continue

        if not cot.wma602 or cot.fechamento >= cot.wma602:
            continue  # somente ações abaixo da WMA602

        dados = {
            'score_reversao': getattr(cot, 'score_reversao', 0) or 0,
            'percentual_diferenca': ((cot.fechamento - cot.wma602) / cot.wma602) * 100,
            'obv_crescente': int(getattr(cot, 'obv_crescente', False) or False),
            'subindo_3dias': int(getattr(cot, 'subindo_3dias', False) or False),
            'volume_acima_media': int(getattr(cot, 'volume_acima_media', False) or False),
            'cruzamento_medias': int(getattr(cot, 'cruzamento_medias', False) or False),
            'rsi_14': getattr(cot, 'rsi_14', None),
            'retorno_5d': getattr(cot, 'retorno_5d', None),
            'media_volume_20d': getattr(cot, 'media_volume_20d', None),
        }

        if any(v is None for v in dados.values()):
            continue

        X = pd.DataFrame([[dados[feat] for feat in FEATURES]], columns=FEATURES)
        perc_previsto = modelo.predict(X)[0]
        perc_conservador = max(0, perc_previsto - MAE)

        fechamento = float(cot.fechamento)
        valor_alvo = fechamento * (1 + perc_conservador / 100)

        _, created = RecomendacaoDiaria.objects.update_or_create(
            acao=acao,
            data=dia_ref,
            origem='ia-rg',
            defaults={
                'fechamento': cot.fechamento,
                'wma602': cot.wma602,
                'abaixo_wma': True,
                'percentual_diferenca': round(dados['percentual_diferenca'], 2),
                'score_reversao': dados['score_reversao'],
                'obv_crescente': bool(dados['obv_crescente']),
                'subindo_3dias': bool(dados['subindo_3dias']),
                'volume_acima_media': bool(dados['volume_acima_media']),
                'cruzamento_medias': bool(dados['cruzamento_medias']),
                'comentario': f"IA prev. máx: {round(perc_previsto, 2)}% ",
                'origem': 'ia-rg',
                'perc_alvo': round(Decimal(perc_conservador), 2),
                'alvo_sugerido': valor_alvo
            }
        )

        total_salvos += 1

    print(f"✅ {total_salvos} recomendações salvas na tabela RecomendacaoDiaria.")

if __name__ == '__main__':
    prever_e_salvar()
