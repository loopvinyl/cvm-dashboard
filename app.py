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
@st.cache_data(ttl=86400) # === 🏆 CORREÇÃO 2: Adiciona cache para yfinance e estabiliza a busca de dividendos ===
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
    CORRIGIDA: compatibilidade de timezone e de tipo datetime
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

        # === 🏆 CORREÇÃO 1: Tratar datetime.date para compatibilidade (Invalid comparison error) ===
        # Se for um objeto datetime.date (comum em st.date_input), converte para datetime.datetime
        if hasattr(data_inicio, 'day') and not isinstance(data_inicio, datetime):
            data_inicio = datetime.combine(data_inicio, datetime.min.time()) # Garante que é datetime.datetime
        # ===============================================================
        
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
        # OBS: Esta função agora usa cache (CORREÇÃO 2)
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
        (df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()),
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
        number = {'prefix': "R$ ", 'valueformat': ',.2f', 'font': {'size': 30}},
        title = {'text': f"<span style='font-size:1.2em'>Cotação Atual ({ticker})</span><br><span style='font-size:0.8em; color:gray'>[{cotacao_formatada}]</span>"},
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'shape': "bullet",
            'axis': {'range': [min_val, max_val]},
            'threshold': {
                'line': {'color': "red", 'width': 3},
                'thickness': 0.75,
                'value': preco_calculado
            },
            'steps': [
                {'range': [min_val, preco_calculado * 0.9], 'color': "lightgray"},
                {'range': [preco_calculado * 0.9, preco_calculado * 1.1], 'color': "gray"},
                {'range': [preco_calculado * 1.1, max_val], 'color': "lightgray"}
            ],
            'bar': {'color': "darkblue", 'thickness': 0.3}
        }
    ))

    # Adicionar anotação para o Preço Calculado
    fig.add_annotation(
        x=0.5, y=0.1,
        text=f"Preço Calculado (Vellani): {preco_formatado}",
        showarrow=False,
        font=dict(size=14, color='red'),
        xref="paper", yref="paper"
    )
    
    fig.update_layout(height=200, margin=dict(t=50, b=50, l=10, r=10))

    return fig


# ==============================
# FUNÇÕES DE VISUALIZAÇÃO
# ==============================

def criar_grafico_evolucao(df_ticker, coluna, titulo, formato='moeda'):
    """
    Cria um gráfico de linha para a evolução de um indicador
    """
    if df_ticker.empty:
        return None
        
    fig = px.line(df_ticker, x='Ano', y=coluna, title=titulo, markers=True)
    
    if formato == 'moeda':
        # Definir o formato do eixo Y para moeda em BRL (R$ X mil)
        fig.update_layout(yaxis_tickprefix='R$ ', yaxis_tickformat='.0f', 
                          yaxis_ticksuffix=' mil') # Os dados são R$ mil
    elif formato == 'percentual':
        # Definir o formato do eixo Y para percentual (0.00%)
        fig.update_layout(yaxis_tickformat=',.2%')
    
    fig.update_xaxes(dtick=1, showgrid=True)
    fig.update_traces(line=dict(width=3))
    
    return fig

def criar_grafico_caixa_vs_lucro(df_ticker):
    """
    Cria um gráfico de barras comparando Caixa Líquido de Atividades Operacionais e Lucro Líquido
    """
    if df_ticker.empty:
        return None

    df_plot = df_ticker[['Ano', 'Caixa Líquido de Atividades Operacionais', 'Lucro/Prejuízo Consolidado do Período']].copy()
    df_plot.columns = ['Ano', 'Caixa Operacional (R$ mil)', 'Lucro Líquido (R$ mil)']
    
    fig = px.bar(
        df_plot.melt(id_vars='Ano', var_name='Métrica', value_name='Valor (R$ mil)'),
        x='Ano',
        y='Valor (R$ mil)',
        color='Métrica',
        barmode='group',
        title='Caixa Operacional vs Lucro Líquido (R$ mil)',
        height=450
    )

    # Formatar eixo Y para moeda em R$ mil
    fig.update_layout(yaxis_tickprefix='R$ ', yaxis_tickformat=',.0f', yaxis_ticksuffix=' mil')
    fig.update_xaxes(dtick=1)
    
    return fig

