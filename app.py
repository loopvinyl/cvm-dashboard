import streamlit as st
import pandas as pd
import plotly.express as px

# ==============================
# CONFIGURAÇÕES INICIAIS
# ==============================
st.set_page_config(page_title="Dashboard CVM", layout="wide")
st.title("🚀 Dashboard CVM - Versão 2.0")

# ==============================
# LEITURA DE DADOS
# ==============================
@st.cache_data
def load_data():
    df = pd.read_excel("data_frame.xlsx")

    # Normalizar nomes de colunas
    df.columns = [c.strip() for c in df.columns]

    # Calcular indicadores financeiros
    df["Margem Bruta"] = df["Resultado Bruto"] / df["Receita de Venda de Bens e/ou Serviços"]
    df["Margem Operacional"] = df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Receita de Venda de Bens e/ou Serviços"]
    df["Margem Líquida"] = df["Lucro/Prejuízo Consolidado do Período"] / df["Receita de Venda de Bens e/ou Serviços"]
    df["ROE"] = df["Lucro/Prejuízo Consolidado do Período"] / df["Patrimônio Líquido Consolidado"]
    df["ROA"] = df["Lucro/Prejuízo Consolidado do Período"] / df["Ativo Total"]
    df["Endividamento"] = df["Passivo Total"] / df["Patrimônio Líquido Consolidado"]

    return df

df = load_data()

# ==============================
# KPIs GERAIS
# ==============================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Empresas (Tickers)", df["Ticker"].nunique())
col2.metric("Setores", df["Setor"].nunique())
col3.metric("Período", f"{df['Ano'].min()} - {df['Ano'].max()}")
col4.metric("Linhas", len(df))

st.divider()

# ==============================
# SIDEBAR
# ==============================
st.sidebar.header("Filtros")
opcao = st.sidebar.radio("Escolha a análise", ["📊 Ranking Geral", "🏭 Por Setor", "🏢 Por Empresa"])

# ==============================
# RANKING GERAL
# ==============================
if opcao == "📊 Ranking Geral":
    st.subheader("Top 10 Tickers - Lucro Líquido")
    top_lucro = df.groupby("Ticker")["Lucro/Prejuízo Consolidado do Período"].sum().nlargest(10).reset_index()
    fig1 = px.bar(top_lucro, x="Ticker", y="Lucro/Prejuízo Consolidado do Período", title="Top 10 por Lucro")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Top 10 Tickers - Receita")
    top_receita = df.groupby("Ticker")["Receita de Venda de Bens e/ou Serviços"].sum().nlargest(10).reset_index()
    fig2 = px.bar(top_receita, x="Ticker", y="Receita de Venda de Bens e/ou Serviços", title="Top 10 por Receita")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Top 10 Tickers - Ativo Total")
    top_ativo = df.groupby("Ticker")["Ativo Total"].sum().nlargest(10).reset_index()
    fig3 = px.bar(top_ativo, x="Ticker", y="Ativo Total", title="Top 10 por Ativo")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Top 10 Tickers - Patrimônio Líquido")
    top_pl = df.groupby("Ticker")["Patrimônio Líquido Consolidado"].sum().nlargest(10).reset_index()
    fig4 = px.bar(top_pl, x="Ticker", y="Patrimônio Líquido Consolidado", title="Top 10 por Patrimônio Líquido")
    st.plotly_chart(fig4, use_container_width=True)

# ==============================
# POR SETOR
# ==============================
elif opcao == "🏭 Por Setor":
    setor = st.sidebar.selectbox("Selecione o setor", sorted(df["Setor"].dropna().unique()))
    df_setor = df[df["Setor"] == setor]

    st.subheader(f"📊 Análise do Setor: {setor}")

    top_setor = df_setor.groupby("Ticker")["Receita de Venda de Bens e/ou Serviços"].sum().nlargest(10).reset_index()
    fig5 = px.bar(top_setor, x="Ticker", y="Receita de Venda de Bens e/ou Serviços", title=f"Top 10 Tickers por Receita ({setor})")
    st.plotly_chart(fig5, use_container_width=True)

    fig6 = px.scatter(df_setor,
                      x="Receita de Venda de Bens e/ou Serviços",
                      y="Lucro/Prejuízo Consolidado do Período",
                      size="Ativo Total", color="Ticker",
                      title=f"Receita vs Lucro ({setor})")
    st.plotly_chart(fig6, use_container_width=True)

# ==============================
# POR EMPRESA (TICKER)
# ==============================
elif opcao == "🏢 Por Empresa":
    ticker = st.sidebar.selectbox("Selecione o ticker", sorted(df["Ticker"].dropna().unique()))
    df_emp = df[df["Ticker"] == ticker]

    st.subheader(f"📈 Evolução do Ticker: {ticker}")

    fig7 = px.line(df_emp, x="Ano", y="Lucro/Prejuízo Consolidado do Período", title="Lucro por Ano")
    st.plotly_chart(fig7, use_container_width=True)

    fig8 = px.line(df_emp, x="Ano", y="Receita de Venda de Bens e/ou Serviços", title="Receita por Ano")
    st.plotly_chart(fig8, use_container_width=True)

    st.write("### Indicadores Financeiros")
    indicadores = df_emp[["Ano", "Margem Bruta", "Margem Operacional", "Margem Líquida", "ROE", "ROA", "Endividamento"]]
    st.dataframe(indicadores)
