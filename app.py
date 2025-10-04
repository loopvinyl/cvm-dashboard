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
# LEITURA E PREPARAÇÃO DE DADOS
# ==============================
@st.cache_data
def load_data():
    df = pd.read_excel("data_frame.xlsx")
    df.columns = [c.strip() for c in df.columns]
    
    # Ordenar por Ticker e Ano para cálculos consistentes
    df = df.sort_values(['Ticker', 'Ano'])
    
    # =============================================
    # CÁLCULO DAS MÉDIAS (CORRETO)
    # =============================================
    
    # Criar DataFrame com dados do ano anterior para cada empresa
    df_anterior = df.copy()
    df_anterior['Ano'] = df_anterior['Ano'] + 1
    
    # Merge para ter dados atual e anterior na mesma linha
    df_completo = pd.merge(
        df, 
        df_anterior, 
        on=['Ticker', 'Ano'], 
        suffixes=('', '_anterior'),
        how='left'
    )
    
    # 1. ATIVO MÉDIO = (Ativo Total atual + Ativo Total anterior) / 2
    df_completo["Ativo Médio"] = (
        df_completo["Ativo Total"] + df_completo["Ativo Total_anterior"]
    ) / 2
    
    # 2. PL MÉDIO = (Patrimônio Líquido atual + Patrimônio Líquido anterior) / 2  
    df_completo["PL Médio"] = (
        df_completo["Patrimônio Líquido Consolidado"] + 
        df_completo["Patrimônio Líquido Consolidado_anterior"]
    ) / 2
    
    # 3. PASSIVO ONEROSO MÉDIO = (Empréstimos Total atual + Empréstimos Total anterior) / 2
    df_completo["Empréstimos Total"] = (
        df_completo["Empréstimos e Financiamentos - Circulante"].fillna(0) +
        df_completo["Empréstimos e Financiamentos - Não Circulante"].fillna(0)
    )
    
    df_completo["Empréstimos Total_anterior"] = (
        df_completo["Empréstimos e Financiamentos - Circulante_anterior"].fillna(0) +
        df_completo["Empréstimos e Financiamentos - Não Circulante_anterior"].fillna(0)
    )
    
    df_completo["Passivo Oneroso Médio"] = (
        df_completo["Empréstimos Total"] + df_completo["Empréstimos Total_anterior"]
    ) / 2
    
    # 4. INVESTIMENTO MÉDIO = (Empréstimos Total + PL atual + Empréstimos Total anterior + PL anterior) / 2
    df_completo["Investimento Total"] = (
        df_completo["Empréstimos Total"] + 
        df_completo["Patrimônio Líquido Consolidado"]
    )
    
    df_completo["Investimento Total_anterior"] = (
        df_completo["Empréstimos Total_anterior"] + 
        df_completo["Patrimônio Líquido Consolidado_anterior"]
    )
    
    df_completo["Investimento Médio"] = (
        df_completo["Investimento Total"] + df_completo["Investimento Total_anterior"]
    ) / 2
    
    # =============================================
    # INDICADORES DE RENTABILIDADE (CORRETOS)
    # =============================================
    
    # ROA = Resultado Antes do Resultado Financeiro e dos Tributos / Ativo Médio
    df_completo["ROA"] = np.where(
        df_completo["Ativo Médio"] > 0,
        df_completo["Resultado Antes do Resultado Financeiro e dos Tributos"] / df_completo["Ativo Médio"],
        np.nan
    )
    
    # ROI = Resultado Antes do Resultado Financeiro e dos Tributos / Investimento Médio  
    df_completo["ROI"] = np.where(
        df_completo["Investimento Médio"] > 0,
        df_completo["Resultado Antes do Resultado Financeiro e dos Tributos"] / df_completo["Investimento Médio"],
        np.nan
    )
    
    # ROE = Lucro Líquido / PL Médio
    df_completo["ROE"] = np.where(
        df_completo["PL Médio"] > 0,
        df_completo["Lucro/Prejuízo Consolidado do Período"] / df_completo["PL Médio"],
        np.nan
    )
    
    # =============================================
    # ESTRUTURA DE CAPITAL (CORRETO)
    # =============================================
    
    # Total do Passivo = Passivo Circulante + Passivo Não Circulante + Patrimônio Líquido
    df_completo["Total Passivo"] = (
        df_completo["Passivo Circulante"].fillna(0) + 
        df_completo["Passivo Não Circulante"].fillna(0) + 
        df_completo["Patrimônio Líquido Consolidado"].fillna(0)
    )
    
    # Percentual Capital Terceiros = (Passivo Circulante + Passivo Não Circulante) / Total Passivo
    df_completo["Percentual Capital Terceiros"] = np.where(
        df_completo["Total Passivo"] > 0,
        (df_completo["Passivo Circulante"].fillna(0) + df_completo["Passivo Não Circulante"].fillna(0)) / df_completo["Total Passivo"],
        np.nan
    )
    
    # Percentual Capital Próprio = Patrimônio Líquido / Total Passivo
    df_completo["Percentual Capital Próprio"] = np.where(
        df_completo["Total Passivo"] > 0,
        df_completo["Patrimônio Líquido Consolidado"] / df_completo["Total Passivo"],
        np.nan
    )
    
    # =============================================
    # CUSTO DE CAPITAL (CORRETO - BASE EXCEL)
    # =============================================
    
    # ki (Custo da Dívida) = Despesas Financeiras / Passivo Oneroso Médio
    df_completo["ki"] = np.where(
        (df_completo["Passivo Oneroso Médio"] > 0) & (df_completo["Despesas Financeiras"].notna()),
        df_completo["Despesas Financeiras"].abs() / df_completo["Passivo Oneroso Médio"],
        np.nan
    )
    
    # ke (Custo do Capital Próprio) = Dividendos Pagos / PL Médio
    df_completo["ke"] = np.where(
        (df_completo["PL Médio"] > 0) & (df_completo["Pagamento de Dividendos"].notna()),
        df_completo["Pagamento de Dividendos"].abs() / df_completo["PL Médio"],
        np.nan
    )
    
    # WACC = (ki × Passivo Oneroso Médio + ke × PL Médio) / (Passivo Oneroso Médio + PL Médio)
    df_completo["wacc"] = np.where(
        (df_completo["ki"].notna()) & (df_completo["ke"].notna()) & 
        (df_completo["Passivo Oneroso Médio"].notna()) & (df_completo["PL Médio"].notna()),
        (df_completo["ki"] * df_completo["Passivo Oneroso Médio"] + 
         df_completo["ke"] * df_completo["PL Médio"]) / 
        (df_completo["Passivo Oneroso Médio"] + df_completo["PL Médio"]),
        np.nan
    )
    
    # =============================================
    # EBITDA E LUCRO ECONÔMICO (CORRETO)
    # =============================================
    
    # EBITDA = Resultado Antes do Resultado Financeiro + Despesas Financeiras (absoluto)
    df_completo["EBITDA"] = (
        df_completo["Resultado Antes do Resultado Financeiro e dos Tributos"] + 
        df_completo["Despesas Financeiras"].abs()
    )
    
    # ROI EBITDA = EBITDA / Investimento Médio
    df_completo["ROI EBITDA"] = np.where(
        (df_completo["EBITDA"].notna()) & (df_completo["Investimento Médio"] > 0),
        df_completo["EBITDA"] / df_completo["Investimento Médio"],
        np.nan
    )
    
    # Lucro Econômico 1 = (ROI - WACC) × Investimento Médio
    df_completo["Lucro Econômico 1"] = (
        (df_completo["ROI"] - df_completo["wacc"]) * df_completo["Investimento Médio"]
    )
    
    # Lucro Econômico 2 = Lucro Líquido - Despesas Financeiras - Dividendos
    df_completo["Lucro Econômico 2"] = (
        df_completo["Lucro/Prejuízo Consolidado do Período"] - 
        df_completo["Despesas Financeiras"].abs() - 
        df_completo["Pagamento de Dividendos"].abs()
    )
    
    # Lucro Econômico EBITDA = (ROI EBITDA - WACC) × Investimento Médio  
    df_completo["Lucro Econômico EBITDA"] = (
        (df_completo["ROI EBITDA"] - df_completo["wacc"]) * df_completo["Investimento Médio"]
    )
    
    # =============================================
    # ANÁLISE DE ALAVANCAGEM
    # =============================================
    
    df_completo["Alavancagem Eficaz"] = (
        (df_completo["ROE"] > df_completo["ROA"]) & 
        (df_completo["ROE"] > df_completo["ROI"])
    )
    
    return df_completo

# Carregar dados
df = load_data()

# Restante do código permanece igual...
