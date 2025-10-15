# ==============================================================
# 📊 DASHBOARD CVM - Indicadores Financeiros (VERSÃO COM YFINANCE)
# ==============================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os
import yfinance as yf
from datetime import datetime, timedelta
import locale

# ==============================
# CONFIGURAÇÃO INICIAL DO STREAMLIT
# ==============================
st.set_page_config(
    page_title="Dashboard CVM - Indicadores Financeiros", 
    layout="wide",
    page_icon="📊"
)

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
# CARREGAMENTO DE DADOS
# ==============================
@st.cache_data
def load_data():
    data_path = "dff_2010_2024.xlsx"
    
    if not os.path.exists(data_path):
        st.error(
            "❌ Arquivo 'dff_2010_2024.xlsx' não encontrado na mesma pasta do app.\n\n"
            "Por favor, certifique-se de que o arquivo está no mesmo diretório que app.py"
        )
        st.stop()

    # Ler o Excel
    df = pd.read_excel(data_path)
    df.columns = [c.strip() for c in df.columns]

    # Ordenar por Ticker e Ano para garantir que shift() funcione corretamente
    df = df.sort_values(['Ticker', 'Ano']).reset_index(drop=True)

    # =============================================================
    # CÁLCULOS DE MÉDIAS
    # =============================================================
    df["Ativo Médio"] = (df["Ativo Total"] + df.groupby("Ticker")["Ativo Total"].shift(1)) / 2
    df["PL Médio"] = (df["Patrimônio Líquido Consolidado"] + df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1)) / 2

    df["Passivo Oneroso Atual"] = (
        df["Empréstimos e Financiamentos - Circulante"].fillna(0) + 
        df["Empréstimos e Financiamentos - Não Circulante"].fillna(0)
    )
    df["Passivo Oneroso Anterior"] = (
        df.groupby("Ticker")["Empréstimos e Financiamentos - Circulante"].shift(1).fillna(0) +
        df.groupby("Ticker")["Empréstimos e Financiamentos - Não Circulante"].shift(1).fillna(0)
    )
    df["Passivo Oneroso Médio"] = (df["Passivo Oneroso Atual"] + df["Passivo Oneroso Anterior"]) / 2

    df["Investimento Atual"] = (
        df["Empréstimos e Financiamentos - Circulante"].fillna(0) + 
        df["Empréstimos e Financiamentos - Não Circulante"].fillna(0) + 
        df["Patrimônio Líquido Consolidado"]
    )
    df["Investimento Anterior"] = (
        df.groupby("Ticker")["Empréstimos e Financiamentos - Circulante"].shift(1).fillna(0) +
        df.groupby("Ticker")["Empréstimos e Financiamentos - Não Circulante"].shift(1).fillna(0) +
        df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1).fillna(0)
    )
    df["Investimento Médio"] = (df["Investimento Atual"] + df["Investimento Anterior"]) / 2

    # =============================================================
    # INDICADORES DE RENTABILIDADE
    # =============================================================
    df["ROA"] = np.where(
        df["Ativo Médio"] > 0,
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Ativo Médio"],
        np.nan
    )

    df["ROI"] = np.where(
        df["Investimento Médio"] > 0,
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Investimento Médio"],
        np.nan
    )

    df["ROE"] = np.where(
        df["PL Médio"] > 0,
        df["Lucro/Prejuízo Consolidado do Período"] / df["PL Médio"],
        np.nan
    )

    # =============================================================
    # MARGENS
    # =============================================================
    df["Margem Bruta"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] > 0,
        df["Resultado Bruto"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )

    df["Margem Operacional"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] > 0,
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )

    df["Margem Líquida"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] > 0,
        df["Lucro/Prejuízo Consolidado do Período"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )

    # =============================================================
    # ESTRUTURA DE CAPITAL
    # =============================================================
    df["Total Passivo"] = (
        df["Passivo Circulante"].fillna(0) + 
        df["Passivo Não Circulante"].fillna(0) + 
        df["Patrimônio Líquido Consolidado"].fillna(0)
    )

    df["Percentual Capital Terceiros"] = np.where(
        df["Total Passivo"] > 0,
        (df["Passivo Circulante"].fillna(0) + df["Passivo Não Circulante"].fillna(0)) / df["Total Passivo"],
        np.nan
    )

    df["Percentual Capital Próprio"] = np.where(
        df["Total Passivo"] > 0,
        df["Patrimônio Líquido Consolidado"] / df["Total Passivo"],
        np.nan
    )

    # =============================================================
    # CUSTO DE CAPITAL
    # =============================================================
    df["ki"] = np.where(
        (df["Passivo Oneroso Médio"] > 0) & (df["Despesas Financeiras"].notna()),
        df["Despesas Financeiras"].abs() / df["Passivo Oneroso Médio"],
        np.nan
    )

    df["ke"] = np.where(
        (df["PL Médio"] > 0) & (df["Pagamento de Dividendos"].notna()),
        df["Pagamento de Dividendos"].abs() / df["PL Médio"],
        np.nan
    )

    df["wacc"] = np.where(
        (df["ki"].notna()) & (df["ke"].notna()) & 
        (df["Percentual Capital Terceiros"].notna()) & (df["Percentual Capital Próprio"].notna()),
        (df["ki"] * df["Percentual Capital Terceiros"]) + (df["ke"] * df["Percentual Capital Próprio"]),
        np.nan
    )

    # =============================================================
    # EBITDA CORRIGIDO
    # =============================================================
    nome_coluna_da = None
    for col in df.columns:
        if 'depreciação' in col.lower() and 'amortização' in col.lower():
            nome_coluna_da = col
            break

    if nome_coluna_da:
        depreciacao_amortizacao = abs(df[nome_coluna_da].fillna(0))
        df["EBITDA"] = np.where(
            df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna(),
            df["Resultado Antes do Resultado Financeiro e dos Tributos"] + depreciacao_amortizacao,
            np.nan
        )
    else:
        df["EBITDA"] = df["Resultado Antes do Resultado Financeiro e dos Tributos"]

    # =============================================================
    # LUCRO ECONÔMICO
    # =============================================================
    df["Lucro Econômico 1"] = np.where(
        (df["ROI"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()),
        (df["ROI"] - df["wacc"]) * df["Investimento Médio"],
        np.nan
    )

    df["Lucro Econômico 2"] = np.where(
        (df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna()) & 
        (df["wacc"].notna()) & 
        (df["Investimento Médio"].notna()),
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] - (df["wacc"] * df["Investimento Médio"]),
        np.nan
    )

    df["Diferença Lucro Econômico"] = abs(df["Lucro Econômico 1"] - df["Lucro Econômico 2"])

    df["Alavancagem Eficaz"] = np.where(
        (df["ROE"].notna()) & (df["ROA"].notna()) & (df["ROI"].notna()),
        (df["ROE"] > df["ROA"]) & (df["ROE"] > df["ROI"]),
        False
    )

    return df

