import pandas as pd
import os
import pymssql
import streamlit as st
import config

UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
# Sobe um nível para chegar à raiz do projeto
PROJECT_ROOT = os.path.dirname(UTILS_DIR)
# Cria o caminho para a pasta 'data'
DATA_DIR = config.DATA_DIR



@st.cache_data(ttl=3600)
def carregar_dados_falhas():
    arquivo_csv = 'dados_otimizados_falhas.csv'
    df_calendario = pd.read_csv('data\calendario_produtivo.csv', sep=',')
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

@st.cache_data(ttl=3600)
def carregar_dados_ope():
    arquivo_csv = config.OPE_CSV_PATH
    if os.path.exists(arquivo_csv):
        df = pd.read_csv(arquivo_csv, sep=';')
    else:
        raise FileNotFoundError(f"Arquivo '{arquivo_csv}' não encontrado. Execute a extração inicial do banco de dados primeiro.")

    df['EffectiveDate'] = pd.to_datetime(df['EffectiveDate'], errors='coerce')
    return df

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
    
    total_uptime_minutos = 0
    minutos_por_turno = {1: 8.3 * 60, 2: 8.3 * 60, 3: 5.5 * 60}
    for _, row in dias_e_turnos_unicos.iterrows():
        dia_da_semana = pd.to_datetime(row['EffectiveDay']).weekday() # Segunda=0, Domingo=6
        if dia_da_semana == 6: # Se for domingo
             total_uptime_minutos += 4 * 60
        else:
             total_uptime_minutos += minutos_por_turno.get(row['ShiftId'], 0)

    mttr_minutos = total_downtime_minutos / numero_de_falhas if numero_de_falhas > 0 else 0
    mtbf_minutos = total_uptime_minutos / numero_de_falhas if numero_de_falhas > 0 else total_uptime_minutos
    
    return {'mttr_minutos': mttr_minutos, 'mtbf_minutos': mtbf_minutos}

def calcular_metricas_ope(df_ope_filtrado):
    if df_ope_filtrado.empty:
        return {'ope': 0, 'pecas_boas': 0, 'pecas_ruins': 0, 'total_produzido': 0}
    total_produzido = df_ope_filtrado['EffectiveProd'].sum()
    target_producao = df_ope_filtrado['TargProd'].sum()
    
    ope = (total_produzido / target_producao) * 100 if target_producao > 0 else 0
    
    return {'ope': ope, 'pecas_boas': total_produzido, 'pecas_ruins': 0, 'total_produzido': total_produzido}

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
    cond8 = df_copy['ElementDesc'].isin(['BRS01', 'BR_01', 'BR_02', 'BR_03', 'BR_04', 'BR_05', 'BR_06', 
                                                  'BR_07', 'BR_08', 'BR_09', 'BR_10', 'BR_11', 'BR_12', 'HGD01', 'HGD02', 
                                                  'HGD_01', 'HLC01', 'HLC_01', 'PRB01', 'PRB02', 'PRB03', 'PRB04', 'PRB05', 
                                                  'PRB06', 'PTZ01', 'PTZ02', 'PTZ03', 'PTZ04', 'VT01', 'VT_01', 'VT_02', 'VT_03',
                                                  'VT_04', 'VT_06', 'XGA01', 'XGA02', 'XGA03', 'XGA04', 'XGA05', 'XGA06', 'XGA07', 'XGA08'])
    indices = df_copy[cond1 | cond2 | cond3 | cond4 | cond5 | cond6 | cond7 | cond8].index
    if tipo_selecionado == 'Com Stop In Go': return df_copy.loc[indices]
    elif tipo_selecionado == 'Sem Stop In Go': return df_copy.drop(indices)
    return df_copy

def aplicar_filtros_ope(df, data_inicio, data_fim, linha, shift, tipo_dia, df_calendario):
    df_filtrado = df.copy()
    df_filtrado = df_filtrado[
        (df_filtrado['EffectiveDate'].dt.date >= data_inicio) &
        (df_filtrado['EffectiveDate'].dt.date <= data_fim)
    ]
    if linha != "Todas": df_filtrado = df_filtrado[df_filtrado['LineDesc'] == linha]
    if shift != "Todos": df_filtrado = df_filtrado[df_filtrado['ShiftId'] == shift]
    if tipo_dia != "Todos":
        datas_filtradas = df_calendario[df_calendario['Tipo'] == tipo_dia]['Data'].dt.date
        df_filtrado = df_filtrado[df_filtrado['EffectiveDate'].dt.date.isin(datas_filtradas)]
    return df_filtrado

# Adicione esta função em utils/calculations.py

@st.cache_data
def obter_dados_filtrados(df_falhas_base, df_ope_base, df_calendario, data_inicio, data_fim, linegroup, linha, shift, tipo_dia, tipo_parada, stopingo):
    """
    Aplica todos os filtros de uma vez e armazena o resultado em cache.
    Esta função será o "motor" de filtragem do dashboard.
    """
    # Filtra DataFrame de falhas
    df_falhas_filtrado_base = df_falhas_base[
        (df_falhas_base['EffectiveDay'].dt.date >= data_inicio) & 
        (df_falhas_base['EffectiveDay'].dt.date <= data_fim)
    ]
    df_falhas_filtrado = aplicar_filtros_geograficos(df_falhas_filtrado_base, linegroup, linha, shift, tipo_dia, tipo_parada, df_calendario)
    df_falhas_filtrado = aplicar_filtro_stopingo(df_falhas_filtrado, stopingo)

    # Filtra DataFrame de OPE
    df_ope_filtrado = aplicar_filtros_ope(df_ope_base, data_inicio, data_fim, linha, shift, tipo_dia, df_calendario)
    
    return df_falhas_filtrado, df_ope_filtrado