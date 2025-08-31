
# IA03_probabilidades_faixas.py
import sys, os, django
from datetime import date, timedelta
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from imblearn.over_sampling import SMOTE

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from cotacoes.models import RecomendacaoSimulada

FEATURES = [
    'score_reversao', 'percentual_diferenca', 'obv_crescente',
    'subindo_3dias', 'volume_acima_media', 'cruzamento_medias',
    'rsi_14', 'retorno_5d', 'media_volume_20d'
]

FAIXAS = {
    '1a2': (1, 2),
    '2a3': (2, 3),
    '3a4': (3, 4),
    '4a5': (4, 5),
}

def preparar_dataset():
    dados = RecomendacaoSimulada.objects.all().values(
        *FEATURES, 'fechamento', 'acao_id', 'data'
    )
    df = pd.DataFrame.from_records(dados)
    df = df.dropna()

    from cotacoes.models import Cotacao

    alvos = []
    for i, row in df.iterrows():
        cotacoes_futuras = Cotacao.objects.filter(
            acao_id=row['acao_id'],
            data__gt=row['data'],
            data__lte=row['data'] + timedelta(days=5)
        ).order_by('data')
        if not cotacoes_futuras.exists():
            alvos.append(None)
            continue
        max_high = max(c.maxima for c in cotacoes_futuras)
        perc = ((max_high / row['fechamento']) - 1) * 100
        alvos.append(perc)

    df['max_high_5d'] = alvos
    df = df.dropna()

    for nome, (min_v, max_v) in FAIXAS.items():
        df[f'faixa_{nome}'] = df['max_high_5d'].apply(lambda x: 1 if min_v <= x < max_v else 0)

    for col in ['obv_crescente', 'subindo_3dias', 'volume_acima_media', 'cruzamento_medias']:
        df[col] = df[col].astype(int)

    return df

def treinar_modelos_por_faixa(df):
    modelos = {}
    for nome in FAIXAS:
        print(f"Treinando modelo para faixa {nome}...")
        X = df[FEATURES]
        y = df[f'faixa_{nome}']

        sm = SMOTE(random_state=42)
        X_res, y_res = sm.fit_resample(X, y)

        X_train, X_test, y_train, y_test = train_test_split(X_res, y_res, test_size=0.2, random_state=42)

        modelo = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42)
        modelo.fit(X_train, y_train)

        y_pred = modelo.predict(X_test)
        print(classification_report(y_test, y_pred))

        joblib.dump(modelo, f'modelo_faixa_{nome}.pkl')
        modelos[nome] = modelo

    return modelos

if __name__ == '__main__':
    df = preparar_dataset()
    modelos = treinar_modelos_por_faixa(df)
    print("✅ Modelos treinados e salvos.")
