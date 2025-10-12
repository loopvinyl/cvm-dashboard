# ==============================================================
# 📊 DASHBOARD CVM - Indicadores Financeiros (VERSÃO CORRIGIDA - VALORES EM R$ MIL)
# ==============================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os

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
    # Procurar automaticamente o arquivo em locais possíveis
    possible_paths = [
        "/content/dff_2010_2024.xlsx",   # Google Colab
        "dff_2010_2024.xlsx",            # mesma pasta do app
        "./data/dff_2010_2024.xlsx"      # subpasta data/
    ]
    data_path = None
    for path in possible_paths:
        if os.path.exists(path):
            data_path = path
            break

    if data_path is None:
        st.error(
            "❌ Arquivo 'dff_2010_2024.xlsx' não encontrado.\n\n"
            "Coloque o arquivo na mesma pasta do app ou em /content/ (se estiver no Colab),\n"
            "ou salve em ./data/dff_2010_2024.xlsx.\n\n"
            "Caminhos verificados:\n- " + "\n- ".join(possible_paths)
        )
        st.stop()

    # Ler o Excel
    df = pd.read_excel(data_path)
    df.columns = [c.strip() for c in df.columns]

    # =============================================================
    # AVISO SOBRE ESCALA DOS VALORES
    # =============================================================
    st.sidebar.info("💡 **Nota:** Todos os valores financeiros estão em **R$ mil**")

    # =============================================================
    # MAPEAMENTO EXATO DAS CONTAS (compatível com dff_2010_2024)
    # =============================================================
    # Ordenar por Ticker e Ano para garantir que shift() funcione corretamente
    df = df.sort_values(['Ticker', 'Ano']).reset_index(drop=True)

    # =============================================================
    # CÁLCULOS DE MÉDIAS - CORRIGIDOS (VALORES JÁ ESTÃO EM R$ MIL)
    # =============================================================
    
    # 1. Ativo Médio ✅ CORRETO
    df["Ativo Médio"] = (df["Ativo Total"] + df.groupby("Ticker")["Ativo Total"].shift(1)) / 2

    # 2. PL Médio ✅ CORRETO
    df["PL Médio"] = (df["Patrimônio Líquido Consolidado"] + df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1)) / 2

    # 3. Passivo Oneroso Médio ✅ CORRIGIDO
    df["Passivo Oneroso Atual"] = (
        df["Empréstimos e Financiamentos - Circulante"].fillna(0) + 
        df["Empréstimos e Financiamentos - Não Circulante"].fillna(0)
    )
    df["Passivo Oneroso Anterior"] = (
        df.groupby("Ticker")["Empréstimos e Financiamentos - Circulante"].shift(1).fillna(0) +
        df.groupby("Ticker")["Empréstimos e Financiamentos - Não Circulante"].shift(1).fillna(0)
    )
    df["Passivo Oneroso Médio"] = (df["Passivo Oneroso Atual"] + df["Passivo Oneroso Anterior"]) / 2

    # 4. Investimento Médio ✅ CORRIGIDO
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
    # INDICADORES DE RENTABILIDADE - CORRIGIDOS
    # =============================================================
    
    # ROA = Resultado Antes do Resultado Financeiro e dos Tributos / Ativo Médio
    df["ROA"] = np.where(
        df["Ativo Médio"] > 0,
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Ativo Médio"],
        np.nan
    )

    # ROI = Resultado Antes do Resultado Financeiro e dos Tributos / Investimento Médio
    df["ROI"] = np.where(
        df["Investimento Médio"] > 0,
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Investimento Médio"],
        np.nan
    )

    # ROE = Lucro Líquido / PL Médio
    df["ROE"] = np.where(
        df["PL Médio"] > 0,
        df["Lucro/Prejuízo Consolidado do Período"] / df["PL Médio"],
        np.nan
    )

    # =============================================================
    # MARGENS - ✅ TODOS CORRETOS
    # =============================================================
    
    # Margem Bruta = Resultado Bruto / Receita
    df["Margem Bruta"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] > 0,
        df["Resultado Bruto"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )

    # Margem Operacional = Resultado Operacional / Receita
    df["Margem Operacional"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] > 0,
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )

    # Margem Líquida = Lucro Líquido / Receita
    df["Margem Líquida"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] > 0,
        df["Lucro/Prejuízo Consolidado do Período"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )

    # =============================================================
    # ESTRUTURA DE CAPITAL - ✅ TODOS CORRETOS
    # =============================================================
    
    # Total do Passivo = Passivo Circulante + Passivo Não Circulante + Patrimônio Líquido
    df["Total Passivo"] = (
        df["Passivo Circulante"].fillna(0) + 
        df["Passivo Não Circulante"].fillna(0) + 
        df["Patrimônio Líquido Consolidado"].fillna(0)
    )

    # Percentual Capital Terceiros = (Passivo Circulante + Passivo Não Circulante) / Total Passivo
    df["Percentual Capital Terceiros"] = np.where(
        df["Total Passivo"] > 0,
        (df["Passivo Circulante"].fillna(0) + df["Passivo Não Circulante"].fillna(0)) / df["Total Passivo"],
        np.nan
    )

    # Percentual Capital Próprio = Patrimônio Líquido / Total Passivo
    df["Percentual Capital Próprio"] = np.where(
        df["Total Passivo"] > 0,
        df["Patrimônio Líquido Consolidado"] / df["Total Passivo"],
        np.nan
    )

    # =============================================================
    # CUSTO DE CAPITAL - ✅ TODOS CORRETOS
    # =============================================================
    
    # ki (Custo da Dívida) = Despesas Financeiras / Passivo Oneroso Médio
    df["ki"] = np.where(
        (df["Passivo Oneroso Médio"] > 0) & (df["Despesas Financeiras"].notna()),
        df["Despesas Financeiras"].abs() / df["Passivo Oneroso Médio"],
        np.nan
    )

    # ke (Custo do Capital Próprio) = Dividendos Pagos / PL Médio
    df["ke"] = np.where(
        (df["PL Médio"] > 0) & (df["Pagamento de Dividendos"].notna()),
        df["Pagamento de Dividendos"].abs() / df["PL Médio"],
        np.nan
    )

    # WACC = (ki × % Capital Terceiros) + (ke × % Capital Próprio)
    df["wacc"] = np.where(
        (df["ki"].notna()) & (df["ke"].notna()) & 
        (df["Percentual Capital Terceiros"].notna()) & (df["Percentual Capital Próprio"].notna()),
        (df["ki"] * df["Percentual Capital Terceiros"]) + (df["ke"] * df["Percentual Capital Próprio"]),
        np.nan
    )

    # =============================================================
    # EBITDA CORRIGIDO - USANDO SOMENTE 'Depreciação e amortização'
    # =============================================================
    
    # Encontrar o nome exato da coluna
    nome_coluna_da = None
    for col in df.columns:
        if 'depreciação' in col.lower() and 'amortização' in col.lower():
            nome_coluna_da = col
            break

    if nome_coluna_da:
        # Usar APENAS a coluna consolidada 'Depreciação e amortização'
        # CORREÇÃO: usar valor absoluto para garantir que estamos adicionando despesas não-caixa
        depreciacao_amortizacao = abs(df[nome_coluna_da].fillna(0))
        df["EBITDA"] = np.where(
            df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna(),
            df["Resultado Antes do Resultado Financeiro e dos Tributos"] + depreciacao_amortizacao,
            np.nan
        )
    else:
        # Se não temos dados de depreciação/amortização consolidada, usar aproximação
        df["EBITDA"] = df["Resultado Antes do Resultado Financeiro e dos Tributos"]
        st.warning("⚠️ Dados de Depreciação/Amortização não encontrados. EBITDA calculado como aproximação do Resultado Operacional.")

    # =============================================================
    # LUCRO ECONÔMICO - CORRIGIDOS CONFORME VELLANI
    # =============================================================
    
    # LUCRO ECONÔMICO 1 = (ROI - WACC) × Investimento Médio
    df["Lucro Econômico 1"] = np.where(
        (df["ROI"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()),
        (df["ROI"] - df["wacc"]) * df["Investimento Médio"],
        np.nan
    )

    # LUCRO ECONÔMICO 2 = Resultado Operacional - (WACC × Investimento Médio)
    df["Lucro Econômico 2"] = np.where(
        (df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna()) & 
        (df["wacc"].notna()) & 
        (df["Investimento Médio"].notna()),
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] - (df["wacc"] * df["Investimento Médio"]),
        np.nan
    )

    # VERIFICAÇÃO DE CONSISTÊNCIA
    df["Diferença Lucro Econômico"] = abs(df["Lucro Econômico 1"] - df["Lucro Econômico 2"])

    # =============================================================
    # ANÁLISE DE ALAVANCAGEM - ✅ CORRETO
    # =============================================================
    
    # Verifica se a alavancagem é eficaz (ROE > ROA e ROE > ROI)
    df["Alavancagem Eficaz"] = np.where(
        (df["ROE"].notna()) & (df["ROA"].notna()) & (df["ROI"].notna()),
        (df["ROE"] > df["ROA"]) & (df["ROE"] > df["ROI"]),
        False
    )

    return df