# Carregar dados
df = load_data()

# ==============================
# FUNÇÕES AUXILIARES
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

# Funções yfinance
def buscar_dividendos_historicos(ticker):
    try:
        ticker_yf = f"{ticker}.SA" if not ticker.endswith('.SA') else ticker
        acao = yf.Ticker(ticker_yf)
        dividendos = acao.dividends
        
        if dividendos.empty:
            return None
            
        df_dividendos = dividendos.reset_index()
        df_dividendos.columns = ['Data', 'Dividendo']
        df_dividendos['Ticker'] = ticker
        df_dividendos['Ano'] = df_dividendos['Data'].dt.year
        df_dividendos['Mes'] = df_dividendos['Data'].dt.month
        
        return df_dividendos
        
    except Exception as e:
        return None

def buscar_cotacao_atual(ticker):
    try:
        ticker_yf = f"{ticker}.SA" if not ticker.endswith('.SA') else ticker
        acao = yf.Ticker(ticker_yf)
        historico = acao.history(period="1d")
        
        if historico.empty:
            return None
            
        preco = historico['Close'].iloc[-1]
        
        setor = "N/A"
        try:
            empresa_info = df[df['Ticker'] == ticker]
            if not empresa_info.empty:
                setor = empresa_info['SETOR_ATIV'].iloc[0]
        except:
            pass
        
        return {
            'cotacao': preco,
            'setor': setor,
            'data_atualizacao': datetime.now().strftime("%d/%m/%Y")
        }
        
    except Exception as e:
        return None

