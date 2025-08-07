import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Define os caminhos para as pastas principais a partir da raiz
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')
STYLES_DIR = os.path.join(ASSETS_DIR, 'styles.css')
# Define os caminhos para arquivos de dados específicos
FALHAS_CSV_PATH = os.path.join(DATA_DIR, 'dados_otimizados_falhas.csv')
OPE_CSV_PATH = os.path.join(DATA_DIR, 'dados_ope.csv')
CALENDARIO_CSV_PATH = os.path.join(DATA_DIR, 'calendario_produtivo.csv')
FEATURES_RUL_CSV_PATH = os.path.join(DATA_DIR, 'dados_features_rul.csv')

# Define os caminhos para os modelos e colunas
MODELO_PREDITIVO_PATH = os.path.join(MODELS_DIR, 'modelo_preditivo.joblib')
COLUNAS_MODELO_PATH = os.path.join(MODELS_DIR, 'colunas_modelo.joblib')
MODELO_RUL_PATH = os.path.join(MODELS_DIR, 'modelo_rul.joblib')
COLUNAS_RUL_PATH = os.path.join(MODELS_DIR, 'colunas_rul.joblib')


# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
DB_CONFIG = {
    'server': '172.29.138.147',
    'database': 'MPM_to_PBI',
    'user': 'mpm_pbi',
    'password': 'mpmpbi@2024'
}


# --- CONFIGURAÇÕES DA APLICAÇÃO ---
CORES = {
    "azul_escuro": "#243782",
    "laranja": "#e94e24",
    "verde_ope": "#43aaa0",
    "cinza_target": "#adb5bd"
}

MAPA_MESES = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}


# --- PARÂMETROS DE MACHINE LEARNING ---
BREAKDOWN_THRESHOLD_SECONDS = 600 # Limite em segundos para considerar uma parada como Breakdown
RUL_TIME_UNIT = 'D' # Unidade de tempo para agregação das features de RUL (Diária)