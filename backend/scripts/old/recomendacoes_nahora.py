import sys, os, django
from datetime import date
from decimal import Decimal
import joblib
import pandas as pd
import yfinance as yf
from django.db.models import Max

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import Acao, Cotacao

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
    print(f"📊 Recomendação IA com yfinance em tempo real ({DIA_REFERENCIA}):\n")
    acoes = Acao.objects.all()

    for acao in acoes:
        try:
            cotacao = Cotacao.objects.get(acao=acao, data=DIA_REFERENCIA)
        except Cotacao.DoesNotExist:
            continue

        if not cotacao.wma602:
            continue

        # Busca a cotação atual pelo yfinance
        try:
            ticker_yt = f"{acao.ticker}.SA"
            dados_yt = yf.Ticker(ticker_yt).history(period="1d")
            if dados_yt.empty:
                continue
            preco_atual = float(dados_yt['Close'].iloc[-1])
        except Exception as e:
            print(f"Erro ao buscar {acao.ticker}: {e}")
            continue

        if preco_atual >= float(cotacao.wma602):
            continue

        percentual_diferenca = ((preco_atual - float(cotacao.wma602)) / float(cotacao.wma602)) * 100

        dados = {
            'score_reversao': float(getattr(cotacao, 'score_reversao', 0) or 0),
            'percentual_diferenca': percentual_diferenca,
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
            print(f"✅ {acao.ticker} | Prob: {round(prob * 100, 2)}% | Preço atual: {preco_atual:.2f} | WMA602: {cotacao.wma602:.2f} | Dif: {percentual_diferenca:.2f}%")

if __name__ == '__main__':
    gerar_recomendacoes_hoje()
