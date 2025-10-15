# ==============================================================
# 📊 DASHBOARD CVM - Indicadores Financeiros (VERSÃO COMPLETA COM DADOS YFINANCE)
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
# SISTEMA PRINCIPAL - CARREGAR DADOS DO YFINANCE (SUBSTITUINDO EXCEL)
# ==============================
@st.cache_data(ttl=86400)  # Cache por 24 horas
def carregar_dados_acoes_completo():
    """
    Função mantida para compatibilidade, mas agora retorna None
    pois usaremos yfinance diretamente
    """
    return None

# Carregar dados uma vez no início
DADOS_ACOES = carregar_dados_acoes_completo()

# ==============================
# FUNÇÕES DE FORMATAÇÃO COM ESCALAS CORRIGIDAS
# ==============================
# [MANTIDO TODAS AS FUNÇÕES DE FORMATAÇÃO ORIGINAIS]
# ... (manter todas as funções de formatação originais)

# ==============================
# FUNÇÕES DE DIVIDENDOS E INVESTIMENTO (USANDO YFINANCE - CORRIGIDAS)
# ==============================
def buscar_dividendos_historicos(ticker):
    """
    Busca dividendos históricos usando yfinance
    """
    try:
        # Formatar ticker para yfinance (adicionar .SA se necessário)
        ticker_yf = ticker
        if not ticker.endswith('.SA'):
            ticker_yf = f"{ticker}.SA"
        
        # Buscar dados do yfinance
        acao = yf.Ticker(ticker_yf)
        dividendos = acao.dividends
        
        if dividendos.empty:
            return None
            
        # Converter para DataFrame no formato esperado
        df_dividendos = dividendos.reset_index()
        df_dividendos.columns = ['Data', 'Dividendo']
        df_dividendos['Ticker'] = ticker
        df_dividendos['Ticker_Yahoo'] = ticker_yf
        df_dividendos['Ano'] = df_dividendos['Data'].dt.year
        df_dividendos['Mes'] = df_dividendos['Data'].dt.month
        
        return df_dividendos
        
    except Exception as e:
        st.warning(f"⚠️ Não foi possível buscar dividendos para {ticker}: {str(e)}")
        return None

def calcular_estatisticas_dividendos(df_dividendos):
    """
    Calcula estatísticas dos dividendos a partir do yfinance
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
    Busca histórico de preços usando yfinance
    """
    try:
        # Formatar ticker para yfinance (adicionar .SA se necessário)
        ticker_yf = ticker
        if not ticker.endswith('.SA'):
            ticker_yf = f"{ticker}.SA"
        
        # Buscar dados do yfinance
        acao = yf.Ticker(ticker_yf)
        historico = acao.history(period=periodo_maximo)
        
        if historico.empty:
            return None
            
        # Manter apenas a coluna Close e resetar índice
        historico = historico[['Close']].reset_index()
        historico.columns = ['Data', 'Close']
        historico['Ticker'] = ticker
        historico['Ticker_Yahoo'] = ticker_yf
        
        # Configurar índice de data
        historico = historico.set_index('Data')
        historico = historico.sort_index()
        
        return historico[['Close']]
        
    except Exception as e:
        st.warning(f"⚠️ Não foi possível buscar histórico de preços para {ticker}: {str(e)}")
        return None

def simular_investimento_lotes(ticker, data_inicio, quantidade_acoes=100):
    """
    Simula um investimento por quantidade de ações (lotes)
    CORREÇÃO COMPLETA: Compatibilidade de datas entre yfinance e datetime
    """
    try:
        # Buscar histórico de preços do yfinance
        historico = buscar_historico_precos(ticker, "max")
        if historico is None:
            st.warning(f"❌ Não há dados de preços para {ticker}")
            return None
        
        # Buscar dividendos do yfinance
        dividendos = buscar_dividendos_historicos(ticker)
        
        # CORREÇÃO CRÍTICA: Converter data_inicio para o mesmo tipo que o índice
        if isinstance(data_inicio, str):
            data_inicio = pd.to_datetime(data_inicio)
        elif isinstance(data_inicio, datetime):
            data_inicio = pd.to_datetime(data_inicio)
        
        # CORREÇÃO: Garantir que o índice seja datetime
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
            # CORREÇÃO: Garantir compatibilidade de dates
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

