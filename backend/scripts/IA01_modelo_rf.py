import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from imblearn.over_sampling import SMOTE
import matplotlib.pyplot as plt
import seaborn as sns

import sys, os, django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import RecomendacaoSimulada

THRESHOLD = 0.35  # Probabilidade mínima para considerar recomendação

FEATURES_USADAS = [
    'score_reversao',
    'percentual_diferenca',
    'obv_crescente',
    'subindo_3dias',
    'volume_acima_media',
    'cruzamento_medias',
    'rsi_14',
    'retorno_5d',
    'media_volume_20d'
]

def treinar_modelo_ia():
    # Extrai os dados do banco
    dados = RecomendacaoSimulada.objects.all().values(*FEATURES_USADAS, 'atingiu_alvo')
    df = pd.DataFrame.from_records(dados)
    df = df.dropna()

    # Campos booleanos convertidos para int
    for col in ['obv_crescente', 'subindo_3dias', 'volume_acima_media', 'cruzamento_medias']:
        df[col] = df[col].astype(int)

    X = df[FEATURES_USADAS]
    y = df['atingiu_alvo'].astype(int)

    # Oversampling com SMOTE
    smote = SMOTE(random_state=42)
    X_resampled, y_resampled = smote.fit_resample(X, y)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_resampled, y_resampled, test_size=0.2, random_state=42
    )

    # Modelo
    modelo = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42)
    modelo.fit(X_train, y_train)

    # Avaliação com threshold customizado
    y_proba = modelo.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= THRESHOLD).astype(int)

    print(confusion_matrix(y_test, y_pred))
    print(classification_report(y_test, y_pred))

    # Importância das features
    importancias = pd.Series(modelo.feature_importances_, index=FEATURES_USADAS)
    print("\nImportância das features:")
    print(importancias.sort_values(ascending=False))

    # Gráfico
    sns.barplot(x=importancias.sort_values(), y=importancias.sort_values().index)
    plt.title("Importância das variáveis no modelo")
    plt.tight_layout()
    plt.show()

    # Salva o modelo para uso em produção
    joblib.dump(modelo, 'modelo_rf_simulado.pkl')

    return modelo

if __name__ == '__main__':
    treinar_modelo_ia()
