import streamlit as st
import pandas as pd
import os

# Importa o arquivo de configuração central
import config

# Importa as funções de UI e Cálculos
from utils.ui import (
    carregar_css,
    criar_tela_analise_mtbf,
    criar_tela_analise_mttr,
    criar_tela_analise_ope,
    exibir_kpis_falhas,
    criar_tela_analise_preditiva,
    criar_tela_analise_rul
)
from utils.calculations import (
    carregar_dados_falhas,
    carregar_dados_ope,
    obter_dados_filtrados  # <-- IMPORTANTE: Importamos a nova função
)
from ml import predictions

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard de Análise Industrial",
    page_icon="🛠️",
    layout="wide"
)

# Carrega o CSS
carregar_css('style.css')


# --- CARREGAMENTO INICIAL DOS DADOS ---
# Esta parte só roda uma vez graças ao session_state
if 'dados_carregados' not in st.session_state:
    st.session_state.dados_carregados = True
    
    df_falhas_base, df_calendario = carregar_dados_falhas()
    df_ope_base = carregar_dados_ope()
    df_features_rul = pd.read_csv(config.FEATURES_RUL_CSV_PATH)

    # Armazena os dados BRUTOS no estado da sessão
    st.session_state.df_falhas_base = df_falhas_base
    st.session_state.df_ope_base = df_ope_base
    st.session_state.df_calendario = df_calendario
    st.session_state.df_features_rul = df_features_rul
    
    print("Dados base e de features carregados e armazenados no session_state.")


# --- SIDEBAR DE FILTROS ---
with st.sidebar:
    st.header("Filtros de Análise")
    min_date = st.session_state.df_falhas_base['EffectiveDay'].min().date()
    max_date = st.session_state.df_falhas_base['EffectiveDay'].max().date()

    st.date_input("Data de Início", min_date, min_value=min_date, max_value=max_date, key="data_inicio")
    st.date_input("Data de Fim", max_date, min_value=min_date, max_value=max_date, key="data_fim")

    opcoes_grupo_linha = ["Todas"] + sorted([lg for lg in st.session_state.df_falhas_base['LineGroupDesc'].unique() if pd.notna(lg)])
    st.selectbox("Grupo de Linha", opcoes_grupo_linha, key="linegroup_selecionado")
    
    linhas_disponiveis = ["Todas"] + sorted(pd.concat([st.session_state.df_falhas_base['LineDesc'], st.session_state.df_ope_base['LineDesc']]).dropna().unique())
    st.selectbox("Linha", linhas_disponiveis, key="linha_selecionada")

    opcoes_shift = ["Todos"] + sorted(st.session_state.df_falhas_base['ShiftId'].dropna().unique().astype(int))
    shift_map = {1: "Turno 3", 2: "Turno 1", 3: "Turno 2"}
    st.selectbox("Turno", opcoes_shift, format_func=lambda id: shift_map.get(id, "Todos"), key="shift_selecionado_id")
    
    st.selectbox('Tipo de dia', options=['Todos', 'Produtivo', 'Improdutivo'], key="tipo_dia_selecionado")
    st.selectbox('Tipo de Parada', options=['Todas', 'Breakdown (>10 min)', 'Microparada (<10 min)'], key="tipo_parada_selecionado")
    st.selectbox('Filtro Stop-in-Go', options=['Sem Stop In Go', 'Com Stop In Go', 'Todos'], index=0, key="stopingo_selecionado")


# --- PROCESSAMENTO DOS DADOS FILTRADOS ---
df_falhas_filtrado, df_ope_filtrado = obter_dados_filtrados(
    st.session_state.df_falhas_base,
    st.session_state.df_ope_base,
    st.session_state.df_calendario,
    st.session_state.data_inicio,
    st.session_state.data_fim,
    st.session_state.linegroup_selecionado,
    st.session_state.linha_selecionada,
    st.session_state.shift_selecionado_id,
    st.session_state.tipo_dia_selecionado,
    st.session_state.tipo_parada_selecionado,
    st.session_state.stopingo_selecionado
)


# --- INÍCIO DO DASHBOARD ---   
st.title("Dashboard de Análise Industrial")
st.markdown("---")

main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
    "🔩 Análise de Falhas", 
    "⚙️ Análise de OPE", 
    "🤖 Risco de Breakdown", 
    "🔮 Previsão de Falha Crítica (RUL)"
])

with main_tab1:
    exibir_kpis_falhas(df_falhas_filtrado, st.session_state.df_calendario, config.CORES)
    st.markdown("---")
    
    tab_mtbf, tab_mttr = st.tabs(["📊 Análise de MTBF", "📈 Análise de MTTR"])
    with tab_mtbf:
        criar_tela_analise_mtbf(df_falhas_filtrado.copy(), st.session_state.df_calendario, config.CORES['azul_escuro'], config.MAPA_MESES)
    with tab_mttr:
        criar_tela_analise_mttr(df_falhas_filtrado.copy(), st.session_state.df_calendario, config.CORES['laranja'], config.MAPA_MESES)

with main_tab2:
    criar_tela_analise_ope(df_ope_filtrado, config.CORES, config.MAPA_MESES)

with main_tab3:
   criar_tela_analise_preditiva(df_falhas_filtrado)
   
with main_tab4:
    criar_tela_analise_rul(
        df_features=st.session_state.df_features_rul,
        df_falhas_filtrado=df_falhas_filtrado
    )