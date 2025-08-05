import streamlit as st
import pandas as pd
import pymssql
import os
from datetime import timedelta
import altair as alt
import matplotlib.pyplot as plt
import io
import base64
from streamlit_echarts import st_echarts

# --- CONFIGURAÇÕES GERAIS E ESTILO 
st.set_page_config(
    page_title="Dashboard de Análise de Falhas",
    page_icon="🛠️",
    layout="wide"
)

cores = {
    "azul_escuro": "#243782",
    "laranja": "#e94e24",
     "verde_ope": "#43aaa0",      
    "cinza_target": "#adb5bd"   
}

mapa_meses = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}

# --- FUNÇÕES UTILITÁRIAS ---

def carregar_css(caminho_arquivo):
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Arquivo CSS '{caminho_arquivo}' não encontrado.")

def ler_html(caminho_arquivo):
    """Lê o conteúdo de um arquivo HTML e o retorna como uma string."""
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning(f"Arquivo de template '{caminho_arquivo}' não encontrado.")
        return """
        <div class="kpi-card">
            <div class="kpi-title">{{titulo}}</div>
            <div class="kpi-value">{{valor}}</div>
            <div class="sparkline-container">
                <img src="{{sparkline_base64}}">
            </div>
            <div class="kpi-variation">{{variacao_texto}}</div>
        </div>
        """
def ler_html(caminho_arquivo):
    """Lê o conteúdo de um arquivo HTML e o retorna como uma string."""
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning(f"Arquivo de template '{caminho_arquivo}' não encontrado.")
        return """
        <div class="kpi-card">
            <div class="kpi-title">{{titulo}}</div>
            <div class="kpi-value">{{valor}}</div>
        </div>
        """
@st.cache_data
def convert_df_to_csv(df):
    """Converte um DataFrame para CSV, otimizado para cache."""
    return df.to_csv(index=False, sep=';').encode('utf-8-sig')

