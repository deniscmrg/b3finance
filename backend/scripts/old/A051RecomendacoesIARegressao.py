import sys, os, django
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import joblib
import pandas as pd

# Configuração do ambiente Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import Acao, Cotacao, RecomendacaoDiaria
from django.db.models import Max

# Carregamento dos modelos
modelo_classificacao = joblib.load('modelo_rf_simulado.pkl')
modelo_regressao = joblib.load('modelo_rf_regressao.pkl')

DIA_REFERENCIA = Cotacao.objects.aggregate(ultima=Max('data'))['ultima']
THRESHOLD_CLASSIFICACAO = 0.35

FEATURES_CLASSIFICACAO = [
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

FEATURES_REGRESSAO = [
    'score_reversao',
    'percentual_diferenca',
    'obv_crescente',
    'subindo_3dias',
    'volume_acima_media',
    'cruzamento_medias',
    'rsi_14',
    'media_volume_20d'
]

def gerar_recomendacoes_hibridas():
    print(f"🔍 Gerando recomendações combinadas para {DIA_REFERENCIA}...\n")
    total_salvas = 0

    for acao in Acao.objects.all():
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

        # Classificação
        X_class = pd.DataFrame([[dados[f] for f in FEATURES_CLASSIFICACAO]], columns=FEATURES_CLASSIFICACAO)
        prob = modelo_classificacao.predict_proba(X_class)[0][1]
        if prob < THRESHOLD_CLASSIFICACAO:
            continue

        # Regressão
        X_regr = pd.DataFrame([[dados[f] for f in FEATURES_REGRESSAO]], columns=FEATURES_REGRESSAO)
        retorno_estimado = float(modelo_regressao.predict(X_regr)[0])
        retorno_estimado = Decimal(retorno_estimado).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if retorno_estimado <= 0:
            continue

        RecomendacaoDiaria.objects.update_or_create(
            acao=acao,
            data=DIA_REFERENCIA,
            origem='IA-Híbrido',
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
                'alvo_sugerido': retorno_estimado,
                'comentario': f"Prob: {round(prob * 100, 1)}% | Retorno estimado: {retorno_estimado}%",
                'origem': 'IA-Híbrido',
            }
        )
        total_salvas += 1

    print(f"✅ {total_salvas} recomendações IA-Híbrido salvas com alvo_sugerido > 0%.")

if __name__ == '__main__':
    gerar_recomendacoes_hibridas()
