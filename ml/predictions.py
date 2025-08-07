import pandas as pd
import joblib
from datetime import datetime, timedelta

# Importa as configurações centralizadas
import config

# --- Carregamento dos Modelos e Colunas (Lazy Loading) ---
model_breakdown = None
columns_breakdown = None
model_rul = None
columns_rul = None

def carregar_modelo_breakdown():
    """Carrega o modelo de classificação de breakdown e suas colunas."""
    global model_breakdown, columns_breakdown
    if model_breakdown is None:
        try:
            model_breakdown = joblib.load(config.MODELO_PREDITIVO_PATH)
            columns_breakdown = joblib.load(config.COLUNAS_MODELO_PATH)
        except FileNotFoundError:
            return False
    return True

# ... (o resto das funções, como carregar_modelo_rul e prever_vida_util_restante, continua igual) ...
def carregar_modelo_rul():
    """Carrega o modelo de regressão de RUL e suas colunas."""
    global model_rul, columns_rul
    if model_rul is None:
        try:
            model_rul = joblib.load(config.MODELO_RUL_PATH)
            columns_rul = joblib.load(config.COLUNAS_RUL_PATH)
        except FileNotFoundError:
            return False
    return True

def prever_risco_breakdown(lista_componentes, turno_selecionado):
    """
    Recebe uma lista de componentes, calcula a probabilidade de breakdown para cada um
    e retorna um DataFrame com os resultados e os dados prontos para explicação.
    """
    if not carregar_modelo_breakdown():
        return None, None

    all_input_data = []
    for _, componente in lista_componentes.iterrows():
        input_data = {
            'LineGroupDesc': componente['LineGroupDesc'],
            'LineDesc': componente['LineDesc'],
            'StationDesc': componente['StationDesc'],
            'ElementDesc': componente['ElementDesc'],
            'ShiftId': turno_selecionado
        }
        all_input_data.append(input_data)
        
    if not all_input_data:
        return pd.DataFrame(), pd.DataFrame()

    input_df = pd.DataFrame(all_input_data).fillna('N/A')
    
    # Etapa 1: Codificação One-Hot consistente com o treinamento
    input_encoded = pd.get_dummies(input_df)
    
    # Etapa 2: Alinhamento com as colunas do modelo
    # Garantimos que todas as colunas que o modelo espera existam, preenchendo com 0 as que faltam.
    input_aligned = input_encoded.reindex(columns=columns_breakdown, fill_value=0)
    
    # Etapa 3 (Segurança): Forçar a conversão para tipo numérico antes de passar para o modelo
    input_aligned = input_aligned.astype(float)

    # Prever todas as probabilidades de uma vez para eficiência
    prediction_probas = model_breakdown.predict_proba(input_aligned)[:, 1]

    # Criar o dataframe de resultados
    df_riscos = lista_componentes[['StationDesc', 'ElementDesc']].copy()
    df_riscos['Probabilidade de Breakdown'] = prediction_probas
    df_riscos = df_riscos.sort_values(by='Probabilidade de Breakdown', ascending=False).reset_index(drop=True)
    
    # Reordenar o input_aligned para corresponder à ordem do df_riscos
    input_aligned_sorted = input_aligned.reindex(df_riscos.index)

    return df_riscos, input_aligned_sorted

def prever_vida_util_restante(df_features_filtrado):
    """
    Recebe um DataFrame de features para os componentes filtrados e prevê o RUL.
    """
    if not carregar_modelo_rul():
        return None 

    dados_recentes = df_features_filtrado.loc[df_features_filtrado.groupby('ElementDesc')['StartTime'].idxmax()].copy()

    if dados_recentes.empty:
        return pd.DataFrame()

    # Assegura que as colunas de features sejam numéricas
    features_para_prever = dados_recentes[columns_rul].astype(float)
    previsoes_rul = model_rul.predict(features_para_prever)
    dados_recentes['RUL_Previsto'] = previsoes_rul

    hoje = datetime.now().date()
    dados_recentes['Ultimo_Status_Data'] = pd.to_datetime(dados_recentes['StartTime']).dt.date
    dados_recentes['Data_Falha_Prevista'] = dados_recentes.apply(
        lambda row: row['Ultimo_Status_Data'] + timedelta(days=int(row['RUL_Previsto'])), axis=1
    )
    dados_recentes['Dias_Ate_Falha_Hoje'] = (pd.to_datetime(dados_recentes['Data_Falha_Prevista']) - pd.to_datetime(hoje)).dt.days

    relatorio = dados_recentes[['ElementDesc', 'Dias_Ate_Falha_Hoje', 'Data_Falha_Prevista', 'Ultimo_Status_Data']]
    relatorio.columns = ['Componente em Risco', 'Previsão (dias a partir de hoje)', 'Data Estimada da Falha Crítica', 'Baseado em Dados de']

    relatorio_futuro = relatorio[relatorio['Previsão (dias a partir de hoje)'] >= 0].sort_values(by='Previsão (dias a partir de hoje)')

    return relatorio_futuro