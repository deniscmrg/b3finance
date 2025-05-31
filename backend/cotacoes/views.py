from django.shortcuts import render
from django.http import JsonResponse
from cotacoes.models import Cotacao, Acao 
from django.utils.dateparse import parse_date
from datetime import timedelta, date
from cotacoes.models import RecomendacaoDiaria, Acao
from django.db.models import F

def grafico_score_html(request):
    return render(request, 'cotacoes/grafico-score.html')


def dados_score_todas_acoes(request):
    hoje = date.today()
    trinta_dias_atras = hoje - timedelta(days=30)

    recomendacoes = RecomendacaoDiaria.objects.filter(data__gte=trinta_dias_atras) \
        .select_related('acao') \
        .order_by('acao__ticker', 'data')

    dados_por_acao = {}

    for rec in recomendacoes:
        if not rec.data or not rec.acao:
            continue

        ticker = rec.acao.ticker
        if ticker not in dados_por_acao:
            dados_por_acao[ticker] = {}

        data_str = str(rec.data)
        dados_por_acao[ticker][data_str] = float(rec.score_reversao or 0)

    # Agora garantidamente todas as datas são string
    todas_datas = sorted(set(str(data) for a in dados_por_acao.values() for data in a.keys()))

    acoes_data = []
    for ticker, dados in dados_por_acao.items():
        scores = [dados.get(data, 0) for data in todas_datas]
        acoes_data.append({
            'ticker': ticker,
            'scores': scores
        })

    return JsonResponse({
        'datas': todas_datas,
        'acoes': acoes_data
    })


def grafico_view(request, ticker):
    return render(request, 'cotacoes/grafico.html', {'ticker': ticker})


def dados_grafico(request, ticker):
    ticker = ticker.upper()

    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')

    data_inicio = parse_date(data_inicio_str) if data_inicio_str else None
    data_fim = parse_date(data_fim_str) if data_fim_str else None

    # data_inicio = parse_date(request.GET.get('data_inicio'))
    # data_fim = parse_date(request.GET.get('data_fim'))

    try:
        acao = Acao.objects.get(ticker=ticker)
    except Acao.DoesNotExist:
        return JsonResponse({'erro': 'Ação não encontrada'}, status=404)

    cotacoes = Cotacao.objects.filter(acao=acao).order_by('data')
    
    if data_inicio:
        cotacoes = cotacoes.filter(data__gte=data_inicio)
    if data_fim:
        cotacoes = cotacoes.filter(data__lte=data_fim)

    dados = [
        {
            'data': cot.data.strftime('%Y-%m-%d'),
            'fechamento': float(cot.fechamento),
            'wma17': float(cot.wma17) if cot.wma17 else None,
            'wma34': float(cot.wma34) if cot.wma34 else None,
            'wma72': float(cot.wma72) if cot.wma72 else None,
            'wma144': float(cot.wma144) if cot.wma144 else None,
            'wma602': float(cot.wma602) if cot.wma602 else None,
        }
        for cot in cotacoes
    ]

    return JsonResponse(dados, safe=False)