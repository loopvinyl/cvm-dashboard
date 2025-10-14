# ==============================================================
# 📊 DASHBOARD CVM - Indicadores Financeiros (VERSÃO COMPLETA COM ANÁLISES AVANÇADAS)
# ==============================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os
import yfinance as yf
from datetime import datetime, timedelta
import locale

# ==============================
# CONFIGURAÇÃO DE FORMATAÇÃO BRASILEIRA
# ==============================
def configurar_locale_brasil():
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
        except:
            # Remove o warning, apenas ignora silenciosamente
            pass

configurar_locale_brasil()

# ==============================
# FUNÇÕES DE FORMATAÇÃO COM ESCALAS CORRIGIDAS
# ==============================
def formatar_moeda_brasil_correta(valor, casas_decimais=2):
    """
    Formata valor monetário CORRETO considerando que entra em R$ mil
    e sai convertido para escala apropriada
    """
    if valor is None or pd.isna(valor):
        return "R$ -"
    
    try:
        # Converter de R$ mil para R$
        valor_em_reais = valor * 1000
        
        if abs(valor_em_reais) >= 1e12:  # Trilhões
            return f"R$ {valor_em_reais/1e12:,.{casas_decimais}f} tri".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(valor_em_reais) >= 1e9:  # Bilhões
            return f"R$ {valor_em_reais/1e9:,.{casas_decimais}f} bi".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(valor_em_reais) >= 1e6:  # Milhões
            return f"R$ {valor_em_reais/1e6:,.{casas_decimais}f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
        else:  # Valores pequenos - mostrar em milhares
            return f"R$ {valor_em_reais/1e3:,.0f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return f"R$ {valor}"

