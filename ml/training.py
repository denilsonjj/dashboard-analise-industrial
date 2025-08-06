import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib
import os

def treinar_e_salvar_modelo():
    """
    Carrega os dados de falhas, cria features, treina um modelo de classificação
    e o salva em um arquivo para uso posterior pelo dashboard.
    """
    print("Iniciando o processo de treinamento do modelo de IA...")

    # Define os caminhos dos arquivos
    caminho_dados = os.path.join('data', 'dados_otimizados_falhas.csv')
    diretorio_modelos = 'models'
    caminho_modelo = os.path.join(diretorio_modelos, 'modelo_preditivo.joblib')
    caminho_colunas = os.path.join(diretorio_modelos, 'colunas_modelo.joblib')

    # Cria a pasta 'models' se ela não existir
    if not os.path.exists(diretorio_modelos):
        os.makedirs(diretorio_modelos)
        print(f"Diretório '{diretorio_modelos}' criado.")

    # --- 1. Carregamento de Dados ---
    try:
        df_falhas = pd.read_csv(caminho_dados, sep=',')
        print("Dados de falhas carregados com sucesso.")
    except FileNotFoundError:
        print(f"ERRO: Arquivo de dados não encontrado em '{caminho_dados}'.")
        print("Por favor, certifique-se que o arquivo 'dados_otimizados_falhas.csv' está na pasta 'data'.")
        return

    # --- 2. Engenharia de Features e Definição do Alvo ---
    # Alvo: Prever se uma parada será longa (Breakdown)
    df_falhas['Target'] = (df_falhas['Duration'] >= 600).astype(int) # 1 para Breakdown, 0 para Microparada

    # Features: Variáveis que o modelo usará para aprender
    features = ['LineGroupDesc', 'LineDesc', 'StationDesc', 'ElementDesc', 'ShiftId']

    # Lidar com valores nulos antes do one-hot encoding
    df_features = df_falhas[features].fillna('N/A')

    # Converter variáveis categóricas em numéricas (One-Hot Encoding)
    X = pd.get_dummies(df_features, drop_first=True)
    y = df_falhas['Target']
    print("Engenharia de features concluída.")

    # --- 3. Divisão dos Dados em Treino e Teste ---
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # --- 4. Treinamento do Modelo ---
    print("Iniciando o treinamento do modelo RandomForest...")
    # Usamos 'class_weight' para lidar com dados desbalanceados (se houver mais microparadas que breakdowns)
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced', n_jobs=-1)
    model.fit(X_train, y_train)
    print("Treinamento concluído.")

    # --- 5. Avaliação do Modelo (Opcional, mas recomendado) ---
    y_pred = model.predict(X_test)
    print("\n--- Avaliação do Modelo no Conjunto de Teste ---")
    print(classification_report(y_test, y_pred, target_names=['Microparada (<10min)', 'Breakdown (>10min)']))
    print("--------------------------------------------------\n")

    # --- 6. Salvando o Modelo e as Colunas ---
    joblib.dump(model, caminho_modelo)
    joblib.dump(X.columns, caminho_colunas)

    print(f"✅ Modelo salvo com sucesso em: '{caminho_modelo}'")
    print(f"✅ Colunas do modelo salvas em: '{caminho_colunas}'")


if __name__ == '__main__':
    treinar_e_salvar_modelo()