def criar_grafico_dy(df_dividendos):
    """
    Cria um gráfico de barras da distribuição de dividendos por ano.
    """
    if df_dividendos is None or df_dividendos.empty:
        return None
        
    # Agrupar dividendos por ano
    df_anual = df_dividendos.groupby('Ano')['Dividendo'].sum().reset_index()
    
    fig = px.bar(
        df_anual,
        x='Ano',
        y='Dividendo',
        title='Evolução de Dividendos Pagos (R$/ação)',
        text_auto='.2f',
        height=450
    )
    
    fig.update_traces(textposition='outside')
    fig.update_xaxes(dtick=1)
    
    return fig

def criar_grafico_investimento(df_historico, data_compra, preco_compra, preco_atual):
    """
    Cria um gráfico de linha da evolução do preço da ação
    """
    if df_historico is None or df_historico.empty:
        return None
    
    fig = go.Figure()
    
    # 1. Linha do preço
    fig.add_trace(go.Scatter(
        x=df_historico.index, 
        y=df_historico['Close'], 
        mode='lines', 
        name='Preço de Fechamento',
        line=dict(color='darkblue', width=2)
    ))
    
    # 2. Ponto de Compra
    fig.add_trace(go.Scatter(
        x=[data_compra], 
        y=[preco_compra], 
        mode='markers', 
        name=f'Compra ({data_compra.strftime("%Y-%m-%d")})',
        marker=dict(color='green', size=10)
    ))

    # 3. Ponto Atual
    fig.add_trace(go.Scatter(
        x=[df_historico.index[-1]], 
        y=[preco_atual], 
        mode='markers', 
        name=f'Atual ({df_historico.index[-1].strftime("%Y-%m-%d")})',
        marker=dict(color='red', size=10)
    ))

    fig.update_layout(
        title='Evolução do Preço da Ação e Pontos de Simulação',
        yaxis_title='Preço (R$)',
        hovermode='x unified'
    )
    
    return fig