def formatar_numero_brasil_correto(valor, casas_decimais=0):
    """
    Formata número CORRETO considerando possível conversão de escala
    """
    if valor is None or pd.isna(valor):
        return "N/A"
    
    try:
        if abs(valor) >= 1e12:  # Trilhões
            return f"{valor/1e12:,.{casas_decimais}f} tri".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(valor) >= 1e9:  # Bilhões
            return f"{valor/1e9:,.{casas_decimais}f} bi".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(valor) >= 1e6:  # Milhões
            return f"{valor/1e6:,.{casas_decimais}f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
        elif casas_decimais == 0:
            return f"{valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"{valor:,.{casas_decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)

def formatar_percentual_brasil(valor, casas_decimais=2):
    """
    Formata percentual no padrão brasileiro: 10,50%
    """
    if valor is None or pd.isna(valor):
        return "N/A"
    
    try:
        return f"{valor:.{casas_decimais}%}".replace(".", ",")
    except:
        return str(valor)

# Funções para formatar dataframes
def formatar_dataframe_moeda(df, colunas):
    """Formata colunas do dataframe como moeda brasileira com escala correta"""
    df_formatado = df.copy()
    for coluna in colunas:
        if coluna in df_formatado.columns:
            df_formatado[coluna] = df_formatado[coluna].apply(
                lambda x: formatar_moeda_brasil_correta(x, 0) if pd.notna(x) else "N/A"
            )
    return df_formatado

def formatar_dataframe_percentual(df, colunas):
    """Formata colunas do dataframe como percentual brasileiro"""
    df_formatado = df.copy()
    for coluna in colunas:
        if coluna in df_formatado.columns:
            df_formatado[coluna] = df_formatado[coluna].apply(
                lambda x: formatar_percentual_brasil(x, 2) if pd.notna(x) else "N/A"
            )
    return df_formatado

# ==============================
# FUNÇÕES DE DIVIDENDOS E INVESTIMENTO (CORRIGIDAS)
# ==============================
def buscar_dividendos_historicos(ticker):
    """
    Busca dividendos históricos usando yfinance ATÉ A DATA ATUAL
    """
    try:
        # Adiciona .SA para ações brasileiras
        ticker_yf = f"{ticker}.SA"
        acao = yf.Ticker(ticker_yf)
        
        # Busca dividendos históricos ATÉ HOJE
        dividendos = acao.dividends
        
        if dividendos.empty:
            return None
            
        # Converter para DataFrame e formatar
        df_dividendos = dividendos.reset_index()
        df_dividendos.columns = ['Data', 'Dividendo']
        
        # CORREÇÃO: Remover timezone para compatibilidade
        df_dividendos['Data'] = df_dividendos['Data'].dt.tz_localize(None)
        
        # CORREÇÃO: Filtrar apenas a partir de 2010
        df_dividendos = df_dividendos[df_dividendos['Data'] >= datetime(2010, 1, 1)]
        
        df_dividendos['Ano'] = df_dividendos['Data'].dt.year
        df_dividendos['Mes'] = df_dividendos['Data'].dt.month
        
        # Ordenar por data
        df_dividendos = df_dividendos.sort_values('Data')
        
        return df_dividendos
        
    except Exception as e:
        st.warning(f"⚠️ Não foi possível buscar dividendos para {ticker}: {str(e)}")
        return None

def calcular_estatisticas_dividendos(df_dividendos):
    """
    Calcula estatísticas dos dividendos
    """
    if df_dividendos is None or df_dividendos.empty:
        return None
    
    stats = {
        'total_dividendos': df_dividendos['Dividendo'].sum(),
        'media_anual': df_dividendos.groupby('Ano')['Dividendo'].sum().mean(),
        'maior_dividendo': df_dividendos['Dividendo'].max(),
        'menor_dividendo': df_dividendos['Dividendo'].min(),
        'frequencia_media': len(df_dividendos) / df_dividendos['Ano'].nunique(),
        'ultimo_dividendo': df_dividendos.iloc[-1]['Dividendo'] if len(df_dividendos) > 0 else 0,
        'data_ultimo': df_dividendos.iloc[-1]['Data'] if len(df_dividendos) > 0 else None
    }
    
    return stats

def buscar_historico_precos(ticker, periodo_maximo="max"):
    """
    Busca histórico de preços de uma ação
    """
    try:
        ticker_yf = f"{ticker}.SA"
        acao = yf.Ticker(ticker_yf)
        historico = acao.history(period=periodo_maximo)
        
        if historico.empty:
            return None
        
        # CORREÇÃO: Remover timezone para compatibilidade
        historico.index = historico.index.tz_localize(None)
        
        return historico
    except Exception as e:
        st.warning(f"⚠️ Não foi possível buscar histórico de preços para {ticker}: {str(e)}")
        return None

def simular_investimento(ticker, data_inicio, valor_investido=1000):
    """
    Simula um investimento de R$ 1.000,00 a partir de uma data específica
    CORRIGIDA: compatibilidade de timezone
    """
    try:
        # Buscar histórico de preços
        historico = buscar_historico_precos(ticker, "max")
        if historico is None:
            return None
        
        # Buscar dividendos
        dividendos = buscar_dividendos_historicos(ticker)
        
        # Converter data_inicio para datetime (sem timezone)
        if isinstance(data_inicio, str):
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        
        # Encontrar o primeiro preço disponível após a data de início
        precos_apos_inicio = historico[historico.index >= data_inicio]
        if precos_apos_inicio.empty:
            return None
        
        primeira_data = precos_apos_inicio.index[0]
        preco_compra = precos_apos_inicio['Close'].iloc[0]
        
        # Calcular quantidade de ações compradas
        quantidade_acoes = valor_investido / preco_compra
        
        # Preço atual (último preço disponível)
        preco_atual = historico['Close'].iloc[-1]
        
        # Calcular dividendos recebidos desde a data de compra
        total_dividendos_recebidos = 0
        if dividendos is not None and not dividendos.empty:
            dividendos_apos_compra = dividendos[dividendos['Data'] >= primeira_data]
            total_dividendos_recebidos = (dividendos_apos_compra['Dividendo'] * quantidade_acoes).sum()
        
        # Calcular valores atuais
        valor_investido_atual = quantidade_acoes * preco_atual
        ganho_preco = valor_investido_atual - valor_investido
        ganho_total = ganho_preco + total_dividendos_recebidos
        
        # Calcular percentuais
        rentabilidade_dividendos_percentual = (total_dividendos_recebidos / valor_investido) * 100
        rentabilidade_preco_percentual = (ganho_preco / valor_investido) * 100
        rentabilidade_total_percentual = (ganho_total / valor_investido) * 100
        
        return {
            'data_compra': primeira_data,
            'preco_compra': preco_compra,
            'quantidade_acoes': quantidade_acoes,
            'preco_atual': preco_atual,
            'valor_investido_atual': valor_investido_atual,
            'total_dividendos_recebidos': total_dividendos_recebidos,
            'ganho_preco': ganho_preco,
            'ganho_total': ganho_total,
            'rentabilidade_dividendos_percentual': rentabilidade_dividendos_percentual,
            'rentabilidade_preco_percentual': rentabilidade_preco_percentual,
            'rentabilidade_total_percentual': rentabilidade_total_percentual
        }
        
    except Exception as e:
        st.warning(f"⚠️ Erro na simulação de investimento: {str(e)}")
        return None

def calcular_dividend_yield(ticker):
    """
    Calcula o dividend yield de uma ação
    """
    try:
        # Buscar dados da ação
        dados_cotacao = buscar_cotacao_atual(ticker)
        if not dados_cotacao:
            return None
            
        # Buscar dividendos dos últimos 12 meses
        dividendos = buscar_dividendos_historicos(ticker)
        if dividendos is None:
            return None
            
        # Calcular dividendos dos últimos 12 meses
        data_limite = datetime.now() - timedelta(days=365)
        dividendos_12m = dividendos[dividendos['Data'] >= data_limite]
        
        if dividendos_12m.empty:
            return None
            
        total_dividendos_12m = dividendos_12m['Dividendo'].sum()
        cotacao_atual = dados_cotacao['cotacao']
        
        # Calcular dividend yield
        dividend_yield = (total_dividendos_12m / cotacao_atual) * 100
        
        return dividend_yield
        
    except Exception as e:
        return None

# ==============================
# CONFIGURAÇÕES INICIAIS
# ==============================
st.set_page_config(page_title="Dashboard CVM - Indicadores", layout="wide")
st.title("Dashboard CVM : Análise das Demonstrações Financeiras")

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
    # INDICADORES DE RENTABILIDATE - CORRIGIDOS
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

# ==============================
# FUNÇÃO PARA VALUATION POR LUCRO ECONÔMICO/SELIC (CORRIGIDA)
# ==============================
def calcular_valuation_lucro_economico_selic(lucro_economico, selic_percentual=15):
    """
    Calcula o valuation da empresa usando método Lucro Econômico/SELIC
    
    Fórmula CORRETA: Valor da Empresa = Lucro Econômico ÷ (SELIC/100)
    """
    if lucro_economico and lucro_economico > 0:
        valor_empresa = lucro_economico / (selic_percentual / 100)
        return valor_empresa
    return None

def buscar_cotacao_atual(ticker):
    """
    Busca a cotação atual do ticker no Yahoo Finance
    """
    try:
        # Adiciona .SA para ações brasileiras
        ticker_yf = f"{ticker}.SA"
        acao = yf.Ticker(ticker_yf)
        info = acao.info
        
        cotacao = info.get('regularMarketPrice') or info.get('currentPrice')
        if cotacao:
            return {
                'cotacao': cotacao,
                'moeda': info.get('currency', 'BRL'),
                'nome': info.get('longName', ticker),
                'setor': info.get('sector', 'N/A'),
                'industria': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap'),
                'volume': info.get('volume'),
                'data_atualizacao': datetime.now().strftime("%d/%m/%Y %H:%M")
            }
    except Exception as e:
        st.warning(f"⚠️ Não foi possível buscar cotação para {ticker}: {str(e)}")
    
    return None

def criar_grafico_comparativo(preco_calculado, cotacao_atual, ticker):
    """
    Cria gráfico bullet chart comparativo entre preço calculado e cotação atual
    COM FORMATAÇÃO BRASILEIRA
    """
    fig = go.Figure()
    
    # Definir range do gráfico
    max_val = max(preco_calculado, cotacao_atual) * 1.3
    min_val = min(preco_calculado, cotacao_atual) * 0.7
    
    # Formatar valores para exibição
    preco_formatado = f"R$ {preco_calculado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    cotacao_formatada = f"R$ {cotacao_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    # Adicionar barra do preço calculado
    fig.add_trace(go.Indicator(
        mode = "number+gauge+delta",
        value = cotacao_atual,
        number = {'prefix': "R$ ", 'valueformat': ",.2f"},
        delta = {'reference': preco_calculado, 'relative': True, 'valueformat': ".1%"},
        domain = {'x': [0.1, 1], 'y': [0.1, 0.9]},
        title = {'text': f"💰 {ticker} - Cotação<br><span style='font-size:0.8em'>{cotacao_formatada} vs {preco_formatado}</span>"},
        gauge = {
            'shape': "bullet",
            'axis': {'range': [min_val, max_val], 'tickformat': ",.2f"},
            'threshold': {
                'line': {'color': "red", 'width': 2},
                'thickness': 0.75,
                'value': preco_calculado},
            'steps': [
                {'range': [min_val, preco_calculado], 'color': "lightgray"},
                {'range': [preco_calculado, max_val], 'color': "lightblue"}],
            'bar': {'color': "darkblue", 'thickness': 0.5}}
    ))
    
    fig.update_layout(
        height=200,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig

# Carregar dados
df = load_data()

# ==============================
# SIDEBAR - FILTROS PRINCIPAIS
# ==============================
st.sidebar.header("🔧 Filtros Principais")

# Seleção de modo de análise
modo_analise = st.sidebar.radio(
    "Modo de Análise:",
    ["🏆 Dados Gerais", "📈 Visão por Empresa", "🏭 Análise Setorial"]
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
    
else:  # Dados Gerais
    df_filtrado = df[df["Ano"] == ano_selecionado]

# ==============================
# TELA PRINCIPAL - RANKING COMPARATIVO (ESCALAS CORRIGIDAS)
# ==============================
if modo_analise == "🏆 Dados Gerais":
    st.header(f"🏆 Ano mais recente publicado: {ano_selecionado}")
    
    # KPIs Gerais no Topo - ESCALAS CORRIGIDAS
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        empresas_ativas = df_filtrado["Ticker"].nunique()
        st.metric("Empresas Analisadas", empresas_ativas)
    
    with col2:
        setores_ativos = df_filtrado["SETOR_ATIV"].nunique()
        st.metric("Setores Representados", setores_ativos)
    
    with col3:
        # CORREÇÃO: Usar formatação com escala automática
        receita_total = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum()
        st.metric("Receita Total", formatar_moeda_brasil_correta(receita_total, 2))
    
    with col4:
        # CORREÇÃO: Usar formatação com escala automática
        lucro_total = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum()
        st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_total, 2))
    
    st.divider()
    
    # Abas para diferentes rankings - ADICIONANDO ABA DE DIVIDENDOS
    rank_tab1, rank_tab2, rank_tab3, rank_tab4, rank_tab5 = st.tabs([
        "📈 Rentabilidade", "💰 Lucro e Receita", "🏛️ Solidez", "📊 Eficiência", "💰 Dividendos"
    ])
    
    with rank_tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 15 Empresas por ROE")
            roe_ranking = df_filtrado[df_filtrado["ROE"].notna()].nlargest(15, "ROE")[["Ticker", "SETOR_ATIV", "ROE"]]
            
            if not roe_ranking.empty:
                fig_roe_rank = px.bar(roe_ranking, x="Ticker", y="ROE", color="SETOR_ATIV",
                                    title="Ranking de ROE (Return on Equity)")
                fig_roe_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_roe_rank, use_container_width=True)
            else:
                st.warning("Não há dados de ROE disponíveis para ranking")
        
        with col2:
            st.subheader("Top 15 Empresas por ROA")
            roa_ranking = df_filtrado[df_filtrado["ROA"].notna()].nlargest(15, "ROA")[["Ticker", "SETOR_ATIV", "ROA"]]
            
            if not roa_ranking.empty:
                fig_roa_rank = px.bar(roa_ranking, x="Ticker", y="ROA", color="SETOR_ATIV",
                                    title="Ranking de ROA (Return on Assets)")
                fig_roa_rank.update_layout(yaxis_tickformat=',.2%')
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
            # Formatar para porcentagem brasileira
            rentabilidade_formatado = formatar_dataframe_percentual(
                rentabilidade_consolidado, 
                ['ROE', 'ROA', 'ROI', 'Margem Líquida']
            )
            st.dataframe(rentabilidade_formatado, use_container_width=True)
        else:
            st.warning("Não há dados suficientes para exibir a tabela consolidada")
    
    with rank_tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 15 Empresas por Lucro Líquido")
            lucro_ranking = df_filtrado.nlargest(15, "Lucro/Prejuízo Consolidado do Período")[["Ticker", "SETOR_ATIV", "Lucro/Prejuízo Consolidado do Período"]]
            
            if not lucro_ranking.empty:
                # CORREÇÃO: Converter para escala apropriada para gráfico
                lucro_ranking["Lucro (R$)"] = lucro_ranking["Lucro/Prejuízo Consolidado do Período"] * 1000 / 1e9  # Converter para bilhões
                
                fig_lucro_rank = px.bar(lucro_ranking, x="Ticker", y="Lucro (R$)", color="SETOR_ATIV",
                                      title="Ranking por Lucro Líquido")
                fig_lucro_rank.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig_lucro_rank, use_container_width=True)
                
                # Tabela com valores formatados
                lucro_ranking["Lucro"] = lucro_ranking["Lucro/Prejuízo Consolidado do Período"].apply(formatar_moeda_brasil_correta)
                st.dataframe(lucro_ranking[["Ticker", "SETOR_ATIV", "Lucro"]], use_container_width=True)
            else:
                st.warning("Não há dados de lucro disponíveis para ranking")
        
        with col2:
            st.subheader("Top 15 Empresas por Receita")
            receita_ranking = df_filtrado.nlargest(15, "Receita de Venda de Bens e/ou Serviços")[["Ticker", "SETOR_ATIV", "Receita de Venda de Bens e/ou Serviços"]]
            
            if not receita_ranking.empty:
                # CORREÇÃO: Converter para escala apropriada para gráfico
                receita_ranking["Receita (R$)"] = receita_ranking["Receita de Venda de Bens e/ou Serviços"] * 1000 / 1e9  # Converter para bilhões
                
                fig_receita_rank = px.bar(receita_ranking, x="Ticker", y="Receita (R$)", color="SETOR_ATIV",
                                        title="Ranking por Receita")
                fig_receita_rank.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig_receita_rank, use_container_width=True)
                
                # Tabela com valores formatados
                receita_ranking["Receita"] = receita_ranking["Receita de Venda de Bens e/ou Serviços"].apply(formatar_moeda_brasil_correta)
                st.dataframe(receita_ranking[["Ticker", "SETOR_ATIV", "Receita"]], use_container_width=True)
            else:
                st.warning("Não há dados de receita disponíveis para ranking")
    
    with rank_tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 15 Empresas por Patrimônio Líquido")
            pl_ranking = df_filtrado.nlargest(15, "Patrimônio Líquido Consolidado")[["Ticker", "SETOR_ATIV", "Patrimônio Líquido Consolidado"]]
            
            if not pl_ranking.empty:
                # CORREÇÃO: Converter para escala apropriada para gráfico
                pl_ranking["PL (R$)"] = pl_ranking["Patrimônio Líquido Consolidado"] * 1000 / 1e9  # Converter para bilhões
                
                fig_pl_rank = px.bar(pl_ranking, x="Ticker", y="PL (R$)", color="SETOR_ATIV",
                                   title="Ranking de Patrimônio Líquido")
                fig_pl_rank.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig_pl_rank, use_container_width=True)
                
                # Tabela com valores formatados
                pl_ranking["Patrimônio Líquido"] = pl_ranking["Patrimônio Líquido Consolidado"].apply(formatar_moeda_brasil_correta)
                st.dataframe(pl_ranking[["Ticker", "SETOR_ATIV", "Patrimônio Líquido"]], use_container_width=True)
            else:
                st.warning("Não há dados de patrimônio líquido disponíveis para ranking")
        
        with col2:
            st.subheader("Top 15 Empresas por ROI")
            roi_ranking = df_filtrado[df_filtrado["ROI"].notna()].nlargest(15, "ROI")[["Ticker", "SETOR_ATIV", "ROI"]]
            
            if not roi_ranking.empty:
                fig_roi_rank = px.bar(roi_ranking, x="Ticker", y="ROI", color="SETOR_ATIV",
                                    title="Ranking de ROI (Return on Investment)")
                fig_roi_rank.update_layout(yaxis_tickformat=',.2%')
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
                fig_margem_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_margem_rank, use_container_width=True)
            else:
                st.warning("Não há dados de margem líquida disponíveis para ranking")
        
        with col2:
            st.subheader("Empresas com Melhor WACC")
            wacc_ranking = df_filtrado[df_filtrado["wacc"].notna()].nsmallest(15, "wacc")[["Ticker", "SETOR_ATIV", "wacc"]]
            
            if not wacc_ranking.empty:
                fig_wacc_rank = px.bar(wacc_ranking, x="Ticker", y="wacc", color="SETOR_ATIV",
                                     title="Ranking por WACC (menor é melhor)")
                fig_wacc_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_wacc_rank, use_container_width=True)
            else:
                st.warning("Não há dados de WACC disponíveis para ranking")
    
    with rank_tab5:
        st.header("💰 Top 10 Pagadores de Dividendos")
        st.write("**Ranking baseado no Dividend Yield (últimos 12 meses)**")
        
        # Buscar dados de dividend yield para todas as empresas
        tickers_unicos = df_filtrado['Ticker'].unique()
        
        # Aumentar limite para 50 empresas
        tickers_analisar = tickers_unicos[:50]
        
        dados_dy = []
        
        with st.spinner("Calculando dividend yields... Isso pode levar alguns minutos"):
            progress_bar = st.progress(0)
            for i, ticker in enumerate(tickers_analisar):
                try:
                    dy = calcular_dividend_yield(ticker)
                    if dy is not None and dy > 0:  # Só incluir se tiver dividend yield positivo
                        dados_cotacao = buscar_cotacao_atual(ticker)
                        if dados_cotacao:
                            dados_dy.append({
                                'Ticker': ticker,
                                'Dividend Yield': dy,
                                'Cotação': dados_cotacao['cotacao'],
                                'Setor': dados_cotacao['setor']
                            })
                except Exception as e:
                    # Silenciosamente ignora erros e continua
                    pass
                
                # Atualizar barra de progresso
                progress_bar.progress((i + 1) / len(tickers_analisar))
        
        if dados_dy:
            # Criar DataFrame e ordenar por Dividend Yield
            df_dy = pd.DataFrame(dados_dy)
            df_dy = df_dy.nlargest(10, 'Dividend Yield')
            
            # Gráfico de barras
            fig_dy = px.bar(
                df_dy, 
                x='Ticker', 
                y='Dividend Yield',
                color='Setor',
                title='Top 10 Empresas por Dividend Yield'
            )
            fig_dy.update_layout(
                yaxis_title='Dividend Yield (%)',
                yaxis_tickformat=',.2f',
                height=500
            )
            st.plotly_chart(fig_dy, use_container_width=True)
            
            # Tabela detalhada
            st.subheader("📊 Detalhamento do Ranking")
            
            # Formatar a tabela
            df_dy_display = df_dy.copy()
            df_dy_display['Dividend Yield'] = df_dy_display['Dividend Yield'].apply(
                lambda x: f"{x:.2f}%"
            )
            df_dy_display['Cotação'] = df_dy_display['Cotação'].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
            
            st.dataframe(
                df_dy_display[['Ticker', 'Dividend Yield', 'Cotação', 'Setor']],
                use_container_width=True
            )
            
            # Análise qualitativa
            st.subheader("💡 Análise dos Dividend Yields")
            
            dy_medio = df_dy['Dividend Yield'].mean()
            dy_maximo = df_dy['Dividend Yield'].max()
            dy_minimo = df_dy['Dividend Yield'].min()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Dividend Yield Médio", f"{dy_medio:.2f}%")
            
            with col2:
                st.metric("Maior Dividend Yield", f"{dy_maximo:.2f}%")
            
            with col3:
                st.metric("Menor Dividend Yield", f"{dy_minimo:.2f}%")
            
            st.info("""
            **📈 Interpretação dos Dividend Yields:**
            
            - **Acima de 8%:** Yield muito alto - pode indicar oportunidades ou riscos elevados
            - **Entre 4% e 8%:** Yield atrativo - potencialmente bom para renda
            - **Abaixo de 4%:** Yield moderado - empresas em crescimento podem pagar menos dividendos
            
            ⚠️ **Atenção:** Dividend Yield alto nem sempre é bom - pode indicar que o preço da ação caiu devido a problemas na empresa.
            """)
            
        else:
            st.warning("""
            **ℹ️ Não foi possível calcular dividend yields**
            
            Possíveis razões:
            - Limitações na API do Yahoo Finance
            - Empresas não pagam dividendos regularmente
            - Dados históricos insuficientes
            """)

