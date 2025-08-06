import streamlit as st
import pandas as pd
from datetime import timedelta
import os

# Importando as funções dos nossos módulos
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
    aplicar_filtros_geograficos,
    aplicar_filtro_stopingo,
    aplicar_filtros_ope
)

# --- CONFIGURAÇÕES GERAIS E ESTILO
st.set_page_config(
    page_title="Dashboard de Análise Industrial",
    page_icon="🛠️",
    layout="wide"
)

# Carrega o CSS
carregar_css('style.css')

# Constantes de estilo
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

# --- FUNÇÃO DE CALLBACK PARA ATUALIZAR OS DADOS ---
def atualizar_dados_filtrados():
    """
    Esta função é chamada APENAS quando um filtro da sidebar muda.
    Ela aplica os filtros e guarda os resultados no st.session_state.
    """
    st.session_state.df_falhas_filtrado = aplicar_filtros_geograficos(
        st.session_state.df_falhas_base[
            (st.session_state.df_falhas_base['EffectiveDay'].dt.date >= st.session_state.data_inicio) &
            (st.session_state.df_falhas_base['EffectiveDay'].dt.date <= st.session_state.data_fim)
        ],
        st.session_state.linegroup_selecionado,
        st.session_state.linha_selecionada,
        st.session_state.shift_selecionado_id,
        st.session_state.tipo_dia_selecionado,
        st.session_state.tipo_parada_selecionado,
        st.session_state.df_calendario
    )
    st.session_state.df_falhas_filtrado = aplicar_filtro_stopingo(st.session_state.df_falhas_filtrado, st.session_state.stopingo_selecionado)
    
    st.session_state.df_ope_filtrado = aplicar_filtros_ope(
        st.session_state.df_ope_base,
        st.session_state.data_inicio,
        st.session_state.data_fim,
        st.session_state.linha_selecionada,
        st.session_state.shift_selecionado_id,
        st.session_state.tipo_dia_selecionado,
        st.session_state.df_calendario
    )

# --- INICIALIZAÇÃO DO SESSION STATE ---
if 'dados_carregados' not in st.session_state:
    st.session_state.dados_carregados = True
    df_falhas_base, df_calendario = carregar_dados_falhas()
    df_ope_base = carregar_dados_ope()

    # --- LINHA ADICIONADA AQUI ---
    st.session_state.df_features_rul = pd.read_csv('data/dados_features_rul.csv')

    # Guarda os dataframes base na memória da sessão
    st.session_state.df_falhas_base = df_falhas_base
    st.session_state.df_ope_base = df_ope_base
    st.session_state.df_calendario = df_calendario

    print("Dados base e de features carregados e armazenados no session_state.")

# --- SIDEBAR DE FILTROS ---
with st.sidebar:
    st.header("Filtros de Análise")
    min_date = st.session_state.df_falhas_base['EffectiveDay'].min().date()
    max_date = st.session_state.df_falhas_base['EffectiveDay'].max().date()

    # Cada widget agora tem uma chave 'key' e chama a função de callback no 'on_change'
    st.date_input("Data de Início", min_date, min_value=min_date, max_value=max_date, key="data_inicio", on_change=atualizar_dados_filtrados)
    st.date_input("Data de Fim", max_date, min_value=min_date, max_value=max_date, key="data_fim", on_change=atualizar_dados_filtrados)

    opcoes_grupo_linha = ["Todas"] + sorted([lg for lg in st.session_state.df_falhas_base['LineGroupDesc'].unique() if pd.notna(lg)])
    st.selectbox("Grupo de Linha", opcoes_grupo_linha, key="linegroup_selecionado", on_change=atualizar_dados_filtrados)
    
    linhas_disponiveis = ["Todas"] + sorted(pd.concat([st.session_state.df_falhas_base['LineDesc'], st.session_state.df_ope_base['LineDesc']]).dropna().unique())
    st.selectbox("Linha", linhas_disponiveis, key="linha_selecionada", on_change=atualizar_dados_filtrados)

    opcoes_shift = ["Todos"] + sorted(st.session_state.df_falhas_base['ShiftId'].dropna().unique().astype(int))
    shift_map = {1: "Turno 1", 2: "Turno 2", 3: "Turno 3"}
    st.selectbox("Turno", opcoes_shift, format_func=lambda id: shift_map.get(id, "Todos"), key="shift_selecionado_id", on_change=atualizar_dados_filtrados)
    
    st.selectbox('Tipo de dia', options=['Todos', 'Produtivo', 'Improdutivo'], key="tipo_dia_selecionado", on_change=atualizar_dados_filtrados)
    st.selectbox('Tipo de Parada', options=['Todas', 'Breakdown (>10 min)', 'Microparada (<10 min)'], key="tipo_parada_selecionado", on_change=atualizar_dados_filtrados)
    st.selectbox('Filtro Stop-in-Go', options=['Sem Stop In Go', 'Com Stop In Go', 'Todos'], index=0, key="stopingo_selecionado", on_change=atualizar_dados_filtrados)

# --- CHAMA A FUNÇÃO DE ATUALIZAÇÃO UMA VEZ NA PRIMEIRA EXECUÇÃO ---
if 'df_falhas_filtrado' not in st.session_state:
    atualizar_dados_filtrados()
    print("Dados filtrados pela primeira vez.")

# --- LAYOUT PRINCIPAL ---
st.title("Dashboard de Análise Industrial")
st.markdown("---")

main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
    "🔩 Análise de Falhas", 
    "⚙️ Análise de OPE", 
    "🤖 Risco de Breakdown", 
    "🔮 Previsão de Falha Crítica (RUL)"
])

with main_tab1:
    contexto_texto = f"**Grupo:** {st.session_state.linegroup_selecionado}"
    # ... (o resto da sua lógica de contexto)
    st.markdown(f"<p style='text-align: center; color: grey;'>🔎 Visualizando: {contexto_texto}</p>", unsafe_allow_html=True)
    
    st.markdown("### Resumo do Período Selecionado")
    # As funções agora lêem os dados diretamente do session_state
    exibir_kpis_falhas(st.session_state.df_falhas_filtrado, st.session_state.df_calendario, CORES)
    st.markdown("---")
    
    tab_mtbf, tab_mttr = st.tabs(["📊 Análise de MTBF", "📈 Análise de MTTR"])
    with tab_mtbf:
        criar_tela_analise_mtbf(st.session_state.df_falhas_filtrado.copy(), st.session_state.df_calendario, CORES['azul_escuro'], MAPA_MESES)
    with tab_mttr:
        criar_tela_analise_mttr(st.session_state.df_falhas_filtrado.copy(), st.session_state.df_calendario, CORES['laranja'], MAPA_MESES)

with main_tab2:
    # ... (lógica de contexto da aba OPE)
    criar_tela_analise_ope(st.session_state.df_ope_filtrado, CORES, MAPA_MESES)

with main_tab3:
   criar_tela_analise_preditiva(st.session_state.df_falhas_filtrado)
with main_tab4:
    if 'df_features_rul' in st.session_state:
        # --- MODIFICAÇÃO APLICADA AQUI ---
        # Passamos o DataFrame que JÁ foi filtrado pela sidebar
        criar_tela_analise_rul(
            df_features=st.session_state.df_features_rul,
            df_falhas_filtrado=st.session_state.df_falhas_filtrado # Usamos o df já filtrado
        )
    else:
        st.error("Dados de features para RUL não foram carregados. Reinicie a aplicação.")