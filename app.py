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

    # Padronizar nomes de colunas: remover espaços e deixar maiúsculas
    df.columns = df.columns.str.strip().str.upper()

    # Calcular indicadores financeiros
    df["MARGEM_BRUTA"] = df["RESULTADO_BRUTO"] / df["RECEITA DE VENDA DE BENS E/OU SERVIÇOS"]
    df["MARGEM_OPERACIONAL"] = df["RESULTADO ANTES DO RESULTADO FINANCEIRO E DOS TRIBUTOS"] / df["RECEITA DE VENDA DE BENS E/OU SERVIÇOS"]
    df["MARGEM_LIQUIDA"] = df["LUCRO/PREJUÍZO CONSOLIDADO DO PERÍODO"] / df["RECEITA DE VENDA DE BENS E/OU SERVIÇOS"]
    df["ROE"] = df["LUCRO/PREJUÍZO CONSOLIDADO DO PERÍODO"] / df["PATRIMÔNIO LÍQUIDO CONSOLIDADO"]
    df["ROA"] = df["LUCRO/PREJUÍZO CONSOLIDADO DO PERÍODO"] / df["ATIVO TOTAL"]
    df["ENDIVIDAMENTO"] = df["PASSIVO TOTAL"] / df["PATRIMÔNIO LÍQUIDO CONSOLIDADO"]

    return df

df = load_data()

# ==============================
# KPIs GERAIS
# ==============================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Empresas (Tickers)", df["TICKER"].nunique())
col2.metric("Setores", df["SETOR_ATIV"].nunique())
col3.metric("Período", f"{df['ANO'].min()} - {df['ANO'].max()}")
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
    top_lucro = df.groupby("TICKER")["LUCRO/PREJUÍZO CONSOLIDADO DO PERÍODO"].sum().nlargest(10).reset_index()
    fig1 = px.bar(top_lucro, x="TICKER", y="LUCRO/PREJUÍZO CONSOLIDADO DO PERÍODO", title="Top 10 por Lucro")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Top 10 Tickers - Receita")
    top_receita = df.groupby("TICKER")["RECEITA DE VENDA DE BENS E/OU SERVIÇOS"].sum().nlargest(10).reset_index()
    fig2 = px.bar(top_receita, x="TICKER", y="RECEITA DE VENDA DE BENS E/OU SERVIÇOS", title="Top 10 por Receita")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Top 10 Tickers - Ativo Total")
    top_ativo = df.groupby("TICKER")["ATIVO TOTAL"].sum().nlargest(10).reset_index()
    fig3 = px.bar(top_ativo, x="TICKER", y="ATIVO TOTAL", title="Top 10 por Ativo")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Top 10 Tickers - Patrimônio Líquido")
    top_pl = df.groupby("TICKER")["PATRIMÔNIO LÍQUIDO CONSOLIDADO"].sum().nlargest(10).reset_index()
    fig4 = px.bar(top_pl, x="TICKER", y="PATRIMÔNIO LÍQUIDO CONSOLIDADO", title="Top 10 por Patrimônio Líquido")
    st.plotly_chart(fig4, use_container_width=True)

# ==============================
# POR SETOR
# ==============================
elif opcao == "🏭 Por Setor":
    setor = st.sidebar.selectbox("Selecione o setor", sorted(df["SETOR_ATIV"].dropna().unique()))
    df_setor = df[df["SETOR_ATIV"] == setor]

    st.subheader(f"📊 Análise do Setor: {setor}")

    top_setor = df_setor.groupby("TICKER")["RECEITA DE VENDA DE BENS E/OU SERVIÇOS"].sum().nlargest(10).reset_index()
    fig5 = px.bar(top_setor, x="TICKER", y="RECEITA DE VENDA DE BENS E/OU SERVIÇOS", title=f"Top 10 Tickers por Receita ({setor})")
    st.plotly_chart(fig5, use_container_width=True)

    fig6 = px.scatter(df_setor,
                      x="RECEITA DE VENDA DE BENS E/OU SERVIÇOS",
                      y="LUCRO/PREJUÍZO CONSOLIDADO DO PERÍODO",
                      size="ATIVO TOTAL",
                      color="TICKER",
                      title=f"Receita vs Lucro ({setor})")
    st.plotly_chart(fig6, use_container_width=True)

# ==============================
# POR EMPRESA (TICKER)
# ==============================
elif opcao == "🏢 Por Empresa":
    ticker = st.sidebar.selectbox("Selecione o ticker", sorted(df["TICKER"].dropna().unique()))
    df_emp = df[df["TICKER"] == ticker]

    st.subheader(f"📈 Evolução do Ticker: {ticker}")

    fig7 = px.line(df_emp, x="ANO", y="LUCRO/PREJUÍZO CONSOLIDADO DO PERÍODO", title="Lucro por Ano")
    st.plotly_chart(fig7, use_container_width=True)

    fig8 = px.line(df_emp, x="ANO", y="RECEITA DE VENDA DE BENS E/OU SERVIÇOS", title="Receita por Ano")
    st.plotly_chart(fig8, use_container_width=True)

    st.write("### Indicadores Financeiros")
    indicadores = df_emp[["ANO", "MARGEM_BRUTA", "MARGEM_OPERACIONAL", "MARGEM_LIQUIDA", "ROE", "ROA", "ENDIVIDAMENTO"]]
    st.dataframe(indicadores)
