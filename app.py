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

    # Normalizar nomes: apenas strip nos nomes originais
    df.columns = [c.strip() for c in df.columns]

    # Calcular indicadores financeiros BÁSICOS
    df["Margem Bruta"] = df["Resultado Bruto"] / df["Receita de Venda de Bens e/ou Serviços"]
    df["Margem Operacional"] = df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Receita de Venda de Bens e/ou Serviços"]
    df["Margem Líquida"] = df["Lucro/Prejuízo Consolidado do Período"] / df["Receita de Venda de Bens e/ou Serviços"]
    df["ROE"] = df["Lucro/Prejuízo Consolidado do Período"] / df["Patrimônio Líquido Consolidado"]
    df["ROA"] = df["Lucro/Prejuízo Consolidado do Período"] / df["Ativo Total"]
    df["Endividamento"] = df["Passivo Total"] / df["Patrimônio Líquido Consolidado"]
    
    # NOVOS INDICADORES BASEADOS NA ABA "INDICADORES" DO EXCEL
    # ROI (Return on Investment)
    df["Investimento Médio"] = (df["Empréstimos e Financiamentos - Circulante"] + 
                               df["Empréstimos e Financiamentos - Não Circulante"] + 
                               df["Patrimônio Líquido Consolidado"])
    df["ROI"] = df["Lucro/Prejuízo Consolidado do Período"] / df["Investimento Médio"]
    
    # Estrutura de Capital
    df["Percentual Capital Terceiros"] = (df["Passivo Circulante"] + df["Passivo Não Circulante"]) / df["Passivo Total"]
    df["Percentual Capital Próprio"] = df["Patrimônio Líquido Consolidado"] / df["Passivo Total"]
    
    # Custo da Dívida (ki)
    df["Passivo Oneroso Médio"] = (df["Empréstimos e Financiamentos - Circulante"] + 
                                  df["Empréstimos e Financiamentos - Não Circulante"])
    df["ki"] = df["Despesas Financeiras"].abs() / df["Passivo Oneroso Médio"]
    
    # Custo do Capital Próprio (ke)
    df["PL Médio"] = df["Patrimônio Líquido Consolidado"]
    df["ke"] = df["Pagamento de Dividendos"].abs() / df["PL Médio"]
    
    # WACC (Weighted Average Cost of Capital)
    df["wacc"] = ((df["ki"] * df["Passivo Oneroso Médio"]) + (df["ke"] * df["PL Médio"])) / (df["Passivo Oneroso Médio"] + df["PL Médio"])
    
    # Lucro Econômico
    df["Lucro Econômico 1"] = (df["ROI"] - df["wacc"]) * df["Investimento Médio"]
    df["Lucro Econômico 2"] = df["Lucro/Prejuízo Consolidado do Período"] - df["Despesas Financeiras"].abs() - df["Pagamento de Dividendos"].abs()
    
    # EBITDA e ROI baseado em EBITDA
    df["EBITDA"] = df["Resultado Antes do Resultado Financeiro e dos Tributos"] + df["Despesas Financeiras"].abs()
    df["ROI EBITDA"] = df["EBITDA"] / df["Investimento Médio"]
    
    # Lucro Econômico EBITDA
    df["Lucro Econômico EBITDA"] = (df["ROI EBITDA"] - df["wacc"]) * df["Investimento Médio"]

    return df

df = load_data()

# ==============================
# KPIs GERAIS
# ==============================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Empresas (Tickers)", df["Ticker"].nunique())
col2.metric("Setores", df["SETOR_ATIV"].nunique())
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
    
    # NOVOS RANKINGS ADICIONAIS
    st.subheader("Top 10 Tickers - ROI (Return on Investment)")
    top_roi = df.groupby("Ticker")["ROI"].mean().nlargest(10).reset_index()
    fig5 = px.bar(top_roi, x="Ticker", y="ROI", title="Top 10 por ROI")
    st.plotly_chart(fig5, use_container_width=True)
    
    st.subheader("Top 10 Tickers - ROE (Return on Equity)")
    top_roe = df.groupby("Ticker")["ROE"].mean().nlargest(10).reset_index()
    fig6 = px.bar(top_roe, x="Ticker", y="ROE", title="Top 10 por ROE")
    st.plotly_chart(fig6, use_container_width=True)

