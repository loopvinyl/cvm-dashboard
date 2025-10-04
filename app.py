# ==============================================================
# DASHBOARD CVM - Indicadores Financeiros (versão Google Colab)
# ==============================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ==============================
# CONFIGURAÇÕES INICIAIS
# ==============================
st.set_page_config(page_title="Dashboard CVM - Indicadores", layout="wide")
st.title("📊 Dashboard CVM - Análise de Indicadores Financeiros")

# ==============================
# LEITURA DE DADOS
# ==============================
@st.cache_data
def load_data():
    # Caminho no Colab — coloque o arquivo data_frame.xlsx em /content/
    df = pd.read_excel("/content/data_frame.xlsx")
    df.columns = [c.strip() for c in df.columns]

    # =============================================================
    # MAPEAMENTO EXATO DAS CONTAS (compatível com Excel CPFE3)
    # =============================================================
    # BP → data_frame
    #   Ativo Total                                → Ativo Total
    #   Passivo Circulante                         → Passivo Circulante
    #   Passivo Não Circulante                     → Passivo Não Circulante
    #   Empréstimos e Financiamentos - Circulante  → Empréstimos e Financiamentos - Circulante
    #   Empréstimos e Financiamentos - Não Circulante → Empréstimos e Financiamentos - Não Circulante
    #   Patrimônio Líquido Consolidado             → Patrimônio Líquido Consolidado
    # DRE → data_frame
    #   Receita de Venda de Bens e/ou Serviços     → Receita de Venda de Bens e/ou Serviços
    #   Custo dos Bens e/ou Serviços Vendidos      → Custo dos Bens e/ou Serviços Vendidos
    #   Resultado Bruto                            → Resultado Bruto
    #   Resultado Antes do Resultado Financeiro e dos Tributos → Resultado Antes do Resultado Financeiro e dos Tributos
    #   Resultado Financeiro, Receitas Financeiras, Despesas Financeiras, Lucro/Prejuízo Consolidado do Período
    # DFC → data_frame
    #   Pagamento de Dividendos                    → Pagamento de Dividendos

    # =============================================================
    # CÁLCULOS DE MÉDIAS
    # =============================================================
    df["Ativo Médio"] = (df["Ativo Total"] + df.groupby("Ticker")["Ativo Total"].shift(1)) / 2
    df["PL Médio"] = (df["Patrimônio Líquido Consolidado"] + df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1)) / 2
    df["Passivo Oneroso Médio"] = (
        (df["Empréstimos e Financiamentos - Circulante"].fillna(0)
         + df["Empréstimos e Financiamentos - Não Circulante"].fillna(0)
         + df.groupby("Ticker")["Empréstimos e Financiamentos - Circulante"].shift(1).fillna(0)
         + df.groupby("Ticker")["Empréstimos e Financiamentos - Não Circulante"].shift(1).fillna(0)) / 2
    )
    df["Investimento Médio"] = (
        (df["Empréstimos e Financiamentos - Circulante"].fillna(0)
         + df["Empréstimos e Financiamentos - Não Circulante"].fillna(0)
         + df["Patrimônio Líquido Consolidado"]
         + df.groupby("Ticker")["Empréstimos e Financiamentos - Circulante"].shift(1).fillna(0)
         + df.groupby("Ticker")["Empréstimos e Financiamentos - Não Circulante"].shift(1).fillna(0)
         + df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1).fillna(0)) / 2
    )

    # =============================================================
    # INDICADORES DE RENTABILIDADE
    # =============================================================
    df["ROA"] = np.where(df["Ativo Médio"] > 0,
                         df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Ativo Médio"], np.nan)
    df["ROI"] = np.where(df["Investimento Médio"] > 0,
                         df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Investimento Médio"], np.nan)
    df["ROE"] = np.where(df["PL Médio"] > 0,
                         df["Lucro/Prejuízo Consolidado do Período"] / df["PL Médio"], np.nan)

    # =============================================================
    # MARGENS
    # =============================================================
    df["Margem Bruta"] = np.where(df["Receita de Venda de Bens e/ou Serviços"] > 0,
                                  df["Resultado Bruto"] / df["Receita de Venda de Bens e/ou Serviços"], np.nan)
    df["Margem Operacional"] = np.where(df["Receita de Venda de Bens e/ou Serviços"] > 0,
                                        df["Resultado Antes do Resultado Financeiro e dos Tributos"]
                                        / df["Receita de Venda de Bens e/ou Serviços"], np.nan)
    df["Margem Líquida"] = np.where(df["Receita de Venda de Bens e/ou Serviços"] > 0,
                                    df["Lucro/Prejuízo Consolidado do Período"]
                                    / df["Receita de Venda de Bens e/ou Serviços"], np.nan)

    # =============================================================
    # ESTRUTURA DE CAPITAL
    # =============================================================
    df["Total Passivo"] = (df["Passivo Circulante"].fillna(0)
                           + df["Passivo Não Circulante"].fillna(0)
                           + df["Patrimônio Líquido Consolidado"].fillna(0))
    df["Percentual Capital Terceiros"] = np.where(df["Total Passivo"] > 0,
                                                  (df["Passivo Circulante"].fillna(0)
                                                   + df["Passivo Não Circulante"].fillna(0))
                                                  / df["Total Passivo"], np.nan)
    df["Percentual Capital Próprio"] = np.where(df["Total Passivo"] > 0,
                                                df["Patrimônio Líquido Consolidado"]
                                                / df["Total Passivo"], np.nan)

    # =============================================================
    # CUSTO DE CAPITAL
    # =============================================================
    df["ki"] = np.where((df["Passivo Oneroso Médio"] > 0) & (df["Despesas Financeiras"].notna()),
                        df["Despesas Financeiras"].abs() / df["Passivo Oneroso Médio"], np.nan)
    df["ke"] = np.where((df["PL Médio"] > 0) & (df["Pagamento de Dividendos"].notna()),
                        df["Pagamento de Dividendos"].abs() / df["PL Médio"], np.nan)
    df["wacc"] = np.where((df["ki"].notna()) & (df["ke"].notna())
                          & (df["Percentual Capital Terceiros"].notna())
                          & (df["Percentual Capital Próprio"].notna()),
                          (df["ki"] * df["Percentual Capital Terceiros"])
                          + (df["ke"] * df["Percentual Capital Próprio"]), np.nan)

    # =============================================================
    # EBITDA E LUCRO ECONÔMICO
    # =============================================================
    df["EBITDA"] = np.where((df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna())
                            & (df["Despesas Financeiras"].notna()),
                            df["Resultado Antes do Resultado Financeiro e dos Tributos"]
                            + df["Despesas Financeiras"].abs(), np.nan)
    df["ROI EBITDA"] = np.where((df["EBITDA"].notna()) & (df["Investimento Médio"] > 0),
                                df["EBITDA"] / df["Investimento Médio"], np.nan)
    df["Lucro Econômico 1"] = np.where((df["ROI"].notna()) & (df["wacc"].notna())
                                       & (df["Investimento Médio"].notna()),
                                       (df["ROI"] - df["wacc"]) * df["Investimento Médio"], np.nan)
    df["Lucro Econômico 2"] = np.where((df["Lucro/Prejuízo Consolidado do Período"].notna())
                                       & (df["Despesas Financeiras"].notna())
                                       & (df["Pagamento de Dividendos"].notna()),
                                       df["Lucro/Prejuízo Consolidado do Período"]
                                       - df["Despesas Financeiras"].abs()
                                       - df["Pagamento de Dividendos"].abs(), np.nan)
    df["Lucro Econômico EBITDA"] = np.where((df["ROI EBITDA"].notna()) & (df["wacc"].notna())
                                            & (df["Investimento Médio"].notna()),
                                            (df["ROI EBITDA"] - df["wacc"]) * df["Investimento Médio"], np.nan)

    # =============================================================
    # ANÁLISE DE ALAVANCAGEM
    # =============================================================
    df["Alavancagem Eficaz"] = np.where((df["ROE"].notna()) & (df["ROA"].notna())
                                        & (df["ROI"].notna()),
                                        (df["ROE"] > df["ROA"]) & (df["ROE"] > df["ROI"]), False)
    return df


# ==============================
# EXECUÇÃO
# ==============================
df = load_data()

# ==============================
# SIDEBAR - FILTROS
# ==============================
st.sidebar.header("🔧 Filtros Principais")
modo_analise = st.sidebar.radio(
    "Modo de Análise:",
    ["🏆 Ranking Comparativo", "📈 Visão por Empresa", "🏭 Análise Setorial"]
)
anos_disponiveis = sorted(df["Ano"].unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Selecione o Ano:", anos_disponiveis)

if modo_analise == "📈 Visão por Empresa":
    ticker_selecionado = st.sidebar.selectbox("Selecione a Empresa:",
                                              sorted(df["Ticker"].dropna().unique()))
    df_filtrado = df[(df["Ticker"] == ticker_selecionado)
                     & (df["Ano"] == ano_selecionado)]
elif modo_analise == "🏭 Análise Setorial":
    setor_selecionado = st.sidebar.selectbox("Selecione o Setor:",
                                             sorted(df["SETOR_ATIV"].dropna().unique()))
    df_filtrado = df[(df["SETOR_ATIV"] == setor_selecionado)
                     & (df["Ano"] == ano_selecionado)]
else:
    df_filtrado = df[df["Ano"] == ano_selecionado]

# ==============================
# TELAS PRINCIPAIS (Ranking / Empresa / Setor)
# ==============================
# -- Aqui segue exatamente o mesmo código de visualização que você já tinha:
# gráficos de barras, métricas, tabelas e fórmulas —
# nenhuma alteração estrutural é necessária,
# apenas certifique-se de manter os mesmos blocos a partir do
# trecho “# ============================== TELA PRINCIPAL – RANKING COMPARATIVO”.

# (cole aqui o restante do seu código de visualização completo)
