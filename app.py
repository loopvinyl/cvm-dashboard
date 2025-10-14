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
from datetime import datetime, timedelta, date # Importa 'date' para lidar com st.date_input
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
    CORRIGIDA: compatibilidade de timezone e tipos de data
    """
    try:
        # Buscar histórico de preços
        historico = buscar_historico_precos(ticker, "max")
        if historico is None:
            return None
        
        # Buscar dividendos
        dividendos = buscar_dividendos_historicos(ticker)
        
        # Converter data_inicio para datetime (sem timezone)
        # CORREÇÃO: Garante que data_inicio é um objeto datetime.datetime para comparação
        # com o índice datetime64[ns] do Pandas (o st.date_input retorna datetime.date)
        if isinstance(data_inicio, str):
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        elif data_inicio is not None and isinstance(data_inicio, date) and not isinstance(data_inicio, datetime):
            # Se for datetime.date (de st.date_input), converte para datetime.datetime
            data_inicio = datetime.combine(data_inicio, datetime.min.time())
            
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
        st.subheader("💰 Top 10 Pagadores de Dividendos")
        st.caption("Ranking baseado no Dividend Yield (últimos 12 meses)")
        
        # Obtém a lista de Tickers no ano filtrado
        tickers_para_rank = df_filtrado['Ticker'].unique()
        
        # Aumentar limite para 50 empresas para ranking
        tickers_analisar = tickers_para_rank[:50]
        
        # Calcula o Dividend Yield para cada Ticker
        dy_results = []
        st.info(f"Buscando Dividend Yield para {len(tickers_analisar)} empresas...")
        dy_progress = st.progress(0)
        
        for i, ticker in enumerate(tickers_analisar):
            try:
                dy = calcular_dividend_yield(ticker)
                if dy is not None and dy > 0:
                    # Busca o setor para exibir no ranking
                    # Tenta buscar setor do df, se não achar, busca na cotação
                    df_setor = df_filtrado[df_filtrado['Ticker'] == ticker]['SETOR_ATIV']
                    setor = df_setor.iloc[0] if not df_setor.empty else "N/A"
                    
                    dados_cotacao = buscar_cotacao_atual(ticker)
                    cotacao = dados_cotacao['cotacao'] if dados_cotacao else np.nan
                    
                    # Se o setor estiver N/A, tenta buscar na cotação
                    if setor == "N/A" and dados_cotacao:
                        setor = dados_cotacao.get('setor', 'N/A')
                    
                    dy_results.append({
                        'Ticker': ticker, 
                        'SETOR_ATIV': setor, 
                        'Dividend Yield': dy,
                        'Cotação Atual': cotacao
                    })
            except:
                pass # Ignora erros
            dy_progress.progress((i + 1) / len(tickers_analisar))
        
        dy_progress.empty() # Remove a barra de progresso após o cálculo

        df_dy_ranking = pd.DataFrame(dy_results)
        
        if not df_dy_ranking.empty:
            df_dy_ranking = df_dy_ranking.nlargest(10, 'Dividend Yield')

            # Criação do gráfico
            fig_dy_rank = px.bar(df_dy_ranking, x='Ticker', y='Dividend Yield', color='SETOR_ATIV',
                                title='Ranking de Dividend Yield (Últimos 12 meses)')
            
            # Formatação do eixo Y no padrão brasileiro de porcentagem
            fig_dy_rank.update_layout(yaxis_tickformat=',.2%') 
            
            st.plotly_chart(fig_dy_rank, use_container_width=True)
            
            # Tabela formatada
            df_dy_display = df_dy_ranking.copy()
            df_dy_display['Dividend Yield'] = df_dy_display['Dividend Yield'].apply(
                lambda x: formatar_percentual_brasil(x, 2)
            )
            df_dy_display['Cotação Atual'] = df_dy_display['Cotação Atual'].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else "R$ -"
            )
            st.dataframe(df_dy_display[['Ticker', 'SETOR_ATIV', 'Dividend Yield', 'Cotação Atual']], use_container_width=True)

        else:
            st.info("ℹ️ Não foi possível calcular dividend yields para as empresas selecionadas ou os dados são insuficientes.")

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
                        st.metric("ROE*", "-", help="ROE = Lucro Líquido ÷ PL Médio. Calculado apenas quando PL Médio > 0")
                
                with col2:
                    valor_roa = df_filtrado["ROA"].iloc[0]
                    if pd.notna(valor_roa):
                        st.metric("ROA", formatar_percentual_brasil(valor_roa, 2))
                    else:
                        st.metric("ROA*", "-", help="ROA = Resultado Operacional ÷ Ativo Médio. Calculado apenas quando Ativo Médio > 0")
                
                with col3:
                    valor_roi = df_filtrado["ROI"].iloc[0]
                    if pd.notna(valor_roi):
                        st.metric("ROI", formatar_percentual_brasil(valor_roi, 2))
                    else:
                        st.metric("ROI*", "-", help="ROI = Resultado Operacional ÷ Investimento Médio. Calculado apenas quando Investimento Médio > 0")
                
                with col4:
                    valor_wacc = df_filtrado["wacc"].iloc[0]
                    if pd.notna(valor_wacc):
                        st.metric("WACC", formatar_percentual_brasil(valor_wacc, 2))
                    else:
                        st.metric("WACC*", "-", help="WACC não pôde ser calculado devido a dados insuficientes")

                with col5:
                    # ADIÇÃO: Caixa Líquido Atividades Operacionais
                    if 'Caixa Líquido Atividades Operacionais' in df_filtrado.columns:
                        valor_caixa = df_filtrado['Caixa Líquido Atividades Operacionais'].iloc[0]
                        if pd.notna(valor_caixa):
                            st.metric("Caixa Operacional", formatar_moeda_brasil_correta(valor_caixa))
                        else:
                            st.metric("Caixa Operacional*", "N/A", help="Dados de caixa operacional não disponíveis")
                    else:
                        st.metric("Caixa Operacional*", "N/A", help="Coluna 'Caixa Líquido Atividades Operacionais' não encontrada no dataset")

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
                    else:
                        st.warning("⚠️ LUCRO ECONÔMICO 1 ≠ LUCRO ECONÔMICO 2 (Diferença acima da tolerância)")
                        
                    st.write(f"Lucro Econômico 1: {formatar_moeda_brasil_correta(lucro_eco1)}")
                    st.write(f"Lucro Econômico 2: {formatar_moeda_brasil_correta(lucro_eco2)}")
                    st.write(f"Diferença: {formatar_moeda_brasil_correta(diferenca)}")
                else:
                    st.info("Lucro Econômico não calculado por falta de dados (ROI ou WACC)")

                # VALUATION E COTAÇÃO
                st.subheader("💰 Valuation x Cotação Atual")
                cotacao_atual = buscar_cotacao_atual(ticker_selecionado)
                
                if pd.notna(lucro_eco1) and cotacao_atual and cotacao_atual.get('market_cap'):
                    # Lucro Econômico (em R$ mil)
                    lucro_eco_mil = (lucro_eco1 + lucro_eco2) / 2
                    
                    # Calcular Valor da Empresa (em R$ normais)
                    valor_empresa = calcular_valuation_lucro_economico_selic(lucro_eco_mil * 1000)
                    
                    # Calcular Market Cap atual (já em R$ normais, mas a API retorna em USD/BRL)
                    # Presumindo que o Market Cap retornado pelo yfinance para tickers .SA já é em BRL
                    market_cap_atual = cotacao_atual['market_cap']
                    
                    col_val1, col_val2, col_val3 = st.columns(3)
                    with col_val1:
                        st.metric("Market Cap Calculado (R$)", formatar_numero_brasil_correto(valor_empresa, 0))
                    with col_val2:
                        st.metric("Market Cap Atual (R$)", formatar_numero_brasil_correto(market_cap_atual, 0))
                    with col_val3:
                        # Cálculo da diferença percentual
                        if valor_empresa > 0:
                            diferenca_perc = (market_cap_atual / valor_empresa - 1) * 100
                            st.metric("Diferença", formatar_percentual_brasil(diferenca_perc / 100, 2), help="Positivo: Preço de mercado > Preço justo. Negativo: Preço de mercado < Preço justo.")
                        else:
                            st.metric("Diferença", "N/A")

                    st.info(f"Market Cap Calculado = Lucro Econômico (R$) ÷ (SELIC/100). Usando SELIC de 15% (taxa de desconto proxy).")
                elif not cotacao_atual:
                    st.warning(f"⚠️ Não foi possível obter cotação atual para {ticker_selecionado}.SA (Yahoo Finance).")
                else:
                    st.info("Valuation não calculado por falta de Lucro Econômico ou Market Cap.")

                st.subheader("📋 Tabela Consolidada de Indicadores")
                colunas_display = ["Ticker", "Ano", "ROE", "ROA", "ROI", "Margem Líquida", "wacc", "Lucro Econômico 1", "EBITDA"]
                tabela = df_filtrado[colunas_display]
                
                # Formatação
                tabela['ROE'] = tabela['ROE'].apply(lambda x: formatar_percentual_brasil(x))
                tabela['ROA'] = tabela['ROA'].apply(lambda x: formatar_percentual_brasil(x))
                tabela['ROI'] = tabela['ROI'].apply(lambda x: formatar_percentual_brasil(x))
                tabela['Margem Líquida'] = tabela['Margem Líquida'].apply(lambda x: formatar_percentual_brasil(x))
                tabela['wacc'] = tabela['wacc'].apply(lambda x: formatar_percentual_brasil(x))
                tabela['Lucro Econômico 1'] = tabela['Lucro Econômico 1'].apply(lambda x: formatar_moeda_brasil_correta(x))
                tabela['EBITDA'] = tabela['EBITDA'].apply(lambda x: formatar_moeda_brasil_correta(x))
                
                st.dataframe(tabela.set_index('Ticker'), use_container_width=True)

            else:
                st.info(f"Não há dados disponíveis para o Ticker {ticker_selecionado} no ano {ano_selecionado}.")

        with tab_evolucao:
            st.subheader("📈 Evolução dos Indicadores (2010 - Hoje)")
            
            # Gráfico 1: Rentabilidade
            fig_rentabilidade = px.line(
                df_empresa_todos_anos, 
                x='Ano', 
                y=['ROE', 'ROA', 'ROI'], 
                title='Evolução de Rentabilidade (ROE, ROA, ROI)'
            )
            fig_rentabilidade.update_layout(yaxis_tickformat=',.2%') # Formato de porcentagem brasileira
            st.plotly_chart(fig_rentabilidade, use_container_width=True)

            # Gráfico 2: Lucro Econômico
            fig_lucro_eco = px.bar(
                df_empresa_todos_anos,
                x='Ano',
                y=['Lucro Econômico 1', 'Lucro Econômico 2'],
                title='Evolução do Lucro Econômico'
            )
            fig_lucro_eco.update_layout(yaxis_tickformat=',.2f') # Formato de número com vírgula decimal
            st.plotly_chart(fig_lucro_eco, use_container_width=True)

            # Gráfico 3: Margens
            fig_margens = px.line(
                df_empresa_todos_anos,
                x='Ano',
                y=['Margem Líquida', 'Margem Operacional'],
                title='Evolução das Margens'
            )
            fig_margens.update_layout(yaxis_tickformat=',.2%') # Formato de porcentagem brasileira
            st.plotly_chart(fig_margens, use_container_width=True)

            # Gráfico 4: WACC
            fig_wacc = px.line(
                df_empresa_todos_anos,
                x='Ano',
                y='wacc',
                title='Evolução do Custo Médio Ponderado de Capital (WACC)'
            )
            fig_wacc.update_layout(yaxis_tickformat=',.2%') # Formato de porcentagem brasileira
            st.plotly_chart(fig_wacc, use_container_width=True)
            
            # Gráfico 5: Fluxo de Caixa (se a coluna existir)
            if 'Caixa Líquido Atividades Operacionais' in df_empresa_todos_anos.columns:
                fig_caixa = px.bar(
                    df_empresa_todos_anos,
                    x='Ano',
                    y=['Caixa Líquido Atividades Operacionais', 'Lucro/Prejuízo Consolidado do Período'],
                    title='Caixa Operacional vs Lucro Líquido'
                )
                fig_caixa.update_layout(yaxis_tickformat=',.2f') # Formato de número com vírgula decimal
                st.plotly_chart(fig_caixa, use_container_width=True)


        with tab_dividendos:
            st.subheader("💰 Histórico de Dividendos")
            df_dividendos = buscar_dividendos_historicos(ticker_selecionado)
            
            if df_dividendos is not None and not df_dividendos.empty:
                stats = calcular_estatisticas_dividendos(df_dividendos)
                
                # KPIs de Dividendos
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    # Usar valor real, não em R$ mil (multiplicar por 1)
                    st.metric("Último Dividendo", f"R$ {stats['ultimo_dividendo']:,.4f}".replace(",", "X").replace(".", ",").replace("X", "."))
                with col2:
                    # Total Distribuído (em R$ mil, usando formatador de escala)
                    st.metric("Total Distribuído", formatar_moeda_brasil_correta(df_empresa_todos_anos['Pagamento de Dividendos'].sum(), 2))
                with col3:
                    st.metric("Média Anual", f"R$ {stats['media_anual']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                with col4:
                    st.metric("Frequência/Ano", f"{stats['frequencia_media']:.1f}")

                st.divider()

                st.subheader("📈 Evolução dos Dividendos")
                df_dividendos_ano = df_dividendos.groupby('Ano')['Dividendo'].sum().reset_index()
                df_dividendos_ano.columns = ['Ano', 'Dividendo']
                
                fig_dividendos = px.bar(
                    df_dividendos_ano, 
                    x='Ano', 
                    y='Dividendo', 
                    title='Evolução dos Dividendos por Ano'
                )
                # CORREÇÃO DE FORMATAÇÃO DO EIXO Y (Solicitação inicial)
                fig_dividendos.update_layout(
                    height=500,
                    yaxis_title="Dividendos (R$)", # Título claro
                    yaxis_tickprefix="R$ ",
                    yaxis_tickformat=", .2f" # Formato brasileiro: vírgula decimal, 2 casas
                )
                st.plotly_chart(fig_dividendos, use_container_width=True)

                # Tabela detalhada
                st.subheader("📆 Detalhe por Pagamento")
                df_display = df_dividendos.copy()
                df_display['Data'] = df_display['Data'].dt.strftime('%d/%m/%Y')
                df_display['Dividendo (R$)'] = df_display['Dividendo'].apply(
                    lambda x: f"R$ {x:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                st.dataframe(df_display[['Data', 'Dividendo (R$)', 'Ano']], use_container_width=True)
                
            else:
                st.info(f"Não há dados de dividendos disponíveis para {ticker_selecionado} no Yahoo Finance desde 2010.")


        with tab_simulacao:
            st.subheader("💵 Simulação de Investimento")
            st.write("Simule um investimento de R$ 1.000,00 desde uma data específica até hoje")
            
            # Inputs para simulação
            col_sim1, col_sim2 = st.columns(2)
            
            with col_sim1:
                data_minima = datetime(2010, 1, 1).date()
                data_investimento = st.date_input(
                    "Data do investimento inicial", 
                    value=data_minima, 
                    min_value=data_minima,
                    max_value=datetime.now().date()
                )
            
            with col_sim2:
                valor_investido = st.number_input("Valor investido (R$)", min_value=10.0, value=1000.0, step=100.0)
            
            if data_investimento and valor_investido > 0:
                # Realiza a simulação
                resultados = simular_investimento(ticker_selecionado, data_investimento, valor_investido)
                
                if resultados:
                    st.success("✅ Simulação realizada com sucesso!")
                    st.caption(f"Dados usados a partir da primeira cotação disponível após {data_investimento.strftime('%d/%m/%Y')}: {resultados['data_compra'].strftime('%d/%m/%Y')} (Preço: R$ {resultados['preco_compra']:,.2f})")
                    st.write(f"**Quantidade de Ações Compradas:** {resultados['quantidade_acoes']:,.4f}")
                    
                    st.subheader("Resultados:")
                    col_res1, col_res2, col_res3 = st.columns(3)
                    
                    with col_res1:
                        st.metric("Valor Atual do Investimento", f"R$ {resultados['valor_investido_atual']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                        st.metric("Ganho de Capital", f"R$ {resultados['ganho_preco']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                        st.metric("Rentabilidade (Preço)", formatar_percentual_brasil(resultados['rentabilidade_preco_percentual'] / 100, 2))
                    
                    with col_res2:
                        st.metric("Dividendos Recebidos", f"R$ {resultados['total_dividendos_recebidos']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                        st.metric("Ganho Total (Capital + Dividendos)", f"R$ {resultados['ganho_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                        st.metric("Rentabilidade (Dividendos)", formatar_percentual_brasil(resultados['rentabilidade_dividendos_percentual'] / 100, 2))
                        
                    with col_res3:
                        st.metric("Rentabilidade Total", formatar_percentual_brasil(resultados['rentabilidade_total_percentual'] / 100, 2))
                    
                else:
                    st.warning("❌ Não foi possível realizar a simulação")
                    st.info("""
                    Possíveis razões:
                    - Dados históricos insuficientes para o período selecionado
                    - Ticker não encontrado ou sem dados de preços
                    - Erro na conexão com a API do Yahoo Finance
                    Tente selecionar uma data mais recente ou verificar o ticker.
                    """)
            else:
                st.info("Insira a data e o valor para iniciar a simulação.")
    
    else:
        st.info("Selecione uma empresa e um ano para iniciar a análise.")


# ==============================
# TELA - ANÁLISE SETORIAL (ESCALAS CORRIGIDAS)
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    st.header(f"🏭 Análise Setorial - {setor_selecionado}")
    
    if not df_filtrado.empty:
        # KPIs Setoriais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Empresas no Setor", df_filtrado["Ticker"].nunique())
        
        with col2:
            roe_medio = df_filtrado["ROE"].mean()
            st.metric("ROE Médio", formatar_percentual_brasil(roe_medio, 2))
        
        with col3:
            receita_total = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum()
            st.metric("Receita Total", formatar_moeda_brasil_correta(receita_total, 2))
        
        with col4:
            lucro_total = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum()
            st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_total, 2))

        st.divider()
        
        st.subheader(f"Comparativo de Rentabilidade - Ano {ano_selecionado}")
        
        # Gráfico comparativo ROE
        fig_roe_setor = px.bar(
            df_filtrado, 
            x='Ticker', 
            y='ROE', 
            color='Alavancagem Eficaz', 
            title=f'ROE por Empresa no Setor {setor_selecionado}'
        )
        fig_roe_setor.update_layout(yaxis_tickformat=',.2%')
        st.plotly_chart(fig_roe_setor, use_container_width=True)
        
        # Gráfico comparativo ROA/ROI
        fig_roa_roi_setor = px.bar(
            df_filtrado, 
            x='Ticker', 
            y=['ROA', 'ROI'], 
            title=f'ROA e ROI por Empresa no Setor {setor_selecionado}'
        )
        fig_roa_roi_setor.update_layout(yaxis_tickformat=',.2%')
        st.plotly_chart(fig_roa_roi_setor, use_container_width=True)

        st.subheader("Análise de Margens e Custo")
        
        # Gráfico comparativo Margem Líquida
        fig_margem_setor = px.bar(
            df_filtrado, 
            x='Ticker', 
            y=['Margem Líquida'], 
            title=f'Margem Líquida por Empresa no Setor {setor_selecionado}'
        )
        fig_margem_setor.update_layout(yaxis_tickformat=',.2%')
        st.plotly_chart(fig_margem_setor, use_container_width=True)

        # Gráfico comparativo WACC
        fig_wacc_setor = px.bar(
            df_filtrado, 
            x='Ticker', 
            y=['wacc'], 
            title=f'WACC por Empresa no Setor {setor_selecionado}'
        )
        fig_wacc_setor.update_layout(yaxis_tickformat=',.2%')
        st.plotly_chart(fig_wacc_setor, use_container_width=True)

        st.subheader("Tabela de Indicadores Setoriais")
        colunas_display_setor = ["Ticker", "ROE", "ROA", "ROI", "Margem Líquida", "wacc", "Lucro Econômico 1", "EBITDA"]
        tabela_setor = df_filtrado[colunas_display_setor]
        
        # Formatação
        tabela_setor['ROE'] = tabela_setor['ROE'].apply(lambda x: formatar_percentual_brasil(x))
        tabela_setor['ROA'] = tabela_setor['ROA'].apply(lambda x: formatar_percentual_brasil(x))
        tabela_setor['ROI'] = tabela_setor['ROI'].apply(lambda x: formatar_percentual_brasil(x))
        tabela_setor['Margem Líquida'] = tabela_setor['Margem Líquida'].apply(lambda x: formatar_percentual_brasil(x))
        tabela_setor['wacc'] = tabela_setor['wacc'].apply(lambda x: formatar_percentual_brasil(x))
        tabela_setor['Lucro Econômico 1'] = tabela_setor['Lucro Econômico 1'].apply(lambda x: formatar_moeda_brasil_correta(x))
        tabela_setor['EBITDA'] = tabela_setor['EBITDA'].apply(lambda x: formatar_moeda_brasil_correta(x))
        
        st.dataframe(tabela_setor.set_index('Ticker'), use_container_width=True)

    else:
        st.info(f"Não há dados disponíveis para o Setor {setor_selecionado} no ano {ano_selecionado}.")