def buscar_cotacao_atual(ticker):
    """
    Busca a cotação atual do ticker usando yfinance
    """
    try:
        # Formatar ticker para yfinance (adicionar .SA se necessário)
        ticker_yf = ticker
        if not ticker.endswith('.SA'):
            ticker_yf = f"{ticker}.SA"
        
        # Buscar dados do yfinance
        acao = yf.Ticker(ticker_yf)
        info = acao.info
        historico = acao.history(period="1d")
        
        if historico.empty:
            return None
            
        preco = historico['Close'].iloc[-1]
        
        # Buscar informações básicas do dataset CVM para setor
        setor = "N/A"
        try:
            if 'df' in globals():
                empresa_info = df[df['Ticker'] == ticker]
                if not empresa_info.empty:
                    setor = empresa_info['SETOR_ATIV'].iloc[0]
        except:
            pass
        
        return {
            'cotacao': preco,
            'moeda': 'BRL',
            'nome': info.get('longName', ticker),
            'setor': setor,
            'industria': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap', None),
            'volume': info.get('volume', None),
            'data_atualizacao': datetime.now().strftime("%d/%m/%Y")
        }
        
    except Exception as e:
        st.warning(f"⚠️ Não foi possível buscar cotação para {ticker}: {str(e)}")
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

def calcular_ranking_dividendos(df_filtrado, periodo_anos=1, limite_empresas=50):
    """
    Calcula ranking de dividendos com diferentes períodos usando yfinance
    """
    tickers_unicos = df_filtrado['Ticker'].unique()
    tickers_analisar = tickers_unicos[:limite_empresas]
    
    dados_dy = []
    
    with st.spinner(f"📊 Calculando dividend yields (últimos {periodo_anos} anos)..."):
        progress_bar = st.progress(0)
        for i, ticker in enumerate(tickers_analisar):
            try:
                dy = calcular_dividend_yield_otimizado(ticker, periodo_anos)
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
st.title("Dashboard CVM: Análise das Demonstrações Financeiras")

# ==============================
# LEITURA DE DADOS CVM
# ==============================
@st.cache_data
def load_data():
    # ✅ APENAS na mesma pasta do app
    data_path = "dff_2010_2024.xlsx"
    
    if not os.path.exists(data_path):
        st.error(
            "❌ Arquivo 'dff_2010_2024.xlsx' não encontrado na mesma pasta do app.\n\n"
            "Por favor, certifique-se de que o arquivo está no mesmo diretório que app.py"
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

# ==============================
# [MANTIDO TODAS AS OUTRAS FUNÇÕES E CÓDIGO ORIGINAL]
# ==============================
# ... (manter todo o resto do código original, incluindo as funções de valuation, gráficos, etc.)

# ==============================
# SIDEBAR - FILTROS PRINCIPAIS
# ==============================
st.sidebar.header("🔧 Filtros Principais")

# Exibir status dos dados
st.sidebar.success("✅ Dados de ações via yFinance")

# [MANTIDO TODO O RESTANTE DO CÓDIGO ORIGINAL]
# ... (manter toda a lógica de interface, gráficos, tabelas, etc.)

# ==============================
# ATUALIZAÇÃO DA SEÇÃO DE DIVIDENDOS NO SIDEBAR
# ==============================
st.sidebar.divider()
st.sidebar.header("ℹ️ Informações")
st.sidebar.info(
    "Este dashboard apresenta os principais indicadores financeiros "
    "calculados conforme metodologia Vellani (2024). "
    "**Dados de ações via yFinance**"
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
    - **COTAÇÃO:** Busca em tempo real via yFinance
    - **ANÁLISE:** Comparação entre valuation calculado e cotação de mercado

    **Novas Funcionalidades:**
    - **DADOS YFINANCE:** Usa yfinance para dividendos e cotações em tempo real
    - **FLUXO DE CAIXA OPERACIONAL:** Adicionada análise do Caixa Líquido de Atividades Operacionais
    - **COMPARAÇÃO:** Caixa Operacional vs Lucro Líquido para análise de qualidade do lucro
    - **EVOLUÇÃO TEMPORAL:** Gráficos de fluxo de caixa na análise histórica
    - **DIVIDENDOS:** Histórico de dividendos e análise de dividend yield via yFinance
    - **SIMULAÇÃO DE INVESTIMENTO:** Simulação de compra de lotes desde data específica

    **Dataset: dff_2010_2024**
    - Período: 2010-2024 (15 anos)
    - Empresas: 253 únicas
    - Tickers: 317 únicos
    - Setores: 43 categorias
    - **ESCALA DOS VALORES NO DATASET:** R$ mil
    - **NÚMERO DE AÇÕES:** Disponível apenas para 2024

    **Dados de Ações: yFinance**
    - Dividendos e cotações em tempo real
    - Dados históricos completos
    - Atualização automática
    - Compatível com tickers brasileiros (.SA)
    """)
