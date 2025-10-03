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
    
    # CALCULAR INDICADORES CONFORME ABA "INDICADORES" DO EXCEL
    
    # 1. ROA (Return on Assets)
    df["Ativo Médio"] = (df["Ativo Total"] + df.groupby("Ticker")["Ativo Total"].shift(1)) / 2
    df["ROA"] = df["Lucro/Prejuízo Consolidado do Período"] / df["Ativo Médio"]
    
    # 2. ROI (Return on Investment)
    df["Investimento Médio"] = (
        df["Empréstimos e Financiamentos - Circulante"].fillna(0) + 
        df["Empréstimos e Financiamentos - Não Circulante"].fillna(0) + 
        df["Patrimônio Líquido Consolidado"]
    )
    df["ROI"] = np.where(
        df["Investimento Médio"] != 0,
        df["Lucro/Prejuízo Consolidado do Período"] / df["Investimento Médio"],
        np.nan
    )
    
    # 3. ROE (Return on Equity)
    df["PL Médio"] = (df["Patrimônio Líquido Consolidado"] + df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1)) / 2
    df["ROE"] = df["Lucro/Prejuízo Consolidado do Período"] / df["PL Médio"]
    
    # 4. Estrutura de Capital
    df["Percentual Capital Terceiros"] = (
        (df["Passivo Circulante"].fillna(0) + df["Passivo Não Circulante"].fillna(0)) / 
        df["Passivo Total"]
    )
    df["Percentual Capital Próprio"] = df["Patrimônio Líquido Consolidado"] / df["Passivo Total"]
    
    # 5. Custo da Dívida (ki)
    df["Passivo Oneroso Médio"] = (
        df["Empréstimos e Financiamentos - Circulante"].fillna(0) + 
        df["Empréstimos e Financiamentos - Não Circulante"].fillna(0)
    )
    df["ki"] = np.where(
        (df["Passivo Oneroso Médio"] != 0) & (df["Despesas Financeiras"].notna()),
        df["Despesas Financeiras"].abs() / df["Passivo Oneroso Médio"],
        np.nan
    )
    
    # 6. Custo do Capital Próprio (ke)
    df["ke"] = np.where(
        (df["PL Médio"] != 0) & (df["Pagamento de Dividendos"].notna()),
        df["Pagamento de Dividendos"].abs() / df["PL Médio"],
        np.nan
    )
    
    # 7. WACC (Weighted Average Cost of Capital)
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
    
    # 8. Lucro Econômico
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
    
    # 9. EBITDA e ROI EBITDA
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

# ==============================
# SIDEBAR - FILTROS PRINCIPAIS
# ==============================
st.sidebar.header("🔧 Filtros Principais")

# Seleção de modo de análise
modo_analise = st.sidebar.radio(
    "Modo de Análise:",
    ["📈 Visão por Empresa", "🏭 Análise Setorial", "🏆 Ranking Comparativo"]
)

