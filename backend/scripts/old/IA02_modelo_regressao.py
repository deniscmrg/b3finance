import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns

import sys, os, django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import RecomendacaoSimulada

FEATURES_USADAS = [
    'score_reversao',
    'percentual_diferenca',
    'obv_crescente',
    'subindo_3dias',
    'volume_acima_media',
    'cruzamento_medias',
    'rsi_14',
    'media_volume_20d'
]

TARGET = 'retorno_5d'  # Valor de retorno real após 5 dias

def treinar_modelo_regressao():
    # Extrai os dados do banco
    dados = RecomendacaoSimulada.objects.all().values(*FEATURES_USADAS, TARGET)
    df = pd.DataFrame.from_records(dados)
    df = df.dropna()

    for col in ['obv_crescente', 'subindo_3dias', 'volume_acima_media', 'cruzamento_medias']:
        df[col] = df[col].astype(int)

    X = df[FEATURES_USADAS]
    y = df[TARGET]

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    modelo = RandomForestRegressor(n_estimators=100, random_state=42)
    modelo.fit(X_train, y_train)

    # Avaliação
    y_pred = modelo.predict(X_test)
    print("MAE:", mean_absolute_error(y_test, y_pred))
    print("R² Score:", r2_score(y_test, y_pred))

    # Importância das variáveis
    importancias = pd.Series(modelo.feature_importances_, index=FEATURES_USADAS)
    print("\nImportância das features:")
    print(importancias.sort_values(ascending=False))

    # Gráfico
    sns.barplot(x=importancias.sort_values(), y=importancias.sort_values().index)
    plt.title("Importância das variáveis no modelo de regressão")
    plt.tight_layout()
    plt.show()

    joblib.dump(modelo, 'modelo_rf_regressao.pkl')
    return modelo

if __name__ == '__main__':
    treinar_modelo_regressao()