# ==============================
# FUNÇÃO PRINCIPAL DO DASHBOARD
# ==============================
def main():
    df = load_data()
    df_dividendos_cache = carregar_dados_dividendos_cache()
    
    # === SIDEBAR ===
    st.sidebar.header("Filtros de Análise")
    
    # Filtro de Setor
    setores = ['TODOS'] + sorted(df['Setor'].dropna().unique().tolist())
    setor_selecionado = st.sidebar.selectbox("Selecione o Setor:", setores, index=setores.index('TODOS'))

    # Filtro de Ticker
    if setor_selecionado == 'TODOS':
        tickers_disponiveis = ['TODOS'] + sorted(df['Ticker'].unique().tolist())
    else:
        tickers_disponiveis = ['TODOS'] + sorted(df[df['Setor'] == setor_selecionado]['Ticker'].unique().tolist())
        
    ticker_selecionado = st.sidebar.selectbox("Selecione o Ticker:", tickers_disponiveis)
    
    # Filtro de Ano
    anos = sorted(df['Ano'].unique().tolist(), reverse=True)
    ano_selecionado = st.sidebar.selectbox("Selecione o Ano:", anos, index=0)
    
    # =============================================================
    # LÓGICA DE FILTRAGEM
    # =============================================================
    
    # 1. Filtro por Setor
    if setor_selecionado != 'TODOS':
        df_filtrado = df[df['Setor'] == setor_selecionado].copy()
    else:
        df_filtrado = df.copy()

    # 2. Filtro por Ticker (se 'TODOS', df_filtrado já está no nível Setor ou Geral)
    if ticker_selecionado != 'TODOS':
        df_ticker = df[df['Ticker'] == ticker_selecionado].copy()
        df_ano_ticker = df_ticker[df_ticker['Ano'] == ano_selecionado].copy()
    else:
        df_ticker = pd.DataFrame() # DataFrame vazio para evitar erros
        df_ano_ticker = df_filtrado[df_filtrado['Ano'] == ano_selecionado].copy()

    # =============================================================
    # LAYOUT DO DASHBOARD
    # =============================================================

    if ticker_selecionado != 'TODOS':
        # =============================================================
        # 1. ANÁLISE DETALHADA POR EMPRESA (TICKER SELECIONADO)
        # =============================================================
        st.header(f"Análise Detalhada: {ticker_selecionado} ({ano_selecionado})")
        
        # Nome completo da empresa e Setor
        nome_empresa = df_ano_ticker['Nome da Companhia'].iloc[0] if not df_ano_ticker.empty else 'N/A'
        setor_empresa = df_ano_ticker['Setor'].iloc[0] if not df_ano_ticker.empty else 'N/A'
        st.markdown(f"**Empresa:** {nome_empresa} | **Setor:** {setor_empresa}")
        
        if df_ano_ticker.empty:
            st.warning(f"Não há dados disponíveis para {ticker_selecionado} no ano {ano_selecionado}.")
            return

        dados_ano = df_ano_ticker.iloc[0]
        
        # --- LINHA 1: VALUATION E RENTABILIDADE ---
        st.subheader("Indicadores de Valuation, Lucro Econômico e Rentabilidade")
        col1, col2, col3, col4 = st.columns(4)

        # 1. Valuation por Lucro Econômico
        lucro_economico = dados_ano.get("Lucro Econômico 2") # Usar a versão 2 como padrão
        if lucro_economico and dados_ano.get("Ações em Circulação"):
            valor_empresa_total = calcular_valuation_lucro_economico_selic(lucro_economico * 1000) # De R$ mil para R$
            cotacao_calculada = valor_empresa_total / dados_ano.get("Ações em Circulação")
            cotacao_calculada_formatada = formatar_moeda_brasil_correta(cotacao_calculada / 1000) # Volta para R$ mil para formatação
        else:
            cotacao_calculada = None
            cotacao_calculada_formatada = "N/A"

        col1.metric("Cotação Justa (Vellani)", f"{cotacao_calculada_formatada}")

        # 2. Cotação Atual e Comparação (Busca Online)
        dados_cotacao = buscar_cotacao_atual(ticker_selecionado)
        if dados_cotacao and cotacao_calculada:
            cotacao_atual = dados_cotacao['cotacao']
            
            # Cálculo do potencial de upside/downside
            diferenca = cotacao_calculada - cotacao_atual
            potencial = (diferenca / cotacao_atual)
            
            col2.metric("Cotação Atual (Mercado)", 
                        f"R$ {cotacao_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                        f"{potencial:.2%}".replace(".", ",")
            )
            
            st.markdown("---")
            st.subheader("Comparativo de Valuation")
            st.plotly_chart(criar_grafico_comparativo(cotacao_calculada, cotacao_atual, ticker_selecionado), use_container_width=True)
            st.markdown("---")
        else:
             col2.metric("Cotação Atual (Mercado)", "N/A")


        # 3. ROE
        col3.metric("ROE (Rentab. PL)", formatar_percentual_brasil(dados_ano.get("ROE")))

        # 4. ROI
        col4.metric("ROI (Rentab. Investimento)", formatar_percentual_brasil(dados_ano.get("ROI")))

        st.markdown("---")

        # --- LINHA 2: MARGENS E ALAVANCAGEM ---
        st.subheader("Margens e Estrutura de Capital")
        col5, col6, col7, col8 = st.columns(4)
        
        col5.metric("Margem Líquida", formatar_percentual_brasil(dados_ano.get("Margem Líquida")))
        col6.metric("Margem Operacional", formatar_percentual_brasil(dados_ano.get("Margem Operacional")))
        
        # Alavancagem
        alavancagem_eficaz = "✅ Eficaz" if dados_ano.get("Alavancagem Eficaz") else "❌ Não Eficaz"
        col7.metric("Alavancagem Eficaz", alavancagem_eficaz)
        
        # Caixa vs Lucro
        caixa_op = dados_ano.get("Caixa Líquido de Atividades Operacionais")
        lucro_liq = dados_ano.get("Lucro/Prejuízo Consolidado do Período")

        if lucro_liq and caixa_op:
            qualidade_lucro = caixa_op / lucro_liq
            col8.metric("Caixa Op. / Lucro Líq.", formatar_percentual_brasil(qualidade_lucro))
        else:
            col8.metric("Caixa Op. / Lucro Líq.", "N/A")

        st.markdown("---")
        
        # --- LINHA 3: EBITDA e Lucro Econômico ---
        st.subheader(f"Geração de Valor e Rentabilidade Histórica")
        col_le1, col_le2, col_ebitda = st.columns(3)
        col_le1.metric("Lucro Econômico (Método 1)", formatar_moeda_brasil_correta(lucro_economico))
        col_le2.metric("EBITDA", formatar_moeda_brasil_correta(dados_ano.get("EBITDA")))
        
        # Evolução do ROE
        fig_roe = criar_grafico_evolucao(df_ticker, "ROE", f"Evolução Histórica do ROE - {ticker_selecionado}", 'percentual')
        if fig_roe:
            st.plotly_chart(fig_roe, use_container_width=True)
        else:
            st.warning("Não há dados históricos de ROE para esta empresa.")
        
        st.markdown("---")

        # --- SEÇÃO 4: ANÁLISE DE FLUXO DE CAIXA ---
        st.subheader("Análise de Fluxo de Caixa")
        
        # Gráfico de Caixa Operacional vs Lucro Líquido
        fig_caixa = criar_grafico_caixa_vs_lucro(df_ticker)
        if fig_caixa:
            st.plotly_chart(fig_caixa, use_container_width=True)
        else:
            st.warning("Não há dados de Fluxo de Caixa para esta empresa.")
            
        st.markdown("---")

        # --- SEÇÃO 5: ANÁLISE DE DIVIDENDOS E SIMULAÇÃO ---
        st.subheader("Análise de Dividendos e Simulação de Investimento")
        
        df_dividendos = buscar_dividendos_historicos(ticker_selecionado)
        
        if df_dividendos is not None:
            # Gráfico de dividendos
            st.plotly_chart(criar_grafico_dy(df_dividendos), use_container_width=True)

            # Estatísticas de Dividendos
            stats = calcular_estatisticas_dividendos(df_dividendos)
            
            col_dy1, col_dy2, col_dy3, col_dy4, col_dy5 = st.columns(5)
            
            dy_atual = calcular_dividend_yield(ticker_selecionado)
            
            col_dy1.metric("Dividend Yield (12m)", formatar_percentual_brasil(dy_atual / 100) if dy_atual else "N/A")
            col_dy2.metric("Último Dividendo (R$)", f"R$ {stats['ultimo_dividendo']:,.2f}".replace(".", ","))
            col_dy3.metric("Data Último Div.", stats['data_ultimo'].strftime("%d/%m/%Y") if stats['data_ultimo'] else "N/A")
            col_dy4.metric("Média Anual (R$)", f"R$ {stats['media_anual']:,.2f}".replace(".", ","))
            
            
            st.markdown("---")
            st.subheader("Simulação de Investimento (Buy and Hold)")
            
            # Simulação de Investimento
            col_sim_data, col_sim_qtd, col_sim_botao = st.columns([1, 1, 0.5])
            
            # Determinar a data mínima (início do histórico ou 2010)
            data_minima = datetime(2010, 1, 1)
            
            data_sugerida = datetime.now().date() - timedelta(days=365 * 5)
            if data_sugerida < data_minima.date():
                data_sugerida = data_minima.date()
                
            data_inicio = col_sim_data.date_input("Data de Início da Simulação:", value=data_sugerida, min_value=data_minima.date())
            quantidade_acoes = col_sim_qtd.number_input("Quantidade de Ações (Lotes):", value=100, min_value=1)
            
            
            simulacao_dados = simular_investimento_lotes(ticker_selecionado, data_inicio, quantidade_acoes)
            
            if simulacao_dados:
                st.subheader(f"Resultados da Simulação (Desde {simulacao_dados['data_compra'].strftime('%d/%m/%Y')})")
                
                col_res1, col_res2, col_res3, col_res4 = st.columns(4)
                
                # Resumo
                col_res1.metric("Valor Investido Inicial", f"R$ {simulacao_dados['valor_investido']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col_res2.metric("Valor Atual Investido", f"R$ {simulacao_dados['valor_investido_atual']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col_res3.metric("Total Dividendos Recebidos", f"R$ {simulacao_dados['total_dividendos_recebidos']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                # Rentabilidade Total
                col_res4.metric("Rentabilidade Total", 
                                formatar_percentual_brasil(simulacao_dados['rentabilidade_total_percentual'] / 100),
                                f"R$ {simulacao_dados['ganho_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )

                st.markdown("---")

                # Detalhes da rentabilidade
                col_det1, col_det2 = st.columns(2)
                col_det1.metric("Ganho por Cotação", 
                                formatar_percentual_brasil(simulacao_dados['rentabilidade_preco_percentual'] / 100),
                                f"R$ {simulacao_dados['ganho_preco']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                col_det2.metric("Ganho por Dividendos", 
                                formatar_percentual_brasil(simulacao_dados['rentabilidade_dividendos_percentual'] / 100),
                                f"R$ {simulacao_dados['total_dividendos_recebidos']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )

                # Gráfico do histórico de preços com marcação
                historico = buscar_historico_precos(ticker_selecionado, "max")
                if historico is not None:
                    fig_invest = criar_grafico_investimento(historico, simulacao_dados['data_compra'], simulacao_dados['preco_compra'], simulacao_dados['preco_atual'])
                    st.plotly_chart(fig_invest, use_container_width=True)


            else:
                st.info("Ajuste os parâmetros e clique no botão para simular.")

        else:
            st.info(f"Não foi possível obter dados históricos de dividendos para {ticker_selecionado} para simulação.")


    else:
        # =============================================================
        # 2. ANÁLISE CONSOLIDADA (SETOR OU GERAL)
        # =============================================================
        st.header(f"Análise Consolidada: {setor_selecionado} ({ano_selecionado})")
        
        if df_ano_ticker.empty:
            st.warning(f"Não há dados disponíveis para o setor {setor_selecionado} no ano {ano_selecionado}.")
            return
            
        # Calcular Médias Setoriais (apenas para o ano selecionado)
        df_medias = df_ano_ticker.agg({
            'ROE': 'median',
            'ROI': 'median',
            'ROA': 'median',
            'Margem Líquida': 'median',
            'EBITDA': 'sum',
            'Lucro/Prejuízo Consolidado do Período': 'sum'
        }).to_dict()
        
        # --- LINHA 1: MÉTRICAS CHAVE ---
        st.subheader("Médias (Mediana) de Rentabilidade e Margens")
        col_med1, col_med2, col_med3, col_med4, col_med5 = st.columns(5)
        
        col_med1.metric("Mediana ROE", formatar_percentual_brasil(df_medias['ROE']))
        col_med2.metric("Mediana ROI", formatar_percentual_brasil(df_medias['ROI']))
        col_med3.metric("Mediana ROA", formatar_percentual_brasil(df_medias['ROA']))
        col_med4.metric("Mediana Margem Líquida", formatar_percentual_brasil(df_medias['Margem Líquida']))
        col_med5.metric("Total Lucro Líquido", formatar_moeda_brasil_correta(df_medias['Lucro/Prejuízo Consolidado do Período']))

        st.markdown("---")
        
        # --- SEÇÃO 2: EVOLUÇÃO E RANKING ---
        
        # Evolução do ROE do Setor (Média)
        st.subheader("Evolução Histórica da Mediana do ROE do Setor")
        df_evolucao_setor = df_filtrado.groupby('Ano')['ROE'].median().reset_index()
        
        if not df_evolucao_setor.empty:
            fig_evolucao_roe = px.line(df_evolucao_setor, x='Ano', y='ROE', 
                                       title=f"Evolução Anual da Mediana do ROE - {setor_selecionado}", 
                                       markers=True)
            fig_evolucao_roe.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_evolucao_roe, use_container_width=True)
        else:
            st.warning("Não há dados de evolução de ROE para este setor.")
            
        st.divider()

        # Ranking de Rentabilidade dentro do Setor
        st.subheader(f"Ranking de Rentabilidade (ROE) - {ano_selecionado}")
        ranking_setorial = df_filtrado.nlargest(10, "ROE")[["Ticker", "ROE", "Margem Líquida", "Lucro/Prejuízo Consolidado do Período"]]
        
        if not ranking_setorial.empty:
            # Formata colunas de percentual
            ranking_formatado = formatar_dataframe_percentual(ranking_setorial.copy(), ['ROE', 'Margem Líquida'])
            
            # Formata coluna de lucro
            ranking_formatado['Lucro/Prejuízo Consolidado do Período'] = ranking_formatado['Lucro/Prejuízo Consolidado do Período'].apply(formatar_moeda_brasil_correta)
            ranking_formatado.rename(columns={'Lucro/Prejuízo Consolidado do Período': 'Lucro Líquido'}, inplace=True)
            
            st.dataframe(ranking_formatado, use_container_width=True)
            
            # Gráfico de comparação
            fig_setor_roe = px.bar(ranking_setorial, x="Ticker", y="ROE", 
                                   title="ROE das Top 10 Empresas no Setor",
                                   text_auto='.2%',
                                   color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_setor_roe.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_setor_roe, use_container_width=True)

        else:
            st.info("Não há empresas com ROE positivo para ranqueamento neste ano/setor.")
            
        st.divider()
        
        # Ranking de Dividend Yield (Busca em tempo real limitada)
        st.subheader(f"Ranking de Dividend Yield (Últimos {st.sidebar.slider('Período DY (Anos):', 1, 5, 1)} anos) - Top 50 Tickers")
        
        periodo_dy = st.sidebar.slider('Período DY (Anos):', 1, 5, 1, key='periodo_dy_slider')
        
        ranking_dy = calcular_ranking_dividendos(df_filtrado, periodo_dy)
        
        if ranking_dy:
            df_ranking_dy = pd.DataFrame(ranking_dy)
            df_ranking_dy = df_ranking_dy.sort_values('Dividend Yield', ascending=False)
            
            # Formatação
            df_final_dy = df_ranking_dy[['Ticker', 'Dividend Yield', 'Cotação', 'Setor']].copy()
            df_final_dy['Cotação'] = df_final_dy['Cotação'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            df_final_dy['Dividend Yield'] = df_final_dy['Dividend Yield'].apply(lambda x: formatar_percentual_brasil(x / 100))
            
            st.dataframe(df_final_dy, use_container_width=True)
            
            # Gráfico de DY
            df_plot_dy = df_ranking_dy.nlargest(10, "Dividend Yield")
            fig_dy = px.bar(df_plot_dy, x="Ticker", y="Dividend Yield", 
                            title=f"Top 10 Dividend Yields (Últimos {periodo_dy} anos)",
                            text_auto='.2%',
                            color_discrete_sequence=px.colors.qualitative.Safe)
            fig_dy.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_dy, use_container_width=True)

        else:
            st.info("Não foi possível calcular o ranking de Dividend Yield. Verifique sua conexão e a disponibilidade de dados.")


# Execução do App Streamlit
if __name__ == "__main__":
    main()
