import sys, os, django
from datetime import date, timedelta
from decimal import Decimal
from django.db import IntegrityError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import Acao, Cotacao, RecomendacaoSimulada

DATA_INICIAL = date(2023, 1, 1)
DATA_FINAL = date.today() - timedelta(days=4)

def gerar_recomendacoes_simuladas():
    print("🧹 Limpando tabela cotacoes_recomendacaosimulada...")
    RecomendacaoSimulada.objects.all().delete()

    acoes = Acao.objects.all()
    total = 0
    salvos = 0

    for acao in acoes:
        cotacoes = Cotacao.objects.filter(
            acao=acao,
            data__range=(DATA_INICIAL, DATA_FINAL)
        ).order_by('data')

        for i in range(2, len(cotacoes)):
            hoje = cotacoes[i]
            d1, d2 = cotacoes[i-1], cotacoes[i-2]

            # Regras do score
            subindo_3dias = (hoje.fechamento > d1.fechamento > d2.fechamento)
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
                obv_crescente
            ])

            # Verifica se atingiu o alvo em até 4 dias
            preco_alvo = float(hoje.fechamento) * 1.05
            data_limite = hoje.data + timedelta(days=4)
            futuras = Cotacao.objects.filter(
                acao=acao,
                data__range=(hoje.data + timedelta(days=1), data_limite)
            )

            atingiu_alvo = any(float(c.maxima) >= preco_alvo for c in futuras)

            try:
                RecomendacaoSimulada.objects.create(
                    acao=acao,
                    data=hoje.data,
                    fechamento=hoje.fechamento,
                    wma602=hoje.wma602,
                    percentual_diferenca=round(((hoje.fechamento - hoje.wma602) / hoje.wma602) * 100, 2) if hoje.wma602 else None,
                    subindo_3dias=subindo_3dias,
                    cruzamento_medias=cruzamento_medias,
                    volume_acima_media=volume_acima_media,
                    obv_crescente=obv_crescente,
                    score_reversao=Decimal(score),
                    atingiu_alvo=atingiu_alvo,
                    rsi_14=hoje.rsi_14,
                    retorno_5d=hoje.retorno_5d,
                    media_volume_20d=hoje.media_volume_20d
                )
                salvos += 1
            except IntegrityError:
                continue

            total += 1

    print(f'Total analisados: {total}')
    print(f'Recomendações salvas: {salvos}')

if __name__ == '__main__':
    gerar_recomendacoes_simuladas()
