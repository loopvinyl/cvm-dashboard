# ==============================================================
# 📊 DASHBOARD CVM - Indicadores Financeiros (VERSÃO COM YFINANCE)
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
# SISTEMA PRINCIPAL - CARREGAR DADOS VIA YFINANCE (SUBSTITUI EXCEL)
# ==============================
@st.cache_data(ttl=3600)  # Cache por 1 hora para dados do yfinance
def buscar_dados_yfinance(ticker):
    """
    Busca dados de ações via yfinance
    """
    try:
        # Adiciona .SA se não tiver para ações brasileiras
        if not ticker.endswith('.SA'):
            ticker_yahoo = f"{ticker}.SA"
        else:
            ticker_yahoo = ticker
            
        # Busca o ticker via yfinance
        acao = yf.Ticker(ticker_yahoo)
        
        # Busca histórico de dividendos
        dividendos = acao.dividends
        if not dividendos.empty:
            df_dividendos = pd.DataFrame(dividendos).reset_index()
            df_dividendos.columns = ['Data', 'Dividendo']
            df_dividendos['Ticker'] = ticker
            df_dividendos['Ticker_Yahoo'] = ticker_yahoo
        else:
            df_dividendos = pd.DataFrame(columns=['Data', 'Dividendo', 'Ticker', 'Ticker_Yahoo'])
        
        # Busca histórico de preços
        historico = acao.history(period="max")
        if not historico.empty:
            df_cotacoes = historico[['Close']].reset_index()
            df_cotacoes.columns = ['Data', 'Close']
            df_cotacoes['Ticker'] = ticker
            df_cotacoes['Ticker_Yahoo'] = ticker_yahoo
        else:
            df_cotacoes = pd.DataFrame(columns=['Data', 'Close', 'Ticker', 'Ticker_Yahoo'])
        
        return {
            'dividendos': df_dividendos,
            'cotacoes': df_cotacoes
        }
        
    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar dados do yfinance para {ticker}: {str(e)}")
        return None

# ==============================
# FUNÇÕES DE DIVIDENDOS E INVESTIMENTO (USANDO YFINANCE)
# ==============================
def buscar_dividendos_historicos(ticker):
    """
    Busca dividendos históricos usando yfinance
    """
    try:
        dados = buscar_dados_yfinance(ticker)
        if dados is None:
            return None
            
        df_dividendos = dados['dividendos']
        
        if df_dividendos.empty:
            return None
            
        # Processar dados
        df_dividendos['Data'] = pd.to_datetime(df_dividendos['Data'])
        df_dividendos = df_dividendos.sort_values('Data')
        df_dividendos['Ano'] = df_dividendos['Data'].dt.year
        df_dividendos['Mes'] = df_dividendos['Data'].dt.month
        
        return df_dividendos
        
    except Exception as e:
        st.warning(f"⚠️ Não foi possível buscar dividendos para {ticker}: {str(e)}")
        return None

def buscar_historico_precos(ticker, periodo_maximo="max"):
    """
    Busca histórico de preços usando yfinance
    """
    try:
        dados = buscar_dados_yfinance(ticker)
        if dados is None:
            return None
            
        df_cotacoes = dados['cotacoes']
        
        if df_cotacoes.empty:
            return None
            
        # Processar dados
        df_cotacoes['Data'] = pd.to_datetime(df_cotacoes['Data'])
        df_cotacoes = df_cotacoes.set_index('Data')
        df_cotacoes = df_cotacoes.sort_index()
        
        return df_cotacoes[['Close']]
        
    except Exception as e:
        st.warning(f"⚠️ Não foi possível buscar histórico de preços para {ticker}: {str(e)}")
        return None

def buscar_cotacao_atual(ticker):
    """
    Busca a cotação atual do ticker via yfinance
    """
    try:
        # Adiciona .SA se não tiver para ações brasileiras
        if not ticker.endswith('.SA'):
            ticker_yahoo = f"{ticker}.SA"
        else:
            ticker_yahoo = ticker
            
        acao = yf.Ticker(ticker_yahoo)
        
        # Busca informações atuais
        info = acao.info
        historico = acao.history(period="1d")
        
        if historico.empty:
            return None
        
        preco = historico['Close'].iloc[-1]
        
        return {
            'cotacao': preco,
            'moeda': 'BRL',
            'nome': info.get('longName', ticker),
            'setor': info.get('sector', 'N/A'),
            'industria': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap'),
            'volume': info.get('volume'),
            'data_atualizacao': datetime.now().strftime("%d/%m/%Y")
        }
        
    except Exception as e:
        st.warning(f"⚠️ Não foi possível buscar cotação para {ticker}: {str(e)}")
        return None

