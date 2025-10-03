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
    df = pd.read_excel("data_frame.xlsx")
    
    # Normalizar nomes das colunas
    df.columns = [c.strip() for c in df.columns]
    
    # Adicionar uma coluna 'Ano' com os dados da coluna 'Data Recente'
    df['Ano'] = pd.to_datetime(df['Data Recente']).dt.year
    df['Ticker'] = 'CPFE3' # Simulação, pois a planilha não contém a coluna
    
    # Ordem de Ticker e Data para cálculos com .shift()
    df = df.sort_values(by=['Ticker', 'Ano']).reset_index(drop=True)

    # CALCULAR INDICADORES CONFORME ABA "INDICADORES" DO EXCEL
    
    # Valores Médios do Período Anterior
    df["Ativo Total Anterior"] = df.groupby("Ticker")["Ativo Total"].shift(1)
    df["PL Consolidado Anterior"] = df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1)
    df["Passivo Oneroso Anterior"] = df.groupby("Ticker")["Empréstimos e Financiamentos - Circulante"].shift(1).fillna(0) + df.groupby("Ticker")["Empréstimos e Financiamentos - Não Circulante"].shift(1).fillna(0)

    # 1. ROA (Return on Assets) - APENAS PARA LUCRO POSITIVO E ATIVO MÉDIO POSITIVO
    df["Ativo Médio"] = (df["Ativo Total"] + df["Ativo Total Anterior"]) / 2
    df["ROA"] = np.where(
        (df["Ativo Médio"] > 0) & (df["Lucro/Prejuízo Consolidado do Período"] > 0),
        df["Lucro/Prejuízo Consolidado do Período"] / df["Ativo Médio"],
        np.nan
    )
    
    # 2. ROE (Return on Equity) - APENAS PARA LUCRO POSITIVO E PL MÉDIO POSITIVO
    df["PL Médio"] = (df["Patrimônio Líquido Consolidado"] + df["PL Consolidado Anterior"]) / 2
    df["ROE"] = np.where(
        (df["PL Médio"] > 0) & (df["Lucro/Prejuízo Consolidado do Período"] > 0),
        df["Lucro/Prejuízo Consolidado do Período"] / df["PL Médio"],
        np.nan
    )
    
    # 3. Custo da Dívida (ki)
    df["Passivo Oneroso"] = df["Empréstimos e Financiamentos - Circulante"].fillna(0) + df["Empréstimos e Financiamentos - Não Circulante"].fillna(0)
    df["Passivo Oneroso Médio"] = (df["Passivo Oneroso"] + df["Passivo Oneroso Anterior"]) / 2
    df["ki"] = np.where(
        (df["Passivo Oneroso Médio"] != 0) & (df["Despesas Financeiras"].notna()),
        df["Despesas Financeiras"].abs() / df["Passivo Oneroso Médio"],
        np.nan
    )
    
    # 4. Custo do Capital Próprio (ke)
    df["ke"] = np.where(
        (df["PL Médio"] != 0) & (df["Dividendo e juros sobre o capital próprio pagos"].notna()),
        df["Dividendo e juros sobre o capital próprio pagos"].abs() / df["PL Médio"],
        np.nan
    )
    
    # 5. WACC (Weighted Average Cost of Capital)
    def calcular_wacc(row):
        try:
            if (pd.notna(row['Passivo Oneroso Médio']) and pd.notna(row['PL Médio']) and 
                pd.notna(row['ki']) and pd.notna(row['ke'])):
                
                total_capital = row['Passivo Oneroso Médio'] + row['PL Médio']
                if total_capital > 0:
                    percentual_terceiros = row['Passivo Oneroso Médio'] / total_capital
                    percentual_proprio = row['PL Médio'] / total_capital
                    return (row['ki'] * percentual_terceiros) + (row['ke'] * percentual_proprio)
            return np.nan
        except:
            return np.nan
            
    df["wacc"] = df.apply(calcular_wacc, axis=1)
    
    # 6. ROI (Return on Investment) - APENAS PARA LUCRO POSITIVO E INVESTIMENTO POSITIVO
    df["Investimento Médio"] = df["Passivo Oneroso Médio"] + df["PL Médio"]
    df["ROI"] = np.where(
        (df["Investimento Médio"] > 0) & (df["Lucro/Prejuízo Consolidado do Período"] > 0),
        df["Lucro/Prejuízo Consolidado do Período"] / df["Investimento Médio"],
        np.nan
    )

    # 7. Lucro Econômico
    df["Lucro Econômico 1"] = np.where(
        (df["ROI"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()),
        (df["ROI"] - df["wacc"]) * df["Investimento Médio"],
        np.nan
    )
    
    # Ajuste na fórmula do Lucro Econômico 2 para refletir a planilha
    df["Lucro Econômico 2"] = np.where(
        (df["Lucro/Prejuízo Consolidado do Período"].notna()) & 
        (df["Patrimônio Líquido Consolidado"].notna()) & 
        (df["ke"].notna()),
        df["Lucro/Prejuízo Consolidado do Período"] - (df["Patrimônio Líquido Consolidado"] * df["ke"]),
        np.nan
    )

    # 8. Estrutura de Capital
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
    
    # 9. Margens
    df["Margem Bruta"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] != 0,
        df["Resultado Bruto"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )
    df["Margem Operacional"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] != 0,
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )
    df["Margem Líquida"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] != 0,
        df["Lucro/Prejuízo Consolidado do Período"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )
    
    # 10. EBITDA e ROI EBITDA
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
    
    df["Lucro Econômico EBITDA"] = np.where(
        (df["ROI EBITDA"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()),
        (df["ROI EBITDA"] - df["wacc"]) * df["Investimento Médio"],
        np.nan
    )
    
    return df

df = load_data()
