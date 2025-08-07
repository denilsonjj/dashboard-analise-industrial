import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib
import os
import sys

# Garante que o script encontre o config.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def treinar_e_salvar_modelo():
    """
    Carrega os dados de falhas, cria features, treina um modelo de classificação
    e o salva em um arquivo para uso posterior pelo dashboard.
    """
    print("Iniciando o processo de treinamento do modelo de IA...")

    # Cria a pasta 'models' se ela não existir
    if not os.path.exists(config.MODELS_DIR):
        os.makedirs(config.MODELS_DIR)
        print(f"Diretório '{config.MODELS_DIR}' criado.")

    # --- 1. Carregamento de Dados ---
    try:
        df_falhas = pd.read_csv(config.FALHAS_CSV_PATH, sep=',')
        print("Dados de falhas carregados com sucesso.")
    except FileNotFoundError:
        print(f"ERRO: Arquivo de dados não encontrado em '{config.FALHAS_CSV_PATH}'.")
        print("Certifique-se que o arquivo de dados existe.")
        return

    # --- 2. Engenharia de Features e Definição do Alvo ---
    # Alvo: Prever se uma parada será longa (Breakdown)
    df_falhas['Target'] = (df_falhas['Duration'] >= config.BREAKDOWN_THRESHOLD_SECONDS).astype(int)

    # Features: Variáveis que o modelo usará para aprender
    features = ['LineGroupDesc', 'LineDesc', 'StationDesc', 'ElementDesc', 'ShiftId']
    df_features = df_falhas[features].fillna('N/A')

    # Converter variáveis categóricas em numéricas (One-Hot Encoding)
    # REMOVIDO o drop_first=True para consistência com a previsão
    X = pd.get_dummies(df_features) 
    y = df_falhas['Target']
    print("Engenharia de features concluída.")

    # --- 3. Divisão dos Dados em Treino e Teste ---
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # --- 4. Treinamento do Modelo ---
    print("Iniciando o treinamento do modelo RandomForest...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced', n_jobs=-1)
    model.fit(X_train, y_train)
    print("Treinamento concluído.")

    # --- 5. Avaliação do Modelo ---
    y_pred = model.predict(X_test)
    print("\n--- Avaliação do Modelo no Conjunto de Teste ---")
    print(classification_report(y_test, y_pred, target_names=['Microparada', 'Breakdown']))
    print("--------------------------------------------------\n")

    # --- 6. Salvando o Modelo e as Colunas ---
    joblib.dump(model, config.MODELO_PREDITIVO_PATH)
    joblib.dump(X.columns.tolist(), config.COLUNAS_MODELO_PATH) # Salva como lista

    print(f"✅ Modelo salvo com sucesso em: '{config.MODELO_PREDITIVO_PATH}'")
    print(f"✅ Colunas do modelo salvas em: '{config.COLUNAS_MODELO_PATH}'")


if __name__ == '__main__':
    treinar_e_salvar_modelo()