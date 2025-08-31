
# IA06_modelo_regressao_alvo.py
import sys, os, django
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from imblearn.over_sampling import SMOTE
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import RecomendacaoSimulada, Cotacao

FEATURES = [
    'score_reversao', 'percentual_diferenca', 'obv_crescente',
    'subindo_3dias', 'volume_acima_media', 'cruzamento_medias',
    'rsi_14', 'retorno_5d', 'media_volume_20d'
]

def preparar_dados():
    dados = RecomendacaoSimulada.objects.all().values(*FEATURES, 'fechamento', 'acao_id', 'data')
    df = pd.DataFrame.from_records(dados)
    df = df.dropna()

    alvos = []
    for i, row in df.iterrows():
        futuras = Cotacao.objects.filter(
            acao_id=row['acao_id'],
            data__gt=row['data'],
            data__lte=row['data'] + pd.Timedelta(days=5)
        ).order_by('data')
        if not futuras.exists():
            alvos.append(None)
            continue
        max_high = max(c.maxima for c in futuras)
        perc = ((max_high / row['fechamento']) - 1) * 100
        alvos.append(perc)

    df['max_high_5d'] = alvos
    df = df.dropna()

    for col in ['obv_crescente', 'subindo_3dias', 'volume_acima_media', 'cruzamento_medias']:
        df[col] = df[col].astype(int)

    return df

def treinar_modelo_regressao():
    df = preparar_dados()
    X = df[FEATURES]
    y = df['max_high_5d']

    # sm = SMOTE(random_state=42)
    # X_resampled, y_resampled = sm.fit_resample(X, y)

    # X_train, X_test, y_train, y_test = train_test_split(
    #     X_resampled, y_resampled, test_size=0.2, random_state=42
    # )
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )


    modelo = RandomForestRegressor(n_estimators=200, random_state=42)
    modelo.fit(X_train, y_train)

    y_pred = modelo.predict(X_test)

    print("🎯 Avaliação do modelo de regressão:")
    print(f"MAE: {mean_absolute_error(y_test, y_pred):.2f}")
    print(f"RMSE: {np.sqrt(mean_squared_error(y_test, y_pred)):.2f}")
    print(f"R²: {r2_score(y_test, y_pred):.2f}")

    joblib.dump(modelo, 'modelo_regressao_alvo.pkl')
    print("✅ Modelo salvo como modelo_regressao_alvo.pkl")

if __name__ == '__main__':
    treinar_modelo_regressao()