# ==============================
# INTERFACE PRINCIPAL
# ==============================

# TÍTULO PRINCIPAL
st.title("📊 Dashboard CVM: Análise das Demonstrações Financeiras")

# SIDEBAR - FILTROS
with st.sidebar:
    st.header("🔧 Filtros Principais")
    st.success("✅ Dados de ações via yFinance")
    
    modo_analise = st.radio(
        "Modo de Análise:",
        ["🏆 Dados Gerais", "📈 Visão por Empresa", "🏭 Análise Setorial"]
    )
    
    anos_disponiveis = sorted(df["Ano"].unique(), reverse=True)
    ano_selecionado = st.selectbox("Selecione o Ano:", anos_disponiveis)
    
    if modo_analise == "📈 Visão por Empresa":
        ticker_selecionado = st.selectbox(
            "Selecione a Empresa:",
            sorted(df["Ticker"].dropna().unique())
        )
    elif modo_analise == "🏭 Análise Setorial":
        setor_selecionado = st.selectbox(
            "Selecione o Setor:",
            sorted(df["SETOR_ATIV"].dropna().unique())
        )
    
    st.divider()
    st.header("ℹ️ Informações")
    st.info(
        "Este dashboard apresenta os principais indicadores financeiros "
        "calculados conforme metodologia Vellani (2024). "
        "**Dados de ações via yFinance**"
    )

