import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

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
    
    # CORREÇÃO: NOVOS INDICADORES COM TRATAMENTO DE ERROS
    # Investimento Médio (corrigindo a fórmula)
    df["Investimento Médio"] = (df["Empréstimos e Financiamentos - Circulante"].fillna(0) + 
                               df["Empréstimos e Financiamentos - Não Circulante"].fillna(0) + 
                               df["Patrimônio Líquido Consolidado"].fillna(0))
    
    # ROI com tratamento para evitar divisão por zero
    df["ROI"] = np.where(
        df["Investimento Médio"] != 0,
        df["Lucro/Prejuízo Consolidado do Período"] / df["Investimento Médio"],
        np.nan
    )
    
    # Estrutura de Capital com tratamento
    df["Percentual Capital Terceiros"] = np.where(
        df["Passivo Total"] != 0,
        (df["Passivo Circulante"].fillna(0) + df["Passivo Não Circulante"].fillna(0)) / df["Passivo Total"],
        np.nan
    )
    
    df["Percentual Capital Próprio"] = np.where(
        df["Passivo Total"] != 0,
        df["Patrimônio Líquido Consolidado"] / df["Passivo Total"],
        np.nan
    )
    
    # Custo da Dívida (ki) com tratamento
    df["Passivo Oneroso Médio"] = (df["Empréstimos e Financiamentos - Circulante"].fillna(0) + 
                                  df["Empréstimos e Financiamentos - Não Circulante"].fillna(0))
    
    df["ki"] = np.where(
        (df["Passivo Oneroso Médio"] != 0) & (df["Despesas Financeiras"].notna()),
        df["Despesas Financeiras"].abs() / df["Passivo Oneroso Médio"],
        np.nan
    )
    
    # Custo do Capital Próprio (ke) com tratamento
    df["PL Médio"] = df["Patrimônio Líquido Consolidado"]
    
    df["ke"] = np.where(
        (df["PL Médio"] != 0) & (df["Pagamento de Dividendos"].notna()),
        df["Pagamento de Dividendos"].abs() / df["PL Médio"],
        np.nan
    )
    
    # WACC com tratamento robusto
    def calcular_wacc(row):
        try:
            if (pd.notna(row['Passivo Oneroso Médio']) and pd.notna(row['PL Médio']) and 
                pd.notna(row['ki']) and pd.notna(row['ke'])):
                total_capital = row['Passivo Oneroso Médio'] + row['PL Médio']
                if total_capital > 0:
                    return ((row['ki'] * row['Passivo Oneroso Médio']) + (row['ke'] * row['PL Médio'])) / total_capital
            return np.nan
        except:
            return np.nan
    
    df["wacc"] = df.apply(calcular_wacc, axis=1)
    
    # Lucro Econômico com tratamento
    df["Lucro Econômico 1"] = np.where(
        (df["ROI"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()),
        (df["ROI"] - df["wacc"]) * df["Investimento Médio"],
        np.nan
    )
    
    df["Lucro Econômico 2"] = np.where(
        (df["Lucro/Prejuízo Consolidado do Período"].notna()) & 
        (df["Despesas Financeiras"].notna()) & 
        (df["Pagamento de Dividendos"].notna()),
        df["Lucro/Prejuízo Consolidado do Período"] - df["Despesas Financeiras"].abs() - df["Pagamento de Dividendos"].abs(),
        np.nan
    )
    
    # EBITDA e ROI baseado em EBITDA
    df["EBITDA"] = np.where(
        (df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna()) & 
        (df["Despesas Financeiras"].notna()),
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] + df["Despesas Financeiras"].abs(),
        np.nan
    )
    
    df["ROI EBITDA"] = np.where(
        (df["EBITDA"].notna()) & (df["Investimento Médio"] != 0),
        df["EBITDA"] / df["Investimento Médio"],
        np.nan
    )
    
    # Lucro Econômico EBITDA
    df["Lucro Econômico EBITDA"] = np.where(
        (df["ROI EBITDA"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()),
        (df["ROI EBITDA"] - df["wacc"]) * df["Investimento Médio"],
        np.nan
    )

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

    # NOVOS RANKINGS ADICIONAIS COM FILTRO PARA VALORES VÁLIDOS
    st.subheader("Top 10 Tickers - ROI (Return on Investment)")
    # Filtrar apenas tickers com ROI válido (não nulo e finito)
    roi_valido = df[df["ROI"].notna() & np.isfinite(df["ROI"])]
    if not roi_valido.empty:
        top_roi = roi_valido.groupby("Ticker")["ROI"].mean().nlargest(10).reset_index()
        fig3 = px.bar(top_roi, x="Ticker", y="ROI", title="Top 10 por ROI (apenas valores válidos)")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("Não há dados válidos de ROI para exibir")
    
    st.subheader("Top 10 Tickers - ROE (Return on Equity)")
    # Filtrar apenas tickers com ROE válido
    roe_valido = df[df["ROE"].notna() & np.isfinite(df["ROE"])]
    if not roe_valido.empty:
        top_roe = roe_valido.groupby("Ticker")["ROE"].mean().nlargest(10).reset_index()
        fig4 = px.bar(top_roe, x="Ticker", y="ROE", title="Top 10 por ROE (apenas valores válidos)")
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.warning("Não há dados válidos de ROE para exibir")

    st.subheader("Top 10 Tickers - Ativo Total")
    top_ativo = df.groupby("Ticker")["Ativo Total"].sum().nlargest(10).reset_index()
    fig5 = px.bar(top_ativo, x="Ticker", y="Ativo Total", title="Top 10 por Ativo")
    st.plotly_chart(fig5, use_container_width=True)

    st.subheader("Top 10 Tickers - Patrimônio Líquido")
    top_pl = df.groupby("Ticker")["Patrimônio Líquido Consolidado"].sum().nlargest(10).reset_index()
    fig6 = px.bar(top_pl, x="Ticker", y="Patrimônio Líquido Consolidado", title="Top 10 por Patrimônio Líquido")
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
    
    # NOVO GRÁFICO: Estrutura de Capital por Setor (apenas valores válidos)
    st.subheader(f"Estrutura de Capital - {setor}")
    estrutura_valida = df_setor[df_setor["Percentual Capital Terceiros"].notna() & 
                               df_setor["Percentual Capital Próprio"].notna()]
    if not estrutura_valida.empty:
        estrutura_setor = estrutura_valida.groupby("Ticker")[["Percentual Capital Terceiros", "Percentual Capital Próprio"]].mean().reset_index()
        fig9 = px.bar(estrutura_setor, 
                     x="Ticker", 
                     y=["Percentual Capital Terceiros", "Percentual Capital Próprio"],
                     title=f"Estrutura de Capital por Empresa ({setor})",
                     barmode='stack')
        st.plotly_chart(fig9, use_container_width=True)
    else:
        st.warning(f"Não há dados válidos de estrutura de capital para o setor {setor}")

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
    # Filtrar apenas colunas que têm pelo menos um valor não nulo
    cols_avancadas = ["Ano", "ROI", "EBITDA", "ROI EBITDA", "wacc", "ki", "ke", 
                     "Lucro Econômico 1", "Lucro Econômico 2", "Lucro Econômico EBITDA"]
    cols_disponiveis = [col for col in cols_avancadas if col in df_emp.columns and df_emp[col].notna().any()]
    
    if cols_disponiveis:
        indicadores_avancados = df_emp[cols_disponiveis]
        st.dataframe(indicadores_avancados)
    else:
        st.warning("Não há dados disponíveis para os indicadores avançados desta empresa")
    
    st.write("### Estrutura de Capital")
    estrutura_cols = ["Ano", "Percentual Capital Terceiros", "Percentual Capital Próprio"]
    estrutura_disponivel = [col for col in estrutura_cols if col in df_emp.columns and df_emp[col].notna().any()]
    
    if estrutura_disponivel:
        estrutura = df_emp[estrutura_disponivel]
        st.dataframe(estrutura)
    else:
        st.warning("Não há dados disponíveis sobre a estrutura de capital desta empresa")
    
    # NOVO GRÁFICO: Evolução da Rentabilidade (apenas indicadores válidos)
    st.subheader("Evolução da Rentabilidade")
    rentabilidade_cols = ["ROE", "ROA", "ROI", "ROI EBITDA"]
    rentabilidade_disponivel = [col for col in rentabilidade_cols if col in df_emp.columns and df_emp[col].notna().any()]
    
    if rentabilidade_disponivel:
        rentabilidade_df = df_emp.melt(id_vars=["Ano"], 
                                      value_vars=rentabilidade_disponivel,
                                      var_name="Indicador", 
                                      value_name="Valor")
        fig12 = px.line(rentabilidade_df, x="Ano", y="Valor", color="Indicador", 
                       title="Evolução dos Indicadores de Rentabilidade")
        st.plotly_chart(fig12, use_container_width=True)
    else:
        st.warning("Não há dados válidos de rentabilidade para exibir o gráfico")
