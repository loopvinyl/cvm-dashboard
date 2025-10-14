# ==============================================================
# 📊 DASHBOARD CVM - Indicadores Financeiros (VERSÃO CORRIGIDA)
# ==============================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os
import yfinance as yf
from datetime import datetime, timedelta, date
import locale

# ==============================
# CONFIGURAÇÃO DE FORMATAÇÃO BRASILEIRA
# ==============================
def configurar_locale_brasil():
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
        except:
            pass

configurar_locale_brasil()

# ==============================
# FUNÇÕES DE FORMATAÇÃO
# ==============================
def formatar_moeda_brasil_correta(valor, casas_decimais=2):
    if valor is None or pd.isna(valor):
        return "R$ -"
    
    try:
        valor_em_reais = valor * 1000
        
        if abs(valor_em_reais) >= 1e12:
            return f"R$ {valor_em_reais/1e12:,.{casas_decimais}f} tri".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(valor_em_reais) >= 1e9:
            return f"R$ {valor_em_reais/1e9:,.{casas_decimais}f} bi".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(valor_em_reais) >= 1e6:
            return f"R$ {valor_em_reais/1e6:,.{casas_decimais}f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"R$ {valor_em_reais/1e3:,.0f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return f"R$ {valor}"

def formatar_percentual_brasil(valor, casas_decimais=2):
    if valor is None or pd.isna(valor):
        return "N/A"
    
    try:
        return f"{valor:.{casas_decimais}%}".replace(".", ",")
    except:
        return str(valor)

# ==============================
# FUNÇÕES DE DIVIDENDOS (CORRIGIDAS)
# ==============================
def buscar_dividendos_historicos(ticker):
    try:
        ticker_yf = f"{ticker}.SA"
        acao = yf.Ticker(ticker_yf)
        dividendos = acao.dividends
        
        if dividendos.empty:
            return None
            
        df_dividendos = dividendos.reset_index()
        df_dividendos.columns = ['Data', 'Dividendo']
        df_dividendos['Data'] = df_dividendos['Data'].dt.tz_localize(None)
        df_dividendos = df_dividendos[df_dividendos['Data'] >= datetime(2010, 1, 1)]
        df_dividendos['Ano'] = df_dividendos['Data'].dt.year
        df_dividendos['Mes'] = df_dividendos['Data'].dt.month
        df_dividendos = df_dividendos.sort_values('Data')
        
        return df_dividendos
        
    except Exception as e:
        st.warning(f"⚠️ Não foi possível buscar dividendos para {ticker}: {str(e)}")
        return None

def calcular_estatisticas_dividendos(df_dividendos):
    if df_dividendos is None or df_dividendos.empty:
        return None
    
    stats = {
        'total_dividendos': df_dividendos['Dividendo'].sum(),
        'media_anual': df_dividendos.groupby('Ano')['Dividendo'].sum().mean(),
        'maior_dividendo': df_dividendos['Dividendo'].max(),
        'menor_dividendo': df_dividendos['Dividendo'].min(),
        'frequencia_media': len(df_dividendos) / df_dividendos['Ano'].nunique(),
        'ultimo_dividendo': df_dividendos.iloc[-1]['Dividendo'] if len(df_dividendos) > 0 else 0,
        'data_ultimo': df_dividendos.iloc[-1]['Data'] if len(df_dividendos) > 0 else None
    }
    
    return stats

# ==============================
# CONFIGURAÇÕES INICIAIS
# ==============================
st.set_page_config(page_title="Dashboard CVM - Indicadores", layout="wide")
st.title("Dashboard CVM : Análise das Demonstrações Financeiras")

# ==============================
# LEITURA DE DADOS (simplificada)
# ==============================
@st.cache_data
def load_data():
    possible_paths = [
        "/content/dff_2010_2024.xlsx",
        "dff_2010_2024.xlsx",
        "./data/dff_2010_2024.xlsx"
    ]
    
    data_path = None
    for path in possible_paths:
        if os.path.exists(path):
            data_path = path
            break

    if data_path is None:
        st.error("❌ Arquivo 'dff_2010_2024.xlsx' não encontrado.")
        st.stop()

    df = pd.read_excel(data_path)
    df.columns = [c.strip() for c in df.columns]
    
    # Cálculos básicos (simplificados para exemplo)
    df = df.sort_values(['Ticker', 'Ano']).reset_index(drop=True)
    
    # Cálculo de médias
    df["Ativo Médio"] = (df["Ativo Total"] + df.groupby("Ticker")["Ativo Total"].shift(1)) / 2
    df["PL Médio"] = (df["Patrimônio Líquido Consolidado"] + df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1)) / 2
    
    # Indicadores de rentabilidade
    df["ROE"] = np.where(
        df["PL Médio"] > 0,
        df["Lucro/Prejuízo Consolidado do Período"] / df["PL Médio"],
        np.nan
    )
    
    df["ROA"] = np.where(
        df["Ativo Médio"] > 0,
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Ativo Médio"],
        np.nan
    )
    
    return df

# Carregar dados
df = load_data()

# ==============================
# SIDEBAR - FILTROS
# ==============================
st.sidebar.header("🔧 Filtros Principais")

