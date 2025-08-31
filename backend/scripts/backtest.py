# backtest_carteira.py
import os
import sys
import django
import pandas as pd
import numpy as np
import joblib
from datetime import timedelta, date
from django.db import models

# Configura Django
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from cotacoes.models import Cotacao

# Função para gerar dias úteis
def dias_uteis(inicio, fim):
    return pd.bdate_range(start=inicio, end=fim).date

# Função principal de backtest
def backtest(
    valor_carteira_inicial: float,
    qtd_acoes: int,
    stop_loss_pct: float,
    data_inicio: date,
    data_fim: date,
    conservador_pct: float = 0.5  # porcentagem do alvo para ativar stop conservador
):
    dias = dias_uteis(data_inicio, data_fim)
    modelo = joblib.load("modelos/modelo_random_forest.pkl")

    carteira = []
    historico = []
    valor_carteira = valor_carteira_inicial
    capital_por_acao = valor_carteira / qtd_acoes
    i = 0
    while i < len(dias):
        dia = dias[i]

        # Atualiza carteira
        novas_carteiras = []
        for pos in carteira:
            cot = Cotacao.objects.filter(acao__ticker=pos['ticker'], data=dia).first()
            if not cot:
                novas_carteiras.append(pos)
                continue
            preco_max = float(cot.maxima)
            preco_min = float(cot.minima)

            # Ativa stop conservador
            if pos.get('stop_conservador') is None and preco_max >= (pos['valor_compra'] + (pos['alvo'] - pos['valor_compra']) * conservador_pct):
                pos['stop_conservador'] = preco_max * 0.995  # 0.5% abaixo da máxima do dia

            stop_ativo = pos['stop']
            if pos.get('stop_conservador') is not None:
                stop_ativo = min(stop_ativo, pos['stop_conservador'])

            if preco_max >= pos['alvo']:
                ganho = pos['qtd'] * pos['alvo']
                valor_carteira += ganho
                historico.append(('alvo', pos['ticker'], pos['valor_total'], ganho, dia))
            elif preco_min <= stop_ativo:
                perda = pos['qtd'] * stop_ativo
                valor_carteira += perda
                historico.append(('stop', pos['ticker'], pos['valor_total'], perda, dia))
            else:
                novas_carteiras.append(pos)
        carteira = novas_carteiras

        # Compra novas ações se houver vaga
        vagas = qtd_acoes - len(carteira)
        if vagas > 0:
            encontrou = False
            j = i
            while not encontrou and j < len(dias):
                dia_recomendacao = dias[j]
                qs = Cotacao.objects.filter(
                    data__lte=dia_recomendacao,
                    fechamento__lt=models.F('wma602'),
                    wma17__isnull=False,
                    wma34__isnull=False,
                    obv__isnull=False,
                    rsi_14__isnull=False,
                    media_volume_20d__isnull=False,
                    fechamento_anterior__isnull=False,
                    atr__isnull=False,
                    volume__gt=0
                ).values(
                    'data', 'acao__ticker', 'fechamento', 'atr', 'wma602', 'wma17', 'wma34',
                    'obv', 'rsi_14', 'volume', 'media_volume_20d', 'fechamento_anterior'
                )
                df = pd.DataFrame.from_records(qs)
                if df.empty:
                    j += 1
                    continue

                df.sort_values(by=['acao__ticker', 'data'], inplace=True)
                df['obv_5d'] = df.groupby('acao__ticker')['obv'].shift(5)
                df = df[df['data'] == dia_recomendacao].copy()

                df.ffill(inplace=True)
                df.bfill(inplace=True)
                df.dropna(inplace=True)
                if df.empty:
                    j += 1
                    continue

                df['fechamento_div_wma602'] = df['fechamento'] / df['wma602']
                df['wma17_div_wma34'] = df['wma17'] / df['wma34']
                df['obv_ratio'] = df['obv'] / df['obv_5d']
                df['volume_ratio'] = df['volume'] / df['media_volume_20d']
                df['candlestick'] = df['fechamento'] / df['fechamento_anterior']
                df['potencial_alta'] = df['atr'] / df['fechamento']

                X = df[[
                    'fechamento_div_wma602', 'wma17_div_wma34', 'obv_ratio', 'rsi_14',
                    'volume_ratio', 'candlestick', 'potencial_alta']]
                df['probabilidade'] = modelo.predict_proba(X)[:, 1]

                df = df[df['probabilidade'] >= 0.3]  # apenas probabilidade média ou alta
                df = df.sort_values(by='probabilidade', ascending=False)

                if df.empty:
                    j += 1
                    continue

                for _, row in df.head(vagas).iterrows():
                    preco = float(row['fechamento'])
                    atr = float(row['atr'])
                    valor_total = capital_por_acao
                    qtd = valor_total // preco
                    if qtd == 0:
                        continue
                    alvo = preco + atr
                    stop = preco - ((alvo - preco) * (stop_loss_pct / 100))
                    carteira.append({
                        'ticker': row['acao__ticker'],
                        'data_compra': dia_recomendacao,
                        'valor_compra': preco,
                        'qtd': qtd,
                        'valor_total': qtd * preco,
                        'alvo': alvo,
                        'stop': stop,
                        'stop_conservador': None
                    })
                    valor_carteira -= qtd * preco
                    encontrou = True
                j += 1
        i += 1

    for pos in carteira:
        cot = Cotacao.objects.filter(acao__ticker=pos['ticker'], data=data_fim).first()
        if cot:
            valor_carteira += float(cot.fechamento) * pos['qtd']

    atingiu_alvo = sum(1 for h in historico if h[0] == 'alvo')
    saiu_stop = sum(1 for h in historico if h[0] == 'stop')
    total_op = len(historico)
    lucro_pct = ((valor_carteira / valor_carteira_inicial) - 1) * 100

    print("\n🧾 Relatório de Backtest")
    print(f"Valor inicial da carteira: R$ {valor_carteira_inicial:.2f}")
    print(f"Valor final da carteira:   R$ {valor_carteira:.2f}")
    print(f"Lucro/prejuízo:            {lucro_pct:.2f}%")
    print(f"Entradas com alvo:         {atingiu_alvo}")
    print(f"Entradas com stop:         {saiu_stop}")
    print(f"Total de entradas:         {total_op}")

if __name__ == "__main__":
    from datetime import date
    backtest(
        valor_carteira_inicial=100000.0,
        qtd_acoes=5,
        stop_loss_pct=1,
        data_inicio=date(2025, 4, 1),
        data_fim=date(2025, 6, 28),
        conservador_pct=0.8
    )

