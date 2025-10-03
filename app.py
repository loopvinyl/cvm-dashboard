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
    
    # 1. ROA (Return on Assets) - APENAS PARA LUCRO POSITIVO E ATIVO MÉDIO POSITIVO
    df["Ativo Médio"] = (df["Ativo Total"] + df.groupby("Ticker")["Ativo Total"].shift(1)) / 2
    df["ROA"] = np.where(
        (df["Ativo Médio"] > 0) & (df["Lucro/Prejuízo Consolidado do Período"] > 0),
        df["Lucro/Prejuízo Consolidado do Período"] / df["Ativo Médio"],
        np.nan
    )
    
    # 2. ROI (Return on Investment) - APENAS PARA LUCRO POSITIVO E INVESTIMENTO POSITIVO
    df["Investimento Médio"] = (
        df["Empréstimos e Financiamentos - Circulante"].fillna(0) + 
        df["Empréstimos e Financiamentos - Não Circulante"].fillna(0) + 
        df["Patrimônio Líquido Consolidado"]
    )
    df["ROI"] = np.where(
        (df["Investimento Médio"] > 0) & (df["Lucro/Prejuízo Consolidado do Período"] > 0),
        df["Lucro/Prejuízo Consolidado do Período"] / df["Investimento Médio"],
        np.nan
    )
    
    # 3. ROE (Return on Equity) - APENAS PARA LUCRO POSITIVO E PL MÉDIO POSITIVO
    df["PL Médio"] = (df["Patrimônio Líquido Consolidado"] + df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1)) / 2
    df["ROE"] = np.where(
        (df["PL Médio"] > 0) & (df["Lucro/Prejuízo Consolidado do Período"] > 0),
        df["Lucro/Prejuízo Consolidado do Período"] / df["PL Médio"],
        np.nan
    )
    
    # 4. Estrutura de Capital
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
    
    # 5. Margens
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
    
    # 6. Custo da Dívida (ki)
    df["Passivo Oneroso Médio"] = (
        df["Empréstimos e Financiamentos - Circulante"].fillna(0) + 
        df["Empréstimos e Financiamentos - Não Circulante"].fillna(0)
    )
    df["ki"] = np.where(
        (df["Passivo Oneroso Médio"] != 0) & (df["Despesas Financeiras"].notna()),
        df["Despesas Financeiras"].abs() / df["Passivo Oneroso Médio"],
        np.nan
    )
    
    # 7. Custo do Capital Próprio (ke)
    df["ke"] = np.where(
        (df["PL Médio"] != 0) & (df["Pagamento de Dividendos"].notna()),
        df["Pagamento de Dividendos"].abs() / df["PL Médio"],
        np.nan
    )
    
    # 8. WACC (Weighted Average Cost of Capital)
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
    
    # 9. Lucro Econômico
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

# ==============================
# SIDEBAR - FILTROS PRINCIPAIS
# ==============================
st.sidebar.header("🔧 Filtros Principais")