modo_analise = st.sidebar.radio(
    "Modo de Análise:",
    ["🏆 Dados Gerais", "📈 Visão por Empresa", "🏭 Análise Setorial"]
)

anos_disponiveis = sorted(df["Ano"].unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Selecione o Ano:", anos_disponiveis)

if modo_analise == "📈 Visão por Empresa":
    ticker_selecionado = st.sidebar.selectbox(
        "Selecione a Empresa:",
        sorted(df["Ticker"].dropna().unique())
    )
    df_filtrado = df[(df["Ticker"] == ticker_selecionado) & (df["Ano"] == ano_selecionado)]
    df_empresa_todos_anos = df[df["Ticker"] == ticker_selecionado].sort_values("Ano")

# ==============================
# TELA - VISÃO POR EMPRESA
# ==============================
if modo_analise == "📈 Visão por Empresa":
    st.header(f"📊 Análise Detalhada - {ticker_selecionado}")
    
    if not df_empresa_todos_anos.empty:
        tab_atual, tab_evolucao, tab_dividendos = st.tabs([
            "📊 Análise do Ano", "📈 Evolução Temporal", "💰 Dividendos"
        ])
        
        with tab_dividendos:
            st.subheader("💰 Histórico de Dividendos")
            
            with st.spinner("Buscando dados de dividendos..."):
                df_dividendos = buscar_dividendos_historicos(ticker_selecionado)
            
            if df_dividendos is not None and not df_dividendos.empty:
                stats = calcular_estatisticas_dividendos(df_dividendos)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Último Dividendo", 
                        f"R$ {stats['ultimo_dividendo']:.2f}".replace(".", ","),
                        help=f"Data: {stats['data_ultimo'].strftime('%d/%m/%Y') if stats['data_ultimo'] else 'N/A'}"
                    )
                
                with col2:
                    st.metric(
                        "Total Distribuído", 
                        formatar_moeda_brasil_correta(stats['total_dividendos'] * 1000),
                        help="Soma histórica de dividendos"
                    )
                
                with col3:
                    st.metric(
                        "Média Anual", 
                        formatar_moeda_brasil_correta(stats['media_anual'] * 1000),
                        help="Média de dividendos por ano"
                    )
                
                with col4:
                    st.metric(
                        "Frequência/Ano", 
                        f"{stats['frequencia_media']:.1f}",
                        help="Pagamentos médios por ano"
                    )
                
                # GRÁFICO CORRIGIDO: Evolução dos Dividendos
                st.subheader("📈 Evolução dos Dividendos")
                
                fig_dividendos = px.line(
                    df_dividendos, 
                    x='Data', 
                    y='Dividendo',
                    title=f'Dividendos por Ação - {ticker_selecionado}',
                    markers=True
                )
                
                # ✅ CORREÇÃO APLICADA: Formatação brasileira com 2 casas decimais
                fig_dividendos.update_layout(
                    yaxis_title='Dividendo por Ação (R$)',
                    xaxis_title='Data',
                    height=400,
                    yaxis=dict(
                        tickformat=",.2f",  # 2 casas decimais
                        separatethousands=True,
                        tickprefix="R$ "    # Prefixo de moeda
                    )
                )
                
                st.plotly_chart(fig_dividendos, use_container_width=True)
                
                # GRÁFICO CORRIGIDO: Dividendos por ano
                st.subheader("📊 Dividendos por Ano")
                dividendos_ano = df_dividendos.groupby('Ano')['Dividendo'].sum().reset_index()
                dividendos_ano['Dividendo Total'] = dividendos_ano['Dividendo']
                
                fig_ano = px.bar(
                    dividendos_ano,
                    x='Ano',
                    y='Dividendo Total',
                    title='Total de Dividendos por Ano'
                )
                
                # ✅ CORREÇÃO APLICADA: Formatação brasileira com 2 casas decimais
                fig_ano.update_layout(
                    height=400,
                    yaxis_title='Dividendos (R$)',
                    yaxis_tickprefix="R$ ",
                    yaxis_tickformat=", .2f"  # Formato brasileiro com 2 casas
                )
                
                st.plotly_chart(fig_ano, use_container_width=True)
                
                # Tabela detalhada
                st.subheader("📋 Detalhamento dos Dividendos")
                
                df_display = df_dividendos.copy()
                df_display['Dividendo'] = df_display['Dividendo'].apply(
                    lambda x: f"R$ {x:.2f}".replace(".", ",")  # ✅ 2 casas decimais na tabela também
                )
                df_display['Data'] = df_display['Data'].dt.strftime('%d/%m/%Y')
                df_display = df_display[['Data', 'Dividendo', 'Ano']].sort_values('Data', ascending=False)
                
                st.dataframe(df_display, use_container_width=True)
                
            else:
                st.warning(f"""
                **ℹ️ Dados de Dividendos Não Encontrados**
                
                Não foi possível recuperar o histórico de dividendos para {ticker_selecionado}.
                """)

# Rodapé
st.divider()
st.caption(f"📊 Dashboard CVM - Indicadores Financeiros | Dados atualizados para {ano_selecionado}")
