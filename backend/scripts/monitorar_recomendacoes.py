import os
import sys
import django
from decimal import Decimal
from datetime import date, datetime
import yfinance as yf
import pytz

# Configuração Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import RecomendacaoDiaria

LOG_PATH = os.path.join(os.path.dirname(__file__), 'monitor.log')

def registrar(msg):
    agora = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_PATH, 'a', encoding='utf-8') as log:
        log.write(f"[{agora}] {msg}\n")

def mercado_aberto():
    agora = datetime.now(pytz.timezone("America/Sao_Paulo")).time()
    return agora >= datetime.strptime("10:00", "%H:%M").time() and agora <= datetime.strptime("17:00", "%H:%M").time()

def monitorar_recomendacoes():
    if not mercado_aberto():
        registrar("⏱️ Fora do horário de pregão. Ignorando execução.")
        return

    recomendacoes = RecomendacaoDiaria.objects.filter(data_alvo__isnull=True)
    registrar(f"🔍 Monitorando {recomendacoes.count()} recomendações...")

    for rec in recomendacoes:
        try:
            ticker_full = f"{rec.acao.ticker}.SA"
            dados = yf.download(ticker_full, period="1d", interval="1m", progress=False)

            if dados.empty:
                registrar(f"⚠️ Sem dados de hoje para {rec.acao.ticker}")
                continue

            preco_atual = Decimal(str(dados['Close'].iloc[-1]))
            preco_alvo = rec.fechamento * Decimal('1.05')

            if preco_atual >= preco_alvo:
                rec.data_alvo = date.today()
                rec.fechamento_alvo = round(preco_atual, 2)
                rec.save()
                registrar(f"🎯 {rec.acao.ticker} atingiu o alvo! Fechamento atual: {preco_atual:.2f}")
            else:
                registrar(f"🔎 {rec.acao.ticker}: atual {preco_atual:.2f} | alvo {preco_alvo:.2f}")

        except Exception as e:
            registrar(f"❌ Erro ao processar {rec.acao.ticker}: {e}")

if __name__ == '__main__':
    monitorar_recomendacoes()