# CONTEÚDO PRINCIPAL BASEADO NO MODO DE ANÁLISE
if modo_analise == "🏆 Dados Gerais":
    st.header(f"🏆 Dados Gerais - Ano {ano_selecionado}")
    
    # KPIs Gerais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        empresas_ativas = df[df["Ano"] == ano_selecionado]["Ticker"].nunique()
        st.metric("Empresas Analisadas", empresas_ativas)
    
    with col2:
        setores_ativos = df[df["Ano"] == ano_selecionado]["SETOR_ATIV"].nunique()
        st.metric("Setores Representados", setores_ativos)
    
    with col3:
        receita_total = df[df["Ano"] == ano_selecionado]["Receita de Venda de Bens e/ou Serviços"].sum()
        st.metric("Receita Total", formatar_moeda_brasil_correta(receita_total, 2))
    
    with col4:
        lucro_total = df[df["Ano"] == ano_selecionado]["Lucro/Prejuízo Consolidado do Período"].sum()
        st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_total, 2))
    
    # Abas para diferentes rankings
    tab1, tab2, tab3 = st.tabs(["📈 Rentabilidade", "💰 Lucro e Receita", "🏛️ Solidez"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 10 Empresas por ROE")
            roe_ranking = df[(df["Ano"] == ano_selecionado) & (df["ROE"].notna())].nlargest(10, "ROE")
            if not roe_ranking.empty:
                fig_roe = px.bar(roe_ranking, x="Ticker", y="ROE", color="SETOR_ATIV",
                               title="Ranking de ROE")
                fig_roe.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_roe, use_container_width=True)
        
        with col2:
            st.subheader("Top 10 Empresas por ROA")
            roa_ranking = df[(df["Ano"] == ano_selecionado) & (df["ROA"].notna())].nlargest(10, "ROA")
            if not roa_ranking.empty:
                fig_roa = px.bar(roa_ranking, x="Ticker", y="ROA", color="SETOR_ATIV",
                               title="Ranking de ROA")
                fig_roa.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_roa, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 10 Empresas por Lucro Líquido")
            lucro_ranking = df[df["Ano"] == ano_selecionado].nlargest(10, "Lucro/Prejuízo Consolidado do Período")
            if not lucro_ranking.empty:
                fig_lucro = px.bar(lucro_ranking, x="Ticker", y="Lucro/Prejuízo Consolidado do Período", 
                                 color="SETOR_ATIV", title="Ranking por Lucro Líquido")
                st.plotly_chart(fig_lucro, use_container_width=True)
        
        with col2:
            st.subheader("Top 10 Empresas por Receita")
            receita_ranking = df[df["Ano"] == ano_selecionado].nlargest(10, "Receita de Venda de Bens e/ou Serviços")
            if not receita_ranking.empty:
                fig_receita = px.bar(receita_ranking, x="Ticker", y="Receita de Venda de Bens e/ou Serviços", 
                                   color="SETOR_ATIV", title="Ranking por Receita")
                st.plotly_chart(fig_receita, use_container_width=True)

elif modo_analise == "📈 Visão por Empresa":
    st.header(f"📈 Análise Detalhada - {ticker_selecionado}")
    
    df_empresa = df[(df["Ticker"] == ticker_selecionado) & (df["Ano"] == ano_selecionado)]
    
    if not df_empresa.empty:
        # KPIs Principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            roe = df_empresa["ROE"].iloc[0]
            st.metric("ROE", formatar_percentual_brasil(roe) if pd.notna(roe) else "N/A")
        
        with col2:
            roa = df_empresa["ROA"].iloc[0]
            st.metric("ROA", formatar_percentual_brasil(roa) if pd.notna(roa) else "N/A")
        
        with col3:
            margem_liquida = df_empresa["Margem Líquida"].iloc[0]
            st.metric("Margem Líquida", formatar_percentual_brasil(margem_liquida) if pd.notna(margem_liquida) else "N/A")
        
        with col4:
            # Buscar cotação atual
            cotacao_data = buscar_cotacao_atual(ticker_selecionado)
            if cotacao_data:
                st.metric("Cotação Atual", f"R$ {cotacao_data['cotacao']:.2f}")
        
        # Abas de análise
        tab1, tab2, tab3 = st.tabs(["📊 Indicadores", "💰 Dividendos", "📈 Evolução"])
        
        with tab1:
            st.subheader("Indicadores Financeiros")
            
            # Criar dataframe com indicadores
            indicadores_data = []
            indicadores = [
                ("ROE", "ROE"),
                ("ROA", "ROA"), 
                ("ROI", "ROI"),
                ("Margem Bruta", "Margem Bruta"),
                ("Margem Operacional", "Margem Operacional"),
                ("Margem Líquida", "Margem Líquida"),
                ("WACC", "wacc")
            ]
            
            for nome, coluna in indicadores:
                valor = df_empresa[coluna].iloc[0] if coluna in df_empresa.columns else None
                if pd.notna(valor):
                    if "Margem" in nome or "RO" in nome or "WACC" in nome:
                        valor_formatado = formatar_percentual_brasil(valor)
                    else:
                        valor_formatado = formatar_moeda_brasil_correta(valor)
                    indicadores_data.append({"Indicador": nome, "Valor": valor_formatado})
            
            if indicadores_data:
                st.dataframe(pd.DataFrame(indicadores_data), use_container_width=True, hide_index=True)
        
        with tab2:
            st.subheader("Histórico de Dividendos")
            
            dividendos = buscar_dividendos_historicos(ticker_selecionado)
            if dividendos is not None and not dividendos.empty:
                # Gráfico de dividendos
                fig = px.line(dividendos, x='Data', y='Dividendo', 
                            title=f'Dividendos por Ação - {ticker_selecionado}')
                st.plotly_chart(fig, use_container_width=True)
                
                # Últimos dividendos
                st.subheader("Últimos Dividendos")
                ultimos_dividendos = dividendos.nlargest(10, 'Data')[['Data', 'Dividendo']]
                ultimos_dividendos['Data'] = ultimos_dividendos['Data'].dt.strftime('%d/%m/%Y')
                ultimos_dividendos['Dividendo'] = ultimos_dividendos['Dividendo'].apply(
                    lambda x: f"R$ {x:.4f}"
                )
                st.dataframe(ultimos_dividendos, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ Não foram encontrados dados de dividendos para esta empresa")
        
        with tab3:
            st.subheader("Evolução Temporal")
            
            df_historico = df[df["Ticker"] == ticker_selecionado].sort_values("Ano")
            
            if len(df_historico) > 1:
                fig = go.Figure()
                
                # Adicionar ROE
                if "ROE" in df_historico.columns:
                    fig.add_trace(go.Scatter(
                        x=df_historico['Ano'], 
                        y=df_historico['ROE'],
                        mode='lines+markers',
                        name='ROE',
                        line=dict(color='#1f77b4', width=3)
                    ))
                
                # Adicionar ROA
                if "ROA" in df_historico.columns:
                    fig.add_trace(go.Scatter(
                        x=df_historico['Ano'], 
                        y=df_historico['ROA'],
                        mode='lines+markers',
                        name='ROA',
                        line=dict(color='#ff7f0e', width=3)
                    ))
                
                fig.update_layout(
                    title='Evolução da Rentabilidade',
                    xaxis_title='Ano',
                    yaxis_title='Percentual',
                    yaxis_tickformat=',.2%',
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("ℹ️ São necessários dados de múltiplos anos para análise de evolução")

elif modo_analise == "🏭 Análise Setorial":
    st.header(f"🏭 Análise Setorial - {setor_selecionado}")
    
    df_setor = df[(df["SETOR_ATIV"] == setor_selecionado) & (df["Ano"] == ano_selecionado)]
    
    if not df_setor.empty:
        # KPIs do Setor
        col1, col2, col3 = st.columns(3)
        
        with col1:
            empresas_setor = df_setor["Ticker"].nunique()
            st.metric("Empresas no Setor", empresas_setor)
        
        with col2:
            receita_setor = df_setor["Receita de Venda de Bens e/ou Serviços"].sum()
            st.metric("Receita Total", formatar_moeda_brasil_correta(receita_setor, 2))
        
        with col3:
            lucro_setor = df_setor["Lucro/Prejuízo Consolidado do Período"].sum()
            st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_setor, 2))
        
        # Ranking do setor
        st.subheader("Ranking por ROE no Setor")
        ranking_roe = df_setor[df_setor["ROE"].notna()].nlargest(15, "ROE")
        
        if not ranking_roe.empty:
            fig = px.bar(ranking_roe, x="Ticker", y="ROE", 
                       title=f"Top Empresas por ROE - {setor_selecionado}")
            fig.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig, use_container_width=True)

# ==============================
# RODAPÉ
# ==============================
st.divider()
st.caption(f"📊 Dashboard CVM - Indicadores Financeiros | Dados atualizados para {ano_selecionado} | Total de empresas na base: {df['Ticker'].nunique()}")

# ==============================
# SEÇÃO DE INFORMAÇÕES NO SIDEBAR
# ==============================
with st.sidebar:
    with st.expander("💡 Metodologia Vellani (2024)"):
        st.write("""
        **Indicadores Calculados:**
        - **ROE**: Lucro Líquido ÷ PL Médio
        - **ROA**: Resultado Operacional ÷ Ativo Médio  
        - **ROI**: Resultado Operacional ÷ Investimento Médio
        - **WACC**: Custo médio ponderado de capital
        - **EBITDA**: Resultado Operacional + Depreciação/Amortização
        
        **Fonte dos Dados:**
        - Demonstrações financeiras: CVM (2010-2024)
        - Cotações e dividendos: yFinance
        - Metodologia: Vellani (2024)
        """)