# Carregar dados
df = load_data()

# ==============================
# SIDEBAR - FILTROS PRINCIPAIS
# ==============================
st.sidebar.header("🔧 Filtros Principais")

# Seleção de modo de análise
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
    # Dados para série temporal - todos os anos da empresa selecionada
    df_empresa_todos_anos = df[df["Ticker"] == ticker_selecionado].sort_values("Ano")
    
elif modo_analise == "🏭 Análise Setorial":
    setor_selecionado = st.sidebar.selectbox(
        "Selecione o Setor:",
        sorted(df["SETOR_ATIV"].dropna().unique())
    )
    df_filtrado = df[(df["SETOR_ATIV"] == setor_selecionado) & (df["Ano"] == ano_selecionado)]
    # Dados para série temporal - todos os anos do setor selecionado
    df_setor_todos_anos = df[df["SETOR_ATIV"] == setor_selecionado].sort_values(["Ano", "Ticker"])
    
else:  # Ranking Comparativo
    df_filtrado = df[df["Ano"] == ano_selecionado]

# ==============================
# TELA PRINCIPAL - RANKING COMPARATIVO
# ==============================
if modo_analise == "🏆 Ranking Comparativo":
    st.header(f"🏆 Ano mais recente publicado: {ano_selecionado}")
    
    # KPIs Gerais no Topo
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        empresas_ativas = df_filtrado["Ticker"].nunique()
        st.metric("Empresas Analisadas", empresas_ativas)
    
    with col2:
        setores_ativos = df_filtrado["SETOR_ATIV"].nunique()
        st.metric("Setores Representados", setores_ativos)
    
    with col3:
        # VALORES JÁ ESTÃO EM R$ MIL - CONVERTER PARA BILHÕES
        receita_total = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum() / 1e6
        st.metric("Receita Total (R$ Bi)", f"R$ {receita_total:.2f}")
    
    with col4:
        # VALORES JÁ ESTÃO EM R$ MIL - CONVERTER PARA BILHÕES
        lucro_total = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum() / 1e6
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
                # VALORES JÁ ESTÃO EM R$ MIL - CONVERTER PARA MILHÕES
                lucro_ranking["Lucro (R$ Mi)"] = lucro_ranking["Lucro/Prejuízo Consolidado do Período"] / 1e3
                fig_lucro_rank = px.bar(lucro_ranking, x="Ticker", y="Lucro (R$ Mi)", color="SETOR_ATIV",
                                      title="Ranking por Lucro Líquido")
                st.plotly_chart(fig_lucro_rank, use_container_width=True)
            else:
                st.warning("Não há dados de lucro disponíveis para ranking")
        
        with col2:
            st.subheader("Top 15 Empresas por Receita")
            receita_ranking = df_filtrado.nlargest(15, "Receita de Venda de Bens e/ou Serviços")[["Ticker", "SETOR_ATIV", "Receita de Venda de Bens e/ou Serviços"]]
            
            if not receita_ranking.empty:
                # VALORES JÁ ESTÃO EM R$ MIL - CONVERTER PARA BILHÕES
                receita_ranking["Receita (R$ Bi)"] = receita_ranking["Receita de Venda de Bens e/ou Serviços"] / 1e6
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
                # VALORES JÁ ESTÃO EM R$ MIL - CONVERTER PARA BILHÕES
                pl_ranking["PL (R$ Bi)"] = pl_ranking["Patrimônio Líquido Consolidado"] / 1e6
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
    st.header(f"📊 Análise Detalhada - {ticker_selecionado}")
    
    if not df_empresa_todos_anos.empty:
        # Abas para análise atual vs evolução temporal
        tab_atual, tab_evolucao = st.tabs(["📊 Análise do Ano", "📈 Evolução Temporal"])
        
        with tab_atual:
            st.subheader(f"Ano {ano_selecionado}")
            
            if not df_filtrado.empty:
                # KPIs Principais
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    valor_roe = df_filtrado["ROE"].iloc[0]
                    if pd.notna(valor_roe):
                        st.metric("ROE", f"{valor_roe:.2%}")
                    else:
                        st.metric("ROE*", "-", 
                                 help="ROE = Lucro Líquido ÷ PL Médio. Calculado apenas quando PL Médio > 0")
                
                with col2:
                    valor_roa = df_filtrado["ROA"].iloc[0]
                    if pd.notna(valor_roa):
                        st.metric("ROA", f"{valor_roa:.2%}")
                    else:
                        st.metric("ROA*", "-", 
                                 help="ROA = Resultado Operacional ÷ Ativo Médio. Calculado apenas quando Ativo Médio > 0")
                
                with col3:
                    valor_roi = df_filtrado["ROI"].iloc[0]
                    if pd.notna(valor_roi):
                        st.metric("ROI", f"{valor_roi:.2%}")
                    else:
                        st.metric("ROI*", "-", 
                                 help="ROI = Resultado Operacional ÷ Investimento Médio. Calculado apenas quando Investimento Médio > 0")
                
                with col4:
                    valor_wacc = df_filtrado["wacc"].iloc[0]
                    if pd.notna(valor_wacc):
                        st.metric("WACC", f"{valor_wacc:.2%}")
                    else:
                        st.metric("WACC*", "-", 
                                 help="WACC não pôde ser calculado devido a dados insuficientes")
                
                # VERIFICAÇÃO LUCRO ECONÔMICO 1 vs 2
                st.subheader("🔍 Verificação: Lucro Econômico 1 vs 2")
                lucro_eco1 = df_filtrado["Lucro Econômico 1"].iloc[0]
                lucro_eco2 = df_filtrado["Lucro Econômico 2"].iloc[0]
                
                if pd.notna(lucro_eco1) and pd.notna(lucro_eco2):
                    diferenca = abs(lucro_eco1 - lucro_eco2)
                    # Tolerância de 0.1% do maior valor absoluto
                    tolerancia = max(abs(lucro_eco1), abs(lucro_eco2)) * 0.001
                    
                    if diferenca <= tolerancia:
                        st.success("✅ LUCRO ECONÔMICO 1 = LUCRO ECONÔMICO 2")
                        # VALORES JÁ ESTÃO EM R$ MIL - EXIBIR DIRETAMENTE
                        st.write(f"Lucro Econômico 1: R$ {lucro_eco1:,.0f} mil")
                        st.write(f"Lucro Econômico 2: R$ {lucro_eco2:,.0f} mil")
                        st.write(f"Diferença: R$ {diferenca:,.2f} mil (dentro da tolerância)")
                    else:
                        st.error("❌ LUCRO ECONÔMICO 1 ≠ LUCRO ECONÔMICO 2")
                        st.write(f"Lucro Econômico 1: R$ {lucro_eco1:,.0f} mil")
                        st.write(f"Lucro Econômico 2: R$ {lucro_eco2:,.0f} mil")
                        st.write(f"Diferença: R$ {diferenca:,.0f} mil")
                else:
                    st.info("ℹ️ Dados de Lucro Econômico não disponíveis para verificação")
                
                # Análise de Alavancagem
                st.subheader("🔍 Análise de Alavancagem")
                if pd.notna(df_filtrado["Alavancagem Eficaz"].iloc[0]):
                    if df_filtrado["Alavancagem Eficaz"].iloc[0]:
                        st.success("✅ Alavancagem com Eficácia: SIM")
                        st.write(f"ROE ({df_filtrado['ROE'].iloc[0]:.2%}) > ROA ({df_filtrado['ROA'].iloc[0]:.2%})")
                    else:
                        st.warning("⚠️ Alavancagem com Eficácia: NÃO")
                else:
                    st.info("ℹ️ Análise de alavancagem não disponível")
                
                st.divider()
                
                # Abas para diferentes categorias de indicadores
                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Rentabilidade", "💰 EBITDA", "🏛️ Estrutura Capital", "💸 Custo Capital", "📊 Lucro Econômico", "📋 Dados Brutos"])
                
                with tab1:
                    st.subheader("Indicadores de Rentabilidade")
                    rentabilidade_cols = ["ROE", "ROA", "ROI", "Margem Bruta", "Margem Operacional", "Margem Líquida"]
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
                    st.subheader("EBITDA - Geração de Caixa Operacional")
                    
                    # Mostrar cálculo do EBITDA
                    ebitda_valor = df_filtrado["EBITDA"].iloc[0] if "EBITDA" in df_filtrado.columns and pd.notna(df_filtrado["EBITDA"].iloc[0]) else None
                    resultado_operacional = df_filtrado["Resultado Antes do Resultado Financeiro e dos Tributos"].iloc[0] if pd.notna(df_filtrado["Resultado Antes do Resultado Financeiro e dos Tributos"].iloc[0]) else None
                    
                    if ebitda_valor is not None and resultado_operacional is not None:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # VALORES JÁ ESTÃO EM R$ MIL - EXIBIR DIRETAMENTE
                            st.metric("EBITDA", f"R$ {ebitda_valor:,.0f} mil")
                            
                        with col2:
                            st.metric("Resultado Operacional", f"R$ {resultado_operacional:,.0f} mil")
                        
                        # Detalhamento do cálculo
                        st.subheader("📊 Detalhamento do Cálculo do EBITDA")
                        
                        # Encontrar o nome exato da coluna no DataFrame filtrado
                        nome_coluna_da_filtrado = None
                        for col in df_filtrado.columns:
                            if 'depreciação' in col.lower() and 'amortização' in col.lower():
                                nome_coluna_da_filtrado = col
                                break

                        if nome_coluna_da_filtrado and pd.notna(df_filtrado[nome_coluna_da_filtrado].iloc[0]):
                            depreciacao_amortizacao = df_filtrado[nome_coluna_da_filtrado].iloc[0]
                            depreciacao_amortizacao_abs = abs(depreciacao_amortizacao)
                            st.write(f"**Resultado Operacional:** R$ {resultado_operacional:,.0f} mil")
                            st.write(f"**Depreciação e Amortização:** R$ {depreciacao_amortizacao_abs:,.0f} mil")
                            st.write(f"**EBITDA = Resultado Operacional + Depreciação e Amortização**")
                            st.write(f"**EBITDA =** R$ {resultado_operacional:,.0f} mil + R$ {depreciacao_amortizacao_abs:,.0f} mil = **R$ {ebitda_valor:,.0f} mil**")
                        else:
                            st.info("ℹ️ Dados de Depreciação/Amortização não disponíveis. EBITDA calculado como aproximação do Resultado Operacional.")
                            st.write(f"**EBITDA ≈ Resultado Operacional = R$ {ebitda_valor:,.0f} mil**")
                    
                    else:
                        st.warning("Dados de EBITDA não disponíveis")
                
                with tab3:
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
                
                with tab4:
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
                
                with tab5:
                    st.subheader("Lucro Econômico")
                    lucro_cols = ["Lucro Econômico 1", "Lucro Econômico 2"]
                    lucro_data = []
                    
                    for col in lucro_cols:
                        if col in df_filtrado.columns:
                            valor = df_filtrado[col].iloc[0]
                            if pd.notna(valor):
                                # VALORES JÁ ESTÃO EM R$ MIL - EXIBIR DIRETAMENTE
                                lucro_data.append({
                                    "Indicador": col,
                                    "Valor (R$ Mil)": f"R$ {valor:,.0f}",
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
                
                with tab6:
                    st.subheader("Dados Financeiros Brutos (R$ Mil)")
                    dados_brutos_cols = [
                        "Receita de Venda de Bens e/ou Serviços",
                        "Resultado Bruto", 
                        "Resultado Antes do Resultado Financeiro e dos Tributos",
                        "Lucro/Prejuízo Consolidado do Período",
                        "Despesas Financeiras",
                        "Pagamento de Dividendos",
                        "Ativo Total",
                        "Patrimônio Líquido Consolidado",
                        "Empréstimos e Financiamentos - Circulante",
                        "Empréstimos e Financiamentos - Não Circulante"
                    ]
                    
                    # Adicionar a coluna de depreciação/amortização se existir
                    nome_coluna_da_brutos = None
                    for col in df_filtrado.columns:
                        if 'depreciação' in col.lower() and 'amortização' in col.lower():
                            nome_coluna_da_brutos = col
                            break

                    if nome_coluna_da_brutos:
                        dados_brutos_cols.append(nome_coluna_da_brutos)
                    
                    dados_brutos = {}
                    for col in dados_brutos_cols:
                        if col in df_filtrado.columns:
                            valor = df_filtrado[col].iloc[0]
                            if pd.notna(valor):
                                # VALORES JÁ ESTÃO EM R$ MIL - MANTER COMO ESTÁ
                                dados_brutos[col] = valor
                            else:
                                dados_brutos[col] = None
                    
                    # Formatar valores em milhares (já estão em mil)
                    dados_formatados = {k: f"R$ {v:,.0f}" if v is not None else "N/A" for k, v in dados_brutos.items()}
                    st.dataframe(pd.DataFrame.from_dict(dados_formatados, orient='index', columns=['Valor (R$ Mil)']), 
                               use_container_width=True)
            
            else:
                st.warning(f"Não há dados disponíveis para {ticker_selecionado} no ano {ano_selecionado}")
        
        with tab_evolucao:
            st.subheader(f"Evolução Temporal - {ticker_selecionado}")
            
            if len(df_empresa_todos_anos) > 1:
                # Gráficos de evolução temporal
                col1, col2 = st.columns(2)
                
                with col1:
                    # Rentabilidade
                    fig_rentabilidade = go.Figure()
                    
                    indicadores_rentabilidade = ['ROE', 'ROA', 'ROI', 'Margem Líquida']
                    cores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
                    
                    for i, indicador in enumerate(indicadores_rentabilidade):
                        if indicador in df_empresa_todos_anos.columns:
                            dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                            if not dados_validos.empty:
                                fig_rentabilidade.add_trace(go.Scatter(
                                    x=dados_validos['Ano'],
                                    y=dados_validos[indicador],
                                    mode='lines+markers',
                                    name=indicador,
                                    line=dict(color=cores[i % len(cores)], width=3),
                                    marker=dict(size=8)
                                ))
                    
                    fig_rentabilidade.update_layout(
                        title='Evolução da Rentabilidade',
                        xaxis_title='Ano',
                        yaxis_title='Percentual',
                        yaxis_tickformat='.2%',
                        height=400,
                        showlegend=True
                    )
                    st.plotly_chart(fig_rentabilidade, use_container_width=True)
                
                with col2:
                    # Estrutura de Capital
                    fig_estrutura = go.Figure()
                    
                    indicadores_estrutura = ['Percentual Capital Terceiros', 'Percentual Capital Próprio']
                    cores_estrutura = ['#e74c3c', '#2ecc71']
                    
                    for i, indicador in enumerate(indicadores_estrutura):
                        if indicador in df_empresa_todos_anos.columns:
                            dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                            if not dados_validos.empty:
                                fig_estrutura.add_trace(go.Scatter(
                                    x=dados_validos['Ano'],
                                    y=dados_validos[indicador],
                                    mode='lines+markers',
                                    name=indicador,
                                    line=dict(color=cores_estrutura[i % len(cores_estrutura)], width=3),
                                    marker=dict(size=8),
                                    stackgroup='one' if i == 0 else None
                                ))
                    
                    fig_estrutura.update_layout(
                        title='Evolução da Estrutura de Capital',
                        xaxis_title='Ano',
                        yaxis_title='Percentual',
                        yaxis_tickformat='.2%',
                        height=400,
                        showlegend=True
                    )
                    st.plotly_chart(fig_estrutura, use_container_width=True)
                
                # Segunda linha de gráficos
                col3, col4 = st.columns(2)
                
                with col3:
                    # Custo de Capital
                    fig_custo = go.Figure()
                    
                    indicadores_custo = ['ki', 'ke', 'wacc']
                    nomes_custo = ['Custo da Dívida (ki)', 'Custo do Capital Próprio (ke)', 'WACC']
                    cores_custo = ['#9b59b6', '#3498db', '#f39c12']
                    
                    for i, indicador in enumerate(indicadores_custo):
                        if indicador in df_empresa_todos_anos.columns:
                            dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                            if not dados_validos.empty:
                                fig_custo.add_trace(go.Scatter(
                                    x=dados_validos['Ano'],
                                    y=dados_validos[indicador],
                                    mode='lines+markers',
                                    name=nomes_custo[i],
                                    line=dict(color=cores_custo[i % len(cores_custo)], width=3),
                                    marker=dict(size=8)
                                ))
                    
                    fig_custo.update_layout(
                        title='Evolução do Custo de Capital',
                        xaxis_title='Ano',
                        yaxis_title='Percentual',
                        yaxis_tickformat='.2%',
                        height=400,
                        showlegend=True
                    )
                    st.plotly_chart(fig_custo, use_container_width=True)
                
                with col4:
                    # Margens
                    fig_margens = go.Figure()
                    
                    indicadores_margens = ['Margem Bruta', 'Margem Operacional', 'Margem Líquida']
                    cores_margens = ['#16a085', '#27ae60', '#2980b9']
                    
                    for i, indicador in enumerate(indicadores_margens):
                        if indicador in df_empresa_todos_anos.columns:
                            dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                            if not dados_validos.empty:
                                fig_margens.add_trace(go.Scatter(
                                    x=dados_validos['Ano'],
                                    y=dados_validos[indicador],
                                    mode='lines+markers',
                                    name=indicador,
                                    line=dict(color=cores_margens[i % len(cores_margens)], width=3),
                                    marker=dict(size=8)
                                ))
                    
                    fig_margens.update_layout(
                        title='Evolução das Margens',
                        xaxis_title='Ano',
                        yaxis_title='Percentual',
                        yaxis_tickformat='.2%',
                        height=400,
                        showlegend=True
                    )
                    st.plotly_chart(fig_margens, use_container_width=True)
                
                # TERCEIRA LINHA - LUCRO ECONÔMICO E EBITDA
                st.subheader("💰 Evolução do Lucro Econômico e EBITDA")
                col5, col6 = st.columns(2)
                
                with col5:
                    # Lucro Econômico em valores absolutos
                    fig_lucro_absoluto = go.Figure()
                    
                    indicadores_lucro = ['Lucro Econômico 1', 'Lucro Econômico 2']
                    nomes_lucro = ['Lucro Econômico 1', 'Lucro Econômico 2']
                    cores_lucro = ['#e74c3c', '#3498db']
                    
                    for i, indicador in enumerate(indicadores_lucro):
                        if indicador in df_empresa_todos_anos.columns:
                            dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                            if not dados_validos.empty:
                                # VALORES JÁ ESTÃO EM R$ MIL - EXIBIR DIRETAMENTE
                                fig_lucro_absoluto.add_trace(go.Scatter(
                                    x=dados_validos['Ano'],
                                    y=dados_validos[indicador],
                                    mode='lines+markers',
                                    name=nomes_lucro[i],
                                    line=dict(color=cores_lucro[i % len(cores_lucro)], width=3),
                                    marker=dict(size=8)
                                ))
                    
                    fig_lucro_absoluto.update_layout(
                        title='Lucro Econômico (Valores Absolutos)',
                        xaxis_title='Ano',
                        yaxis_title='Valor (R$ Mil)',
                        height=400,
                        showlegend=True
                    )
                    st.plotly_chart(fig_lucro_absoluto, use_container_width=True)
                
                with col6:
                    # EBITDA vs Resultado Operacional
                    fig_ebitda = go.Figure()
                    
                    indicadores_ebitda = ['EBITDA', 'Resultado Antes do Resultado Financeiro e dos Tributos']
                    nomes_ebitda = ['EBITDA', 'Resultado Operacional']
                    cores_ebitda = ['#2ecc71', '#34495e']
                    
                    for i, indicador in enumerate(indicadores_ebitda):
                        if indicador in df_empresa_todos_anos.columns:
                            dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                            if not dados_validos.empty:
                                # VALORES JÁ ESTÃO EM R$ MIL - EXIBIR DIRETAMENTE
                                fig_ebitda.add_trace(go.Scatter(
                                    x=dados_validos['Ano'],
                                    y=dados_validos[indicador],
                                    mode='lines+markers',
                                    name=nomes_ebitda[i],
                                    line=dict(color=cores_ebitda[i % len(cores_ebitda)], width=3),
                                    marker=dict(size=8)
                                ))
                    
                    fig_ebitda.update_layout(
                        title='EBITDA vs Resultado Operacional',
                        xaxis_title='Ano',
                        yaxis_title='Valor (R$ Mil)',
                        height=400,
                        showlegend=True
                    )
                    st.plotly_chart(fig_ebitda, use_container_width=True)
                
                # Tabela resumo da evolução
                st.subheader("📋 Resumo da Evolução - Principais Indicadores")
                
                # Selecionar indicadores chave para a tabela
                indicadores_resumo = ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio', 
                                    'Lucro Econômico 1', 'Resultado Antes do Resultado Financeiro e dos Tributos', 'EBITDA']
                df_resumo = df_empresa_todos_anos[['Ano'] + [col for col in indicadores_resumo if col in df_empresa_todos_anos.columns]]
                
                # Formatar para porcentagem e valores monetários
                def formatar_valor(valor, coluna):
                    if coluna in ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio']:
                        return f"{valor:.2%}" if pd.notna(valor) else "N/A"
                    elif coluna in ['Lucro Econômico 1', 'Resultado Antes do Resultado Financeiro e dos Tributos', 'EBITDA']:
                        # VALORES JÁ ESTÃO EM R$ MIL - EXIBIR DIRETAMENTE
                        return f"R$ {valor:,.0f} mil" if pd.notna(valor) else "N/A"
                    else:
                        return valor
                
                # Aplicar formatação
                df_resumo_formatado = df_resumo.copy()
                for col in df_resumo_formatado.columns:
                    if col != 'Ano':
                        df_resumo_formatado[col] = df_resumo_formatado[col].apply(lambda x: formatar_valor(x, col))
                
                st.dataframe(df_resumo_formatado, use_container_width=True)
                
            else:
                st.info("ℹ️ São necessários dados de múltiplos anos para análise de evolução temporal")

# ==============================
# TELA - ANÁLISE SETORIAL
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    st.header(f"🏭 Análise Setorial - {setor_selecionado}")
    
    if not df_setor_todos_anos.empty:
        # Abas para análise atual vs evolução temporal
        tab_atual_setor, tab_evolucao_setor = st.tabs(["📊 Análise do Ano", "📈 Evolução Temporal"])
        
        with tab_atual_setor:
            st.subheader(f"Ano {ano_selecionado}")
            
            if not df_filtrado.empty:
                # KPIs do Setor
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    empresas_setor = df_filtrado["Ticker"].nunique()
                    st.metric("Empresas no Setor", empresas_setor)
                
                with col2:
                    # VALORES JÁ ESTÃO EM R$ MIL - CONVERTER PARA BILHÕES
                    receita_setor = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum() / 1e6
                    st.metric("Receita Total (R$ Bi)", f"R$ {receita_setor:.2f}")
                
                with col3:
                    # VALORES JÁ ESTÃO EM R$ MIL - CONVERTER PARA BILHÕES
                    lucro_setor = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum() / 1e6
                    st.metric("Lucro Total (R$ Bi)", f"R$ {lucro_setor:.2f}")
                
                with col4:
                    # VALORES JÁ ESTÃO EM R$ MIL - CONVERTER PARA BILHÕES
                    pl_setor = df_filtrado["Patrimônio Líquido Consolidado"].sum() / 1e6
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
        
        with tab_evolucao_setor:
            st.subheader(f"Evolução Temporal do Setor - {setor_selecionado}")
            
            if len(df_setor_todos_anos['Ano'].unique()) > 1:
                # Calcular médias do setor por ano
                indicadores_setor = ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio', 'Lucro Econômico 1', 'EBITDA']
                
                # Agrupar por ano e calcular mediana (menos sensível a outliers)
                df_setor_evolucao = df_setor_todos_anos.groupby('Ano')[indicadores_setor].median().reset_index()
                
                # Gráficos de evolução do setor
                col1, col2 = st.columns(2)
                
                with col1:
                    # Rentabilidade do setor
                    fig_setor_rent = go.Figure()
                    
                    indicadores_rent_setor = ['ROE', 'ROA', 'ROI']
                    cores_setor = ['#1f77b4', '#ff7f0e', '#2ca02c']
                    
                    for i, indicador in enumerate(indicadores_rent_setor):
                        if indicador in df_setor_evolucao.columns:
                            dados_validos = df_setor_evolucao[df_setor_evolucao[indicador].notna()]
                            if not dados_validos.empty:
                                fig_setor_rent.add_trace(go.Scatter(
                                    x=dados_validos['Ano'],
                                    y=dados_validos[indicador],
                                    mode='lines+markers',
                                    name=indicador,
                                    line=dict(color=cores_setor[i % len(cores_setor)], width=3),
                                    marker=dict(size=8)
                                ))
                    
                    fig_setor_rent.update_layout(
                        title='Evolução da Rentabilidade do Setor (Mediana)',
                        xaxis_title='Ano',
                        yaxis_title='Percentual',
                        yaxis_tickformat='.2%',
                        height=400,
                        showlegend=True
                    )
                    st.plotly_chart(fig_setor_rent, use_container_width=True)
                
                with col2:
                    # Estrutura e custo do setor
                    fig_setor_estrutura = go.Figure()
                    
                    indicadores_estrutura_setor = ['Percentual Capital Próprio', 'wacc']
                    nomes_estrutura = ['Capital Próprio (%)', 'WACC']
                    cores_estrutura_setor = ['#2ecc71', '#f39c12']
                    
                    for i, indicador in enumerate(indicadores_estrutura_setor):
                        if indicador in df_setor_evolucao.columns:
                            dados_validos = df_setor_evolucao[df_setor_evolucao[indicador].notna()]
                            if not dados_validos.empty:
                                fig_setor_estrutura.add_trace(go.Scatter(
                                    x=dados_validos['Ano'],
                                    y=dados_validos[indicador],
                                    mode='lines+markers',
                                    name=nomes_estrutura[i],
                                    line=dict(color=cores_estrutura_setor[i % len(cores_estrutura_setor)], width=3),
                                    marker=dict(size=8)
                                ))
                    
                    fig_setor_estrutura.update_layout(
                        title='Evolução da Estrutura e Custo de Capital (Mediana)',
                        xaxis_title='Ano',
                        yaxis_title='Percentual',
                        yaxis_tickformat='.2%',
                        height=400,
                        showlegend=True
                    )
                    st.plotly_chart(fig_setor_estrutura, use_container_width=True)
                
                # TERCEIRA LINHA - LUCRO ECONÔMICO E EBITDA DO SETOR
                st.subheader("💰 Evolução do Lucro Econômico e EBITDA no Setor")
                col3, col4 = st.columns(2)
                
                with col3:
                    # Lucro Econômico médio do setor
                    if 'Lucro Econômico 1' in df_setor_evolucao.columns:
                        fig_setor_lucro = px.line(df_setor_evolucao, x='Ano', y='Lucro Econômico 1',
                                                title='Lucro Econômico Médio do Setor (Mediana)')
                        fig_setor_lucro.update_layout(
                            yaxis_title='Lucro Econômico (R$ Mil)',
                            height=400
                        )
                        st.plotly_chart(fig_setor_lucro, use_container_width=True)
                
                with col4:
                    # EBITDA médio do setor
                    if 'EBITDA' in df_setor_evolucao.columns:
                        fig_setor_ebitda = px.line(df_setor_evolucao, x='Ano', y='EBITDA',
                                                 title='EBITDA Médio do Setor (Mediana)')
                        fig_setor_ebitda.update_layout(
                            yaxis_title='EBITDA (R$ Mil)',
                            height=400
                        )
                        st.plotly_chart(fig_setor_ebitda, use_container_width=True)
                
                # Tabela resumo da evolução do setor
                st.subheader("📋 Resumo da Evolução do Setor - Principais Indicadores")
                
                # Formatar para porcentagem e valores monetários
                def formatar_valor_setor(valor, coluna):
                    if coluna in ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio']:
                        return f"{valor:.2%}" if pd.notna(valor) else "N/A"
                    elif coluna in ['Lucro Econômico 1', 'EBITDA']:
                        # VALORES JÁ ESTÃO EM R$ MIL - EXIBIR DIRETAMENTE
                        return f"R$ {valor:,.0f} mil" if pd.notna(valor) else "N/A"
                    else:
                        return valor
                
                # Aplicar formatação
                df_setor_formatado = df_setor_evolucao.copy()
                for col in df_setor_formatado.columns:
                    if col != 'Ano':
                        df_setor_formatado[col] = df_setor_formatado[col].apply(lambda x: formatar_valor_setor(x, col))
                
                st.dataframe(df_setor_formatado, use_container_width=True)
                
                # Dispersão do setor
                st.subheader("📊 Dispersão de Rentabilidade no Setor")
                
                if ano_selecionado in df_setor_todos_anos['Ano'].values:
                    df_setor_ano = df_setor_todos_anos[df_setor_todos_anos['Ano'] == ano_selecionado]
                    
                    if not df_setor_ano.empty and 'ROE' in df_setor_ano.columns:
                        fig_dispersao = px.box(df_setor_ano, y='ROE', 
                                             title=f'Distribuição do ROE no Setor - {ano_selecionado}')
                        fig_dispersao.update_layout(yaxis_tickformat='.2%')
                        st.plotly_chart(fig_dispersao, use_container_width=True)
                
            else:
                st.info("ℹ️ São necessários dados de múltiplos anos para análise de evolução temporal do setor")

# ==============================
# SEÇÃO DE FÓRMULAS DOS INDICADORES
# ==============================
st.divider()
st.header("📚 Fórmulas dos Indicadores (VELLANI, 2024)")

formulas = {
    "ROE (Return on Equity)": "Lucro Líquido ÷ Patrimônio Líquido Médio",
    "ROA (Return on Assets)": "Resultado Operacional ÷ Ativo Total Médio", 
    "ROI (Return on Investment)": "Resultado Operacional ÷ Investimento Médio",
    "Investimento Médio": "Média[(Empréstimos Circulante + Empréstimos Não Circulante + PL) atual e anterior]",
    "Margem Bruta": "Resultado Bruto ÷ Receita de Vendas",
    "Margem Operacional": "Resultado Operacional ÷ Receita de Vendas",
    "Margem Líquida": "Lucro Líquido ÷ Receita de Vendas",
    "ki (Custo da Dívida)": "Despesas Financeiras ÷ Passivo Oneroso Médio",
    "ke (Custo do Capital Próprio)": "Dividendos Pagos ÷ Patrimônio Líquido Médio",
    "WACC": "(ki × % Capital Terceiros) + (ke × % Capital Próprio)",
    "Lucro Econômico 1": "(ROI - WACC) × Investimento Médio",
    "Lucro Econômico 2": "Resultado Operacional - (WACC × Investimento Médio)",
    "EBITDA": "Resultado Operacional + Depreciação + Amortização",
    "Percentual Capital Terceiros": "(Passivo Circulante + Não Circulante) ÷ Total Passivo",
    "Percentual Capital Próprio": "Patrimônio Líquido ÷ Total Passivo"
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
    "calculados conforme metodologia Vellani (2024)"
)

# Rodapé
st.divider()
st.caption(f"📊 Dashboard CVM - Indicadores Financeiros | Dados atualizados para {ano_selecionado} | Total de empresas na base: {df['Ticker'].nunique()}")

# Adicionar informações sobre os cálculos
with st.sidebar.expander("💡 Metodologia livro Vellani (2024)"):
    st.write("""
    **Cálculos Verificados:**
    
    **VERIFICAÇÃO:**
    - Lucro Econômico 1 IGUAL ao Lucro Econômico 2 
    
     **Consistência Garantida:**
    - ROI = Resultado Operacional ÷ Investimento Médio
    - Lucro Econômico 1 = (ROI - WACC) × Investimento Médio
    - Lucro Econômico 2 = Resultado Operacional - (WACC × Investimento Médio)
    - **RESULTADO:** Lucro Econômico 1 = Lucro Econômico 2

    **EBITDA Corrigido:**
    - **EXCLUSIVAMENTE** usando a coluna 'Depreciação e amortização'
    - **CORREÇÃO:** Usa valores absolutos para depreciação/amortização para garantir cálculo correto
    - **FÓRMULA:** EBITDA = Resultado Operacional + |Depreciação e Amortização|
    - **ESCALA:** Todos os valores estão em R$ mil

    **Dataset: dff_2010_2024**
    - Período: 2010-2024 (15 anos)
    - Empresas: 253 únicas
    - Tickers: 317 únicos
    - Setores: 43 categorias
    - **ESCALA DOS VALORES:** R$ mil
    """)

# FIM DO SCRIPT