# ==============================
# TELA - VISÃO POR EMPRESA (ESCALAS CORRIGIDAS)
# ==============================
elif modo_analise == "📈 Visão por Empresa":
    st.header(f"📊 Análise Detalhada - {ticker_selecionado}")
    
    if not df_empresa_todos_anos.empty:
        # Abas para análise atual vs evolução temporal - ADICIONANDO ABA DE SIMULAÇÃO
        tab_atual, tab_evolucao, tab_dividendos, tab_simulacao = st.tabs([
            "📊 Análise do Ano", "📈 Evolução Temporal", "💰 Dividendos", "💵 Simulação Investimento"
        ])
        
        with tab_atual:
            st.subheader(f"Ano {ano_selecionado}")
            
            if not df_filtrado.empty:
                # KPIs Principais - ADICIONANDO CAIXA OPERACIONAL COMO QUINTA COLUNA
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    valor_roe = df_filtrado["ROE"].iloc[0]
                    if pd.notna(valor_roe):
                        st.metric("ROE", formatar_percentual_brasil(valor_roe, 2))
                    else:
                        st.metric("ROE*", "-", 
                                 help="ROE = Lucro Líquido ÷ PL Médio. Calculado apenas quando PL Médio > 0")
                
                with col2:
                    valor_roa = df_filtrado["ROA"].iloc[0]
                    if pd.notna(valor_roa):
                        st.metric("ROA", formatar_percentual_brasil(valor_roa, 2))
                    else:
                        st.metric("ROA*", "-", 
                                 help="ROA = Resultado Operacional ÷ Ativo Médio. Calculado apenas quando Ativo Médio > 0")
                
                with col3:
                    valor_roi = df_filtrado["ROI"].iloc[0]
                    if pd.notna(valor_roi):
                        st.metric("ROI", formatar_percentual_brasil(valor_roi, 2))
                    else:
                        st.metric("ROI*", "-", 
                                 help="ROI = Resultado Operacional ÷ Investimento Médio. Calculado apenas quando Investimento Médio > 0")
                
                with col4:
                    valor_wacc = df_filtrado["wacc"].iloc[0]
                    if pd.notna(valor_wacc):
                        st.metric("WACC", formatar_percentual_brasil(valor_wacc, 2))
                    else:
                        st.metric("WACC*", "-", 
                                 help="WACC não pôde ser calculado devido a dados insuficientes")
                
                with col5:
                    # ADIÇÃO: Caixa Líquido Atividades Operacionais
                    if 'Caixa Líquido Atividades Operacionais' in df_filtrado.columns:
                        valor_caixa = df_filtrado['Caixa Líquido Atividades Operacionais'].iloc[0]
                        if pd.notna(valor_caixa):
                            st.metric("Caixa Operacional", formatar_moeda_brasil_correta(valor_caixa))
                        else:
                            st.metric("Caixa Operacional*", "N/A", 
                                     help="Dados de caixa operacional não disponíveis")
                    else:
                        st.metric("Caixa Operacional*", "N/A", 
                                 help="Coluna 'Caixa Líquido Atividades Operacionais' não encontrada no dataset")
                
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
                        st.write(f"Lucro Econômico 1: {formatar_moeda_brasil_correta(lucro_eco1)}")
                        st.write(f"Lucro Econômico 2: {formatar_moeda_brasil_correta(lucro_eco2)}")
                        st.write(f"Diferença: {formatar_moeda_brasil_correta(diferenca)} (dentro da tolerância)")
                    else:
                        st.error("❌ LUCRO ECONÔMICO 1 ≠ LUCRO ECONÔMICO 2")
                        st.write(f"Lucro Econômico 1: {formatar_moeda_brasil_correta(lucro_eco1)}")
                        st.write(f"Lucro Econômico 2: {formatar_moeda_brasil_correta(lucro_eco2)}")
                        st.write(f"Diferença: {formatar_moeda_brasil_correta(diferenca)}")
                else:
                    st.info("ℹ️ Dados de Lucro Econômico não disponíveis para verificação")
                
                # Análise de Alavancagem
                st.subheader("🔍 Análise de Alavancagem")
                if pd.notna(df_filtrado["Alavancagem Eficaz"].iloc[0]):
                    if df_filtrado["Alavancagem Eficaz"].iloc[0]:
                        st.success("✅ Alavancagem com Eficácia: SIM")
                        st.write(f"ROE ({formatar_percentual_brasil(df_filtrado['ROE'].iloc[0], 2)}) > ROA ({formatar_percentual_brasil(df_filtrado['ROA'].iloc[0], 2)})")
                    else:
                        st.warning("⚠️ Alavancagem com Eficácia: NÃO")
                else:
                    st.info("ℹ️ Análise de alavancagem não disponível")
                
                st.divider()
                
                # Abas para diferentes categorias de indicadores - ADICIONANDO ABA DE FLUXO DE CAIXA
                tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📈 Rentabilidade", "💰 EBITDA", "🏛️ Estrutura Capital", "💸 Custo Capital", "📊 Lucro Econômico", "💵 Fluxo de Caixa", "📋 Dados Brutos"])
                
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
                                    "Valor": formatar_percentual_brasil(valor, 2),
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
                            st.metric("EBITDA", formatar_moeda_brasil_correta(ebitda_valor))
                            
                        with col2:
                            st.metric("Resultado Operacional", formatar_moeda_brasil_correta(resultado_operacional))
                        
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
                            st.write(f"**Resultado Operacional:** {formatar_moeda_brasil_correta(resultado_operacional)}")
                            st.write(f"**Depreciação e Amortização:** {formatar_moeda_brasil_correta(depreciacao_amortizacao_abs)}")
                            st.write(f"**EBITDA = Resultado Operacional + Depreciação e Amortização**")
                            st.write(f"**EBITDA =** {formatar_moeda_brasil_correta(resultado_operacional)} + {formatar_moeda_brasil_correta(depreciacao_amortizacao_abs)} = **{formatar_moeda_brasil_correta(ebitda_valor)}**")
                        else:
                            st.info("ℹ️ Dados de Depreciação/Amortização não disponíveis. EBITDA calculado como aproximação do Resultado Operacional.")
                            st.write(f"**EBITDA ≈ Resultado Operacional = {formatar_moeda_brasil_correta(ebitda_valor)}**")
                        
                        # =============================================================
                        # 🏦 SEÇÃO CORRIGIDA: VALUATION POR LUCRO ECONÔMICO/SELIC
                        # =============================================================
                        st.divider()
                        st.subheader("🏦 Valuation por Lucro Econômico/SELIC")

                        # Configuração da SELIC
                        col_selic1, col_selic2 = st.columns([2, 1])
                        with col_selic1:
                            st.write("**Configuração da Taxa SELIC:**")
                        with col_selic2:
                            selic_percentual = st.number_input(
                                "SELIC (%)",
                                min_value=0.1,
                                max_value=30.0,
                                value=15.0,
                                step=0.1,
                                help="Taxa SELIC atual para cálculo do valuation"
                            )

                        # Usar Lucro Econômico 1 para o cálculo (já que Lucro Econômico 1 = Lucro Econômico 2)
                        lucro_economico_valor = df_filtrado["Lucro Econômico 1"].iloc[0] if "Lucro Econômico 1" in df_filtrado.columns and pd.notna(df_filtrado["Lucro Econômico 1"].iloc[0]) else None

                        if lucro_economico_valor is not None and lucro_economico_valor > 0:
                            # Cálculo do Valuation CORRETO usando Lucro Econômico
                            valor_empresa = calcular_valuation_lucro_economico_selic(lucro_economico_valor, selic_percentual)

                            if valor_empresa:
                                # CORREÇÃO: Converter de R$ mil para R$ normais (multiplicar por 1000)
                                valor_empresa_reais = valor_empresa * 1000
                                
                                # Buscar número de ações (apenas para ano mais recente - 2024)
                                numero_acoes = None
                                if 'Numero_Acoes' in df_filtrado.columns and pd.notna(df_filtrado['Numero_Acoes'].iloc[0]):
                                    numero_acoes = df_filtrado['Numero_Acoes'].iloc[0]
                                
                                # Calcular cotação esperada se tivermos número de ações
                                cotacao_esperada = None
                                if numero_acoes and numero_acoes > 0:
                                    cotacao_esperada = valor_empresa_reais / numero_acoes
                                
                                # Buscar cotação atual
                                dados_cotacao = buscar_cotacao_atual(ticker_selecionado)
                                
                                # CÁLCULO DA SELIC IMPLÍCITA (NOVO)
                                selic_implicita = None
                                market_cap_atual = None
                                if dados_cotacao and numero_acoes and numero_acoes > 0:
                                    market_cap_atual = dados_cotacao['cotacao'] * numero_acoes
                                    if lucro_economico_valor > 0:
                                        # Fórmula: SELIC implícita = (Lucro Econômico / Market Cap) × 100
                                        selic_implicita = (lucro_economico_valor * 1000 / market_cap_atual) * 100
                                
                                # CÁLCULO DO EBITDA NECESSÁRIO (NOVO)
                                ebitda_necessario = None
                                if dados_cotacao and numero_acoes and numero_acoes > 0:
                                    # Fórmula: EBITDA necessário = (Market Cap × (SELIC/100) + DA + WACC × Investimento) / (1 - relação EBITDA/Lucro Econ)
                                    # Simplificação: Vamos usar uma aproximação baseada na margem operacional atual
                                    investimento_medio = df_filtrado["Investimento Médio"].iloc[0] if pd.notna(df_filtrado["Investimento Médio"].iloc[0]) else 0
                                    wacc = df_filtrado["wacc"].iloc[0] if pd.notna(df_filtrado["wacc"].iloc[0]) else 0
                                    
                                    # Encontrar depreciação e amortização
                                    nome_coluna_da = None
                                    for col in df_filtrado.columns:
                                        if 'depreciação' in col.lower() and 'amortização' in col.lower():
                                            nome_coluna_da = col
                                            break
                                    
                                    depreciacao_amortizacao = 0
                                    if nome_coluna_da and pd.notna(df_filtrado[nome_coluna_da].iloc[0]):
                                        depreciacao_amortizacao = abs(df_filtrado[nome_coluna_da].iloc[0])
                                    
                                    # Calcular relação atual entre EBITDA e Lucro Econômico
                                    ebitda_atual = df_filtrado["EBITDA"].iloc[0] if pd.notna(df_filtrado["EBITDA"].iloc[0]) else 0
                                    if ebitda_atual > 0 and lucro_economico_valor > 0:
                                        relacao_ebitda_lucro_eco = ebitda_atual / lucro_economico_valor
                                    else:
                                        # Se não temos dados, usar uma relação conservadora de 2:1
                                        relacao_ebitda_lucro_eco = 2.0
                                    
                                    # Cálculo do EBITDA necessário
                                    # Lucro Econômico necessário = Market Cap × (SELIC/100)
                                    lucro_economico_necessario = market_cap_atual * (selic_percentual / 100) / 1000  # Dividir por 1000 para voltar para R$ mil
                                    
                                    # EBITDA necessário = Lucro Econômico necessário × relação EBITDA/Lucro Econ
                                    ebitda_necessario = lucro_economico_necessario * relacao_ebitda_lucro_eco
                                
                                # Exibir resultados do valuation
                                col_val1, col_val2, col_val3, col_val4 = st.columns(4)
                                
                                with col_val1:
                                    st.metric(
                                        "Valor da Empresa (EV)",
                                        formatar_moeda_brasil_correta(valor_empresa_reais / 1000),
                                        help="EV = Lucro Econômico ÷ (SELIC/100) - Convertido para R$"
                                    )
                                
                                with col_val2:
                                    st.metric(
                                        "Valor da Empresa",
                                        formatar_moeda_brasil_correta(valor_empresa_reais / 1000),
                                        help="Valor da empresa"
                                    )
                                
                                with col_val3:
                                    if numero_acoes:
                                        st.metric(
                                            "Número de Ações",
                                            formatar_numero_brasil_correto(numero_acoes, 0),
                                            help="Quantidade total de ações"
                                        )
                                    else:
                                        st.metric(
                                            "Número de Ações*",
                                            "Não disponível",
                                            help="Dados de número de ações só disponíveis para 2024"
                                        )
                                
                                with col_val4:
                                    if cotacao_esperada:
                                        st.metric(
                                            "Cotação Esperada",
                                            f"R$ {cotacao_esperada:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                                            help="Preço por ação calculado"
                                        )
                                    else:
                                        st.metric(
                                            "Cotação Esperada*",
                                            "N/A",
                                            help="Necessário número de ações"
                                        )
                                
                                # Fórmula detalhada CORRETA
                                st.info(f"""
                                **📊 Fórmula do Valuation (CORRIGIDA):**
                                ```
                                Valor da Empresa = Lucro Econômico ÷ (SELIC/100)
                                Valor da Empresa = {formatar_moeda_brasil_correta(lucro_economico_valor)} ÷ ({selic_percentual}%/100)
                                Valor da Empresa = {formatar_moeda_brasil_correta(lucro_economico_valor)} ÷ {selic_percentual/100:.3f}
                                Valor da Empresa = {formatar_moeda_brasil_correta(valor_empresa)}
                                Valor da Empresa (R$) = {formatar_moeda_brasil_correta(valor_empresa)} × 1.000 = {formatar_moeda_brasil_correta(valor_empresa_reais / 1000)}
                                ```
                                """)
                                
                                if cotacao_esperada:
                                    st.info(f"""
                                    **💰 Cálculo da Cotação Esperada:**
                                    ```
                                    Cotação Esperada = Valor da Empresa (R$) ÷ Número de Ações
                                    Cotação Esperada = {formatar_moeda_brasil_correta(valor_empresa_reais / 1000)} ÷ {formatar_numero_brasil_correto(numero_acoes, 0)}
                                    Cotação Esperada = R$ {cotacao_esperada:,.2f}
                                    ```
                                    """)
                                
                                # NOVO: CÁLCULO DA SELIC IMPLÍCITA
                                if selic_implicita is not None:
                                    st.info(f"""
                                    **🎯 SELIC Implícita (Para igualar à cotação atual):**
                                    ```
                                    Market Cap Atual = Cotação Atual × Número de Ações
                                    Market Cap Atual = R$ {dados_cotacao['cotacao']:,.2f} × {formatar_numero_brasil_correto(numero_acoes, 0)}
                                    Market Cap Atual = {formatar_moeda_brasil_correta(market_cap_atual / 1000)}
                                    
                                    SELIC Implícita = (Lucro Econômico ÷ Market Cap Atual) × 100
                                    SELIC Implícita = ({formatar_moeda_brasil_correta(lucro_economico_valor)} ÷ {formatar_moeda_brasil_correta(market_cap_atual / 1000)}) × 100
                                    SELIC Implícita = {selic_implicita:.1f}%
                                    ```
                                    
                                    **💡 Interpretação:**
                                    - Para que a **cotação esperada** seja igual à **cotação atual** (R$ {dados_cotacao['cotacao']:,.2f})
                                    - A **SELIC** deveria ser de **{selic_implicita:.1f}%** a.a.
                                    - Isso significa que o mercado está precificando a empresa como se a taxa de desconto fosse {selic_implicita:.1f}% a.a.
                                    """)
                                    
                                    # Análise da SELIC implícita
                                    if selic_implicita < selic_percentual:
                                        st.success(f"**✅ SELIC Implícita ({selic_implicita:.1f}%) < SELIC Atual ({selic_percentual}%)**")
                                        st.write("O mercado está exigindo uma taxa de retorno **menor** que a SELIC atual, indicando **confiança** na empresa.")
                                    else:
                                        st.warning(f"**⚠️ SELIC Implícita ({selic_implicita:.1f}%) > SELIC Atual ({selic_percentual}%)**")
                                        st.write("O mercado está exigindo uma taxa de retorno **maior** que a SELIC atual, indicando **mais risco** percebido na empresa.")
                                
                                # NOVO: CÁLCULO DO EBITDA NECESSÁRIO
                                if ebitda_necessario is not None and ebitda_necessario > 0:
                                    ebitda_atual = df_filtrado["EBITDA"].iloc[0] if pd.notna(df_filtrado["EBITDA"].iloc[0]) else 0
                                    variacao_necessaria = ((ebitda_necessario - ebitda_atual) / ebitda_atual) * 100
                                    
                                    st.info(f"""
                                    **📈 EBITDA Necessário (Para igualar à cotação atual com SELIC {selic_percentual}%):**
                                    ```
                                    Market Cap Atual = {formatar_moeda_brasil_correta(market_cap_atual / 1000)}
                                    Lucro Econômico Necessário = Market Cap × (SELIC/100)
                                    Lucro Econômico Necessário = {formatar_moeda_brasil_correta(market_cap_atual / 1000)} × ({selic_percentual}%/100)
                                    Lucro Econômico Necessário = {formatar_moeda_brasil_correta(lucro_economico_necessario)}
                                    
                                    EBITDA Necessário = Lucro Econômico Necessário × (EBITDA Atual ÷ Lucro Econ Atual)
                                    EBITDA Necessário = {formatar_moeda_brasil_correta(lucro_economico_necessario)} × ({formatar_moeda_brasil_correta(ebitda_atual)} ÷ {formatar_moeda_brasil_correta(lucro_economico_valor)})
                                    EBITDA Necessário = {formatar_moeda_brasil_correta(ebitda_necessario)}
                                    ```
                                    
                                    **💡 Interpretação:**
                                    - Para justificar a **cotação atual** (R$ {dados_cotacao['cotacao']:,.2f}) com **SELIC atual** ({selic_percentual}%)
                                    - A empresa precisaria ter um **EBITDA** de **{formatar_moeda_brasil_correta(ebitda_necessario)}**
                                    - EBITDA Atual: {formatar_moeda_brasil_correta(ebitda_atual)}
                                    - Variação necessária: {variacao_necessaria:+.1f}%
                                    """)
                                    
                                    # Análise do EBITDA necessário
                                    if variacao_necessaria > 0:
                                        st.warning(f"**📈 EBITDA precisa crescer {variacao_necessaria:+.1f}%**")
                                        st.write("Para justificar a cotação atual, a empresa precisa **aumentar** seu EBITDA significativamente.")
                                    else:
                                        st.success(f"**✅ EBITDA atual já justifica a cotação**")
                                        st.write("O EBITDA atual já é suficiente para justificar a cotação de mercado com a SELIC atual.")
                                
                                # Mostrar também os dados de EBITDA para referência
                                if ebitda_valor:
                                    st.info(f"""
                                    **📊 Dados de Referência Atuais:**
                                    - **EBITDA:** {formatar_moeda_brasil_correta(ebitda_valor)}
                                    - **Lucro Econômico:** {formatar_moeda_brasil_correta(lucro_economico_valor)}
                                    - **Investimento Médio:** {formatar_moeda_brasil_correta(df_filtrado['Investimento Médio'].iloc[0])}
                                    - **ROI:** {formatar_percentual_brasil(df_filtrado['ROI'].iloc[0], 2)}
                                    - **WACC:** {formatar_percentual_brasil(df_filtrado['wacc'].iloc[0], 2)}
                                    """)
                                
                                # Se temos dados da cotação, fazer análise comparativa
                                if dados_cotacao:
                                    st.divider()
                                    st.subheader("📈 Análise Comparativa com Cotação de Mercado")
                                    
                                    # Informações da empresa
                                    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                                    
                                    with col_info1:
                                        st.metric("Cotação Atual", f"R$ {dados_cotacao['cotacao']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                    
                                    with col_info2:
                                        if cotacao_esperada:
                                            diferenca_percentual = ((dados_cotacao['cotacao'] - cotacao_esperada) / cotacao_esperada) * 100
                                            st.metric(
                                                "Diferença vs Calculado", 
                                                f"{diferenca_percentual:+.1f}%",
                                                delta=f"{diferenca_percentual:+.1f}%"
                                            )
                                    
                                    with col_info3:
                                        st.metric("Setor", dados_cotacao['setor'])
                                    
                                    with col_info4:
                                        if dados_cotacao['market_cap']:
                                            market_cap_tri = dados_cotacao['market_cap'] / 1e12
                                            st.metric("Market Cap", f"R$ {market_cap_tri:,.2f} tri".replace(",", "X").replace(".", ",").replace("X", "."))
                                    
                                    # Análise de valuation implícito
                                    st.write("**💡 Interpretação:**")
                                    
                                    if cotacao_esperada:
                                        st.write(f"""
                                        - **Lucro Econômico Anual:** {formatar_moeda_brasil_correta(lucro_economico_valor)}
                                        - **Taxa de Desconto (SELIC):** {selic_percentual}% a.a.
                                        - **Valor Justo Calculado:** {formatar_moeda_brasil_correta(valor_empresa_reais / 1000)}
                                        - **Número de Ações:** {formatar_numero_brasil_correto(numero_acoes, 0)}
                                        - **Cotação Esperada:** R$ {cotacao_esperada:,.2f}
                                        - **Cotação Atual ({dados_cotacao['data_atualizacao']}):** R$ {dados_cotacao['cotacao']:,.2f}
                                        - **Diferença:** {diferenca_percentual:+.1f}%
                                        """)
                                    else:
                                        st.write(f"""
                                        - **Lucro Econômico Anual:** {formatar_moeda_brasil_correta(lucro_economico_valor)}
                                        - **Taxa de Desconto (SELIC):** {selic_percentual}% a.a.
                                        - **Valor Justo Calculado:** {formatar_moeda_brasil_correta(valor_empresa_reais / 1000)}
                                        - **Cotação Atual ({dados_cotacao['data_atualizacao']}):** R$ {dados_cotacao['cotacao']:,.2f}
                                        """)
                                    
                                    # Gráfico comparativo
                                    if cotacao_esperada:
                                        st.subheader("🎯 Comparação Visual")
                                        
                                        fig_comparativo = criar_grafico_comparativo(
                                            cotacao_esperada, 
                                            dados_cotacao['cotacao'], 
                                            ticker_selecionado
                                        )
                                        st.plotly_chart(fig_comparativo, use_container_width=True)
                                        
                                        # Análise qualitativa
                                        if diferenca_percentual > 20:
                                            st.error("""
                                            **🔴 Sobrevalorizado:** A cotação atual está significativamente acima do valuation calculado.
                                            *Possíveis razões:* Expectativas de crescimento futuro, fatores setoriais favoráveis, ou especulação de mercado.
                                            """)
                                        elif diferenca_percentual < -20:
                                            st.success("""
                                            **🟢 Subvalorizado:** A cotação atual está significativamente abaixo do valuation calculado.
                                            *Possíveis oportunidades:* Valorização potencial, retorno ao valuation justo.
                                            """)
                                        else:
                                            st.info("""
                                            **🟡 Valuation Próximo:** A cotação atual está alinhada com o valuation calculado.
                                            *Interpretação:* Preço de mercado condizente com fundamentos.
                                            """)
                                
                                else:
                                    st.warning("""
                                    **ℹ️ Informações Adicionais Necessárias:**
                                    - Para análise completa, é necessário o número de ações em circulação
                                    - Considere também: crescimento futuro, perspectivas do setor, concorrência
                                    """)
                            
                            else:
                                st.warning("Não foi possível calcular o valuation. Lucro Econômico inválido ou negativo.")
                        else:
                            st.warning("Dados de Lucro Econômico não disponíveis para cálculo do valuation.")
                    
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
                                    "Valor": formatar_percentual_brasil(valor, 2),
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
                                    "Valor": formatar_percentual_brasil(valor, 2),
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
                                lucro_data.append({
                                    "Indicador": col,
                                    "Valor": formatar_moeda_brasil_correta(valor),
                                    "Status": "✓"
                                })
                            else:
                                lucro_data.append({
                                    "Indicador": f"{col}*",
                                    "Valor": "Não calculado",
                                    "Status": "✗"
                                })
                    
                    if lucro_data:
                        lucro_df = pd.DataFrame(lucro_data)
                        st.dataframe(lucro_df[["Indicador", "Valor"]], use_container_width=True, hide_index=True)
                    else:
                        st.warning("Não há dados de lucro econômico disponíveis")
                
                with tab6:
                    # NOVA ABA: FLUXO DE CAIXA OPERACIONAL
                    st.subheader("💵 Fluxo de Caixa Operacional")
                    
                    if 'Caixa Líquido Atividades Operacionais' in df_filtrado.columns:
                        valor_caixa = df_filtrado['Caixa Líquido Atividades Operacionais'].iloc[0]
                        
                        if pd.notna(valor_caixa):
                            # KPI Principal
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Caixa Operacional", formatar_moeda_brasil_correta(valor_caixa))
                            
                            with col2:
                                # Comparação com Lucro Líquido
                                lucro_liquido = df_filtrado["Lucro/Prejuízo Consolidado do Período"].iloc[0] if pd.notna(df_filtrado["Lucro/Prejuízo Consolidado do Período"].iloc[0]) else 0
                                if lucro_liquido != 0:
                                    relacao_caixa_lucro = (valor_caixa / lucro_liquido) * 100
                                    st.metric("Caixa/Lucro", f"{relacao_caixa_lucro:.1f}%")
                            
                            with col3:
                                # Comparação com EBITDA
                                ebitda = df_filtrado["EBITDA"].iloc[0] if "EBITDA" in df_filtrado.columns and pd.notna(df_filtrado["EBITDA"].iloc[0]) else 0
                                if ebitda != 0:
                                    relacao_caixa_ebitda = (valor_caixa / ebitda) * 100
                                    st.metric("Caixa/EBITDA", f"{relacao_caixa_ebitda:.1f}%")
                            
                            # Análise Qualitativa
                            st.subheader("📊 Análise do Fluxo de Caixa")
                            
                            if valor_caixa > 0:
                                st.success("**✅ Geração Positiva de Caixa**")
                                st.write("A empresa está gerando caixa líquido positivo em suas atividades operacionais.")
                            else:
                                st.warning("**⚠️ Geração Negativa de Caixa**")
                                st.write("A empresa está consumindo caixa em suas atividades operacionais.")
                            
                            # Comparação com indicadores de rentabilidade
                            if lucro_liquido != 0:
                                if abs(relacao_caixa_lucro - 100) > 50:
                                    if relacao_caixa_lucro > 150:
                                        st.info("**💡 Caixa > Lucro:** A empresa gera mais caixa que lucro contábil, indicando boa qualidade do lucro.")
                                    elif relacao_caixa_lucro < 50:
                                        st.warning("**💡 Caixa < Lucro:** A empresa gera menos caixa que lucro contábil, pode indicar diferenças temporárias ou baixa qualidade do lucro.")
                            
                        else:
                            st.warning("Dados de Caixa Líquido de Atividades Operacionais não disponíveis para este ano")
                    else:
                        st.warning("Coluna 'Caixa Líquido Atividades Operacionais' não encontrada no dataset")
                
                with tab7:
                    st.subheader("Dados Financeiros Brutos")
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
                        "Empréstimos e Financiamentos - Não Circulante",
                        "Caixa Líquido Atividades Operacionais"  # ADICIONADO
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
                                dados_brutos[col] = formatar_moeda_brasil_correta(valor)
                            else:
                                dados_brutos[col] = "N/A"
                    
                    st.dataframe(pd.DataFrame.from_dict(dados_brutos, orient='index', columns=['Valor']), 
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
                        yaxis_tickformat=',.2%',
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
                        yaxis_tickformat=',.2%',
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
                        yaxis_tickformat=',.2%',
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
                        yaxis_tickformat=',.2%',
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
                        yaxis_title='Valor',
                        yaxis_tickformat=',.0f',
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
                        yaxis_title='Valor',
                        yaxis_tickformat=',.0f',
                        height=400,
                        showlegend=True
                    )
                    st.plotly_chart(fig_ebitda, use_container_width=True)
                
                # QUARTA LINHA - FLUXO DE CAIXA OPERACIONAL (NOVA SEÇÃO)
                st.subheader("💸 Evolução do Fluxo de Caixa Operacional")
                if 'Caixa Líquido Atividades Operacionais' in df_empresa_todos_anos.columns:
                    col7, col8 = st.columns(2)
                    
                    with col7:
                        # Caixa Líquido Atividades Operacionais
                        fig_caixa = px.line(df_empresa_todos_anos, x='Ano', y='Caixa Líquido Atividades Operacionais',
                                          title='Caixa Líquido de Atividades Operacionais')
                        fig_caixa.update_layout(
                            yaxis_title='Caixa Operacional',
                            yaxis_tickformat=',.0f',
                            height=400
                        )
                        st.plotly_chart(fig_caixa, use_container_width=True)
                    
                    with col8:
                        # Comparação Caixa vs Lucro Líquido
                        df_comparacao = df_empresa_todos_anos.copy()
                        df_comparacao = df_comparacao[df_comparacao['Caixa Líquido Atividades Operacionais'].notna() & 
                                                    df_comparacao['Lucro/Prejuízo Consolidado do Período'].notna()]
                        
                        if not df_comparacao.empty:
                            fig_comparacao = go.Figure()
                            
                            fig_comparacao.add_trace(go.Scatter(
                                x=df_comparacao['Ano'],
                                y=df_comparacao['Caixa Líquido Atividades Operacionais'],
                                mode='lines+markers',
                                name='Caixa Operacional',
                                line=dict(color='#27ae60', width=3),
                                marker=dict(size=8)
                            ))
                            
                            fig_comparacao.add_trace(go.Scatter(
                                x=df_comparacao['Ano'],
                                y=df_comparacao['Lucro/Prejuízo Consolidado do Período'],
                                mode='lines+markers',
                                name='Lucro Líquido',
                                line=dict(color='#e74c3c', width=3),
                                marker=dict(size=8)
                            ))
                            
                            fig_comparacao.update_layout(
                                title='Comparação: Caixa Operacional vs Lucro Líquido',
                                xaxis_title='Ano',
                                yaxis_title='Valor',
                                yaxis_tickformat=',.0f',
                                height=400,
                                showlegend=True
                            )
                            st.plotly_chart(fig_comparacao, use_container_width=True)
                
                # Tabela resumo da evolução - INCLUINDO CAIXA OPERACIONAL
                st.subheader("📋 Resumo da Evolução - Principais Indicadores")
                
                # Selecionar indicadores chave para a tabela - ADICIONANDO CAIXA OPERACIONAL
                indicadores_resumo = ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio', 
                                    'Lucro Econômico 1', 'Resultado Antes do Resultado Financeiro e dos Tributos', 'EBITDA',
                                    'Caixa Líquido Atividades Operacionais']  # ADICIONADO
                df_resumo = df_empresa_todos_anos[['Ano'] + [col for col in indicadores_resumo if col in df_empresa_todos_anos.columns]]
                
                # Formatar para porcentagem e valores monetários - ATUALIZADO PARA INCLUIR CAIXA
                def formatar_valor(valor, coluna):
                    if coluna in ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio']:
                        return formatar_percentual_brasil(valor, 2) if pd.notna(valor) else "N/A"
                    elif coluna in ['Lucro Econômico 1', 'Resultado Antes do Resultado Financeiro e dos Tributos', 'EBITDA', 'Caixa Líquido Atividades Operacionais']:
                        return formatar_moeda_brasil_correta(valor) if pd.notna(valor) else "N/A"
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
        
        with tab_dividendos:
            st.subheader("💰 Histórico de Dividendos")
            
            # Buscar dividendos ATÉ A DATA ATUAL
            with st.spinner("Buscando dados de dividendos..."):
                df_dividendos = buscar_dividendos_historicos(ticker_selecionado)
            
            if df_dividendos is not None and not df_dividendos.empty:
                # Estatísticas rápidas
                stats = calcular_estatisticas_dividendos(df_dividendos)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Último Dividendo", 
                        f"R$ {stats['ultimo_dividendo']:.4f}".replace(".", ","),
                        help=f"Data: {stats['data_ultimo'].strftime('%d/%m/%Y') if stats['data_ultimo'] else 'N/A'}"
                    )
                
                with col2:
                    st.metric(
                        "Total Distribuído", 
                        formatar_moeda_brasil_correta(stats['total_dividendos'] * 1000),  # Converter para R$
                        help="Soma histórica de dividendos"
                    )
                
                with col3:
                    st.metric(
                        "Média Anual", 
                        formatar_moeda_brasil_correta(stats['media_anual'] * 1000),
                        help="Média de dividendos por ano"
                    )
                
                with col4:
                    st.metric(
                        "Frequência/Ano", 
                        f"{stats['frequencia_media']:.1f}",
                        help="Pagamentos médios por ano"
                    )
                
                # Gráfico de dividendos ao longo do tempo
                                    fig_dividendos = px.bar(
                        df_dividendos_ano, 
                        x="Ano", 
                        y="Dividendo", 
                        title="📈 Evolução dos Dividendos"
                    )
                    fig_dividendos.update_layout(
                        yaxis_title="Dividendos (R$)",
                        yaxis_tickprefix="R$ ",
                        yaxis_tickformat=", .2f"
                    )
                    st.plotly_chart(fig_dividendos, use_container_width=True)

                
                # CORREÇÃO ADICIONAL: Formatar os ticks do eixo Y manualmente para usar vírgula
                # Isso é necessário porque o plotly não suporta diretamente a substituição do ponto por vírgula
                # Vamos atualizar os textos dos ticks para substituir ponto por vírgula
                fig_dividendos.update_yaxes(
                    tickformat=".4f",
                    ticktext=[f"{y:.4f}".replace('.', ',') for y in fig_dividendos.data[0].y]
                )
                
                st.plotly_chart(fig_dividendos, use_container_width=True)
                
                # Dividendos por ano
                st.subheader("📊 Dividendos por Ano")
                dividendos_ano = df_dividendos.groupby('Ano')['Dividendo'].sum().reset_index()
                dividendos_ano['Dividendo Total'] = dividendos_ano['Dividendo']
                
                fig_ano = px.bar(
                    dividendos_ano,
                    x='Ano',
                    y='Dividendo Total',
                    title='Total de Dividendos por Ano'
                )
                fig_ano.update_layout(
                    height=400,
                    yaxis=dict(
                        tickformat=",.2f",  # 2 casas decimais para totais anuais
                        title='Dividendos (R$)'
                    )
                )
                st.plotly_chart(fig_ano, use_container_width=True)
                
                # Tabela detalhada
                st.subheader("📋 Detalhamento dos Dividendos")
                
                # Formatar a tabela
                df_display = df_dividendos.copy()
                df_display['Dividendo'] = df_display['Dividendo'].apply(
                    lambda x: f"R$ {x:.4f}".replace(".", ",")
                )
                df_display['Data'] = df_display['Data'].dt.strftime('%d/%m/%Y')  # Formato brasileiro
                df_display = df_display[['Data', 'Dividendo', 'Ano']].sort_values('Data', ascending=False)
                
                st.dataframe(df_display, use_container_width=True)
                
                # Análise de yield (se tivermos cotação)
                st.subheader("🎯 Análise de Dividend Yield")
                
                # Buscar cotação atual para cálculo do yield
                dados_cotacao = buscar_cotacao_atual(ticker_selecionado)
                
                if dados_cotacao and stats['ultimo_dividendo'] > 0:
                    cotacao_atual = dados_cotacao['cotacao']
                    
                    # Calcular dividend yield baseado no último dividendo
                    dy_ultimo = (stats['ultimo_dividendo'] / cotacao_atual) * 100
                    
                    # Calcular dividend yield médio anual
                    dy_medio = (stats['media_anual'] / cotacao_atual) * 100
                    
                    col_dy1, col_dy2, col_dy3 = st.columns(3)
                    
                    with col_dy1:
                        st.metric(
                            "Dividend Yield (Último)",
                            f"{dy_ultimo:.2f}%",
                            help="Baseado no último dividendo e cotação atual"
                        )
                    
                    with col_dy2:
                        st.metric(
                            "Dividend Yield (Médio)",
                            f"{dy_medio:.2f}%",
                            help="Baseado na média anual de dividendos"
                        )
                    
                    with col_dy3:
                        st.metric(
                            "Cotação Atual",
                            f"R$ {cotacao_atual:.2f}".replace(".", ",")
                        )
                    
                    # Análise qualitativa do yield
                    st.write("**💡 Análise do Dividend Yield:**")
                    if dy_ultimo > 6:
                        st.success("**✅ Yield Alto:** Acima de 6% ao ano - potencialmente atrativo para investidores de renda")
                    elif dy_ultimo > 3:
                        st.info("**🟡 Yield Moderado:** Entre 3% e 6% ao ano - dentro da média do mercado")
                    else:
                        st.warning("**🔴 Yield Baixo:** Abaixo de 3% ao ano - foco pode ser mais no crescimento que na renda")
                
            else:
                st.warning(f"""
                **ℹ️ Dados de Dividendos Não Encontrados**
                
                Não foi possível recuperar o histórico de dividendos para {ticker_selecionado}.
                
                Possíveis razões:
                - A empresa não distribui dividendos regularmente
                - O ticker pode estar com formato diferente
                - Limitações temporárias na API do Yahoo Finance
                - A empresa pode ser recente no mercado
                """)
        
        with tab_simulacao:
            st.subheader("💵 Simulação de Investimento")
            st.write("**Simule um investimento de R$ 1.000,00 desde uma data específica até hoje**")
            
            # Configuração da simulação
            col1, col2 = st.columns(2)
            
            with col1:
                # CORREÇÃO: Usar formato brasileiro explicitamente
                data_inicio = st.date_input(
                    "Data do investimento inicial",
                    min_value=datetime(2010, 1, 1),
                    max_value=datetime.now(),
                    value=datetime(2015, 1, 1),
                    format="DD/MM/YYYY",  # FORÇAR FORMATO BRASILEIRO
                    help="Data em que o investimento de R$ 1.000,00 seria feito (formato DD/MM/AAAA)"
                )
            
            with col2:
                valor_investido = st.number_input(
                    "Valor investido (R$)",
                    min_value=100,
                    value=1000,
                    step=100,
                    help="Valor inicial do investimento"
                )
            
            if st.button("🎯 Calcular Simulação", type="primary"):
                with st.spinner("Calculando resultado do investimento..."):
                    resultado = simular_investimento(ticker_selecionado, data_inicio, valor_investido)
                
                if resultado:
                    st.success("Simulação concluída!")
                    
                    # Métricas principais
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Valor Investido", 
                            formatar_moeda_brasil_correta(valor_investido / 1000),
                            help="Valor inicial do investimento"
                        )
                    
                    with col2:
                        st.metric(
                            "Valor Atual da Posição", 
                            formatar_moeda_brasil_correta(resultado['valor_investido_atual'] / 1000),
                            delta=f"{resultado['rentabilidade_preco_percentual']:+.2f}%",
                            help="Valor atual das ações (sem considerar dividendos)"
                        )
                    
                    with col3:
                        st.metric(
                            "Total em Dividendos", 
                            formatar_moeda_brasil_correta(resultado['total_dividendos_recebidos'] / 1000),
                            delta=f"{resultado['rentabilidade_dividendos_percentual']:+.2f}%",
                            help="Total de dividendos recebidos no período"
                        )
                    
                    with col4:
                        st.metric(
                            "Retorno Total", 
                            formatar_moeda_brasil_correta(resultado['ganho_total'] / 1000),
                            delta=f"{resultado['rentabilidade_total_percentual']:+.2f}%",
                            help="Soma da valorização + dividendos"
                        )
                    
                    # Detalhamento da simulação
                    st.subheader("📊 Detalhamento da Simulação")
                    
                    col_det1, col_det2 = st.columns(2)
                    
                    with col_det1:
                        st.write("**📈 Informações da Compra:**")
                        st.write(f"- **Data da compra:** {resultado['data_compra'].strftime('%d/%m/%Y')}")  # Formato brasileiro
                        st.write(f"- **Preço de compra:** R$ {resultado['preco_compra']:.2f}".replace(".", ","))
                        st.write(f"- **Quantidade de ações:** {resultado['quantidade_acoes']:.2f}")
                        st.write(f"- **Valor investido:** {formatar_moeda_brasil_correta(valor_investido / 1000)}")
                    
                    with col_det2:
                        st.write("**💰 Situação Atual:**")
                        st.write(f"- **Preço atual:** R$ {resultado['preco_atual']:.2f}".replace(".", ","))
                        st.write(f"- **Valor das ações hoje:** {formatar_moeda_brasil_correta(resultado['valor_investido_atual'] / 1000)}")
                        st.write(f"- **Total em dividendos:** {formatar_moeda_brasil_correta(resultado['total_dividendos_recebidos'] / 1000)}")
                        st.write(f"- **Retorno total:** {formatar_moeda_brasil_correta(resultado['ganho_total'] / 1000)}")
                    
                    # Análise qualitativa
                    st.subheader("💡 Análise do Investimento")
                    
                    if resultado['rentabilidade_total_percentual'] > 0:
                        if resultado['rentabilidade_total_percentual'] > 100:
                            st.success(f"""
                            **🎉 Excelente Investimento!**
                            
                            Se você tivesse investido **{formatar_moeda_brasil_correta(valor_investido / 1000)}** em {ticker_selecionado} em {data_inicio.strftime('%d/%m/%Y')}:
                            
                            - 🔥 **Seu investimento teria mais que DOBRADO**
                            - 💰 **Valor total hoje:** {formatar_moeda_brasil_correta((valor_investido + resultado['ganho_total']) / 1000)}
                            - 📈 **Retorno total:** {resultado['rentabilidade_total_percentual']:.2f}%
                            - 🎯 **Isso equivale a** {resultado['rentabilidade_total_percentual']/12:.2f}% ao ano em média
                            """)
                        else:
                            st.success(f"""
                            **✅ Bom Investimento!**
                            
                            Se você tivesse investido **{formatar_moeda_brasil_correta(valor_investido / 1000)}** em {ticker_selecionado} em {data_inicio.strftime('%d/%m/%Y')}:
                            
                            - 💰 **Valor total hoje:** {formatar_moeda_brasil_correta((valor_investido + resultado['ganho_total']) / 1000)}
                            - 📈 **Retorno total:** {resultado['rentabilidade_total_percentual']:.2f}%
                            - 🎯 **Isso equivale a** {resultado['rentabilidade_total_percentual']/12:.2f}% ao ano em média
                            """)
                    else:
                        st.warning(f"""
                        **⚠️ Investimento com Prejuízo**
                        
                        Se você tivesse investido **{formatar_moeda_brasil_correta(valor_investido / 1000)}** em {ticker_selecionado} em {data_inicio.strftime('%d/%m/%Y')}:
                        
                        - 💸 **Valor total hoje:** {formatar_moeda_brasil_correta((valor_investido + resultado['ganho_total']) / 1000)}
                        - 📉 **Prejuízo total:** {resultado['rentabilidade_total_percentual']:.2f}%
                        - ⏳ **Isso equivale a** {resultado['rentabilidade_total_percentual']/12:.2f}% ao ano em média
                        """)
                    
                    # Composição do retorno
                    st.subheader("📈 Composição do Retorno")
                    
                    fig_composicao = go.Figure()
                    
                    valores = [
                        resultado['ganho_preco'],
                        resultado['total_dividendos_recebidos']
                    ]
                    nomes = ['Valorização do Preço', 'Dividendos Recebidos']
                    cores = ['#2ecc71', '#3498db']
                    
                    fig_composicao.add_trace(go.Pie(
                        labels=nomes,
                        values=valores,
                        hole=.3,
                        marker=dict(colors=cores)
                    ))
                    
                    fig_composicao.update_layout(
                        title='Composição do Ganho Total',
                        height=400
                    )
                    
                    st.plotly_chart(fig_composicao, use_container_width=True)
                    
                    st.info(f"""
                    **📊 Resumo da Composição:**
                    
                    - **Valorização do preço:** {formatar_moeda_brasil_correta(resultado['ganho_preco'] / 1000)} ({resultado['rentabilidade_preco_percentual']:.2f}%)
                    - **Dividendos recebidos:** {formatar_moeda_brasil_correta(resultado['total_dividendos_recebidos'] / 1000)} ({resultado['rentabilidade_dividendos_percentual']:.2f}%)
                    - **Retorno total:** {formatar_moeda_brasil_correta(resultado['ganho_total'] / 1000)} ({resultado['rentabilidade_total_percentual']:.2f}%)
                    
                    **💡 Interpretação:**
                    - A **valorização do preço** reflete o crescimento (ou queda) no valor das ações
                    - Os **dividendos** representam a distribuição de lucros aos acionistas
                    - O **retorno total** é a soma desses dois componentes
                    """)
                
                else:
                    st.error("""
                    **❌ Não foi possível realizar a simulação**
                    
                    Possíveis razões:
                    - Dados históricos insuficientes para o período selecionado
                    - Ticker não encontrado ou sem dados de preços
                    - Erro na conexão com a API do Yahoo Finance
                    
                    Tente selecionar uma data mais recente ou verificar o ticker.
                    """)

