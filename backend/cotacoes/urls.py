from django.urls import path
from . import views

urlpatterns = [
    path('grafico/todas-acoes/', views.dados_score_todas_acoes, name='grafico_todas_acoes'),
    path('grafico-score/', views.grafico_score_html, name='grafico-score'),
    path('grafico/<str:ticker>/', views.dados_grafico, name='dados_grafico'),
    path('ver-grafico/<str:ticker>/', views.grafico_view, name='grafico_view'),
    path('carteira/<int:cliente_id>/', views.carteira_cliente, name='carteira_cliente'),
]