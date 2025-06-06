import sys, os, django
from datetime import date, timedelta
from decimal import Decimal
import joblib
import pandas as pd
from django.db.models import Max

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import Acao, Cotacao, RecomendacaoDiaria

# DIA_REFERENCIA = date.today() - timedelta(days=1)
DIA_REFERENCIA = Cotacao.objects.aggregate(ultima=Max('data'))['ultima']
THRESHOLD = 0.35
modelo = joblib.load('modelo_rf_simulado.pkl')

FEATURES_USADAS = [
    'score_reversao',
    'percentual_diferenca',
    'obv_crescente',
    'subindo_3dias',
    'volume_acima_media',
    'cruzamento_medias',
    'rsi_14',
    'retorno_5d',
    'media_volume_20d'
]

def gerar_recomendacoes_hoje():
    print(f"Gerando recomendações do modelo IA para {DIA_REFERENCIA}...\n")
    acoes = Acao.objects.all()
    total_salvas = 0

    for acao in acoes:
        try:
            cotacao = Cotacao.objects.get(acao=acao, data=DIA_REFERENCIA)
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

        X = pd.DataFrame([[dados[feat] for feat in FEATURES_USADAS]], columns=FEATURES_USADAS)
        prob = modelo.predict_proba(X)[0][1]

        if prob >= THRESHOLD:
            _, created = RecomendacaoDiaria.objects.update_or_create(
                acao=acao,
                data=DIA_REFERENCIA,
                defaults={
                    'fechamento': cotacao.fechamento,
                    'wma602': cotacao.wma602,
                    'abaixo_wma': True,
                    'percentual_diferenca': round(dados['percentual_diferenca'], 2),
                    'score_reversao': dados['score_reversao'],
                    'obv_crescente': bool(dados['obv_crescente']),
                    'subindo_3dias': bool(dados['subindo_3dias']),
                    'volume_acima_media': bool(dados['volume_acima_media']),
                    'cruzamento_medias': bool(dados['cruzamento_medias']),
                    'comentario': f"Probabilidade IA: {round(prob * 100, 2)}%",
                    'origem': 'ia',
                }
            )
            total_salvas += 1

    print(f"\n{total_salvas} recomendações IA salvas na tabela RecomendacaoDiaria.")

if __name__ == '__main__':
    gerar_recomendacoes_hoje()
