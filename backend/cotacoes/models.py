from django.db import models
from decimal import Decimal



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

    #RSI
    rsi_14 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    #RETORNO 5 DIAS
    retorno_5d = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    #VOLUME 20DIDAS
    media_volume_20d = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    #REVERSÃO
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

    # memória de cálculo do score
    subindo_3dias = models.BooleanField(null=True, blank=True)
    cruzamento_medias = models.BooleanField(null=True, blank=True)
    volume_acima_media = models.BooleanField(null=True, blank=True)
    obv_crescente = models.BooleanField(null=True, blank=True)

    # score
    score_reversao = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # origem da recomendação
    origem = models.CharField(
        max_length=10,
        choices=[('score', 'Score'), ('ia', 'IA')],
        default='score'
    )

    class Meta:
        unique_together = ('acao', 'data')


class Cliente(models.Model):
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    documento = models.CharField(max_length=20, unique=True)  # CPF ou CNPJ
    telefone = models.CharField(max_length=20, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.nome} ({self.email})'

class OperacaoCarteira(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    acao = models.ForeignKey(Acao, on_delete=models.CASCADE)
    data_compra = models.DateField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.IntegerField()
    valor_total_compra = models.DecimalField(max_digits=12, decimal_places=2)

    data_venda = models.DateField(null=True, blank=True)
    preco_venda_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_total_venda = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def calcular_valor_total_compra(self):
        return Decimal(self.preco_unitario) * self.quantidade

    def calcular_valor_total_venda(self):
        if self.preco_venda_unitario:
            return Decimal(self.preco_venda_unitario) * self.quantidade
        return None

    def lucro_percentual(self):
        if self.valor_total_venda and self.valor_total_compra:
            lucro = ((self.valor_total_venda / self.valor_total_compra) - 1) * 100
            return round(lucro, 2)
        return None

    def __str__(self):
        return f'{self.cliente.nome} - {self.acao.ticker} ({self.data_compra})'


# app: cotacoes/models.py

class RecomendacaoSimulada(models.Model):
    acao = models.ForeignKey('Acao', on_delete=models.CASCADE)
    data = models.DateField()
    fechamento = models.DecimalField(max_digits=10, decimal_places=2)
    wma602 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percentual_diferenca = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    subindo_3dias = models.BooleanField(null=True, blank=True)
    cruzamento_medias = models.BooleanField(null=True, blank=True)
    volume_acima_media = models.BooleanField(null=True, blank=True)
    obv_crescente = models.BooleanField(null=True, blank=True)
    score_reversao = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    atingiu_alvo = models.BooleanField(null=True, blank=True)
    rsi_14 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    retorno_5d = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    media_volume_20d = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('acao', 'data')
