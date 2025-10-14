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

def simular_investimento_lotes(ticker, data_inicio, quantidade_acoes=100):
    """
    Simula um investimento por quantidade de ações (lotes)
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
        
        # Calcular valor investido baseado na quantidade de ações
        valor_investido = quantidade_acoes * preco_compra
        
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
            'valor_investido': valor_investido,
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
# NOVO: SISTEMA DE CACHE DE DIVIDENDOS
# ==============================
@st.cache_data(ttl=86400)  # Cache por 24 horas
def carregar_dados_dividendos_cache():
    """
    Carrega dados de dividendos de um arquivo CSV pré-processado
    ou busca via Yahoo Finance com fallback
    """
    try:
        # Tentar carregar arquivo local primeiro
        dividendos_paths = [
            "dividendos_historico.csv",
            "./data/dividendos_historico.csv",
            "/content/dividendos_historico.csv"
        ]
        
        for path in dividendos_paths:
            if os.path.exists(path):
                df_dividendos = pd.read_csv(path)
                df_dividendos['Data'] = pd.to_datetime(df_dividendos['Data'])
                return df_dividendos
                
        # Se não encontrou arquivo, retornar None
        return None
    except:
        return None

def calcular_dividend_yield_otimizado(ticker, df_dividendos_cache=None, periodo_anos=1):
    """
    Versão otimizada do cálculo de dividend yield
    """
    try:
        # Buscar cotação atual
        dados_cotacao = buscar_cotacao_atual(ticker)
        if not dados_cotacao:
            return None
            
        cotacao_atual = dados_cotacao['cotacao']
        
        # Tentar usar cache primeiro
        if df_dividendos_cache is not None:
            dividendos_ticker = df_dividendos_cache[df_dividendos_cache['Ticker'] == ticker]
            if not dividendos_ticker.empty:
                # Calcular dividendos dos últimos N anos
                data_limite = datetime.now() - timedelta(days=365 * periodo_anos)
                dividendos_periodo = dividendos_ticker[dividendos_ticker['Data'] >= data_limite]
                
                if not dividendos_periodo.empty:
                    total_dividendos = dividendos_periodo['Dividendo'].sum()
                    dividend_yield = (total_dividendos / cotacao_atual) * 100
                    return dividend_yield
        
        # Fallback: buscar via Yahoo Finance
        return calcular_dividend_yield(ticker)
        
    except Exception as e:
        return None

# ==============================
# NOVO: SISTEMA DE RANKING DE DIVIDENDOS FLEXÍVEL
# ==============================
def calcular_ranking_dividendos(df_filtrado, periodo_anos=1, limite_empresas=50):
    """
    Calcula ranking de dividendos com diferentes períodos
    """
    # Carregar cache de dividendos
    df_dividendos_cache = carregar_dados_dividendos_cache()
    
    tickers_unicos = df_filtrado['Ticker'].unique()
    tickers_analisar = tickers_unicos[:limite_empresas]
    
    dados_dy = []
    
    with st.spinner(f"Calculando dividend yields (últimos {periodo_anos} anos)..."):
        progress_bar = st.progress(0)
        for i, ticker in enumerate(tickers_analisar):
            try:
                dy = calcular_dividend_yield_otimizado(ticker, df_dividendos_cache, periodo_anos)
                if dy is not None and dy > 0:
                    dados_cotacao = buscar_cotacao_atual(ticker)
                    if dados_cotacao:
                        dados_dy.append({
                            'Ticker': ticker,
                            'Dividend Yield': dy,
                            'Cotação': dados_cotacao['cotacao'],
                            'Setor': dados_cotacao['setor'],
                            'Periodo_Anos': periodo_anos
                        })
            except:
                pass
            
            progress_bar.progress((i + 1) / len(tickers_analisar))
    
    return dados_dy

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
    
    # Abas para diferentes rankings - ADICIONANDO ABA DE DIVIDENDOS MELHORADA
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
        st.header("💰 Top Pagadores de Dividendos")
        
        # Controles para seleção de período
        col_periodo, col_lote = st.columns(2)
        with col_periodo:
            periodo_selecionado = st.selectbox(
                "Período de análise:",
                [1, 2, 3, 5, 10],
                index=0,
                format_func=lambda x: f"Últimos {x} anos"
            )
        with col_lote:
            limite_empresas = st.selectbox(
                "Número de empresas:",
                [30, 50, 100],
                index=0,
                format_func=lambda x: f"Top {x} empresas"
            )
            
        # Calcular ranking
        dados_dy = calcular_ranking_dividendos(df_filtrado, periodo_selecionado, limite_empresas)
        
        if dados_dy:
            # Criar DataFrame e ordenar
            df_dy = pd.DataFrame(dados_dy)
            df_dy = df_dy.nlargest(10, 'Dividend Yield')
            
            # Gráfico
            fig_dy = px.bar(
                df_dy,
                x='Ticker',
                y='Dividend Yield',
                color='Setor',
                title=f'Top 10 Empresas por Dividend Yield (Últimos {periodo_selecionado} anos)'
            )
            fig_dy.update_layout(
                yaxis_title='Dividend Yield (%)',
                yaxis_tickformat=',.2f',
                height=500
            )
            st.plotly_chart(fig_dy, use_container_width=True)
            
            # Tabela detalhada
            st.subheader("📊 Detalhamento do Ranking")
            df_dy_display = df_dy.copy()
            df_dy_display['Dividend Yield'] = df_dy_display['Dividend Yield'].apply(lambda x: f"{x:.2f}%")
            df_dy_display['Cotação'] = df_dy_display['Cotação'].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
            df_dy_display.columns = ['Ticker', 'Dividend Yield (Últimos Anos)', 'Cotação Atual', 'Setor', 'Período (Anos)']
            st.dataframe(df_dy_display[['Ticker', 'Setor', 'Dividend Yield (Últimos Anos)', 'Cotação Atual']], use_container_width=True)

# ==============================
# TELA PRINCIPAL - VISÃO POR EMPRESA
# ==============================
elif modo_analise == "📈 Visão por Empresa":
    if df_filtrado.empty:
        st.warning(f"Não há dados para o Ticker **{ticker_selecionado}** no ano de **{ano_selecionado}**.")
    else:
        dados_ano = df_filtrado.iloc[0]
        
        st.header(f"📈 Análise da Empresa: {ticker_selecionado} ({dados_ano['Denominação Social']})")
        st.subheader(f"Dados Consolidados: {dados_ano['Ano']}")
        
        # ==============================
        # BUSCAR COTAÇÃO E VALUATION
        # ==============================
        st.divider()
        st.subheader("Cotação, Dividendos e Valuation")
        
        dados_cotacao = buscar_cotacao_atual(ticker_selecionado)
        
        col_cot1, col_cot2, col_cot3, col_cot4 = st.columns(4)
        
        # Métrica 1: Cotação Atual
        if dados_cotacao:
            with col_cot1:
                st.metric(
                    "Cotação Atual", 
                    f"R$ {dados_cotacao['cotacao']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
            with col_cot2:
                # O Lucro Econômico 2 é o mais robusto (Resultado Operacional - Custo de Capital)
                lucro_economico_2 = dados_ano['Lucro Econômico 2']
                
                # Converter de R$ mil para R$ normais
                if pd.notna(lucro_economico_2):
                    lucro_economico_2_reais = lucro_economico_2 * 1000
                    
                    # Calcular Valuation (Fórmula CORRIGIDA: Lucro Econômico / (SELIC/100))
                    VALOR_EMPRESA_CALCULADO = calcular_valuation_lucro_economico_selic(lucro_economico_2_reais, selic_percentual=15)
                    
                    if VALOR_EMPRESA_CALCULADO and dados_ano["Nº de Ações"]:
                        
                        # CALCULAR COTAÇÃO JUSTA ESPERADA (Valuation / Número de Ações)
                        cotacao_esperada = VALOR_EMPRESA_CALCULADO / dados_ano["Nº de Ações"]
                        
                        # Métrica 2: Valuation
                        st.metric(
                            "Valuation (Cotação Justa)",
                            f"R$ {cotacao_esperada:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                            delta=f"{((cotacao_esperada - dados_cotacao['cotacao']) / dados_cotacao['cotacao']) * 100:.1f}%" if dados_cotacao['cotacao'] else None,
                            delta_color="normal"
                        )
                        with col_cot3:
                            # Métrica 3: Market Cap
                            st.metric(
                                "Market Cap",
                                formatar_moeda_brasil_correta(dados_cotacao['market_cap'] / 1000, 2) # Divisão por 1000 para entrar na função em R$ mil
                            )
                        with col_cot4:
                            # Métrica 4: Número de Ações
                            st.metric(
                                "Nº de Ações",
                                formatar_numero_brasil_correto(dados_ano["Nº de Ações"], 0)
                            )
                            
                        # Gráfico Comparativo
                        st.markdown("**Comparativo Cotação Atual vs. Valor Justo (Lucro Econômico/SELIC)**")
                        st.plotly_chart(criar_grafico_comparativo(cotacao_esperada, dados_cotacao['cotacao'], ticker_selecionado), use_container_width=True)
                    else:
                        st.warning("⚠️ Valuation não calculado: Lucro Econômico <= 0 ou Número de Ações Indisponível.")
                else:
                    st.warning("⚠️ Lucro Econômico não disponível para cálculo de Valuation.")
        else:
            st.warning("⚠️ Cotação atual da ação não encontrada.")
            
        # ==============================
        # DIVIDENDOS E SIMULAÇÃO
        # ==============================
        st.subheader("Histórico e Análise de Dividendos")
        
        # Seleção da data de início para simulação
        data_padrao_simulacao = datetime.now().year - 5
        data_min_historico = df_empresa_todos_anos['Ano'].min() if not df_empresa_todos_anos.empty else datetime.now().year - 10
        
        col_simulacao1, col_simulacao2 = st.columns([1, 3])
        
        with col_simulacao1:
            data_inicio_simulacao = st.date_input(
                "Data de Início da Simulação:",
                value=datetime(data_padrao_simulacao, 1, 1),
                min_value=datetime(data_min_historico, 1, 1) if data_min_historico < datetime.now().year else datetime.now() - timedelta(days=365*10)
            )
            quantidade_acoes = st.number_input("Quantidade de Ações (Lotes de 100):", value=100, min_value=1)
            
            # Buscar Dividend Yield 12m
            dy_12m = calcular_dividend_yield(ticker_selecionado)
            if dy_12m is not None:
                st.metric("Dividend Yield (12m)", formatar_percentual_brasil(dy_12m / 100, 2))
            else:
                st.info("Dividend Yield (12m) não disponível.")
                
        with col_simulacao2:
            simulacao_dados = simular_investimento_lotes(ticker_selecionado, data_inicio_simulacao, quantidade_acoes)
            
            if simulacao_dados:
                st.markdown(f"""
                **Simulação de Investimento:** {formatar_numero_brasil_correto(quantidade_acoes)} ações compradas em **{simulacao_dados['data_compra'].strftime('%d/%m/%Y')}**
                
                * **Valor Investido (Inicial):** {formatar_moeda_brasil_correta(simulacao_dados['valor_investido'] / 1000, 2)}
                * **Valor Atual (Patrimônio):** {formatar_moeda_brasil_correta(simulacao_dados['valor_investido_atual'] / 1000, 2)}
                * **Dividendos Recebidos:** {formatar_moeda_brasil_correta(simulacao_dados['total_dividendos_recebidos'] / 1000, 2)}
                * **Ganho Total (Preço + Div.):** {formatar_moeda_brasil_correta(simulacao_dados['ganho_total'] / 1000, 2)}
                
                **Rentabilidade Total:** {formatar_percentual_brasil(simulacao_dados['rentabilidade_total_percentual'] / 100, 2)}
                """)
                
                # Gráfico de pizza da rentabilidade
                rentabilidade_df = pd.DataFrame({
                    'Fator': ['Variação de Preço', 'Dividendos Recebidos'],
                    'Valor': [simulacao_dados['ganho_preco'], simulacao_dados['total_dividendos_recebidos']]
                })
                rentabilidade_df = rentabilidade_df[rentabilidade_df['Valor'] > 0] # Apenas ganhos positivos
                
                if not rentabilidade_df.empty:
                    fig_pizza = px.pie(rentabilidade_df, names='Fator', values='Valor',
                                       title='Composição do Ganho Total', 
                                       color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig_pizza, use_container_width=True)
                else:
                    st.info("Nenhum ganho registrado no período para análise de composição.")
            else:
                st.info("Não foi possível realizar a simulação de investimento ou encontrar histórico de preços/dividendos.")

        # Gráfico de Dividendos Anuais
        df_dividendos = buscar_dividendos_historicos(ticker_selecionado)
        if df_dividendos is not None and not df_dividendos.empty:
            dividendos_anuais = df_dividendos.groupby('Ano')['Dividendo'].sum().reset_index()
            fig_div = px.bar(dividendos_anuais, x='Ano', y='Dividendo',
                             title=f'Dividendos Anuais Pagos ({ticker_selecionado})')
            fig_div.update_layout(yaxis_title='Dividendo por Ação (R$)', yaxis_tickformat=',.2f')
            st.plotly_chart(fig_div, use_container_width=True)
            
        st.divider()

        # ==============================
        # TABELA PRINCIPAL DE INDICADORES
        # ==============================
        tab1, tab2, tab3 = st.tabs(["💰 Rentabilidade e Margens", "⚙️ Estrutura e Custo de Capital", "💸 Fluxo de Caixa"])
        
        with tab1:
            st.subheader("Indicadores de Rentabilidade")
            col_rent1, col_rent2, col_rent3 = st.columns(3)
            with col_rent1:
                st.metric("ROE (Return on Equity)", formatar_percentual_brasil(dados_ano["ROE"], 2))
                st.metric("Margem Bruta", formatar_percentual_brasil(dados_ano["Margem Bruta"], 2))
            with col_rent2:
                st.metric("ROA (Return on Assets)", formatar_percentual_brasil(dados_ano["ROA"], 2))
                st.metric("Margem Operacional", formatar_percentual_brasil(dados_ano["Margem Operacional"], 2))
            with col_rent3:
                st.metric("ROI (Return on Investment)", formatar_percentual_brasil(dados_ano["ROI"], 2))
                st.metric("Margem Líquida", formatar_percentual_brasil(dados_ano["Margem Líquida"], 2))

            # Gráfico de Alavancagem
            if dados_ano["Alavancagem Eficaz"]:
                st.success("✅ A alavancagem financeira da empresa é EFICAZ (ROE > ROA e ROE > ROI).")
            else:
                st.error("❌ A alavancagem financeira da empresa NÃO é EFICAZ.")

            df_alavancagem = pd.DataFrame({
                'Métrica': ['ROE', 'ROA', 'ROI'],
                'Valor': [dados_ano["ROE"], dados_ano["ROA"], dados_ano["ROI"]]
            })
            fig_alavancagem = px.bar(df_alavancagem, x='Métrica', y='Valor',
                                     title='Comparativo de Rentabilidade (ROE vs ROA vs ROI)',
                                     color='Métrica')
            fig_alavancagem.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_alavancagem, use_container_width=True)

        with tab2:
            st.subheader("Estrutura e Custo de Capital")
            col_custo1, col_custo2, col_custo3 = st.columns(3)
            with col_custo1:
                st.metric("WACC (Custo Médio Ponderado)", formatar_percentual_brasil(dados_ano["wacc"], 2))
                st.metric("ki (Custo da Dívida)", formatar_percentual_brasil(dados_ano["ki"], 2))
            with col_custo2:
                st.metric("Patrimônio Líquido", formatar_moeda_brasil_correta(dados_ano["Patrimônio Líquido Consolidado"], 2))
                st.metric("Passivo Oneroso Médio", formatar_moeda_brasil_correta(dados_ano["Passivo Oneroso Médio"], 2))
            with col_custo3:
                st.metric("% Capital Próprio", formatar_percentual_brasil(dados_ano["Percentual Capital Próprio"], 2))
                st.metric("% Capital Terceiros", formatar_percentual_brasil(dados_ano["Percentual Capital Terceiros"], 2))

            st.subheader("Lucro Econômico e EBITDA")
            col_lucro1, col_lucro2 = st.columns(2)
            with col_lucro1:
                st.metric("EBITDA", formatar_moeda_brasil_correta(dados_ano["EBITDA"], 2))
            with col_lucro2:
                st.metric("Lucro Econômico (Modelo 2)", formatar_moeda_brasil_correta(dados_ano["Lucro Econômico 2"], 2))
                
            # Gráfico de Estrutura de Capital
            df_estrutura = pd.DataFrame({
                'Componente': ['Capital Próprio', 'Capital de Terceiros'],
                'Percentual': [dados_ano["Percentual Capital Próprio"], dados_ano["Percentual Capital Terceiros"]]
            })
            fig_estrutura = px.pie(df_estrutura, names='Componente', values='Percentual',
                                   title='Estrutura de Capital', 
                                   color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_estrutura.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_estrutura, use_container_width=True)
            
        with tab3:
            st.subheader("Análise de Fluxo de Caixa")
            
            # Novo: FCO (Caixa Líquido de Atividades Operacionais)
            # Tentar encontrar a coluna
            nome_coluna_fco = None
            for col in dados_ano.index:
                if 'caixa líquido das atividades operacionais' in col.lower():
                    nome_coluna_fco = col
                    break
            
            if nome_coluna_fco:
                st.metric("Caixa Líquido de Atividades Operacionais (FCO)", 
                          formatar_moeda_brasil_correta(dados_ano[nome_coluna_fco], 2))
                
                # Análise de Qualidade do Lucro (FCO vs Lucro Líquido)
                lucro_liquido = dados_ano['Lucro/Prejuízo Consolidado do Período']
                fco = dados_ano[nome_coluna_fco]
                
                if pd.notna(lucro_liquido) and pd.notna(fco) and lucro_liquido > 0:
                    st.markdown("**Análise de Qualidade do Lucro (FCO / Lucro Líquido)**")
                    
                    if fco >= lucro_liquido:
                        st.success("👍 Qualidade do Lucro Forte: O fluxo de caixa operacional (FCO) é maior ou igual ao Lucro Líquido.")
                    else:
                        st.warning("⚠️ Qualidade do Lucro Fraca: O fluxo de caixa operacional (FCO) é menor que o Lucro Líquido. O lucro pode ser de baixa qualidade (contábil, não em caixa).")
                    
                    # Gráfico de comparação
                    df_caixa_lucro = pd.DataFrame({
                        'Métrica': ['Lucro Líquido', 'FCO'],
                        'Valor': [lucro_liquido, fco]
                    })
                    df_caixa_lucro["Valor (R$ bi)"] = df_caixa_lucro["Valor"] * 1000 / 1e9
                    
                    fig_caixa = px.bar(df_caixa_lucro, x='Métrica', y='Valor (R$ bi)', color='Métrica',
                                       title='Lucro Líquido vs. Fluxo de Caixa Operacional')
                    fig_caixa.update_layout(yaxis_title='Valor (R$ Bi)', yaxis_tickformat=',.2f')
                    st.plotly_chart(fig_caixa, use_container_width=True)
                else:
                    st.info("Não foi possível calcular a qualidade do lucro (Lucro Líquido <= 0 ou FCO indisponível).")
                
                # Evolução Temporal do FCO e Lucro Líquido
                df_evolucao = df_empresa_todos_anos[['Ano', 'Lucro/Prejuízo Consolidado do Período', nome_coluna_fco]].copy()
                df_evolucao.columns = ['Ano', 'Lucro Líquido', 'FCO']
                
                # Converter para escala de bilhões para o gráfico
                df_evolucao['Lucro Líquido (Bi)'] = df_evolucao['Lucro Líquido'] * 1000 / 1e9
                df_evolucao['FCO (Bi)'] = df_evolucao['FCO'] * 1000 / 1e9
                
                fig_evolucao = go.Figure()
                fig_evolucao.add_trace(go.Scatter(x=df_evolucao['Ano'], y=df_evolucao['Lucro Líquido (Bi)'], 
                                                  mode='lines+markers', name='Lucro Líquido'))
                fig_evolucao.add_trace(go.Scatter(x=df_evolucao['Ano'], y=df_evolucao['FCO (Bi)'], 
                                                  mode='lines+markers', name='FCO (Operacional)'))
                
                fig_evolucao.update_layout(
                    title='Evolução Anual do Lucro Líquido e Fluxo de Caixa Operacional',
                    yaxis_title='Valor (R$ Bi)',
                    xaxis_title='Ano',
                    yaxis_tickformat=',.2f'
                )
                st.plotly_chart(fig_evolucao, use_container_width=True)
                
            else:
                st.info("Não foi possível encontrar a conta 'Caixa Líquido de Atividades Operacionais' no dataset para esta empresa.")
                

# ==============================
# TELA PRINCIPAL - ANÁLISE SETORIAL
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    if df_filtrado.empty:
        st.warning(f"Não há dados para o Setor **{setor_selecionado}** no ano de **{ano_selecionado}**.")
    else:
        st.header(f"🏭 Análise Setorial: {setor_selecionado} ({ano_selecionado})")
        
        # Agregação dos dados setoriais
        df_setorial = df_filtrado.groupby("SETOR_ATIV").agg(
            Receita_Total=('Receita de Venda de Bens e/ou Serviços', 'sum'),
            Lucro_Total=('Lucro/Prejuízo Consolidado do Período', 'sum'),
            Media_ROE=('ROE', 'mean'),
            Media_ROA=('ROA', 'mean'),
            Media_ML=('Margem Líquida', 'mean'),
            Num_Empresas=('Ticker', 'nunique')
        ).reset_index()
        
        dados_setor = df_setorial.iloc[0] if not df_setorial.empty else None
        
        if dados_setor is not None:
            # KPIs Setoriais
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Empresas no Setor", dados_setor["Num_Empresas"])
            with col2:
                st.metric("Receita Total do Setor", formatar_moeda_brasil_correta(dados_setor["Receita_Total"], 2))
            with col3:
                st.metric("Lucro Total do Setor", formatar_moeda_brasil_correta(dados_setor["Lucro_Total"], 2))
            with col4:
                st.metric("ROE Médio", formatar_percentual_brasil(dados_setor["Media_ROE"], 2))
                
            st.divider()

            # Ranking por Lucro Líquido no Setor
            st.subheader("Top 10 Empresas por Lucro Líquido no Setor")
            lucro_setor_ranking = df_filtrado.nlargest(10, "Lucro/Prejuízo Consolidado do Período")[
                ["Ticker", "Lucro/Prejuízo Consolidado do Período"]
            ].copy()
            
            lucro_setor_ranking["Lucro"] = lucro_setor_ranking["Lucro/Prejuízo Consolidado do Período"].apply(formatar_moeda_brasil_correta)
            st.dataframe(lucro_setor_ranking[["Ticker", "Lucro"]], use_container_width=True)
            
            # Ranking por Rentabilidade no Setor
            st.subheader("Ranking por Rentabilidade (ROE) no Setor")
            rentabilidade_setor_ranking = df_filtrado[df_filtrado["ROE"].notna()].nlargest(10, "ROE")[
                ["Ticker", "ROE", "ROA", "Margem Líquida"]
            ].copy()
            
            if not rentabilidade_setor_ranking.empty:
                rentabilidade_setor_formatado = formatar_dataframe_percentual(
                    rentabilidade_setor_ranking, 
                    ['ROE', 'ROA', 'Margem Líquida']
                )
                st.dataframe(rentabilidade_setor_formatado, use_container_width=True)
            else:
                st.warning("Não há dados de rentabilidade disponíveis para ranking.")

            st.divider()
            
            # Análise Histórica Setorial (Média Simples)
            st.subheader("Evolução Histórica da Rentabilidade Média do Setor")
            df_setor_media_historica = df_setor_todos_anos.groupby("Ano").agg(
                ROE_Media=('ROE', 'mean'),
                ROA_Media=('ROA', 'mean'),
                Margem_Liquida_Media=('Margem Líquida', 'mean')
            ).reset_index()
            
            # Gráfico de linha
            fig_historico_setorial = go.Figure()
            fig_historico_setorial.add_trace(go.Scatter(x=df_setor_media_historica['Ano'], y=df_setor_media_historica['ROE_Media'], 
                                                        mode='lines+markers', name='ROE Médio'))
            fig_historico_setorial.add_trace(go.Scatter(x=df_setor_media_historica['Ano'], y=df_setor_media_historica['ROA_Media'], 
                                                        mode='lines+markers', name='ROA Médio'))
            fig_historico_setorial.add_trace(go.Scatter(x=df_setor_media_historica['Ano'], y=df_setor_media_historica['Margem_Liquida_Media'], 
                                                        mode='lines+markers', name='Margem Líquida Média'))

            fig_historico_setorial.update_layout(
                title='Evolução Histórica da Rentabilidade Média',
                yaxis_title='Percentual',
                xaxis_title='Ano',
                yaxis_tickformat=',.2%'
            )
            st.plotly_chart(fig_historico_setorial, use_container_width=True)
            
            # Tabela de dados históricos
            st.subheader("Dados Históricos de Rentabilidade Média")
            df_setor_media_historica_formatado = df_setor_media_historica.copy()
            df_setor_media_historica_formatado['ROE_Media'] = df_setor_media_historica_formatado['ROE_Media'].apply(lambda x: formatar_percentual_brasil(x, 2))
            df_setor_media_historica_formatado['ROA_Media'] = df_setor_media_historica_formatado['ROA_Media'].apply(lambda x: formatar_percentual_brasil(x, 2))
            df_setor_media_historica_formatado['Margem_Liquida_Media'] = df_setor_media_historica_formatado['Margem_Liquida_Media'].apply(lambda x: formatar_percentual_brasil(x, 2))
            st.dataframe(df_setor_media_historica_formatado.set_index('Ano'), use_container_width=True)

        else:
            st.warning("Não foi possível calcular as métricas setoriais.")
