import streamlit as st
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import io
import base64
import os
import joblib
from datetime import datetime, timedelta
from streamlit_echarts import st_echarts
from ml import predictions

import shap
import matplotlib.pyplot as plt

# Importa as configurações centralizadas
import config

# Importa as funções de cálculo
from utils.calculations import calcular_metricas_kpi, calcular_metricas_ope


# --- FUNÇÕES UTILITÁRIAS DE UI ---

def carregar_css(nome_arquivo):
    """Lê um arquivo CSS da pasta de assets e o aplica ao app."""
    caminho_completo = os.path.join(config.ASSETS_DIR, nome_arquivo)
    try:
        with open(caminho_completo, 'r', encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Arquivo CSS '{caminho_completo}' não encontrado.")

def ler_html(nome_arquivo):
    """Lê um arquivo de template HTML da pasta de templates."""
    caminho_completo = os.path.join(config.TEMPLATES_DIR, nome_arquivo)
    try:
        with open(caminho_completo, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.error(f"Arquivo de template '{caminho_completo}' não encontrado.")
        return "<p>Erro: Template não encontrado.</p>"

@st.cache_data
def convert_df_to_csv(df):
    """Converte um DataFrame para CSV para download."""
    return df.to_csv(index=False, sep=';').encode('utf-8-sig')

def gerar_sparkline_base64(data, cor_linha):
    """Gera um mini-gráfico (sparkline) como uma imagem base64."""
    if data.empty or len(data) < 2: return ""
    fig, ax = plt.subplots(figsize=(4, 0.8), dpi=80)
    ax.plot(data, color=cor_linha, linewidth=2)
    ax.set_yticklabels([])
    ax.set_xticklabels([])
    ax.tick_params(axis='both', which='both', length=0)
    for spine in ax.spines.values(): spine.set_visible(False)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"


# --- FUNÇÕES DE CRIAÇÃO DE TELAS ---

def exibir_kpis_falhas(df_falhas_filtrado, df_calendario, cores):
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3, gap="large")
    card_template = ler_html('card_template.html')

    with kpi_col1:
        mtbf_geral = calcular_metricas_kpi(df_falhas_filtrado, df_calendario)['mtbf_minutos']
        df_spark_mtbf = df_falhas_filtrado.groupby(df_falhas_filtrado['EffectiveDay'].dt.date).apply(lambda x: calcular_metricas_kpi(x, df_calendario)['mtbf_minutos']).tail(30)
        sparkline_mtbf = gerar_sparkline_base64(df_spark_mtbf, cores['azul_escuro'])
        card_html = card_template.replace("{{titulo}}", "MTBF Médio (minutos)").replace("{{valor}}", f"{mtbf_geral:.2f}").replace("{{sparkline_base64}}", sparkline_mtbf).replace("{{variacao_texto}}", "Tendência (Últimos 30 dias)")
        st.markdown(card_html, unsafe_allow_html=True)
    with kpi_col2:
        mttr_geral = calcular_metricas_kpi(df_falhas_filtrado, df_calendario)['mttr_minutos']
        df_spark_mttr = df_falhas_filtrado.groupby(df_falhas_filtrado['EffectiveDay'].dt.date).apply(lambda x: calcular_metricas_kpi(x, df_calendario)['mttr_minutos']).tail(30)
        sparkline_mttr = gerar_sparkline_base64(df_spark_mttr, cores['laranja'])
        card_html = card_template.replace("{{titulo}}", "MTTR Médio (minutos)").replace("{{valor}}", f"{mttr_geral:.2f}").replace("{{sparkline_base64}}", sparkline_mttr).replace("{{variacao_texto}}", "Tendência (Últimos 30 dias)")
        st.markdown(card_html, unsafe_allow_html=True)
    with kpi_col3:
        num_falhas = len(df_falhas_filtrado[df_falhas_filtrado['StatusDesc'] == "Falha/Parada"])
        df_spark_falhas = df_falhas_filtrado[df_falhas_filtrado['StatusDesc'] == "Falha/Parada"].groupby(df_falhas_filtrado['EffectiveDay'].dt.date).size().tail(30)
        sparkline_falhas = gerar_sparkline_base64(df_spark_falhas, "#6c757d")
        card_html = card_template.replace("{{titulo}}", "Total de Falhas").replace("{{valor}}", f"{num_falhas}").replace("{{sparkline_base64}}", sparkline_falhas).replace("{{variacao_texto}}", "Tendência (Últimos 30 dias)")
        st.markdown(card_html, unsafe_allow_html=True)

def criar_tela_analise_mtbf(df, df_calendario, cor_principal, mapa_meses):
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

    with col4:
        st.markdown('<p class="chart-title">COMPONENTES</p>', unsafe_allow_html=True)
        with st.expander("🔍 Ver/Ocultar Análise por Componentes"):
            mtbf_por_componente_df = df.groupby('ElementDesc').apply(lambda x: calcular_metricas_kpi(x, df_calendario)).apply(pd.Series)
            component_data_df = mtbf_por_componente_df[['mtbf_minutos']].sort_values(by='mtbf_minutos', ascending=True).reset_index()
            component_data_df.rename(columns={'ElementDesc': 'COMPONENTE', 'mtbf_minutos': 'MTBF'}, inplace=True)
            if not component_data_df.empty:
                st.dataframe(component_data_df, use_container_width=True, hide_index=True, column_config={"MTBF": st.column_config.NumberColumn(format="%.2f")})

def criar_tela_analise_mttr(df, df_calendario, cor_principal, mapa_meses):
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

    with col4:
        st.markdown('<p class="chart-title">COMPONENTES</p>', unsafe_allow_html=True)
        with st.expander("🔍 Ver/Ocultar Análise por Componentes"):
            mttr_por_componente_df = df.groupby('ElementDesc').apply(lambda x: calcular_metricas_kpi(x, df_calendario)).apply(pd.Series)
            component_data_df = mttr_por_componente_df[['mttr_minutos']].sort_values(by='mttr_minutos', ascending=False).reset_index()
            component_data_df.rename(columns={'ElementDesc': 'COMPONENTE', 'mttr_minutos': 'MTTR'}, inplace=True)
            if not component_data_df.empty:
                st.dataframe(component_data_df, use_container_width=True, hide_index=True, column_config={"MTTR": st.column_config.NumberColumn(format="%.2f")})

def criar_tela_analise_ope(df, cores, mapa_meses):
    if df.empty:
        st.warning("Nenhum dado de OPE para os filtros selecionados."); return

    st.markdown("### Resumo do Período Selecionado")
    metricas = calcular_metricas_ope(df)
    card_template = ler_html('card_template.html')
    card_kpi_destaques = ler_html('card_kpi_destaques.html')
    kpi1, kpi2, kpi3 = st.columns(3, gap="large")
    with kpi1:
        if 'TargProd' in df.columns and 'EffectiveProd' in df.columns:
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
        if 'EffectiveProd' in df.columns:
            producao_media = df['EffectiveProd'].mean()
            df_spark_media = df.groupby(df['EffectiveDate'].dt.date)['EffectiveProd'].mean().tail(30)
            sparkline_media = gerar_sparkline_base64(df_spark_media, cores['azul_escuro'])
            card_html = card_template.replace("{{titulo}}", "PRODUÇÃO MÉDIA").replace("{{valor}}", f"{producao_media:.2f}").replace("{{sparkline_base64}}", sparkline_media).replace("{{variacao_texto}}", "Tendência (Últimos 30 dias)")
            st.markdown(card_html, unsafe_allow_html=True)
    st.markdown("---")
    
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
       if not df_ope_linha.empty and 'ope' in df_ope_linha.columns:
            melhor_linha = df_ope_linha.loc[df_ope_linha['ope'].idxmax()]
            pior_linha = df_ope_linha.loc[df_ope_linha['ope'].idxmin()]
            st.markdown('<p class="chart-title">DESTAQUES</p>', unsafe_allow_html=True)
            card_kpi_destaques = ler_html('card_kpi_destaques.html')
            card_melhor_html = card_kpi_destaques.replace("{{titulo}}", f" MELHOR LINHA: {melhor_linha['LineDesc']}")\
                                             .replace("{{valor}}", f"{melhor_linha['ope']:.2f}%")                               
            st.markdown(card_melhor_html, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True) 
            card_pior_html = card_kpi_destaques.replace("{{titulo}}", f" PIOR LINHA: {pior_linha['LineDesc']}")\
                                            .replace("{{valor}}", f"{pior_linha['ope']:.2f}%")   
            st.markdown(card_pior_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
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

def criar_tela_analise_preditiva(df_falhas_filtrado):
    st.markdown("### 🤖 Análise de Risco de Breakdown")
    st.info("""
    Esta ferramenta utiliza os **filtros da sidebar** para identificar um grupo de componentes.
    A IA então calcula a probabilidade de a próxima falha de cada um ser um **Breakdown (>10 min)** e explica
    os fatores de risco para o caso mais crítico.
    """)
    st.markdown("---")

    componentes_unicos = df_falhas_filtrado.drop_duplicates(subset=['LineGroupDesc', 'LineDesc', 'StationDesc', 'ElementDesc']).reset_index(drop=True)

    if componentes_unicos.empty:
        st.warning("Nenhum componente corresponde aos filtros selecionados na sidebar.")
        return

    st.markdown("#### Análise de Risco para Componentes Filtrados")

    turno_selecionado = st.session_state.get('shift_selecionado_id', 1)
    if turno_selecionado == "Todos":
        turno_selecionado = 1
        st.caption("Nota: Como o turno 'Todos' está selecionado, a simulação usará o Turno 1 como referência.")

    if st.button("Executar Análise de Risco", type="primary", key="btn_risco_breakdown"):
        with st.spinner(f"Analisando {len(componentes_unicos)} componentes..."):
            
            df_riscos, input_aligned = predictions.prever_risco_breakdown(componentes_unicos, turno_selecionado)

            st.markdown("---")
            st.subheader("Relatório de Risco de Breakdown")

            if df_riscos is None:
                st.error("Modelo preditivo não encontrado. Execute 'ml/training.py' primeiro.")
            elif df_riscos.empty:
                st.info("Não foi possível gerar um relatório para os componentes selecionados.")
            else:
                st.dataframe(
                    df_riscos.style
                    .format({'Probabilidade de Breakdown': '{:.2%}'})
                    .background_gradient(cmap='Reds', subset=['Probabilidade de Breakdown'])
                    .set_properties(**{'text-align': 'left'}),
                    use_container_width=True, hide_index=True
                )

                # --- SEÇÃO DE EXPLICABILIDADE (XAI) COM SHAP - VERSÃO FINAL E ROBUSTA ---
                st.markdown("---")
                st.subheader("🔬 Análise de Causa Raiz para o Componente de Maior Risco")
                
                componente_maior_risco = df_riscos.iloc[0]
                st.write(f"O componente com maior risco de breakdown é **{componente_maior_risco['ElementDesc']}** na estação **{componente_maior_risco['StationDesc']}**.")
                st.write("O gráfico abaixo mostra os fatores que mais contribuíram para esta previsão:")

                try:
                    # Usamos o método 'interventional', que é mais robusto.
                    # Passamos todo o 'input_aligned' como dados de fundo para o explainer,
                    # o que ajuda o SHAP a entender a distribuição dos dados.
                    explainer = shap.TreeExplainer(
                        predictions.model_breakdown, 
                        input_aligned, 
                        feature_perturbation="interventional",
                        model_output="probability"
                    )
                    
                    # Geramos a explicação apenas para o componente de maior risco (índice 0)
                    shap_explanation = explainer(input_aligned.iloc[[0]])

                    # Selecionamos a explicação para a classe positiva ('Breakdown')
                    instance_to_plot = shap_explanation[0, :, 1]

                    # Criamos e exibimos o gráfico
                    plt.figure()
                    shap.plots.waterfall(instance_to_plot, max_display=10, show=False)
                    st.pyplot(plt.gcf())
                    plt.clf()

                except Exception as e:
                    st.error(f"Ocorreu um erro ao gerar a explicação do modelo: {e}")

                with st.expander("Como interpretar o gráfico?"):
                    st.markdown("""
                    - O valor **`E[f(X)]`** na base é a probabilidade média de breakdown para qualquer componente, segundo o modelo.
                    - As **barras vermelhas** representam features que **aumentam** o risco de breakdown.
                    - As **barras azuis** representam features que **diminuem** o risco.
                    - O tamanho de cada barra mostra o **tamanho do impacto** daquela feature.
                    - O valor **`f(x)`** no topo é a previsão final de risco para este componente específico.
                    """)

def criar_tela_analise_rul(df_features, df_falhas_filtrado):
    st.markdown("### 🔮 Previsão de Falhas Críticas por Linha (>10 min)")
    st.info("""
    Esta análise utiliza os **filtros da sidebar** para identificar um grupo de componentes.
    Em seguida, a IA prevê o tempo restante de vida útil para cada um, gerando um relatório 
    de risco priorizado apenas com as falhas críticas futuras.
    """)
    st.markdown("---")

    componentes_elegiveis = df_falhas_filtrado['ElementDesc'].unique()
    df_features_filtrado = df_features[df_features['ElementDesc'].isin(componentes_elegiveis)]

    if df_features_filtrado.empty:
        st.warning("Nenhum componente com dados preditivos corresponde aos filtros selecionados na sidebar.")
        return

    st.markdown("#### Análise de Risco para Componentes Filtrados")

    if st.button("Executar Análise Preditiva nos Componentes Filtrados", type="primary", key="btn_analise_rul"):
        with st.spinner(f"Analisando o ciclo de vida dos componentes..."):
            
            relatorio_final = predictions.prever_vida_util_restante(df_features_filtrado)

            st.markdown("---")
            st.subheader("Relatório de Risco Preditivo (Próximas Falhas Críticas)")

            if relatorio_final is None:
                st.error("Modelo de RUL não encontrado. Execute 'ml/advanced_training.py' primeiro.")
            elif relatorio_final.empty:
                st.success("✅ Nenhuma falha crítica iminente prevista para os componentes selecionados.")
            else:
                st.dataframe(
                    relatorio_final.style.format({
                        'Data Estimada da Falha Crítica': '{:%d/%m/%Y}',
                        'Baseado em Dados de': '{:%d/%m/%Y}',
                        'Previsão (dias a partir de hoje)': '{:.0f}',
                    }).background_gradient(cmap='OrRd', subset=['Previsão (dias a partir de hoje)']),
                    use_container_width=True, hide_index=True
                )