def gerar_sparkline_base64(data, cor_linha):
    """Gera um gráfico de linha simples (sparkline) e retorna como uma imagem Base64."""
    if data.empty or len(data) < 2:
        return ""
    
    fig, ax = plt.subplots(figsize=(4, 0.8), dpi=80)
    ax.plot(data, color=cor_linha, linewidth=2)
    
    ax.set_yticklabels([])
    ax.set_xticklabels([])
    ax.tick_params(axis='both', which='both', length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"

# --- CARREGAMENTO E PROCESSAMENTO DE DADOS ---

@st.cache_data(ttl=3600)
def carregar_dados_falhas():
    arquivo_csv = 'dados_otimizados_falhas.csv'
    df_calendario = pd.read_csv('calendario_produtivo.csv', sep=',')
    df_calendario['Data'] = pd.to_datetime(df_calendario['Data'])

    if os.path.exists(arquivo_csv):
        df = pd.read_csv(arquivo_csv, sep=',')
    else:
        db_config = {
            'server': '172.29.138.147', 'database': 'MPM_to_PBI',
            'user': 'mpm_pbi', 'password': 'mpmpbi@2024',
        }
        sql_query = """
        WITH
        FonteBruta AS (SELECT ElementDesc, LineGroupDesc, LineDesc, StatusDesc, AlarmDesc, Duration, StartTime, EndTime, EffectiveDay, StationDesc, ShiftId FROM vw_Lista_Estados_Montagem WHERE LineGroupDesc IN ('MAIN LINE', 'SUBASSEMBLY') AND EffectiveDay >= '2025-01-01' AND StatusDesc = 'Falha/Parada'),
        FalhasComEndTimeAnterior AS (SELECT *, LAG(EndTime, 1) OVER (PARTITION BY LineDesc, StationDesc, ElementDesc, AlarmDesc ORDER BY StartTime) AS EndTimeAnterior FROM FonteBruta),
        MarcadorDeNovoGrupo AS (SELECT *, CASE WHEN EndTimeAnterior IS NULL OR DATEDIFF(minute, EndTimeAnterior, StartTime) > 5 THEN 1 ELSE 0 END AS IniciouNovoGrupo FROM FalhasComEndTimeAnterior),
        IDGrupoFase1 AS (SELECT *, SUM(IniciouNovoGrupo) OVER (ORDER BY StartTime, LineDesc, StationDesc, ElementDesc) AS IDGrupoNumerico FROM MarcadorDeNovoGrupo),
        DadosAnterioresEquipamento AS (SELECT *, LAG(IDGrupoNumerico, 1) OVER (PARTITION BY LineDesc, StationDesc, ElementDesc ORDER BY StartTime) AS Prev_ID, LAG(EndTime, 1) OVER (PARTITION BY LineDesc, StationDesc, ElementDesc ORDER BY StartTime) AS Prev_EndTime FROM IDGrupoFase1),
        IDGrupoFinal AS (SELECT *, CASE WHEN AlarmDesc = 'TIME OUT APERTURA SAFETY GATE' AND DATEDIFF(minute, Prev_EndTime, StartTime) <= 5 THEN Prev_ID ELSE IDGrupoNumerico END AS IDGrupoFinal FROM DadosAnterioresEquipamento),
        IDAmigavelData AS (SELECT *, FIRST_VALUE(AlarmDesc) OVER (PARTITION BY IDGrupoFinal ORDER BY StartTime) AS PrimeiroAlarmDesc, FIRST_VALUE(ElementDesc) OVER (PARTITION BY IDGrupoFinal ORDER BY StartTime) AS PrimeiroElementDesc FROM IDGrupoFinal)
        SELECT * FROM IDAmigavelData ORDER BY StartTime;
        """
        try:
            with st.spinner("Buscando dados otimizados do banco de dados..."):
                conn = pymssql.connect(**db_config)
                df = pd.read_sql_query(sql_query, conn)
                conn.close()
                df.to_csv(arquivo_csv, index=False, sep=',')
                st.success("Dados buscados e salvos localmente!")
        except Exception as e:
            st.error(f"Falha ao buscar dados do banco de dados: {e}")
            return None, None
            
    df['StartTime'] = pd.to_datetime(df['StartTime'])
    df['EndTime'] = pd.to_datetime(df['EndTime'])
    df['EffectiveDay'] = pd.to_datetime(df['EffectiveDay'])
    return df, df_calendario

def calcular_metricas_kpi(df_falhas_filtradas, df_calendario):
    if df_falhas_filtradas.empty:
        return {'mttr_minutos': 0, 'mtbf_minutos': 0}
    df_main_line_falhas = df_falhas_filtradas[(df_falhas_filtradas['StatusDesc'] == "Falha/Parada") & (df_falhas_filtradas['LineGroupDesc'] == "MAIN LINE")]
    numero_de_falhas = len(df_main_line_falhas)
    df_falha_parada = df_falhas_filtradas[df_falhas_filtradas['StatusDesc'] == "Falha/Parada"]
    total_downtime_minutos = df_falha_parada['Duration'].sum() / 60
    df_copy = df_falhas_filtradas.copy()
    df_copy['EffectiveDay'] = pd.to_datetime(df_copy['EffectiveDay'])
    dias_e_turnos_unicos = df_copy[['EffectiveDay', 'ShiftId']].drop_duplicates()
    dias_e_turnos_unicos['weekday'] = dias_e_turnos_unicos['EffectiveDay'].dt.weekday + 1
    total_uptime_minutos = 0
    minutos_por_turno = {1: 8 * 60, 2: 8 * 60, 3: 5 * 60}
    for _, row in dias_e_turnos_unicos.iterrows():
        total_uptime_minutos += 4 * 60 if row['weekday'] == 7 else minutos_por_turno.get(row['ShiftId'], 0)
    mttr_minutos = total_downtime_minutos / numero_de_falhas if numero_de_falhas > 0 else 0
    mtbf_minutos = total_uptime_minutos / numero_de_falhas if numero_de_falhas > 0 else total_uptime_minutos
    return {'mttr_minutos': mttr_minutos, 'mtbf_minutos': mtbf_minutos}
def criar_grafico_gauge(valor_ope, cor_principal):
    
    """Cria o dicionário de opções para um gráfico de medidor (gauge) do ECharts."""
    options = {
        "tooltip": {
            "formatter": '{a} <br/>{b} : {c}%'
        },
        "series": [
            {
                "name": 'OPE',
                "type": 'gauge',
                "startAngle": 180,
                "endAngle": 0,
                "center": ["50%", "75%"],
                "radius": "110%",
                "axisLine": {
                    "lineStyle": {
                        "width": 20,
                        "color": [
                            [0.7, '#dc3545'],  # Vermelho até 70%
                            [0.85, '#ffc107'], # Amarelo até 85%
                            [1, '#28a745']    # Verde até 100%
                        ]
                    }
                },
                "pointer": {
                    "itemStyle": {"color": "auto"},
                    "width": 5,
                },
                "axisTick": {"show": False},
                "splitLine": {"show": False},
                "axisLabel": {"show": False},
                "detail": {
                    "valueAnimation": True,
                    "formatter": '{value:.2f}%',
                    "fontSize": 24,
                    "fontWeight": "bold",
                    "offsetCenter": [0, '-15%']
                },
                "data": [{
                    "value": valor_ope,
                    "name": 'OPE Geral'
                }]
            }
        ]
    }
    return options
# --- FUNÇÕES DE VISUALIZAÇÃO ---

def criar_tela_analise_mtbf(df, df_calendario, cor_principal):
    if df.empty:
        st.info("Sem dados para análise de MTBF na seleção atual.")
        return

    st.markdown('<p class="chart-title">MTBF POR LINHA</p>', unsafe_allow_html=True)
    mtbf_por_linha_df = df.groupby('LineDesc').apply(lambda x: calcular_metricas_kpi(x, df_calendario)).apply(pd.Series)
    mtbf_por_linha_df = mtbf_por_linha_df[['mtbf_minutos']].sort_values(by='mtbf_minutos', ascending=False).reset_index()
    mtbf_por_linha_df.rename(columns={'LineDesc': 'Linha', 'mtbf_minutos': 'MTBF (minutos)'}, inplace=True)
    if not mtbf_por_linha_df.empty:
        chart = alt.Chart(mtbf_por_linha_df).mark_bar(color=cor_principal).encode(
            x=alt.X('Linha:N', sort='-y', title='Linha de Produção'),
            y=alt.Y('MTBF (minutos):Q', title='MTBF (minutos)', axis=alt.Axis(format='.2f')),
            tooltip=[alt.Tooltip('Linha'), alt.Tooltip('MTBF (minutos)', format='.2f')]
        ).configure_axis(grid=False).configure_view(strokeOpacity=0)
        st.altair_chart(chart, use_container_width=True)
        csv = convert_df_to_csv(mtbf_por_linha_df)
        st.download_button(label="📥 Exportar Dados", data=csv, file_name='mtbf_por_linha.csv', mime='text/csv', key='download_mtbf_linha')

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown('<p class="chart-title">MTBF MENSAL</p>', unsafe_allow_html=True)
        df['MesNum'] = df['EffectiveDay'].dt.month
        mtbf_mensal_df = df.groupby('MesNum').apply(lambda x: calcular_metricas_kpi(x, df_calendario)).apply(pd.Series).reset_index()
        mtbf_mensal_df['Mes'] = mtbf_mensal_df['MesNum'].map(mapa_meses)
        if not mtbf_mensal_df.empty:
            chart_mensal = alt.Chart(mtbf_mensal_df).mark_bar(color=cor_principal).encode(
                x=alt.X('Mes:N', sort=None, title="Mês"),
                y=alt.Y('mtbf_minutos:Q', title="MTBF (minutos)", axis=alt.Axis(format='.2f')),
                tooltip=[alt.Tooltip('Mes'), alt.Tooltip('mtbf_minutos', title='MTBF (minutos)', format='.2f')]
            ).configure_axis(grid=False).configure_view(strokeOpacity=0)
            st.altair_chart(chart_mensal, use_container_width=True)
            csv = convert_df_to_csv(mtbf_mensal_df)
            st.download_button(label="📥 Exportar Dados", data=csv, file_name='mtbf_mensal.csv', mime='text/csv', key='download_mtbf_mensal')

    with col2:
        st.markdown('<p class="chart-title">MTBF POR SEMANA</p>', unsafe_allow_html=True)
        df_semanal = df.copy()
        df_semanal['SemanaNum'] = df_semanal['EffectiveDay'].dt.isocalendar().week
        mtbf_semanal_df = df_semanal.groupby('SemanaNum').apply(lambda x: calcular_metricas_kpi(x, df_calendario)).apply(pd.Series).reset_index()
        mtbf_semanal_df['SemanaLabel'] = 'WK-' + mtbf_semanal_df['SemanaNum'].astype(str)
        if not mtbf_semanal_df.empty:
            chart_semanal = alt.Chart(mtbf_semanal_df).mark_line(point=True, color=cor_principal).encode(
                x=alt.X('SemanaLabel:N', sort=alt.EncodingSortField(field="SemanaNum", order="ascending"), title="Semana"),
                y=alt.Y('mtbf_minutos:Q', title="MTBF (minutos)", axis=alt.Axis(format='.2f')),
                tooltip=['SemanaLabel', alt.Tooltip('mtbf_minutos', title='MTBF (minutos)', format='.2f')]
            ).configure_axis(grid=False).configure_view(strokeOpacity=0)
            st.altair_chart(chart_semanal, use_container_width=True)
            csv = convert_df_to_csv(mtbf_semanal_df)
            st.download_button(label="📥 Exportar Dados", data=csv, file_name='mtbf_semanal.csv', mime='text/csv', key='download_mtbf_semanal')

    col3, col4 = st.columns(2, gap="large")
    with col3:
        st.markdown('<p class="chart-title">TOP 3 FALHAS (POR OCORRÊNCIA)</p>', unsafe_allow_html=True)
        top_3_falhas_df = df.groupby('PrimeiroAlarmDesc').size().nlargest(3).reset_index(name='Número de Falhas')
        top_3_falhas_df.rename(columns={'PrimeiroAlarmDesc': 'Descrição da Falha'}, inplace=True)
        top_3_falhas_df['Descrição Curta'] = top_3_falhas_df['Descrição da Falha'].str.slice(0, 50) + '...'
        if not top_3_falhas_df.empty:
            chart_top3 = alt.Chart(top_3_falhas_df).mark_bar(color=cor_principal).encode(
                x=alt.X('Número de Falhas:Q'),
                y=alt.Y('Descrição Curta:N', sort='-x', title=None),
                tooltip=['Descrição da Falha', 'Número de Falhas']
            ).configure_axis(grid=False).configure_view(strokeOpacity=0)
            st.altair_chart(chart_top3, use_container_width=True)
            csv = convert_df_to_csv(top_3_falhas_df[['Descrição da Falha', 'Número de Falhas']])
            st.download_button(label="📥 Exportar Dados", data=csv, file_name='top_3_falhas_mtbf.csv', mime='text/csv', key='download_top3_mtbf')

    with col4:
        st.markdown('<p class="chart-title">COMPONENTES</p>', unsafe_allow_html=True)
        with st.expander("🔍 Ver/Ocultar Análise por Componentes"):
            mtbf_por_componente_df = df.groupby('ElementDesc').apply(lambda x: calcular_metricas_kpi(x, df_calendario)).apply(pd.Series)
            component_data_df = mtbf_por_componente_df[['mtbf_minutos']].sort_values(by='mtbf_minutos', ascending=True).reset_index()
            component_data_df.rename(columns={'ElementDesc': 'COMPONENTE', 'mtbf_minutos': 'MTBF'}, inplace=True)
            if not component_data_df.empty:
                st.dataframe(component_data_df, use_container_width=True, hide_index=True, column_config={"MTBF": st.column_config.NumberColumn(format="%.2f")})
                csv = convert_df_to_csv(component_data_df)
                st.download_button(label="📥 Exportar Dados", data=csv, file_name='mtbf_por_componente.csv', mime='text/csv', key='download_componentes_mtbf_expander')

def criar_tela_analise_mttr(df, df_calendario, cor_principal):
    if df.empty:
        st.info("Sem dados para análise de MTTR na seleção atual.")
        return
    st.markdown('<p class="chart-title">MTTR POR LINHA</p>', unsafe_allow_html=True)
    mttr_por_linha_df = df.groupby('LineDesc').apply(lambda x: calcular_metricas_kpi(x, df_calendario)).apply(pd.Series)
    mttr_por_linha_df = mttr_por_linha_df[['mttr_minutos']].sort_values(by='mttr_minutos', ascending=False).reset_index()
    mttr_por_linha_df.rename(columns={'LineDesc': 'Linha', 'mttr_minutos': 'MTTR (minutos)'}, inplace=True)
    if not mttr_por_linha_df.empty:
        chart = alt.Chart(mttr_por_linha_df).mark_bar(color=cor_principal).encode(
            x=alt.X('Linha:N', sort='-y', title='Linha de Produção'),
            y=alt.Y('MTTR (minutos):Q', title='MTTR (minutos)', axis=alt.Axis(format='.2f')),
            tooltip=['Linha', alt.Tooltip('MTTR (minutos)', format='.2f')]
        ).configure_axis(grid=False).configure_view(strokeOpacity=0)
        st.altair_chart(chart, use_container_width=True)
        csv = convert_df_to_csv(mttr_por_linha_df)
        st.download_button(label="📥 Exportar Dados", data=csv, file_name='mttr_por_linha.csv', mime='text/csv', key='download_mttr_linha')

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown('<p class="chart-title">MTTR MENSAL</p>', unsafe_allow_html=True)
        df['MesNum'] = df['EffectiveDay'].dt.month
        mttr_mensal_df = df.groupby('MesNum').apply(lambda x: calcular_metricas_kpi(x, df_calendario)).apply(pd.Series).reset_index()
        mttr_mensal_df['Mes'] = mttr_mensal_df['MesNum'].map(mapa_meses)
        if not mttr_mensal_df.empty:
            chart_mensal = alt.Chart(mttr_mensal_df).mark_bar(color=cor_principal).encode(
                x=alt.X('Mes:N', sort=None, title="Mês"),
                y=alt.Y('mttr_minutos:Q', title="MTTR (minutos)", axis=alt.Axis(format='.2f')),
                tooltip=[alt.Tooltip('Mes'), alt.Tooltip('mttr_minutos', title='MTTR (minutos)', format='.2f')]
            ).configure_axis(grid=False).configure_view(strokeOpacity=0)
            st.altair_chart(chart_mensal, use_container_width=True)
            csv = convert_df_to_csv(mttr_mensal_df)
            st.download_button(label="📥 Exportar Dados", data=csv, file_name='mttr_mensal.csv', mime='text/csv', key='download_mttr_mensal')

    with col2:
        st.markdown('<p class="chart-title">MTTR POR SEMANA</p>', unsafe_allow_html=True)
        df_semanal = df.copy()
        df_semanal['SemanaNum'] = df_semanal['EffectiveDay'].dt.isocalendar().week
        mttr_semanal_df = df_semanal.groupby('SemanaNum').apply(lambda x: calcular_metricas_kpi(x, df_calendario)).apply(pd.Series).reset_index()
        mttr_semanal_df['SemanaLabel'] = 'WK-' + mttr_semanal_df['SemanaNum'].astype(str)
        if not mttr_semanal_df.empty:
            chart_semanal = alt.Chart(mttr_semanal_df).mark_line(point=True, color=cor_principal).encode(
                x=alt.X('SemanaLabel:N', sort=alt.EncodingSortField(field="SemanaNum", order="ascending"), title="Semana"),
                y=alt.Y('mttr_minutos:Q', title="MTTR (minutos)", axis=alt.Axis(format='.2f')),
                tooltip=['SemanaLabel', alt.Tooltip('mttr_minutos', title='MTTR (minutos)', format='.2f')]
            ).configure_axis(grid=False).configure_view(strokeOpacity=0)
            st.altair_chart(chart_semanal, use_container_width=True)
            csv = convert_df_to_csv(mttr_semanal_df)
            st.download_button(label="📥 Exportar Dados", data=csv, file_name='mttr_semanal.csv', mime='text/csv', key='download_mttr_semanal')

    col3, col4 = st.columns(2, gap="large")
    with col3:
        st.markdown('<p class="chart-title">TOP 3 MTTR</p>', unsafe_allow_html=True)
        mttr_por_falha_df = df.groupby('PrimeiroAlarmDesc').apply(lambda x: calcular_metricas_kpi(x, df_calendario)).apply(pd.Series)
        top_3_falhas_mttr_df = mttr_por_falha_df[['mttr_minutos']].nlargest(3, 'mttr_minutos').reset_index()
        top_3_falhas_mttr_df.rename(columns={'PrimeiroAlarmDesc': 'Descrição da Falha', 'mttr_minutos': 'MTTR Médio (minutos)'}, inplace=True)
        if not top_3_falhas_mttr_df.empty:
            chart_top3 = alt.Chart(top_3_falhas_mttr_df).mark_bar(color=cor_principal).encode(
                x=alt.X('MTTR Médio (minutos):Q', axis=alt.Axis(format='.2f')),
                y=alt.Y('Descrição da Falha:N', sort='-x', title=None, axis=alt.Axis(labels=False)),
                tooltip=['Descrição da Falha', alt.Tooltip('MTTR Médio (minutos)', format='.2f')]
            ).configure_axis(grid=False).configure_view(strokeOpacity=0)
            st.altair_chart(chart_top3, use_container_width=True)
            csv = convert_df_to_csv(top_3_falhas_mttr_df)
            st.download_button(label="📥 Exportar Dados", data=csv, file_name='top_3_falhas_mttr.csv', mime='text/csv', key='download_top3_mttr')

    with col4:
        st.markdown('<p class="chart-title">COMPONENTES</p>', unsafe_allow_html=True)
        with st.expander("🔍 Ver/Ocultar Análise por Componentes"):
            mttr_por_componente_df = df.groupby('ElementDesc').apply(lambda x: calcular_metricas_kpi(x, df_calendario)).apply(pd.Series)
            component_data_df = mttr_por_componente_df[['mttr_minutos']].sort_values(by='mttr_minutos', ascending=False).reset_index()
            component_data_df.rename(columns={'ElementDesc': 'COMPONENTE', 'mttr_minutos': 'MTTR'}, inplace=True)
            if not component_data_df.empty:
                st.dataframe(component_data_df, use_container_width=True, hide_index=True, column_config={"MTTR": st.column_config.NumberColumn(format="%.2f")})
                csv = convert_df_to_csv(component_data_df)
                st.download_button(label="📥 Exportar Dados", data=csv, file_name='mttr_por_componente.csv', mime='text/csv', key='download_componentes_mttr_expander')

# --- FUNÇÕES DE FILTRAGEM ---

def aplicar_filtros_geograficos(df, grupo, linha, shift, tipo_dia, tipo_parada, df_calendario):
    df_filtrado = df.copy()
    if grupo != "Todas": df_filtrado = df_filtrado[df_filtrado['LineGroupDesc'] == grupo]
    if linha != "Todas": df_filtrado = df_filtrado[df_filtrado['LineDesc'] == linha]
    if shift != "Todos": df_filtrado = df_filtrado[df_filtrado['ShiftId'] == shift]
    if tipo_dia != "Todos":
        datas_filtradas = df_calendario[df_calendario['Tipo'] == tipo_dia]['Data'].dt.date
        df_filtrado = df_filtrado[df_filtrado['EffectiveDay'].dt.date.isin(datas_filtradas)]
    if tipo_parada == 'Breakdown (>10 min)': df_filtrado = df_filtrado[df_filtrado['Duration'] >= 600]
    elif tipo_parada == 'Microparada (<10 min)': df_filtrado = df_filtrado[df_filtrado['Duration'] < 600]
    return df_filtrado

def aplicar_filtro_stopingo(df, tipo_selecionado='Sem Stop In Go'):
    if tipo_selecionado == 'Todos': return df.copy()
    df_copy = df.copy()
    for col in ['LineDesc', 'StationDesc', 'ElementDesc']: df_copy[col] = df_copy[col].fillna('')
    cond1 = (df_copy['LineDesc'].str.contains("GLAZING",case=False))&(df_copy['StationDesc'].str.contains("ZNE05",case=False))&(df_copy['ElementDesc'].isin(["TTS02","TTS04","TTS05"]))
    cond2 = (df_copy['LineDesc'].str.contains("DECKING",case=False))&(df_copy['StationDesc'].str.contains("ZNE07",case=False))&(df_copy['ElementDesc'].isin(["TR01","TR02","TR03","TR04","TR05","TR06","TR07","PLS03"]))
    cond3 = (df_copy['LineDesc'].str.contains("CHASSIS5",case=False))&(df_copy['StationDesc'].str.contains("ZNE01",case=False))
    cond4 = (df_copy['LineDesc'].str.contains("CHASSIS4",case=False))&(df_copy['StationDesc'].str.contains("ZNE02",case=False))
    cond5 = (df_copy['LineDesc'].str.contains("CHASSIS2",case=False))&(df_copy['StationDesc'].str.contains("ZNE06",case=False))
    cond6 = df_copy['ElementDesc'].isin(["PLS01","PLS02","PLS_02","PLS03","PLS04","PLS05","PLS06","PLS07","PLS08","PLS09","PLS10","PLS11","PLS12","PLS13"])
    cond7 = df_copy['StationDesc'].str.contains("ZNE07",case=False)
    indices = df_copy[cond1 | cond2 | cond3 | cond4 | cond5 | cond6 | cond7].index
    if tipo_selecionado == 'Com Stop In Go': return df_copy.loc[indices]
    elif tipo_selecionado == 'Sem Stop In Go': return df_copy.drop(indices)
    return df_copy

def aplicar_filtros_ope(df, data_inicio, data_fim, linha, shift, tipo_dia, df_calendario):
    """Aplica os filtros da sidebar aos dados de OPE."""
    df_filtrado = df.copy()
    
    # Filtro de Data
    df_filtrado = df_filtrado[
        (df_filtrado['EffectiveDate'].dt.date >= data_inicio) & 
        (df_filtrado['EffectiveDate'].dt.date <= data_fim)
    ]

    # Filtros de hierarquia
    if linha != "Todas":
        df_filtrado = df_filtrado[df_filtrado['LineDesc'] == linha]
    if shift != "Todos":
        df_filtrado = df_filtrado[df_filtrado['ShiftId'] == shift]
        
    # Filtro de tipo de dia (produtivo/improdutivo)
    if tipo_dia != "Todos":
        datas_filtradas = df_calendario[df_calendario['Tipo'] == tipo_dia]['Data'].dt.date
        df_filtrado = df_filtrado[df_filtrado['EffectiveDate'].dt.date.isin(datas_filtradas)]
        
    return df_filtrado
@st.cache_data(ttl=3600)
def carregar_dados_ope():
    arquivo_csv = 'dados_ope.csv'
    if os.path.exists(arquivo_csv):
        df = pd.read_csv(arquivo_csv, sep=';')
    else:
        db_config = {'server': '172.29.138.147', 'database': 'MPM_to_PBI', 'user': 'mpm_pbi', 'password': 'mpmpbi@2024'}
        filtro_linhas = "'CHASSIS 4', 'CHASSIS1', 'CHASSIS2', 'CHASSIS3', 'CHASSIS5', 'DECKING DOWN', 'DECKING UP', 'FINAL1', 'FINAL2', 'GLAZING', 'GOMA', 'GOMP', 'TRIM 0', 'TRIM 1', 'TRIM 2'"
        filtro_datas_excluidas = "'2025-02-28', '2025-03-01', '2025-03-02', '2025-03-03', '2025-03-04', '2025-03-05', '2025-03-06', '2025-03-07', '2025-03-08', '2025-03-09', '2025-03-10', '2025-05-01'"
        sql_query = f"SELECT * FROM vw_Resumo_prod_Montagem WHERE LineDesc IN ({filtro_linhas}) AND CONVERT(date, EffectiveDate) NOT IN ({filtro_datas_excluidas}) AND EffectiveProd > 9;"
        try:
            with st.spinner("Buscando dados de OPE do banco de dados..."):
                conn = pymssql.connect(**db_config)
                df = pd.read_sql_query(sql_query, conn)
                conn.close()
                df.to_csv(arquivo_csv, index=False, sep=';')
                st.success("Dados de OPE buscados e salvos localmente!")
        except Exception as e:
            st.error(f"Falha ao buscar dados de OPE: {e}"); return None
            
    df['EffectiveDate'] = pd.to_datetime(df['EffectiveDate'], errors='coerce')
    return df

def calcular_metricas_ope(df_ope_filtrado):
    if df_ope_filtrado.empty:
        return {'ope': 0, 'pecas_boas': 0, 'pecas_ruins': 0, 'total_produzido': 0}
    total_produzido = df_ope_filtrado['EffectiveProd'].sum()
    target_producao = df_ope_filtrado['TargProd'].sum()
    pecas_boas = total_produzido 
    pecas_ruins = 0
    ope = (total_produzido / target_producao) * 100 if target_producao > 0 else 0
    return {'ope': ope, 'pecas_boas': pecas_boas, 'pecas_ruins': pecas_ruins, 'total_produzido': total_produzido}


# Substitua sua função criar_tela_analise_ope inteira por esta versão atualizada

# Substitua sua função criar_tela_analise_ope inteira por esta nova versão

def criar_tela_analise_ope(df):
    if df.empty:
        st.warning("Nenhum dado de OPE para os filtros selecionados."); return

    # --- KPIs GERAIS (Mantidos no topo) ---
    st.markdown("### Resumo do Período Selecionado")
    metricas = calcular_metricas_ope(df)
    card_template = ler_html('card_template.html')
    card_kpi_destaques= ler_html('card_kpi_destaques.html')
    kpi1, kpi2, kpi3 = st.columns(3, gap="large")
    with kpi1:
        total_target = df['TargProd'].mean()
        total_produzido = df['EffectiveProd'].mean()
        perdas = total_target - total_produzido
        df_spark_perdas = df.groupby(df['EffectiveDate'].dt.date).apply(lambda x: x['TargProd'].mean() - x['EffectiveProd'].mean()).tail(30)
        sparkline_perdas = gerar_sparkline_base64(df_spark_perdas, cores['laranja'])
        card_html = card_template.replace("{{titulo}}", "MÉDIA DE PERDAS").replace("{{valor}}", f"{int(perdas):,}").replace("{{sparkline_base64}}", sparkline_perdas).replace("{{variacao_texto}}", "Tendência (Últimos 30 dias)")
        st.markdown(card_html, unsafe_allow_html=True)
    with kpi2:
        ope_geral = metricas['ope']
        df_spark_ope = df.groupby(df['EffectiveDate'].dt.date).apply(lambda x: calcular_metricas_ope(x)['ope']).tail(30)
        sparkline_ope = gerar_sparkline_base64(df_spark_ope, cores['verde_ope'])
        card_html = card_template.replace("{{titulo}}", "OPE GERAL").replace("{{valor}}", f"{ope_geral:.2f}%").replace("{{sparkline_base64}}", sparkline_ope).replace("{{variacao_texto}}", "Tendência (Últimos 30 dias)")
        st.markdown(card_html, unsafe_allow_html=True)
    with kpi3:
        producao_media = df['EffectiveProd'].mean()
        df_spark_media = df.groupby(df['EffectiveDate'].dt.date)['EffectiveProd'].mean().tail(30)
        sparkline_media = gerar_sparkline_base64(df_spark_media, cores['azul_escuro'])
        card_html = card_template.replace("{{titulo}}", "PRODUÇÃO MÉDIA").replace("{{valor}}", f"{producao_media:.2f}").replace("{{sparkline_base64}}", sparkline_media).replace("{{variacao_texto}}", "Tendência (Últimos 30 dias)")
        st.markdown(card_html, unsafe_allow_html=True)
    st.markdown("---")

    # --- NOVO LAYOUT DOS GRÁFICOS ---

    # 1. Gráfico de OPE Mensal (Largura total no topo)
    st.markdown('<p class="chart-title">OPE GERAL POR MÊS</p>', unsafe_allow_html=True)
    df['MesNum'] = df['EffectiveDate'].dt.month
    df_ope_mensal = df.groupby('MesNum').apply(calcular_metricas_ope).apply(pd.Series).reset_index()
    df_ope_mensal['Mes'] = df_ope_mensal['MesNum'].map(mapa_meses)
    if not df_ope_mensal.empty:
        chart_ope_mensal = alt.Chart(df_ope_mensal).mark_bar(color=cores['azul_escuro']).encode(
            x=alt.X('Mes:N', sort=None, title="Mês"),
            y=alt.Y('ope:Q', title=None, axis=alt.Axis(format='.2f')),
            tooltip=[alt.Tooltip('Mes'), alt.Tooltip('ope', title='OPE (%)', format='.2f')]
        ).configure_view(strokeOpacity=0)
        st.altair_chart(chart_ope_mensal, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Linha do Meio: Gráfico de Linhas (Esquerda) e Cards de Destaque (Direita)
    col1, col2 = st.columns([2, 1], gap="large") 
    with col1:
        
        st.markdown('<p class="chart-title">OPE POR LINHA</p>', unsafe_allow_html=True)
        df_ope_linha = df.groupby('LineDesc').apply(calcular_metricas_ope).apply(pd.Series).reset_index()
        if not df_ope_linha.empty:
            chart_ope = alt.Chart(df_ope_linha).mark_bar(color=cores['azul_escuro']).encode(
                x=alt.X('ope:Q', title="OPE (%)", axis=alt.Axis(format='.2f')),
                y=alt.Y('LineDesc:N', sort='-x', title=None),
                tooltip=[alt.Tooltip('LineDesc', title='Linha'), alt.Tooltip('ope', title='OPE (%)', format='.2f')]
            ).configure_view(strokeOpacity=0)
            st.altair_chart(chart_ope, use_container_width=True)
    with col2:
       if not df_ope_linha.empty:
        
            melhor_linha = df_ope_linha.loc[df_ope_linha['ope'].idxmax()]
            pior_linha = df_ope_linha.loc[df_ope_linha['ope'].idxmin()]
            st.markdown('<p class="chart-title">DESTAQUES</p>', unsafe_allow_html=True)
            card_melhor_html = card_kpi_destaques.replace("{{titulo}}", f" MELHOR LINHA: {melhor_linha['LineDesc']}")\
                                             .replace("{{valor}}", f"{melhor_linha['ope']:.2f}%")                               
            st.markdown(card_melhor_html, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True) 
            card_pior_html = card_kpi_destaques.replace("{{titulo}}", f" PIOR LINHA: {pior_linha['LineDesc']}")\
                                            .replace("{{valor}}", f"{pior_linha['ope']:.2f}%")   
            st.markdown(card_pior_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 3. Gráfico de OPE Semanal (Largura total na base)
    st.markdown('<p class="chart-title">OPE SEMANAL</p>', unsafe_allow_html=True)
    df['SemanaNum'] = df['EffectiveDate'].dt.isocalendar().week
    df_ope_semanal = df.groupby('SemanaNum').apply(calcular_metricas_ope).apply(pd.Series).reset_index()
    df_ope_semanal['SemanaLabel'] = 'WK-' + df_ope_semanal['SemanaNum'].astype(str)
    if not df_ope_semanal.empty:
        chart_ope_semanal = alt.Chart(df_ope_semanal).mark_line(point=True, color=cores['verde_ope']).encode(
            x=alt.X('SemanaLabel:N', sort=alt.EncodingSortField(field="SemanaNum"), title="Semana"),
            y=alt.Y('ope:Q', title="OPE (%)", axis=alt.Axis(format='.2f')),
            tooltip=['SemanaLabel', alt.Tooltip('ope', title='OPE (%)', format='.2f')]
        ).configure_view(strokeOpacity=0)
        st.altair_chart(chart_ope_semanal, use_container_width=True)        
#inicio do script principal
carregar_css('style.css')
st.title("Dashboard de Análise Industrial")
st.markdown("---")

# Abas principais do Dashboard
main_tab1, main_tab2 = st.tabs(["🔩 Análise de Falhas", "⚙️ Análise de OPE"])

# --- FILTROS NA SIDEBAR ---
df_falhas_base, df_calendario = carregar_dados_falhas()
df_ope_base = carregar_dados_ope()

if df_falhas_base is None or df_ope_base is None:
    st.error("Falha ao carregar um dos conjuntos de dados. Verifique as conexões e arquivos.")
    st.stop()

st.sidebar.header("Filtros de Análise")
min_date, max_date = df_falhas_base['EffectiveDay'].min().date(), df_falhas_base['EffectiveDay'].max().date()
data_inicio = st.sidebar.date_input("Data de Início", min_date, min_value=min_date, max_value=max_date, key="data_inicio_geral")
data_fim = st.sidebar.date_input("Data de Fim", max_date, min_value=min_date, max_value=max_date, key="data_fim_geral")

opcoes_grupo_linha = ["Todas"] + sorted(df_falhas_base['LineGroupDesc'].astype(str).unique())
linegroup_selecionado = st.sidebar.selectbox("Grupo de Linha", opcoes_grupo_linha)

linhas_disponiveis = sorted(pd.concat([df_falhas_base['LineDesc'], df_ope_base['LineDesc']]).unique())
opcoes_linha = ["Todas"] + linhas_disponiveis
linha_selecionada = st.sidebar.selectbox("Linha", opcoes_linha)
 
opcoes_shift = ["Todos"] + sorted(df_falhas_base['ShiftId'].dropna().unique().astype(int))
shift_map = {1: "Turno 1", 2: "Turno 2", 3: "Turno 3"}
shift_selecionado = st.sidebar.selectbox("Turno", opcoes_shift, format_func=lambda id: shift_map.get(id, "Todos"))

tipo_dia_selecionado = st.sidebar.selectbox('Selecione o tipo de dia:', options=['Todos', 'Produtivo', 'Improdutivo'])
tipo_parada_selecionado = st.sidebar.selectbox('Tipo de Parada', options=['Todas', 'Breakdown (>10 min)', 'Microparada (<10 min)'])
stopingo_selecionado = st.sidebar.selectbox('Filtro Stop-in-Go', options=['Sem Stop In Go', 'Com Stop In Go', 'Todos'], index=0)


# --- TELA DE ANÁLISE DE FALHAS ---
with main_tab1:
    df_falhas_filtrado_base = df_falhas_base[(df_falhas_base['EffectiveDay'].dt.date >= data_inicio) & (df_falhas_base['EffectiveDay'].dt.date <= data_fim)]
    df_falhas_filtrado = aplicar_filtros_geograficos(df_falhas_filtrado_base, linegroup_selecionado, linha_selecionada, shift_selecionado, tipo_dia_selecionado, tipo_parada_selecionado, df_calendario)
    df_falhas_filtrado = aplicar_filtro_stopingo(df_falhas_filtrado, stopingo_selecionado)

    contexto_texto = f"**Grupo:** {linegroup_selecionado}"
    if linha_selecionada != "Todas": contexto_texto += f" | **Linha:** {linha_selecionada}"
    if shift_selecionado != "Todos": contexto_texto += f" | **Turno:** {shift_map.get(shift_selecionado, shift_selecionado)}"
    if tipo_parada_selecionado != 'Todas': contexto_texto += f" | **Tipo:** {tipo_parada_selecionado}"
    st.markdown(f"<p style='text-align: center; color: grey;'>🔎 Visualizando: {contexto_texto}</p>", unsafe_allow_html=True)

    st.markdown("### Resumo do Período Selecionado")
    card_template = ler_html('card_template.html')
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3, gap="large")
    
    # (Seu código dos 3 cards de KPI)
    
    with kpi_col1:
        mtbf_geral = calcular_metricas_kpi(df_falhas_filtrado, df_calendario)['mtbf_minutos']
        df_spark_mtbf = df_falhas_filtrado.groupby(df_falhas_filtrado['EffectiveDay'].dt.date).apply(lambda x: calcular_metricas_kpi(x, df_calendario)['mtbf_minutos']).tail(30)
        sparkline_mtbf = gerar_sparkline_base64(df_spark_mtbf, cores['azul_escuro'])
        card_html = card_template.replace("{{titulo}}", "MTBF Médio (minutos)").replace("{{valor}}", f"{mtbf_geral:.2f}").replace("{{sparkline_base64}}", sparkline_mtbf).replace("{{variacao_texto}}", "")
        st.markdown(card_html, unsafe_allow_html=True)
    with kpi_col2:
        mttr_geral = calcular_metricas_kpi(df_falhas_filtrado, df_calendario)['mttr_minutos']
        df_spark_mttr = df_falhas_filtrado.groupby(df_falhas_filtrado['EffectiveDay'].dt.date).apply(lambda x: calcular_metricas_kpi(x, df_calendario)['mttr_minutos']).tail(30)
        sparkline_mttr = gerar_sparkline_base64(df_spark_mttr, cores['laranja'])
        card_html = card_template.replace("{{titulo}}", "MTTR Médio (minutos)").replace("{{valor}}", f"{mttr_geral:.2f}").replace("{{sparkline_base64}}", sparkline_mttr).replace("{{variacao_texto}}", "")
        st.markdown(card_html, unsafe_allow_html=True)
    with kpi_col3:
        num_falhas = len(df_falhas_filtrado[df_falhas_filtrado['StatusDesc'] == "Falha/Parada"])
        df_spark_falhas = df_falhas_filtrado[df_falhas_filtrado['StatusDesc'] == "Falha/Parada"].groupby(df_falhas_filtrado['EffectiveDay'].dt.date).size().tail(30)
        sparkline_falhas = gerar_sparkline_base64(df_spark_falhas, "#6c757d")
        card_html = card_template.replace("{{titulo}}", "Total de Falhas (Geral)").replace("{{valor}}", f"{num_falhas}").replace("{{sparkline_base64}}", sparkline_falhas).replace("{{variacao_texto}}", "")
        st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("---")
    
    tab_mtbf, tab_mttr = st.tabs(["📊 Análise de MTBF", "📈 Análise de MTTR"])
    with tab_mtbf:
        criar_tela_analise_mtbf(df_falhas_filtrado.copy(), df_calendario, cores['azul_escuro'])
    with tab_mttr:
        criar_tela_analise_mttr(df_falhas_filtrado.copy(), df_calendario, cores['laranja'])

# TELA DE ANÁLISE DE OPE 
with main_tab2:
    df_ope_filtrado = aplicar_filtros_ope(df_ope_base, data_inicio, data_fim, linha_selecionada, shift_selecionado, tipo_dia_selecionado, df_calendario)
    
    # O título dinâmico para a aba de OPE
    contexto_ope = f"**Linha:** {linha_selecionada}"
    if shift_selecionado != "Todos": contexto_ope += f" | **Turno:** {shift_map.get(shift_selecionado, shift_selecionado)}"
    st.markdown(f"<p style='text-align: center; color: grey;'>🔎 Visualizando: {contexto_ope}</p>", unsafe_allow_html=True)

    criar_tela_analise_ope(df_ope_filtrado)