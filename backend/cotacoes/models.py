from django.db import models

class Acao(models.Model):
    ticker = models.CharField(max_length=10, unique=True)
    empresa = models.CharField(max_length=100, blank=True, null=True)
    setor = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.ticker

class Cotacao(models.Model):
    acao = models.ForeignKey('Acao', on_delete=models.CASCADE)
    data = models.DateField()
    abertura = models.DecimalField(max_digits=10, decimal_places=2)
    fechamento = models.DecimalField(max_digits=10, decimal_places=2)
    minima = models.DecimalField(max_digits=10, decimal_places=2)
    maxima = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.BigIntegerField()

    # Médias de Welles Wilder
    wma17 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    wma34 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    wma72 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    wma144 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    wma602 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    #Acumulation/Distribution
    ad = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    #OBV
    obv = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    reversao_detectada = models.BooleanField(default=False)

    class Meta:
        unique_together = ('acao', 'data')


class RecomendacaoDiaria(models.Model):
    acao = models.ForeignKey('Acao', on_delete=models.CASCADE)
    data = models.DateField()
    fechamento = models.DecimalField(max_digits=10, decimal_places=2)
    wma602 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    abaixo_wma = models.BooleanField()
    percentual_diferenca = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    comentario = models.TextField(null=True, blank=True)
    data_alvo = models.DateField(null=True, blank=True)
    fechamento_alvo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    posicao_alvo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    #memórica de cálculo do score
    subindo_3dias = models.BooleanField(null=True, blank=True)
    cruzamento_medias = models.BooleanField(null=True, blank=True)
    volume_acima_media = models.BooleanField(null=True, blank=True)
    obv_crescente = models.BooleanField(null=True, blank=True)

    #score
    score_reversao = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('acao', 'data')

