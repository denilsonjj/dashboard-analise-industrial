import pandas as pd
import numpy as np
import os
from datetime import timedelta

# --- CONFIGURAÇÕES ---
# Caminhos dos ficheiros
DATA_DIR = 'data'
FALHAS_CSV = os.path.join(DATA_DIR, 'dados_otimizados_falhas.csv')
FEATURES_CSV = os.path.join(DATA_DIR, 'dados_features_rul.csv') # Ficheiro de saída

# Parâmetros do modelo
TIME_UNIT = 'D' # Unidade de tempo para a nossa "linha do tempo" (D=Dia)
BREAKDOWN_THRESHOLD_SECONDS = 600 # 10 minutos

def create_rul_features():
    """
    Transforma o registo de falhas num dataset de time-series para prever o RUL (Remaining Useful Life).
    """
    print("Iniciando o processo de engenharia de features para RUL...")

    # --- 1. Carregar e Preparar os Dados Base ---
    try:
        df = pd.read_csv(FALHAS_CSV, sep=',', parse_dates=['StartTime', 'EndTime', 'EffectiveDay'])
        print("Dados de falhas carregados com sucesso.")
    except FileNotFoundError:
        print(f"ERRO: Ficheiro '{FALHAS_CSV}' não encontrado.")
        return

    # Identificar falhas graves (Breakdowns)
    df['is_breakdown'] = df['Duration'] >= BREAKDOWN_THRESHOLD_SECONDS

    # Usaremos ElementDesc como o nosso identificador único de equipamento
    df = df.dropna(subset=['ElementDesc', 'StartTime'])
    df = df.sort_values(by=['ElementDesc', 'StartTime'])

    # --- 2. Calcular o Alvo (Target): RUL ---
    # Para cada equipamento, encontrar a data do próximo breakdown
    df_breakdowns = df[df['is_breakdown']].copy()
    df_breakdowns['next_breakdown_date'] = df_breakdowns.groupby('ElementDesc')['StartTime'].shift(-1)
    
    # Juntar esta informação de volta ao dataframe principal
    df = pd.merge(df, df_breakdowns[['StartTime', 'ElementDesc', 'next_breakdown_date']], on=['StartTime', 'ElementDesc'], how='left')
    
    # Preencher a data do próximo breakdown para as linhas que não são breakdown
    df['next_breakdown_date'] = df.groupby('ElementDesc')['next_breakdown_date'].fillna(method='bfill')
    
    # Calcular RUL (Remaining Useful Life) em dias
    # Se não houver próximo breakdown, não podemos calcular o RUL para esse ciclo
    df_rul = df.dropna(subset=['next_breakdown_date']).copy()
    df_rul['RUL'] = (df_rul['next_breakdown_date'] - df_rul['StartTime']).dt.total_seconds() / (24 * 3600)
    
    print("Cálculo do RUL (alvo) concluído.")

    # --- 3. Criar Features Baseadas em Janelas de Tempo (Rolling Features) ---
    # Agrupar por equipamento e por dia
    df_agg = df_rul.set_index('StartTime').groupby(['ElementDesc', pd.Grouper(freq=TIME_UNIT)]).agg(
        num_paradas=('is_breakdown', 'count'),
        num_breakdowns=('is_breakdown', 'sum'),
        total_duration_parada=('Duration', 'sum')
    ).reset_index()

    df_agg = df_agg.sort_values(by=['ElementDesc', 'StartTime'])

    # Calcular features de janela móvel (ex: últimos 7 dias)
    rolling_windows = [7, 14, 30]
    for window in rolling_windows:
        print(f"Calculando features para janela de {window} dias...")
        df_agg[f'paradas_ultimos_{window}d'] = df_agg.groupby('ElementDesc')['num_paradas'].transform(
            lambda x: x.rolling(window, min_periods=1).sum()
        )
        df_agg[f'duracao_total_ultimos_{window}d'] = df_agg.groupby('ElementDesc')['total_duration_parada'].transform(
            lambda x: x.rolling(window, min_periods=1).sum()
        )

    # Feature: Tempo desde a última falha (qualquer tipo)
    df_agg['tempo_desde_ultima_parada'] = df_agg.groupby('ElementDesc')['StartTime'].diff().dt.total_seconds().fillna(0) / (24*3600)
    
    print("Cálculo de features de janela concluído.")

    # --- 4. Juntar Features e Alvo ---
    # Precisamos de alinhar o RUL com os dados agregados por dia
    # Vamos pegar o RUL no final de cada período de agregação (dia)
    df_rul_daily = df_rul.groupby(['ElementDesc', pd.Grouper(key='StartTime', freq=TIME_UNIT)])['RUL'].min().reset_index()
    
    # Juntar os dados
    df_final = pd.merge(df_agg, df_rul_daily, on=['ElementDesc', 'StartTime'])
    
    # Remover colunas intermédias
    df_final = df_final.drop(columns=['num_paradas', 'num_breakdowns', 'total_duration_parada'])

    # Remover linhas com RUL negativo (acontece no dia exato do breakdown) ou zero
    df_final = df_final[df_final['RUL'] > 0]
    
    # --- 5. Guardar o Dataset Final ---
    df_final.to_csv(FEATURES_CSV, index=False)
    print(f"Engenharia de features concluída! {len(df_final)} linhas de dados de treino foram geradas.")
    print(f"Dataset de features salvo em: '{FEATURES_CSV}'")
    print("\nExemplo do resultado:")
    print(df_final.head())


if __name__ == '__main__':
    create_rul_features()