# ==============================
# TELA - ANÁLISE SETORIAL (ESCALAS CORRIGIDAS)
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    st.header(f"🏭 Análise Setorial - {setor_selecionado}")
    
    if not df_setor_todos_anos.empty:
        # Abas para análise atual vs evolução temporal
        tab_atual_setor, tab_evolucao_setor = st.tabs(["📊 Análise do Ano", "📈 Evolução Temporal"])
        
        with tab_atual_setor:
            st.subheader(f"Ano {ano_selecionado}")
            
            if not df_filtrado.empty:
                # KPIs do Setor - ESCALAS CORRIGIDAS
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    empresas_setor = df_filtrado["Ticker"].nunique()
                    st.metric("Empresas no Setor", empresas_setor)
                
                with col2:
                    receita_setor = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum()
                    st.metric("Receita Total", formatar_moeda_brasil_correta(receita_setor, 2))
                
                with col3:
                    lucro_setor = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum()
                    st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_setor, 2))
                
                with col4:
                    pl_setor = df_filtrado["Patrimônio Líquido Consolidado"].sum()
                    st.metric("Patrimônio Líquido", formatar_moeda_brasil_correta(pl_setor, 2))
                
                st.divider()
                
                # Top empresas do setor por ROE
                st.subheader("Top 10 Empresas do Setor por ROE")
                top_roe_setor = df_filtrado[df_filtrado["ROE"].notna()].nlargest(10, "ROE")[["Ticker", "ROE"]]
                
                if not top_roe_setor.empty:
                    fig_roe = px.bar(top_roe_setor, x="Ticker", y="ROE", 
                                   title="ROE por Empresa no Setor")
                    fig_roe.update_layout(yaxis_tickformat=',.2%')
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
                    fig_estrutura.update_layout(yaxis_tickformat=',.2%')
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
                    rentabilidade_formatado = formatar_dataframe_percentual(
                        rentabilidade_setor,
                        ['ROE', 'ROA', 'ROI', 'Margem Líquida']
                    )
                    st.dataframe(rentabilidade_formatado, use_container_width=True)
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
                        yaxis_tickformat=',.2%',
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
                        yaxis_tickformat=',.2%',
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
                            yaxis_title='Lucro Econômico',
                            yaxis_tickformat=',.0f',
                            height=400
                        )
                        st.plotly_chart(fig_setor_lucro, use_container_width=True)
                
                with col4:
                    # EBITDA médio do setor
                    if 'EBITDA' in df_setor_evolucao.columns:
                        fig_setor_ebitda = px.line(df_setor_evolucao, x='Ano', y='EBITDA',
                                                 title='EBITDA Médio do Setor (Mediana)')
                        fig_setor_ebitda.update_layout(
                            yaxis_title='EBITDA',
                            yaxis_tickformat=',.0f',
                            height=400
                        )
                        st.plotly_chart(fig_setor_ebitda, use_container_width=True)
                
                # Tabela resumo da evolução do setor
                st.subheader("📋 Resumo da Evolução do Setor - Principais Indicadores")
                
                # Formatar para porcentagem e valores monetários
                def formatar_valor_setor(valor, coluna):
                    if coluna in ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio']:
                        return formatar_percentual_brasil(valor, 2) if pd.notna(valor) else "N/A"
                    elif coluna in ['Lucro Econômico 1', 'EBITDA']:
                        return formatar_moeda_brasil_correta(valor) if pd.notna(valor) else "N/A"
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
                        fig_dispersao.update_layout(yaxis_tickformat=',.2%')
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
    "Valuation Lucro Econômico/SELIC": "Lucro Econômico ÷ (SELIC/100)",
    "Percentual Capital Terceiros": "(Passivo Circulante + Não Circulante) ÷ Total Passivo",
    "Percentual Capital Próprio": "Patrimônio Líquido ÷ Total Passivo",
    "Caixa Líquido Atividades Operacionais": "Fluxo de caixa gerado/consumido pelas atividades operacionais"
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

    **Valuation Lucro Econômico/SELIC (CORRIGIDO):**
    - **FÓRMULA CORRETA:** Valor da Empresa = Lucro Econômico ÷ (SELIC/100)
    - **CONVERSÃO:** Valor em R$ mil convertido para R$ normais (×1000)
    - **COTAÇÃO ESPERADA:** Valor da Empresa (R$) ÷ Número de Ações
    - **COTAÇÃO:** Busca em tempo real via Yahoo Finance
    - **ANÁLISE:** Comparação entre valuation calculado e cotação de mercado

    **Novas Funcionalidades:**
    - **FLUXO DE CAIXA OPERACIONAL:** Adicionada análise do Caixa Líquido de Atividades Operacionais
    - **COMPARAÇÃO:** Caixa Operacional vs Lucro Líquido para análise de qualidade do lucro
    - **EVOLUÇÃO TEMPORAL:** Gráficos de fluxo de caixa na análise histórica
    - **DIVIDENDOS:** Histórico de dividendos e análise de dividend yield
    - **SIMULAÇÃO DE INVESTIMENTO:** Simulação de R$ 1.000,00 desde data específica

    **Dataset: dff_2010_2024**
    - Período: 2010-2024 (15 anos)
    - Empresas: 253 únicas
    - Tickers: 317 únicos
    - Setores: 43 categorias
    - **ESCALA DOS VALORES NO DATASET:** R$ mil
    - **NÚMERO DE AÇÕES:** Disponível apenas para 2024
    """)