# Filtro de ano
anos_disponiveis = sorted(df["Ano"].unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Selecione o Ano:", anos_disponiveis)

# Filtro baseado no modo de análise
if modo_analise == "📈 Visão por Empresa":
    ticker_selecionado = st.sidebar.selectbox(
        "Selecione a Empresa:",
        sorted(df["Ticker"].dropna().unique())
    )
    df_filtrado = df[(df["Ticker"] == ticker_selecionado) & (df["Ano"] == ano_selecionado)]
    
elif modo_analise == "🏭 Análise Setorial":
    setor_selecionado = st.sidebar.selectbox(
        "Selecione o Setor:",
        sorted(df["SETOR_ATIV"].dropna().unique())
    )
    df_filtrado = df[(df["SETOR_ATIV"] == setor_selecionado) & (df["Ano"] == ano_selecionado)]
    
else:  # Ranking Comparativo
    df_filtrado = df[df["Ano"] == ano_selecionado]

# ==============================
# TELA PRINCIPAL - INDICADORES
# ==============================

if modo_analise == "📈 Visão por Empresa":
    st.header(f"📊 Análise Detalhada - {ticker_selecionado} ({ano_selecionado})")
    
    # KPIs Principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if not df_filtrado.empty and pd.notna(df_filtrado["ROE"].iloc[0]):
            st.metric("ROE", f"{df_filtrado['ROE'].iloc[0]:.2%}")
        else:
            st.metric("ROE", "N/A")
    
    with col2:
        if not df_filtrado.empty and pd.notna(df_filtrado["ROA"].iloc[0]):
            st.metric("ROA", f"{df_filtrado['ROA'].iloc[0]:.2%}")
        else:
            st.metric("ROA", "N/A")
    
    with col3:
        if not df_filtrado.empty and pd.notna(df_filtrado["ROI"].iloc[0]):
            st.metric("ROI", f"{df_filtrado['ROI'].iloc[0]:.2%}")
        else:
            st.metric("ROI", "N/A")
    
    with col4:
        if not df_filtrado.empty and pd.notna(df_filtrado["wacc"].iloc[0]):
            st.metric("WACC", f"{df_filtrado['wacc'].iloc[0]:.2%}")
        else:
            st.metric("WACC", "N/A")
    
    st.divider()
    
    # Abas para diferentes categorias de indicadores
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Rentabilidade", "🏛️ Estrutura Capital", "💰 Custo Capital", "📊 Lucro Econômico"])
    
    with tab1:
        st.subheader("Indicadores de Rentabilidade")
        rentabilidade_cols = ["ROE", "ROA", "ROI", "ROI EBITDA", "Margem Líquida"]
        rentabilidade_data = {}
        
        for col in rentabilidade_cols:
            if col in df_filtrado.columns and not df_filtrado.empty and pd.notna(df_filtrado[col].iloc[0]):
                rentabilidade_data[col] = df_filtrado[col].iloc[0]
        
        if rentabilidade_data:
            rentabilidade_df = pd.DataFrame(list(rentabilidade_data.items()), columns=["Indicador", "Valor"])
            rentabilidade_df["Valor"] = rentabilidade_df["Valor"].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
            st.dataframe(rentabilidade_df, use_container_width=True, hide_index=True)
        else:
            st.warning("Não há dados de rentabilidade disponíveis")
    
    with tab2:
        st.subheader("Estrutura de Capital")
        estrutura_cols = ["Percentual Capital Terceiros", "Percentual Capital Próprio", "Endividamento"]
        estrutura_data = {}
        
        for col in estrutura_cols:
            if col in df_filtrado.columns and not df_filtrado.empty and pd.notna(df_filtrado[col].iloc[0]):
                estrutura_data[col] = df_filtrado[col].iloc[0]
        
        if estrutura_data:
            estrutura_df = pd.DataFrame(list(estrutura_data.items()), columns=["Indicador", "Valor"])
            estrutura_df["Valor"] = estrutura_df["Valor"].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
            st.dataframe(estrutura_df, use_container_width=True, hide_index=True)
            
            # Gráfico de pizza da estrutura de capital
            if all(col in estrutura_data for col in ["Percentual Capital Terceiros", "Percentual Capital Próprio"]):
                fig_pizza = px.pie(
                    values=[estrutura_data["Percentual Capital Terceiros"], estrutura_data["Percentual Capital Próprio"]],
                    names=["Capital Terceiros", "Capital Próprio"],
                    title="Composição do Capital"
                )
                st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.warning("Não há dados de estrutura de capital disponíveis")
    
    with tab3:
        st.subheader("Custo de Capital")
        custo_cols = ["ki", "ke", "wacc"]
        custo_data = {}
        
        for col in custo_cols:
            if col in df_filtrado.columns and not df_filtrado.empty and pd.notna(df_filtrado[col].iloc[0]):
                custo_data[col] = df_filtrado[col].iloc[0]
        
        if custo_data:
            custo_df = pd.DataFrame(list(custo_data.items()), columns=["Indicador", "Valor"])
            custo_df["Valor"] = custo_df["Valor"].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
            st.dataframe(custo_df, use_container_width=True, hide_index=True)
        else:
            st.warning("Não há dados de custo de capital disponíveis")
    
    with tab4:
        st.subheader("Lucro Econômico")
        lucro_cols = ["Lucro Econômico 1", "Lucro Econômico 2", "Lucro Econômico EBITDA"]
        lucro_data = {}
        
        for col in lucro_cols:
            if col in df_filtrado.columns and not df_filtrado.empty and pd.notna(df_filtrado[col].iloc[0]):
                # Converter para milhões e arredondar
                lucro_data[col] = df_filtrado[col].iloc[0] / 1000
        
        if lucro_data:
            lucro_df = pd.DataFrame(list(lucro_data.items()), columns=["Indicador", "Valor (R$ Mil)"])
            lucro_df["Valor (R$ Mil)"] = lucro_df["Valor (R$ Mil)"].apply(lambda x: f"R$ {x:,.0f}" if pd.notna(x) else "N/A")
            st.dataframe(lucro_df, use_container_width=True, hide_index=True)
        else:
            st.warning("Não há dados de lucro econômico disponíveis")

elif modo_analise == "🏭 Análise Setorial":
    st.header(f"🏭 Análise Setorial - {setor_selecionado} ({ano_selecionado})")
    
    if not df_filtrado.empty:
        # Top empresas do setor por ROE
        st.subheader("Top 10 Empresas do Setor por ROE")
        top_roe_setor = df_filtrado[df_filtrado["ROE"].notna()].nlargest(10, "ROE")[["Ticker", "ROE"]]
        
        if not top_roe_setor.empty:
            fig_roe = px.bar(top_roe_setor, x="Ticker", y="ROE", 
                           title="ROE por Empresa no Setor")
            st.plotly_chart(fig_roe, use_container_width=True)
        else:
            st.warning("Não há dados de ROE disponíveis para este setor")
        
        # Comparativo de estrutura de capital no setor
        st.subheader("Estrutura de Capital no Setor")
        estrutura_setor = df_filtrado[df_filtrado["Percentual Capital Próprio"].notna()].nlargest(15, "Patrimônio Líquido Consolidado")
        
        if not estrutura_setor.empty:
            fig_estrutura = px.bar(estrutura_setor, 
                                 x="Ticker", 
                                 y=["Percentual Capital Terceiros", "Percentual Capital Próprio"],
                                 title="Estrutura de Capital das Principais Empresas do Setor",
                                 barmode='stack')
            st.plotly_chart(fig_estrutura, use_container_width=True)
        else:
            st.warning("Não há dados de estrutura de capital disponíveis para este setor")

else:  # Ranking Comparativo
    st.header(f"🏆 Ranking Comparativo ({ano_selecionado})")
    
    # Abas para diferentes rankings
    rank_tab1, rank_tab2, rank_tab3 = st.tabs(["📈 Rentabilidade", "🏛️ Solidez", "💰 Eficiência"])
    
    with rank_tab1:
        st.subheader("Top 15 Empresas por ROE")
        roe_ranking = df_filtrado[df_filtrado["ROE"].notna()].nlargest(15, "ROE")[["Ticker", "SETOR_ATIV", "ROE"]]
        
        if not roe_ranking.empty:
            fig_roe_rank = px.bar(roe_ranking, x="Ticker", y="ROE", color="SETOR_ATIV",
                                title="Ranking de ROE")
            st.plotly_chart(fig_roe_rank, use_container_width=True)
            st.dataframe(roe_ranking.style.format({"ROE": "{:.2%}"}), use_container_width=True)
        else:
            st.warning("Não há dados de ROE disponíveis para ranking")
    
    with rank_tab2:
        st.subheader("Top 15 Empresas por Patrimônio Líquido")
        pl_ranking = df_filtrado.nlargest(15, "Patrimônio Líquido Consolidado")[["Ticker", "SETOR_ATIV", "Patrimônio Líquido Consolidado"]]
        
        if not pl_ranking.empty:
            # Converter para bilhões
            pl_ranking["PL (R$ Bi)"] = pl_ranking["Patrimônio Líquido Consolidado"] / 1e9
            fig_pl_rank = px.bar(pl_ranking, x="Ticker", y="PL (R$ Bi)", color="SETOR_ATIV",
                               title="Ranking de Patrimônio Líquido")
            st.plotly_chart(fig_pl_rank, use_container_width=True)
            st.dataframe(pl_ranking[["Ticker", "SETOR_ATIV", "PL (R$ Bi)"]].style.format({"PL (R$ Bi)": "R$ {:.2f}"}), 
                        use_container_width=True)
        else:
            st.warning("Não há dados de patrimônio líquido disponíveis para ranking")
    
    with rank_tab3:
        st.subheader("Top 15 Empresas por ROI")
        roi_ranking = df_filtrado[df_filtrado["ROI"].notna()].nlargest(15, "ROI")[["Ticker", "SETOR_ATIV", "ROI"]]
        
        if not roi_ranking.empty:
            fig_roi_rank = px.bar(roi_ranking, x="Ticker", y="ROI", color="SETOR_ATIV",
                                title="Ranking de ROI")
            st.plotly_chart(fig_roi_rank, use_container_width=True)
            st.dataframe(roi_ranking.style.format({"ROI": "{:.2%}"}), use_container_width=True)
        else:
            st.warning("Não há dados de ROI disponíveis para ranking")

# ==============================
# INFORMAÇÕES GERAIS
# ==============================
st.sidebar.divider()
st.sidebar.header("ℹ️ Informações")
st.sidebar.info(
    "Este dashboard apresenta os principais indicadores financeiros "
    "calculados conforme metodologia da aba 'Indicadores' do Excel original. "
    "Os dados são provenientes das demonstrações financeiras consolidadas."
)

# Rodapé
st.divider()
st.caption(f"📊 Dashboard CVM - Indicadores Financeiros | Dados atualizados para {ano_selecionado} | Total de empresas na base: {df['Ticker'].nunique()}")
