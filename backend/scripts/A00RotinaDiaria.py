import A01CargaDiaria as carga
import A02CalcularMediasRetrocesso as medias
import A03GerarRelatorioReversao as relatorio
import A03VerificaAlvoRecomendacoes as alvo

def main():
    carga.atualizar_cotacoes(0)
    medias.calcular_todas()
    alvo.verificar_alvos_recomendacoes()
    relatorio.analisar_potencial_reversao()