def simular_investimento_lotes(ticker, data_inicio, quantidade_acoes=100):
    """
    Simula um investimento por quantidade de ações (lotes)
    usando dados do yfinance
    """
    try:
        # Buscar histórico de preços do yfinance
        historico = buscar_historico_precos(ticker, "max")
        if historico is None:
            st.warning(f"❌ Não há dados de preços para {ticker}")
            return None
        
        # Buscar dividendos do yfinance
        dividendos = buscar_dividendos_historicos(ticker)
        
        # Converter data_inicio para o mesmo tipo que o índice
        if isinstance(data_inicio, str):
            data_inicio = pd.to_datetime(data_inicio)
        elif isinstance(data_inicio, datetime):
            data_inicio = pd.to_datetime(data_inicio)
        
        # Garantir que o índice seja datetime
        historico.index = pd.to_datetime(historico.index)
        
        # Encontrar o primeiro preço disponível após a data de início
        precos_apos_inicio = historico[historico.index >= data_inicio]
        if precos_apos_inicio.empty:
            st.warning(f"❌ Não há dados de preços para {ticker} após {data_inicio.strftime('%d/%m/%Y')}")
            return None
        
        primeira_data = precos_apos_inicio.index[0]
        preco_compra = precos_apos_inicio['Close'].iloc[0]
        
        # Preço atual (último preço disponível)
        preco_atual = historico['Close'].iloc[-1]
        
        # Calcular dividendos recebidos desde a data de compra
        total_dividendos_recebidos = 0
        if dividendos is not None and not dividendos.empty:
            dividendos['Data'] = pd.to_datetime(dividendos['Data'])
            dividendos_apos_compra = dividendos[dividendos['Data'] >= primeira_data]
            total_dividendos_recebidos = (dividendos_apos_compra['Dividendo'] * quantidade_acoes).sum()
        
        # Calcular valores atuais
        valor_investido = quantidade_acoes * preco_compra
        valor_investido_atual = quantidade_acoes * preco_atual
        ganho_preco = valor_investido_atual - valor_investido
        ganho_total = ganho_preco + total_dividendos_recebidos
        
        # Calcular percentuais
        if valor_investido > 0:
            rentabilidade_dividendos_percentual = (total_dividendos_recebidos / valor_investido) * 100
            rentabilidade_preco_percentual = (ganho_preco / valor_investido) * 100
            rentabilidade_total_percentual = (ganho_total / valor_investido) * 100
        else:
            rentabilidade_dividendos_percentual = 0
            rentabilidade_preco_percentual = 0
            rentabilidade_total_percentual = 0
        
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
        st.error(f"❌ Erro na simulação de investimento: {str(e)}")
        return None

def calcular_dividend_yield_otimizado(ticker, periodo_anos=1):
    """
    Versão otimizada do cálculo de dividend yield usando yfinance
    """
    try:
        # Buscar cotação atual do yfinance
        dados_cotacao = buscar_cotacao_atual(ticker)
        if not dados_cotacao:
            return None
            
        cotacao_atual = dados_cotacao['cotacao']
        
        # Buscar dividendos do yfinance
        dividendos = buscar_dividendos_historicos(ticker)
        if dividendos is None or dividendos.empty:
            return None
        
        # Calcular dividendos dos últimos N anos
        data_limite = datetime.now() - timedelta(days=365 * periodo_anos)
        dividendos_periodo = dividendos[dividendos['Data'] >= data_limite]
        
        if not dividendos_periodo.empty:
            total_dividendos = dividendos_periodo['Dividendo'].sum()
            if cotacao_atual > 0:
                dividend_yield = (total_dividendos / cotacao_atual) * 100
                return dividend_yield
        
        return None
        
    except Exception as e:
        return None

# ==============================
# REMOVER FUNÇÕES E VARIÁVEIS RELACIONADAS AO EXCEL
# ==============================
# Remover a função carregar_dados_acoes_completo()
# Remover a variável DADOS_ACOES

# ==============================
# ATUALIZAR A INTERFACE DO USUÁRIO
# ==============================
# No sidebar, atualizar o status dos dados
st.sidebar.success("✅ Dados de ações via yfinance")

# Na seção de dividendos, atualizar a mensagem
# Substituir a mensagem de erro sobre arquivo Excel por:
st.sidebar.info("""
**📊 Fonte de Dados:**
- Dados financeiros: Arquivo CVM
- Dados de ações: yfinance (tempo real)
- Tickers brasileiros: Use formato PETR4.SA ou PETR4
""")

# ==============================
# ATUALIZAR MENSAGENS NA ABA DE DIVIDENDOS
# ==============================
# Na aba de dividendos, substituir a mensagem de erro por:
st.info("""
**📊 Dados via yfinance:**
- Dividendos históricos coletados em tempo real
- Cotações atualizadas do mercado
- Suporte a tickers brasileiros (ex: PETR4.SA, VALE3.SA)
- Dados internacionais também suportados
""")
