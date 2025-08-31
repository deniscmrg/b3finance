import A01CargaDiaria as carga
import A02CalculaMedias as medias
import A04RecomendacoesScore as relatorio_SC
import A05RecomendacoesIA as relatorio_IA
import A03VerificaAlvos as alvo
import A06CargaRecomendacaoSimulada as simulada


def main():
    print("=== CARGA DE COTAÇÕES ===")
    carga.atualizar_cotacoes(0)
    print("=== CALCULO DE MÉDIAS ===")
    medias.calcular_todas()
    print("=== VERIFICA ALVOS ===")
    alvo.verificar_alvos_recomendacoes()
    print("=== RECOMENDAÇÕES SIMULADAS ===")
    simulada.atualizar_recomendacoes_simuladas()
    print("=== RELATORIO DE REVERSÃO ===")
    relatorio_SC.analisar_potencial_reversao()
    #relatorio_IA.gerar_recomendacoes_hoje()


if __name__ == '__main__':
    main()