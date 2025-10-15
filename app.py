# app.py
"""
📊 Dashboard CVM - Indicadores Financeiros (versão limpa e organizada)
Resumo:
- Versão modular do app recebido (base: arquivo enviado).
- Proteções contra NameError quando os dados não carregam.
- Comentários por bloco e funções reutilizáveis.
- Pronto para rodar no Streamlit (coloque este arquivo + datasets no mesmo diretório).
"""

import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# -----------------------------
# Configurações iniciais Streamlit
# -----------------------------
st.set_page_config(page_title="Dashboard CVM - Indicadores", layout="wide")
st.title("Dashboard CVM: Análise das Demonstrações Financeiras")

# -----------------------------
# Config: locale / formatação (silenciosa se não disponível)
# -----------------------------
def configurar_locale_brasil():
    import locale
    try:
        locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
    except Exception:
        try:
            locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
        except Exception:
            pass  # não crítico, apenas tentamos

configurar_locale_brasil()

# -----------------------------
# Utilitários de formatação
# - escala do dataset: R$ **mil** (conforme dataset original)
# -----------------------------
def formatar_moeda_brasil_correta(valor, casas_decimais=2):
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "R$ -"
    try:
        valor_em_reais = float(valor) * 1000  # dado está em R$ mil
        if abs(valor_em_reais) >= 1e12:
            suf = " tri"
            v = valor_em_reais / 1e12
        elif abs(valor_em_reais) >= 1e9:
            suf = " bi"
            v = valor_em_reais / 1e9
        elif abs(valor_em_reais) >= 1e6:
            suf = " mi"
            v = valor_em_reais / 1e6
        else:
            # exibir em milhares
            return f"R$ {valor_em_reais/1e3:,.0f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
        s = f"R$ {v:,.{casas_decimais}f}{suf}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"R$ {valor}"

def formatar_percentual_brasil(valor, casas_decimais=2):
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "N/A"
    try:
        return f"{valor:.{casas_decimais}%}".replace(".", ",")
    except Exception:
        return str(valor)

