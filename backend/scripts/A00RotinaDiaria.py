import A01CargaDiaria as carga
import A02CalcularMediasRetrocesso as medias
import A030GerarRelatorioReversao as relatorio
import A031RecomendacoesIA as relatorio_IA
import backend.scripts.A032RecomendacoesSCORE as alvo

def main():
    print("=== CARGA DE COTAÇÕES ===")
    carga.atualizar_cotacoes(0)
    print("=== CALCULO DE MÉDIAS ===")
    medias.calcular_todas()
    print("=== VERIFICA ALVOS ===")
    alvo.verificar_alvos_recomendacoes()
    print("=== RELATORIO DE REVERSÃO ===")
    relatorio.analisar_potencial_reversao()
    relatorio_IA.gerar_recomendacoes_hoje()


main()