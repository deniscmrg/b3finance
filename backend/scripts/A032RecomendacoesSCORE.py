# scripts/verifica_alvo_recomendacoes.py

import os
import sys
import django
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import Cotacao, RecomendacaoDiaria

def verificar_alvos_recomendacoes():
    recomendacoes = RecomendacaoDiaria.objects.filter(
        fechamento__isnull=False
    )

    for recomendacao in recomendacoes:
        print(f"→ Verificando {recomendacao.acao.ticker} em {recomendacao.data} (fechamento: {recomendacao.fechamento})")
        preco_alvo = float(recomendacao.fechamento) * 1.05

        # Busca o último fechamento disponível
        ultima_cotacao = Cotacao.objects.filter(
            acao_id=recomendacao.acao_id,
            data__gt=recomendacao.data
        ).order_by('-data').first()

        if not ultima_cotacao:
            print(f"[!] Sem cotação após {recomendacao.data} para {recomendacao.acao.ticker}")
            continue  # pula se ainda não houver cotação posterior

        # Caso o alvo ainda não tenha sido atingido
        if recomendacao.data_alvo is None:
            cotacoes_pos = Cotacao.objects.filter(
                acao_id=recomendacao.acao_id,
                data__gt=recomendacao.data
            ).order_by('data')

            for cotacao in cotacoes_pos:
                if cotacao.maxima and cotacao.maxima >= preco_alvo:
                    recomendacao.data_alvo = cotacao.data
                    recomendacao.fechamento_alvo = cotacao.fechamento
                    recomendacao.posicao_alvo = Decimal('100.00')
                    recomendacao.save()
                    print(f"[✔] Alvo atingido: {recomendacao.acao.ticker} em {cotacao.data}")
                    break
            else:
                # Ainda não atingiu: atualiza a posição do alvo
                fechamento_atual = float(ultima_cotacao.fechamento)
                #porcentagem = Decimal(fechamento_atual / preco_alvo * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                porcentagem = Decimal(((fechamento_atual / float(recomendacao.fechamento)) - 1) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                recomendacao.posicao_alvo = porcentagem
                recomendacao.save()
                print(f"[...] {recomendacao.acao.ticker} está em {porcentagem}% do alvo.")
        else:
            # Já atingiu o alvo, garante que esteja fixo em 100%
            if recomendacao.posicao_alvo != Decimal('100.00'):
                recomendacao.posicao_alvo = Decimal('100.00')
                recomendacao.save()
                print(f"[=] Corrigido para 100%: {recomendacao.acao.ticker}")

if __name__ == '__main__':
    verificar_alvos_recomendacoes()