def formatar_numero_brasil_correto(valor, casas_decimais=0):
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "N/A"
    try:
        if casas_decimais == 0:
            return f"{valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"{valor:,.{casas_decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(valor)

# -----------------------------
# Carregar dados (modular, protegido)
# - Espera um arquivo 'dff_2010_2024.xlsx' no mesmo diretório
# - Se quiser usar o histórico de ações, coloque 'historico_acoes_completo.xlsx'
# -----------------------------
@st.cache_data(ttl=86400)
def load_data_cvm(path="dff_2010_2024.xlsx"):
    if not os.path.exists(path):
        return None, f"Arquivo {path} não encontrado."
    try:
        df = pd.read_excel(path)
        df.columns = [c.strip() for c in df.columns]
        # Garante ordenação para operações com shift()
        df = df.sort_values(["Ticker", "Ano"]).reset_index(drop=True)
        return df, None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=86400)
def carregar_dados_acoes(excel_path="historico_acoes_completo.xlsx"):
    if not os.path.exists(excel_path):
        return None
    try:
        dividendos = pd.read_excel(excel_path, sheet_name="Dividendos_Historicos")
        cotacoes = pd.read_excel(excel_path, sheet_name="Cotações_Historicas")
        dividendos['Data'] = pd.to_datetime(dividendos['Data'])
        cotacoes['Data'] = pd.to_datetime(cotacoes['Data'])
        return {"dividendos": dividendos, "cotacoes": cotacoes}
    except Exception:
        # tentativa com outros nomes de sheets/colunas poderia ser adicionada
        return None

# -----------------------------
# Carrega datasets
# -----------------------------
df, err = load_data_cvm()
DADOS_ACOES = carregar_dados_acoes()

# Se df for None, indica erro e interrompe interface principal (com mensagem guia)
if df is None:
    st.sidebar.error("❌ Dataset CVM não encontrado ou não pôde ser lido.")
    st.error(
        "Arquivo 'dff_2010_2024.xlsx' não encontrado ou inválido. "
        "Coloque o arquivo na mesma pasta do app e recarregue."
    )
    st.stop()

# -----------------------------
# Função principal de enrich/cálculos
# - Mantive a mesma lógica do seu script original mas organizada
# -----------------------------
@st.cache_data
def preparar_indicadores(df_in):
    df = df_in.copy()

    # Ativo médio
    df["Ativo Médio"] = (df["Ativo Total"] + df.groupby("Ticker")["Ativo Total"].shift(1)) / 2

    # PL médio
    df["PL Médio"] = (df["Patrimônio Líquido Consolidado"] + df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1)) / 2

    # Passivo oneroso médio
    df["Passivo Oneroso Atual"] = df["Empréstimos e Financiamentos - Circulante"].fillna(0) + df["Empréstimos e Financiamentos - Não Circulante"].fillna(0)
    df["Passivo Oneroso Anterior"] = df.groupby("Ticker")["Empréstimos e Financiamentos - Circulante"].shift(1).fillna(0) + df.groupby("Ticker")["Empréstimos e Financiamentos - Não Circulante"].shift(1).fillna(0)
    df["Passivo Oneroso Médio"] = (df["Passivo Oneroso Atual"] + df["Passivo Oneroso Anterior"]) / 2

    # Investimento médio
    df["Investimento Atual"] = df["Empréstimos e Financiamentos - Circulante"].fillna(0) + df["Empréstimos e Financiamentos - Não Circulante"].fillna(0) + df["Patrimônio Líquido Consolidado"].fillna(0)
    df["Investimento Anterior"] = df.groupby("Ticker")["Empréstimos e Financiamentos - Circulante"].shift(1).fillna(0) + df.groupby("Ticker")["Empréstimos e Financiamentos - Não Circulante"].shift(1).fillna(0) + df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1).fillna(0)
    df["Investimento Médio"] = (df["Investimento Atual"] + df["Investimento Anterior"]) / 2

    # Indicadores de rentabilidade
    df["ROA"] = np.where(df["Ativo Médio"] > 0, df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Ativo Médio"], np.nan)
    df["ROI"] = np.where(df["Investimento Médio"] > 0, df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Investimento Médio"], np.nan)
    df["ROE"] = np.where(df["PL Médio"] > 0, df["Lucro/Prejuízo Consolidado do Período"] / df["PL Médio"], np.nan)

    # Margens
    df["Margem Bruta"] = np.where(df["Receita de Venda de Bens e/ou Serviços"] > 0, df["Resultado Bruto"] / df["Receita de Venda de Bens e/ou Serviços"], np.nan)
    df["Margem Operacional"] = np.where(df["Receita de Venda de Bens e/ou Serviços"] > 0, df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Receita de Venda de Bens e/ou Serviços"], np.nan)
    df["Margem Líquida"] = np.where(df["Receita de Venda de Bens e/ou Serviços"] > 0, df["Lucro/Prejuízo Consolidado do Período"] / df["Receita de Venda de Bens e/ou Serviços"], np.nan)

    # Estrutura de capital
    df["Total Passivo"] = df["Passivo Circulante"].fillna(0) + df["Passivo Não Circulante"].fillna(0) + df["Patrimônio Líquido Consolidado"].fillna(0)
    df["Percentual Capital Terceiros"] = np.where(df["Total Passivo"] > 0, (df["Passivo Circulante"].fillna(0) + df["Passivo Não Circulante"].fillna(0)) / df["Total Passivo"], np.nan)
    df["Percentual Capital Próprio"] = np.where(df["Total Passivo"] > 0, df["Patrimônio Líquido Consolidado"] / df["Total Passivo"], np.nan)

    # Custo de capital
    df["ki"] = np.where((df["Passivo Oneroso Médio"] > 0) & (df["Despesas Financeiras"].notna()), df["Despesas Financeiras"].abs() / df["Passivo Oneroso Médio"], np.nan)
    df["ke"] = np.where((df["PL Médio"] > 0) & (df["Pagamento de Dividendos"].notna()), df["Pagamento de Dividendos"].abs() / df["PL Médio"], np.nan)
    df["wacc"] = np.where((df["ki"].notna()) & (df["ke"].notna()) & (df["Percentual Capital Terceiros"].notna()) & (df["Percentual Capital Próprio"].notna()), (df["ki"] * df["Percentual Capital Terceiros"]) + (df["ke"] * df["Percentual Capital Próprio"]), np.nan)

    # EBITDA
    nome_coluna_da = None
    for col in df.columns:
        if 'depreciação' in col.lower() and 'amortização' in col.lower():
            nome_coluna_da = col
            break
    if nome_coluna_da:
        depreciacao_amortizacao = abs(df[nome_coluna_da].fillna(0))
        df["EBITDA"] = np.where(df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna(), df["Resultado Antes do Resultado Financeiro e dos Tributos"] + depreciacao_amortizacao, np.nan)
    else:
        df["EBITDA"] = df["Resultado Antes do Resultado Financeiro e dos Tributos"]
        # Não interrompemos; apenas sinalizamos na UI quando necessário

    # Lucro econômico
    df["Lucro Econômico 1"] = np.where((df["ROI"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()), (df["ROI"] - df["wacc"]) * df["Investimento Médio"], np.nan)
    df["Lucro Econômico 2"] = np.where((df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()), df["Resultado Antes do Resultado Financeiro e dos Tributos"] - (df["wacc"] * df["Investimento Médio"]), np.nan)
    df["Diferença Lucro Econômico"] = abs(df["Lucro Econômico 1"] - df["Lucro Econômico 2"])

    # Alavancagem eficaz
    df["Alavancagem Eficaz"] = np.where((df["ROE"].notna()) & (df["ROA"].notna()) & (df["ROI"].notna()), (df["ROE"] > df["ROA"]) & (df["ROE"] > df["ROI"]), False)

    return df

# Executa preparação
df = preparar_indicadores(df)

# -----------------------------
# Sidebar: filtros e controles
# -----------------------------
st.sidebar.header("🔧 Filtros Principais")
if DADOS_ACOES is not None:
    st.sidebar.success("✅ Dados de ações carregados do Excel")
else:
    st.sidebar.info("⚠️ Arquivo 'historico_acoes_completo.xlsx' ausente (funcionalidade dividendos desativada)")

modo_analise = st.sidebar.radio("Modo de Análise:", ["🏆 Dados Gerais", "📈 Visão por Empresa", "🏭 Análise Setorial"])
anos_disponiveis = sorted(df["Ano"].dropna().unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Selecione o Ano:", anos_disponiveis)

# Definir df_filtrado/dados por modo (seguro)
if modo_analise == "📈 Visão por Empresa":
    ticker_selecionado = st.sidebar.selectbox("Selecione a Empresa:", sorted(df["Ticker"].dropna().unique()))
    df_filtrado = df[(df["Ticker"] == ticker_selecionado) & (df["Ano"] == ano_selecionado)]
    df_empresa_todos_anos = df[df["Ticker"] == ticker_selecionado].sort_values("Ano")
elif modo_analise == "🏭 Análise Setorial":
    setor_selecionado = st.sidebar.selectbox("Selecione o Setor:", sorted(df["SETOR_ATIV"].dropna().unique()))
    df_filtrado = df[(df["SETOR_ATIV"] == setor_selecionado) & (df["Ano"] == ano_selecionado)]
    df_setor_todos_anos = df[df["SETOR_ATIV"] == setor_selecionado].sort_values(["Ano", "Ticker"])
else:
    df_filtrado = df[df["Ano"] == ano_selecionado]

# -----------------------------
# Tela principal - Dados Gerais
# -----------------------------
if modo_analise == "🏆 Dados Gerais":
    st.header(f"🏆 Ano mais recente publicado: {ano_selecionado}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        empresas_ativas = int(df_filtrado["Ticker"].nunique()) if "Ticker" in df_filtrado.columns else 0
        st.metric("Empresas Analisadas", empresas_ativas)
    with col2:
        setores_ativos = int(df_filtrado["SETOR_ATIV"].nunique()) if "SETOR_ATIV" in df_filtrado.columns else 0
        st.metric("Setores Representados", setores_ativos)
    with col3:
        receita_total = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum() if "Receita de Venda de Bens e/ou Serviços" in df_filtrado.columns else 0
        st.metric("Receita Total", formatar_moeda_brasil_correta(receita_total, 2))
    with col4:
        lucro_total = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum() if "Lucro/Prejuízo Consolidado do Período" in df_filtrado.columns else 0
        st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_total, 2))

    st.divider()

    # Exemplo: ranking ROE / ROA
    tab_roe, tab_roa = st.tabs(["📈 ROE Top", "📉 ROA Top"])
    with tab_roe:
        if "ROE" in df_filtrado.columns:
            roe_ranking = df_filtrado[df_filtrado["ROE"].notna()].nlargest(15, "ROE")[["Ticker", "SETOR_ATIV", "ROE"]]
            if not roe_ranking.empty:
                fig = px.bar(roe_ranking, x="Ticker", y="ROE", color="SETOR_ATIV", title="Top 15 por ROE")
                fig.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados de ROE para o ano selecionado.")
        else:
            st.info("ROE não disponível no dataset.")

    with tab_roa:
        if "ROA" in df_filtrado.columns:
            roa_ranking = df_filtrado[df_filtrado["ROA"].notna()].nlargest(15, "ROA")[["Ticker", "SETOR_ATIV", "ROA"]]
            if not roa_ranking.empty:
                fig = px.bar(roa_ranking, x="Ticker", y="ROA", color="SETOR_ATIV", title="Top 15 por ROA")
                fig.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados de ROA para o ano selecionado.")

# -----------------------------
# Visão por Empresa
# -----------------------------
elif modo_analise == "📈 Visão por Empresa":
    st.header(f"📊 Análise Detalhada - {ticker_selecionado}")
    if df_empresa_todos_anos.empty:
        st.warning("Dados insuficientes para a empresa/ano selecionado.")
    else:
        # KPIs
        col1, col2, col3, col4, col5 = st.columns(5)
        def metric_or_na(df_row, col, fmt_fn):
            if col in df_row and pd.notna(df_row[col].iloc[0]):
                return fmt_fn(df_row[col].iloc[0])
            else:
                return "N/A"

        with col1:
            st.metric("ROE", metric_or_na(df_filtrado, "ROE", lambda v: formatar_percentual_brasil(v, 2)))
        with col2:
            st.metric("ROA", metric_or_na(df_filtrado, "ROA", lambda v: formatar_percentual_brasil(v, 2)))
        with col3:
            st.metric("ROI", metric_or_na(df_filtrado, "ROI", lambda v: formatar_percentual_brasil(v, 2)))
        with col4:
            st.metric("WACC", metric_or_na(df_filtrado, "wacc", lambda v: formatar_percentual_brasil(v, 2)))
        with col5:
            st.metric("Caixa Operacional", metric_or_na(df_filtrado, "Caixa Líquido Atividades Operacionais", formatar_moeda_brasil_correta))

        st.divider()

        # Evolução temporal - gráficos de exemplo (ROE, EBITDA)
        tab_atual, tab_evol = st.tabs(["📊 Ano Selecionado", "📈 Evolução Temporal"])
        with tab_atual:
            st.subheader(f"Ano {ano_selecionado} - Dados Básicos")
            st.dataframe(df_filtrado.head().T, use_container_width=True)

        with tab_evol:
            st.subheader("Evolução Temporal (exemplo: ROE, EBITDA)")
            if len(df_empresa_todos_anos) > 1:
                for indicador in ["ROE", "EBITDA"]:
                    if indicador in df_empresa_todos_anos.columns:
                        serie = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                        if not serie.empty:
                            fig = px.line(serie, x="Ano", y=indicador, title=f"Evolução: {indicador}")
                            st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Série temporal insuficiente.")

# -----------------------------
# Análise Setorial
# -----------------------------
elif modo_analise == "🏭 Análise Setorial":
    st.header(f"🏭 Análise Setorial - {setor_selecionado}")
    if df_filtrado.empty:
        st.warning("Sem dados para o setor/ano selecionado.")
    else:
        st.subheader("Medianas do Setor (por Ano)")
        indicadores = ["ROE", "ROA", "ROI", "Margem Líquida", "wacc"]
        indicador_exist = [c for c in indicadores if c in df_setor_todos_anos.columns]
        if indicador_exist:
            df_mediana = df_setor_todos_anos.groupby("Ano")[indicador_exist].median().reset_index()
            st.dataframe(df_mediana, use_container_width=True)
        else:
            st.info("Indicadores setoriais não disponíveis.")

# -----------------------------
# Rodapé / Metadados (proteção contra NameError)
# -----------------------------
st.divider()
try:
    total_empresas_base = int(df["Ticker"].nunique()) if "Ticker" in df.columns else 0
except Exception:
    total_empresas_base = 0

st.caption(f"📊 Dashboard CVM - Indicadores Financeiros | Dados atualizados para {ano_selecionado} | Total de empresas na base: {total_empresas_base}")

# -----------------------------
# Seção: fórmulas (explicativa)
# -----------------------------
with st.expander("📚 Fórmulas dos Indicadores (metodologia)"):
    st.markdown("""
    - **ROE** = Lucro Líquido ÷ Patrimônio Líquido Médio  
    - **ROA** = Resultado Operacional ÷ Ativo Médio  
    - **ROI** = Resultado Operacional ÷ Investimento Médio  
    - **EBITDA** = Resultado Operacional + Depreciação e Amortização (quando disponível)  
    - **WACC** = ki * %CapitalTerceiros + ke * %CapitalPróprio  
    - **Lucro Econômico** = (ROI - WACC) × Investimento Médio  (verificação com outra formulação)
    """)
