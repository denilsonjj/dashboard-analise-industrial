import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# --- CONFIGURAÇÕES ---
DATA_DIR = 'data'
MODELS_DIR = 'models'
FEATURES_CSV = os.path.join(DATA_DIR, 'dados_features_rul.csv')
MODEL_PATH = os.path.join(MODELS_DIR, 'modelo_rul.joblib')
COLUMNS_PATH = os.path.join(MODELS_DIR, 'colunas_rul.joblib')

def train_rul_model():
    """
    Carrega os dados de features, treina um modelo de regressão para prever o RUL,
    e salva o modelo e as colunas para uso no dashboard.
    """
    print("Iniciando o treino do modelo de regressão RUL...")

    # --- 1. Carregar Dados ---
    try:
        df = pd.read_csv(FEATURES_CSV)
        print("Dataset de features carregado com sucesso.")
    except FileNotFoundError:
        print(f"ERRO: Ficheiro de features '{FEATURES_CSV}' não encontrado.")
        print("Por favor, execute o script 'ml/feature_engineering.py' primeiro.")
        return

   
    y = df['RUL']
    
    # As features (X) são todas as outras colunas, exceto o identificador do equipamento e a data
    X = df.drop(columns=['RUL', 'ElementDesc', 'StartTime'])

    # Guardar os nomes das colunas para uso na previsão
    model_columns = X.columns
    
    print(f"Dataset preparado com {X.shape[1]} features.")

    # --- 3. Dividir os Dados em Treino e Teste ---
    # 80% dos dados para treinar, 20% para validar a performance
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # --- 4. Treinar o Modelo de Regressão ---
    print("Treinando o modelo RandomForestRegressor...")
    # n_jobs=-1 usa todos os processadores disponíveis para acelerar o treino
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1, max_depth=10)
    model.fit(X_train, y_train)
    print("Treino concluído.")

    # --- 5. Avaliar o Modelo ---
    y_pred = model.predict(X_test)
    
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print("\n--- Avaliação do Modelo no Conjunto de Teste ---")
    print(f"Erro Médio Absoluto (MAE): {mae:.2f} dias")
    print(f"  -> Em média, as previsões do modelo erram por +/- {mae:.2f} dias.")
    print(f"Coeficiente de Determinação (R²): {r2:.2%}")
    print(f"  -> O modelo consegue explicar {r2:.2%} da variância nos dados de RUL.")
    print("--------------------------------------------------\n")

    # --- 6. Salvar o Modelo e as Colunas ---
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(model_columns, COLUMNS_PATH)

    print(f"✅ Modelo de RUL salvo com sucesso em: '{MODEL_PATH}'")
    print(f"✅ Colunas do modelo de RUL salvas em: '{COLUMNS_PATH}'")

if __name__ == '__main__':
    train_rul_model()