# Seleção de modo de análise - RANKING COMO PRIMEIRA OPÇÃO
modo_analise = st.sidebar.radio(
    "Modo de Análise:",
    ["🏆 Ranking Comparativo", "📈 Visão por Empresa", "🏭 Análise Setorial"]
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
    
else:  # Ranking Comparativo (PRINCIPAL)
    df_filtrado = df[df["Ano"] == ano_selecionado]

# ==============================
# TELA PRINCIPAL - RANKING COMPARATIVO
# ==============================
if modo_analise == "🏆 Ranking Comparativo":
    st.header(f"🏆 Ranking Comparativo ({ano_selecionado})")
    
    # KPIs Gerais no Topo
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        empresas_ativas = df_filtrado["Ticker"].nunique()
        st.metric("Empresas Analisadas", empresas_ativas)
    
    with col2:
        setores_ativos = df_filtrado["SETOR_ATIV"].nunique()
        st.metric("Setores Representados", setores_ativos)
    
    with col3:
        receita_total = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum() / 1e9
        st.metric("Receita Total (R$ Bi)", f"R$ {receita_total:.2f}")
    
    with col4:
        lucro_total = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum() / 1e9
        st.metric("Lucro Total (R$ Bi)", f"R$ {lucro_total:.2f}")
    
    st.divider()
    
    # Abas para diferentes rankings
    rank_tab1, rank_tab2, rank_tab3, rank_tab4 = st.tabs(["📈 Rentabilidade", "💰 Valor de Mercado", "🏛️ Solidez", "📊 Eficiência"])
    
    with rank_tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 15 Empresas por ROE")
            roe_ranking = df_filtrado[df_filtrado["ROE"].notna()].nlargest(15, "ROE")[["Ticker", "SETOR_ATIV", "ROE"]]
            
            if not roe_ranking.empty:
                fig_roe_rank = px.bar(roe_ranking, x="Ticker", y="ROE", color="SETOR_ATIV",
                                    title="Ranking de ROE (Return on Equity)")
                st.plotly_chart(fig_roe_rank, use_container_width=True)
            else:
                st.warning("Não há dados de ROE disponíveis para ranking")
        
        with col2:
            st.subheader("Top 15 Empresas por ROA")
            roa_ranking = df_filtrado[df_filtrado["ROA"].notna()].nlargest(15, "ROA")[["Ticker", "SETOR_ATIV", "ROA"]]
            
            if not roa_ranking.empty:
                fig_roa_rank = px.bar(roa_ranking, x="Ticker", y="ROA", color="SETOR_ATIV",
                                    title="Ranking de ROA (Return on Assets)")
                st.plotly_chart(fig_roa_rank, use_container_width=True)
            else:
                st.warning("Não há dados de ROA disponíveis para ranking")
        
        # Tabela consolidada de rentabilidade
        st.subheader("📋 Tabela de Rentabilidade - Top 20")
        rentabilidade_consolidado = df_filtrado[
            df_filtrado["ROE"].notna() & 
            df_filtrado["ROA"].notna() & 
            df_filtrado["ROI"].notna()
        ].nlargest(20, "ROE")[["Ticker", "SETOR_ATIV", "ROE", "ROA", "ROI", "Margem Líquida"]]
        
        if not rentabilidade_consolidado.empty:
            # Formatar para porcentagem
            format_dict = {
                'ROE': '{:.2%}',
                'ROA': '{:.2%}', 
                'ROI': '{:.2%}',
                'Margem Líquida': '{:.2%}'
            }
            st.dataframe(
                rentabilidade_consolidado.style.format(format_dict),
                use_container_width=True
            )
        else:
            st.warning("Não há dados suficientes para exibir a tabela consolidada")
    
    with rank_tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 15 Empresas por Lucro Líquido")
            lucro_ranking = df_filtrado.nlargest(15, "Lucro/Prejuízo Consolidado do Período")[["Ticker", "SETOR_ATIV", "Lucro/Prejuízo Consolidado do Período"]]
            
            if not lucro_ranking.empty:
                # Converter para milhões
                lucro_ranking["Lucro (R$ Mi)"] = lucro_ranking["Lucro/Prejuízo Consolidado do Período"] / 1e6
                fig_lucro_rank = px.bar(lucro_ranking, x="Ticker", y="Lucro (R$ Mi)", color="SETOR_ATIV",
                                      title="Ranking por Lucro Líquido")
                st.plotly_chart(fig_lucro_rank, use_container_width=True)
            else:
                st.warning("Não há dados de lucro disponíveis para ranking")
        
        with col2:
            st.subheader("Top 15 Empresas por Receita")
            receita_ranking = df_filtrado.nlargest(15, "Receita de Venda de Bens e/ou Serviços")[["Ticker", "SETOR_ATIV", "Receita de Venda de Bens e/ou Serviços"]]
            
            if not receita_ranking.empty:
                # Converter para bilhões
                receita_ranking["Receita (R$ Bi)"] = receita_ranking["Receita de Venda de Bens e/ou Serviços"] / 1e9
                fig_receita_rank = px.bar(receita_ranking, x="Ticker", y="Receita (R$ Bi)", color="SETOR_ATIV",
                                        title="Ranking por Receita")
                st.plotly_chart(fig_receita_rank, use_container_width=True)
            else:
                st.warning("Não há dados de receita disponíveis para ranking")
    
    with rank_tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 15 Empresas por Patrimônio Líquido")
            pl_ranking = df_filtrado.nlargest(15, "Patrimônio Líquido Consolidado")[["Ticker", "SETOR_ATIV", "Patrimônio Líquido Consolidado"]]
            
            if not pl_ranking.empty:
                # Converter para bilhões
                pl_ranking["PL (R$ Bi)"] = pl_ranking["Patrimônio Líquido Consolidado"] / 1e9
                fig_pl_rank = px.bar(pl_ranking, x="Ticker", y="PL (R$ Bi)", color="SETOR_ATIV",
                                   title="Ranking de Patrimônio Líquido")
                st.plotly_chart(fig_pl_rank, use_container_width=True)
            else:
                st.warning("Não há dados de patrimônio líquido disponíveis para ranking")
        
        with col2:
            st.subheader("Top 15 Empresas por ROI")
            roi_ranking = df_filtrado[df_filtrado["ROI"].notna()].nlargest(15, "ROI")[["Ticker", "SETOR_ATIV", "ROI"]]
            
            if not roi_ranking.empty:
                fig_roi_rank = px.bar(roi_ranking, x="Ticker", y="ROI", color="SETOR_ATIV",
                                    title="Ranking de ROI (Return on Investment)")
                st.plotly_chart(fig_roi_rank, use_container_width=True)
            else:
                st.warning("Não há dados de ROI disponíveis para ranking")
    
    with rank_tab4:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 15 Empresas por Margem Líquida")
            margem_ranking = df_filtrado[df_filtrado["Margem Líquida"].notna()].nlargest(15, "Margem Líquida")[["Ticker", "SETOR_ATIV", "Margem Líquida"]]
            
            if not margem_ranking.empty:
                fig_margem_rank = px.bar(margem_ranking, x="Ticker", y="Margem Líquida", color="SETOR_ATIV",
                                       title="Ranking por Margem Líquida")
                st.plotly_chart(fig_margem_rank, use_container_width=True)
            else:
                st.warning("Não há dados de margem líquida disponíveis para ranking")
        
        with col2:
            st.subheader("Empresas com Melhor WACC")
            wacc_ranking = df_filtrado[df_filtrado["wacc"].notna()].nsmallest(15, "wacc")[["Ticker", "SETOR_ATIV", "wacc"]]
            
            if not wacc_ranking.empty:
                fig_wacc_rank = px.bar(wacc_ranking, x="Ticker", y="wacc", color="SETOR_ATIV",
                                     title="Ranking por WACC (menor é melhor)")
                st.plotly_chart(fig_wacc_rank, use_container_width=True)
            else:
                st.warning("Não há dados de WACC disponíveis para ranking")

# ==============================
# TELA - VISÃO POR EMPRESA
# ==============================
elif modo_analise == "📈 Visão por Empresa":
    st.header(f"📊 Análise Detalhada - {ticker_selecionado} ({ano_selecionado})")
    
    if not df_filtrado.empty:
        # KPIs Principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            valor_roe = df_filtrado["ROE"].iloc[0]
            if pd.notna(valor_roe):
                st.metric("ROE", f"{valor_roe:.2%}")
            else:
                st.metric("ROE*", "-", 
                         help="ROE calculado apenas para empresas com lucro líquido positivo e patrimônio líquido médio positivo")
        
        with col2:
            valor_roa = df_filtrado["ROA"].iloc[0]
            if pd.notna(valor_roa):
                st.metric("ROA", f"{valor_roa:.2%}")
            else:
                st.metric("ROA*", "-", 
                         help="ROA calculado apenas para empresas com lucro líquido positivo e ativo médio positivo")
        
        with col3:
            valor_roi = df_filtrado["ROI"].iloc[0]
            if pd.notna(valor_roi):
                st.metric("ROI", f"{valor_roi:.2%}")
            else:
                st.metric("ROI*", "-", 
                         help="ROI calculado apenas para empresas com lucro líquido positivo e investimento médio positivo")
        
        with col4:
            valor_wacc = df_filtrado["wacc"].iloc[0]
            if pd.notna(valor_wacc):
                st.metric("WACC", f"{valor_wacc:.2%}")
            else:
                st.metric("WACC*", "-", 
                         help="WACC não pôde ser calculado devido a dados insuficientes")
        
        # Legenda explicativa para os asteriscos
        st.caption("* Indicadores marcados com asterisco não puderam ser calculados devido a condições específicas (ver tooltips)")
        
        st.divider()
        
        # Abas para diferentes categorias de indicadores
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Rentabilidade", "🏛️ Estrutura Capital", "💰 Custo Capital", "📊 Lucro Econômico"])
        
        with tab1:
            st.subheader("Indicadores de Rentabilidade")
            rentabilidade_cols = ["ROE", "ROA", "ROI", "ROI EBITDA", "Margem Bruta", "Margem Operacional", "Margem Líquida"]
            rentabilidade_data = []
            
            for col in rentabilidade_cols:
                if col in df_filtrado.columns:
                    valor = df_filtrado[col].iloc[0]
                    if pd.notna(valor):
                        rentabilidade_data.append({
                            "Indicador": col,
                            "Valor": f"{valor:.2%}",
                            "Status": "✓"
                        })
                    else:
                        rentabilidade_data.append({
                            "Indicador": f"{col}*",
                            "Valor": "Não calculado",
                            "Status": "✗"
                        })
            
            if rentabilidade_data:
                rentabilidade_df = pd.DataFrame(rentabilidade_data)
                st.dataframe(rentabilidade_df[["Indicador", "Valor"]], use_container_width=True, hide_index=True)
            else:
                st.warning("Não há dados de rentabilidade disponíveis")
        
        with tab2:
            st.subheader("Estrutura de Capital")
            estrutura_cols = ["Percentual Capital Terceiros", "Percentual Capital Próprio"]
            estrutura_data = []
            
            for col in estrutura_cols:
                if col in df_filtrado.columns:
                    valor = df_filtrado[col].iloc[0]
                    if pd.notna(valor):
                        estrutura_data.append({
                            "Indicador": col,
                            "Valor": f"{valor:.2%}",
                            "Status": "✓"
                        })
                    else:
                        estrutura_data.append({
                            "Indicador": f"{col}*",
                            "Valor": "Não calculado",
                            "Status": "✗"
                        })
            
            if estrutura_data:
                estrutura_df = pd.DataFrame(estrutura_data)
                st.dataframe(estrutura_df[["Indicador", "Valor"]], use_container_width=True, hide_index=True)
                
                # Gráfico de pizza da estrutura de capital (apenas se ambos os valores estiverem disponíveis)
                valores_validos = [d for d in estrutura_data if d["Status"] == "✓"]
                if len(valores_validos) >= 2:
                    nomes = ["Capital Terceiros", "Capital Próprio"]
                    valores = [df_filtrado["Percentual Capital Terceiros"].iloc[0], 
                              df_filtrado["Percentual Capital Próprio"].iloc[0]]
                    
                    fig_pizza = px.pie(
                        values=valores,
                        names=nomes,
                        title="Composição do Capital"
                    )
                    st.plotly_chart(fig_pizza, use_container_width=True)
            else:
                st.warning("Não há dados de estrutura de capital disponíveis")
        
        with tab3:
            st.subheader("Custo de Capital")
            custo_cols = ["ki", "ke", "wacc"]
            custo_data = []
            
            for col in custo_cols:
                if col in df_filtrado.columns:
                    valor = df_filtrado[col].iloc[0]
                    if pd.notna(valor):
                        custo_data.append({
                            "Indicador": col,
                            "Valor": f"{valor:.2%}",
                            "Status": "✓"
                        })
                    else:
                        custo_data.append({
                            "Indicador": f"{col}*",
                            "Valor": "Não calculado",
                            "Status": "✗"
                        })
            
            if custo_data:
                custo_df = pd.DataFrame(custo_data)
                st.dataframe(custo_df[["Indicador", "Valor"]], use_container_width=True, hide_index=True)
            else:
                st.warning("Não há dados de custo de capital disponíveis")
        
        with tab4:
            st.subheader("Lucro Econômico")
            lucro_cols = ["Lucro Econômico 1", "Lucro Econômico 2", "Lucro Econômico EBITDA"]
            lucro_data = []
            
            for col in lucro_cols:
                if col in df_filtrado.columns:
                    valor = df_filtrado[col].iloc[0]
                    if pd.notna(valor):
                        # Converter para milhões
                        valor_mil = valor / 1000
                        lucro_data.append({
                            "Indicador": col,
                            "Valor (R$ Mil)": f"R$ {valor_mil:,.0f}",
                            "Status": "✓"
                        })
                    else:
                        lucro_data.append({
                            "Indicador": f"{col}*",
                            "Valor (R$ Mil)": "Não calculado",
                            "Status": "✗"
                        })
            
            if lucro_data:
                lucro_df = pd.DataFrame(lucro_data)
                st.dataframe(lucro_df[["Indicador", "Valor (R$ Mil)"]], use_container_width=True, hide_index=True)
            else:
                st.warning("Não há dados de lucro econômico disponíveis")
    
    else:
        st.warning(f"Não há dados disponíveis para {ticker_selecionado} no ano {ano_selecionado}")

# ==============================
# TELA - ANÁLISE SETORIAL
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    st.header(f"🏭 Análise Setorial - {setor_selecionado} ({ano_selecionado})")
    
    if not df_filtrado.empty:
        # KPIs do Setor
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            empresas_setor = df_filtrado["Ticker"].nunique()
            st.metric("Empresas no Setor", empresas_setor)
        
        with col2:
            receita_setor = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum() / 1e9
            st.metric("Receita Total (R$ Bi)", f"R$ {receita_setor:.2f}")
        
        with col3:
            lucro_setor = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum() / 1e9
            st.metric("Lucro Total (R$ Bi)", f"R$ {lucro_setor:.2f}")
        
        with col4:
            pl_setor = df_filtrado["Patrimônio Líquido Consolidado"].sum() / 1e9
            st.metric("Patrimônio Líquido (R$ Bi)", f"R$ {pl_setor:.2f}")
        
        st.divider()
        
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
        
        # Ranking de rentabilidade no setor
        st.subheader("Ranking de Rentabilidade no Setor")
        rentabilidade_setor = df_filtrado[
            df_filtrado["ROE"].notna() & 
            df_filtrado["ROA"].notna() & 
            df_filtrado["ROI"].notna()
        ].nlargest(15, "ROE")[["Ticker", "ROE", "ROA", "ROI", "Margem Líquida"]]
        
        if not rentabilidade_setor.empty:
            format_dict = {
                'ROE': '{:.2%}',
                'ROA': '{:.2%}', 
                'ROI': '{:.2%}',
                'Margem Líquida': '{:.2%}'
            }
            st.dataframe(
                rentabilidade_setor.style.format(format_dict),
                use_container_width=True
            )
        else:
            st.warning("Não há dados de rentabilidade suficientes para exibir o ranking")
    
    else:
        st.warning(f"Não há dados disponíveis para o setor {setor_selecionado} no ano {ano_selecionado}")

# ==============================
# SEÇÃO DE FÓRMULAS DOS INDICADORES
# ==============================
st.divider()
st.header("📚 Fórmulas dos Indicadores")

formulas = {
    "ROE (Return on Equity)": "Lucro Líquido ÷ Patrimônio Líquido Médio",
    "ROA (Return on Assets)": "Lucro Líquido ÷ Ativo Total Médio", 
    "ROI (Return on Investment)": "Lucro Líquido ÷ Investimento Médio",
    "Investimento Médio": "Empréstimos (Circulante + Não Circulante) + Patrimônio Líquido",
    "Margem Bruta": "Resultado Bruto ÷ Receita de Vendas",
    "Margem Operacional": "Resultado Antes do Resultado Financeiro e Tributos ÷ Receita de Vendas",
    "Margem Líquida": "Lucro Líquido ÷ Receita de Vendas",
    "ki (Custo da Dívida)": "Despesas Financeiras ÷ Passivo Oneroso Médio",
    "ke (Custo do Capital Próprio)": "Dividendos Pagos ÷ Patrimônio Líquido Médio",
    "WACC": "(ki × % Capital Terceiros) + (ke × % Capital Próprio)",
    "Lucro Econômico 1": "(ROI - WACC) × Investimento Médio",
    "Lucro Econômico 2": "Lucro Líquido - Despesas Financeiras - Dividendos",
    "EBITDA": "Resultado Antes do Resultado Financeiro e Tributos + Despesas Financeiras",
    "ROI EBITDA": "EBITDA ÷ Investimento Médio",
    "Percentual Capital Terceiros": "(Passivo Circulante + Não Circulante) ÷ Passivo Total",
    "Percentual Capital Próprio": "Patrimônio Líquido ÷ Passivo Total"
}

# Exibir fórmulas em colunas
col1, col2 = st.columns(2)

with col1:
    for i, (indicador, formula) in enumerate(formulas.items()):
        if i < len(formulas) // 2:
            with st.expander(f"**{indicador}**"):
                st.write(f"`{formula}`")

with col2:
    for i, (indicador, formula) in enumerate(formulas.items()):
        if i >= len(formulas) // 2:
            with st.expander(f"**{indicador}**"):
                st.write(f"`{formula}`")

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

# Adicionar informações sobre os cálculos
with st.sidebar.expander("💡 Sobre os Cálculos"):
    st.write("""
    **Metodologia:**
    - Todos os indicadores seguem as fórmulas da aba 'Indicadores' do Excel
    - Valores médios calculados entre período atual e anterior
    - Dados em R$ mil, conforme padrão CVM
    - Tratamento de valores missing e divisão por zero
    
    **Condições para cálculo:**
    - ROE: Apenas quando Lucro Líquido > 0 e PL Médio > 0
    - ROA: Apenas quando Lucro Líquido > 0 e Ativo Médio > 0  
    - ROI: Apenas quando Lucro Líquido > 0 e Investimento Médio > 0
    """)
