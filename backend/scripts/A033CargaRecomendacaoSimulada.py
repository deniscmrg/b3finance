import os
import sys
from datetime import timedelta
from decimal import Decimal

import django
from django.db.models import Max

# Ajusta o caminho para encontrar o settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import Acao, Cotacao, RecomendacaoSimulada


def atualizar_recomendacoes_simuladas():
    # Dia analisado é o último dia com cotação menos 4 dias
    ultima_data = Cotacao.objects.aggregate(ultima=Max('data'))['ultima']
    if not ultima_data:
        print("Nenhuma cotação disponível.")
        return

    dia_referencia = ultima_data - timedelta(days=4)
    print(f"Gerando recomendações simuladas para {dia_referencia}...")

    total_salvas = 0
    for acao in Acao.objects.all():
        cotacoes = list(Cotacao.objects.filter(
            acao=acao,
            data__range=(dia_referencia - timedelta(days=2), dia_referencia + timedelta(days=4))
        ).order_by('data'))

        # Encontra a cotação do dia de referência
        hoje = next((c for c in cotacoes if c.data == dia_referencia), None)
        if not hoje:
            continue
        idx = cotacoes.index(hoje)
        if idx < 2:
            continue

        d1, d2 = cotacoes[idx - 1], cotacoes[idx - 2]

        subindo_3dias = hoje.fechamento > d1.fechamento > d2.fechamento
        cruzamento_medias = hoje.wma17 and hoje.wma34 and hoje.wma17 > hoje.wma34
        volume_acima_media = hoje.volume > ((d1.volume + d2.volume) / 2)
        obv_crescente = hoje.obv and d1.obv and hoje.obv > d1.obv
        abaixo_wma = hoje.wma602 and hoje.fechamento < hoje.wma602

        if not abaixo_wma:
            continue

        score = sum([
            subindo_3dias,
            cruzamento_medias,
            volume_acima_media,
            obv_crescente,
        ])

        preco_alvo = float(hoje.fechamento) * 1.05
        futuras = [c for c in cotacoes[idx + 1:] if c.data <= dia_referencia + timedelta(days=4)]
        atingiu_alvo = any(float(c.maxima) >= preco_alvo for c in futuras)

        RecomendacaoSimulada.objects.update_or_create(
            acao=acao,
            data=dia_referencia,
            defaults={
                'fechamento': hoje.fechamento,
                'wma602': hoje.wma602,
                'percentual_diferenca': round(((hoje.fechamento - hoje.wma602) / hoje.wma602) * 100, 2) if hoje.wma602 else None,
                'subindo_3dias': subindo_3dias,
                'cruzamento_medias': cruzamento_medias,
                'volume_acima_media': volume_acima_media,
                'obv_crescente': obv_crescente,
                'score_reversao': Decimal(score),
                'atingiu_alvo': atingiu_alvo,
                'rsi_14': hoje.rsi_14,
                'retorno_5d': hoje.retorno_5d,
                'media_volume_20d': hoje.media_volume_20d,
            }
        )
        total_salvas += 1

    print(f"{total_salvas} recomendações simuladas salvas para {dia_referencia}.")


if __name__ == '__main__':
    atualizar_recomendacoes_simuladas()