# ==============================
# POR SETOR
# ==============================
elif opcao == "🏭 Por Setor":
    setor = st.sidebar.selectbox("Selecione o setor", sorted(df["SETOR_ATIV"].dropna().unique()))
    df_setor = df[df["SETOR_ATIV"] == setor]

    st.subheader(f"📊 Análise do Setor: {setor}")

    top_setor = df_setor.groupby("Ticker")["Receita de Venda de Bens e/ou Serviços"].sum().nlargest(10).reset_index()
    fig7 = px.bar(top_setor, x="Ticker", y="Receita de Venda de Bens e/ou Serviços", title=f"Top 10 Tickers por Receita ({setor})")
    st.plotly_chart(fig7, use_container_width=True)

    fig8 = px.scatter(df_setor,
                      x="Receita de Venda de Bens e/ou Serviços",
                      y="Lucro/Prejuízo Consolidado do Período",
                      size="Ativo Total",
                      color="Ticker",
                      title=f"Receita vs Lucro ({setor})")
    st.plotly_chart(fig8, use_container_width=True)
    
    # NOVO GRÁFICO: Estrutura de Capital por Setor
    st.subheader(f"Estrutura de Capital - {setor}")
    estrutura_setor = df_setor.groupby("Ticker")[["Percentual Capital Terceiros", "Percentual Capital Próprio"]].mean().reset_index()
    fig9 = px.bar(estrutura_setor, 
                 x="Ticker", 
                 y=["Percentual Capital Terceiros", "Percentual Capital Próprio"],
                 title=f"Estrutura de Capital por Empresa ({setor})",
                 barmode='stack')
    st.plotly_chart(fig9, use_container_width=True)

# ==============================
# POR EMPRESA (TICKER)
# ==============================
elif opcao == "🏢 Por Empresa":
    ticker = st.sidebar.selectbox("Selecione o ticker", sorted(df["Ticker"].dropna().unique()))
    df_emp = df[df["Ticker"] == ticker]

    st.subheader(f"📈 Evolução do Ticker: {ticker}")

    fig10 = px.line(df_emp, x="Ano", y="Lucro/Prejuízo Consolidado do Período", title="Lucro por Ano")
    st.plotly_chart(fig10, use_container_width=True)

    fig11 = px.line(df_emp, x="Ano", y="Receita de Venda de Bens e/ou Serviços", title="Receita por Ano")
    st.plotly_chart(fig11, use_container_width=True)

    st.write("### Indicadores Financeiros Básicos")
    indicadores_basicos = df_emp[["Ano", "Margem Bruta", "Margem Operacional", "Margem Líquida", "ROE", "ROA", "Endividamento"]]
    st.dataframe(indicadores_basicos)
    
    st.write("### Novos Indicadores de Performance")
    indicadores_avancados = df_emp[["Ano", "ROI", "EBITDA", "ROI EBITDA", "wacc", "ki", "ke", 
                                   "Lucro Econômico 1", "Lucro Econômico 2", "Lucro Econômico EBITDA"]]
    st.dataframe(indicadores_avancados)
    
    st.write("### Estrutura de Capital")
    estrutura = df_emp[["Ano", "Percentual Capital Terceiros", "Percentual Capital Próprio"]]
    st.dataframe(estrutura)
    
    # NOVO GRÁFICO: Evolução da Rentabilidade
    st.subheader("Evolução da Rentabilidade")
    rentabilidade_df = df_emp.melt(id_vars=["Ano"], 
                                  value_vars=["ROE", "ROA", "ROI", "ROI EBITDA"],
                                  var_name="Indicador", 
                                  value_name="Valor")
    fig12 = px.line(rentabilidade_df, x="Ano", y="Valor", color="Indicador", 
                   title="Evolução dos Indicadores de Rentabilidade")
    st.plotly_chart(fig12, use_container_width=True)
