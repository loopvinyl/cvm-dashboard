# ==============================================================
# 📊 DASHBOARD CVM - Indicadores Financeiros (VERSÃO CONSOLIDADA)
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
@st.cache_data(ttl=86400)  # 🏆 CORREÇÃO: Adiciona cache para yfinance
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

        # === 🏆 CORREÇÃO: Tratar datetime.date para compatibilidade (Invalid comparison error) ===
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
# SISTEMA DE CACHE DE DIVIDENDOS
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
        
        # Fallback: buscar via Yahoo Finance (agora com cache na função)
        return calcular_dividend_yield(ticker)
        
    except Exception as e:
        return None

# ==============================
# SISTEMA DE RANKING DE DIVIDENDOS FLEXÍVEL
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
                df_dy, x='Ticker', y='Dividend Yield', color='Setor',
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
            st.dataframe(
                df_dy_display[['Ticker', 'Dividend Yield', 'Cotação', 'Setor']],
                use_container_width=True
            )
            
            # Análise
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
                **📈 Interpretação:**
                - **Acima de 8%:** Yield muito alto - pode indicar oportunidades ou riscos
                - **Entre 4%-8%:** Yield atrativo - bom para renda
                - **Abaixo de 4%:** Yield moderado - empresas em crescimento
            """)
        else:
            st.warning("""
                **📝 Como obter dados de dividendos:**
                
                O problema pode ser resolvido com a correção de cache que foi aplicada, mas se persistir:
                1. **Solução Imediata:** Aguarde alguns segundos e recarregue a página
                2. **Solução Permanente:** Baixe o arquivo de dividendos históricos:
                ```python
                # Arquivo CSV esperado: dividendos_historico.csv
                # Colunas: Ticker,Data,Dividendo
                # Exemplo: PETR4,2024-01-15,2.50
                ```
                [📥 Download do modelo de arquivo](https://exemplo.com/dividendos_modelo.csv)
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
                    valor_roe = df_filtrado["ROE"].iloc[0] if pd.notna(df_filtrado["ROE"].iloc[0]) else 0
                    st.metric("ROE", formatar_percentual_brasil(valor_roe))
                with col2:
                    valor_ml = df_filtrado["Margem Líquida"].iloc[0] if pd.notna(df_filtrado["Margem Líquida"].iloc[0]) else 0
                    st.metric("Margem Líquida", formatar_percentual_brasil(valor_ml))
                with col3:
                    valor_alavancagem = df_filtrado["Percentual Capital Terceiros"].iloc[0] if pd.notna(df_filtrado["Percentual Capital Terceiros"].iloc[0]) else 0
                    st.metric("Capital Terceiros", formatar_percentual_brasil(valor_alavancagem))
                with col4:
                    valor_wacc = df_filtrado["wacc"].iloc[0] if pd.notna(df_filtrado["wacc"].iloc[0]) else 0
                    st.metric("WACC", formatar_percentual_brasil(valor_wacc))
                with col5:
                    # CORREÇÃO: Usar o Caixa Líquido de Atividades Operacionais
                    # Tenta encontrar a coluna pelo nome, se não, usa 0
                    caixa_op_col = [col for col in df_filtrado.columns if "caixa líquido de atividades operacionais" in col.lower()]
                    
                    valor_caixa_op = 0
                    if caixa_op_col and pd.notna(df_filtrado[caixa_op_col[0]].iloc[0]):
                        valor_caixa_op = df_filtrado[caixa_op_col[0]].iloc[0]
                    
                    st.metric("Caixa Op. (R$)", formatar_moeda_brasil_correta(valor_caixa_op))

                st.divider()

                # Análise de Lucro e Valuation
                col_lucro, col_valuation = st.columns(2)
                
                with col_lucro:
                    st.subheader("💰 Lucro Líquido vs Caixa Operacional")
                    
                    lucro_liquido = df_filtrado["Lucro/Prejuízo Consolidado do Período"].iloc[0]
                    caixa_op = valor_caixa_op # Reutiliza o valor da coluna 5
                    
                    if pd.notna(lucro_liquido) and caixa_op != 0:
                        caixa_por_lucro = caixa_op / lucro_liquido if lucro_liquido != 0 else np.nan
                        
                        st.metric("Lucro Líquido (R$)", formatar_moeda_brasil_correta(lucro_liquido))
                        st.metric("Caixa Op. por Lucro", formatar_numero_brasil_correto(caixa_por_lucro, 2))
                        
                        if caixa_por_lucro >= 1:
                            st.success("✅ Alta qualidade do lucro (Caixa > Lucro)")
                        elif caixa_por_lucro > 0:
                            st.warning("⚠️ Qualidade média (Caixa < Lucro, mas positivo)")
                        else:
                            st.error("❌ Baixa qualidade do lucro (Caixa negativo ou zero)")
                    else:
                        st.warning("Dados de Lucro Líquido ou Caixa Operacional insuficientes para análise.")
                
                with col_valuation:
                    st.subheader("✨ Valuation (Lucro Econômico)")
                    
                    # Usa o Lucro Econômico 2 (Resultado Operacional - Custo do Capital)
                    lucro_economico_2 = df_filtrado["Lucro Econômico 2"].iloc[0] if pd.notna(df_filtrado["Lucro Econômico 2"].iloc[0]) else 0
                    
                    if lucro_economico_2 > 0:
                        # Cálculo do Valor da Empresa (R$ mil)
                        valor_empresa_mil = calcular_valuation_lucro_economico_selic(lucro_economico_2, 15)
                        
                        # Buscar dados da ação (cotação e Market Cap)
                        dados_cotacao = buscar_cotacao_atual(ticker_selecionado)
                        
                        if valor_empresa_mil and dados_cotacao and dados_cotacao['market_cap']:
                            # Valor da Empresa em Reais (R$)
                            valor_empresa_reais = valor_empresa_mil * 1000
                            
                            st.metric("Valor da Empresa (Calculado)", formatar_moeda_brasil_correta(valor_empresa_mil, 2))
                            st.metric("Market Cap (Mercado)", formatar_moeda_brasil_correta(dados_cotacao['market_cap']/1000, 2))
                            
                            # Cotação por Valuation (Aproximação)
                            # Não temos o número de ações, usamos o Market Cap como proxy de valor justo
                            market_cap_calculado = valor_empresa_reais
                            market_cap_atual = dados_cotacao['market_cap']
                            cotacao_atual = dados_cotacao['cotacao']
                            
                            # Cotação calculada (proxy)
                            cotacao_calculada = cotacao_atual * (market_cap_calculado / market_cap_atual)
                            
                            st.metric("Cotação Atual", f"R$ {cotacao_atual:,.2f}".replace(".", ","))
                            st.metric("Cotação Justa (Estimativa)", f"R$ {cotacao_calculada:,.2f}".replace(".", ","))
                            
                            # Gráfico de comparação
                            fig_valuation = criar_grafico_comparativo(cotacao_calculada, cotacao_atual, ticker_selecionado)
                            st.plotly_chart(fig_valuation, use_container_width=True)
                            
                        else:
                            st.warning("Faltam dados de Market Cap ou cotação para o Valuation (Yahoo Finance)")
                    else:
                        st.warning("Lucro Econômico Negativo ou Zero. Valuation por este método não é aplicável.")
                
            else:
                st.warning(f"Não há dados financeiros para {ticker_selecionado} no ano de {ano_selecionado}.")

        with tab_evolucao:
            st.subheader("📈 Evolução dos Indicadores ao Longo do Tempo")
            
            df_evolucao = df_empresa_todos_anos.copy()
            
            # Gráfico de Rentabilidade
            fig_rentab = go.Figure()
            fig_rentab.add_trace(go.Scatter(x=df_evolucao['Ano'], y=df_evolucao['ROE'] * 100, mode='lines+markers', name='ROE'))
            fig_rentab.add_trace(go.Scatter(x=df_evolucao['Ano'], y=df_evolucao['ROA'] * 100, mode='lines+markers', name='ROA'))
            fig_rentab.update_layout(title='Evolução da Rentabilidade (ROE e ROA)', 
                                     yaxis_title='Percentual (%)',
                                     xaxis_title='Ano')
            st.plotly_chart(fig_rentab, use_container_width=True)
            
            # Gráfico de Lucro e Caixa
            col_lucro_g, col_estrutura_g = st.columns(2)
            
            with col_lucro_g:
                fig_lucro = go.Figure()
                
                # Tenta encontrar o Caixa Operacional para o gráfico
                caixa_op_col_g = [col for col in df_evolucao.columns if "caixa líquido de atividades operacionais" in col.lower()]
                caixa_op_serie = df_evolucao[caixa_op_col_g[0]] if caixa_op_col_g else None

                fig_lucro.add_trace(go.Bar(x=df_evolucao['Ano'], y=df_evolucao['Lucro/Prejuízo Consolidado do Período'], name='Lucro Líquido (R$ mil)'))
                
                if caixa_op_serie is not None:
                    fig_lucro.add_trace(go.Bar(x=df_evolucao['Ano'], y=caixa_op_serie, name='Caixa Op. (R$ mil)'))

                fig_lucro.update_layout(title='Evolução do Lucro Líquido vs. Caixa Operacional', 
                                        yaxis_title='Valor (R$ mil)',
                                        barmode='group')
                st.plotly_chart(fig_lucro, use_container_width=True)
            
            with col_estrutura_g:
                fig_estrutura = go.Figure()
                fig_estrutura.add_trace(go.Scatter(x=df_evolucao['Ano'], y=df_evolucao['Percentual Capital Terceiros'] * 100, mode='lines+markers', name='Capital Terceiros'))
                fig_estrutura.add_trace(go.Scatter(x=df_evolucao['Ano'], y=df_evolucao['Percentual Capital Próprio'] * 100, mode='lines+markers', name='Capital Próprio'))
                fig_estrutura.update_layout(title='Evolução da Estrutura de Capital', 
                                            yaxis_title='Percentual do Passivo (%)',
                                            xaxis_title='Ano',
                                            yaxis=dict(range=[0, 100]))
                st.plotly_chart(fig_estrutura, use_container_width=True)

            with tab_dividendos:
                st.subheader("💰 Histórico de Dividendos")
                
                # Tenta buscar os dividendos (agora com cache)
                df_dividendos = buscar_dividendos_historicos(ticker_selecionado)
                
                if df_dividendos is not None and not df_dividendos.empty:
                    stats = calcular_estatisticas_dividendos(df_dividendos)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Último Dividendo", f"R$ {stats['ultimo_dividendo']:,.4f}".replace(".", ","))
                    with col2:
                        st.metric("Total Pago (Período)", f"R$ {stats['total_dividendos']:,.2f}".replace(".", ","))
                    with col3:
                        st.metric("Média Anual", f"R$ {stats['media_anual']:,.2f}".replace(".", ","))
                    with col4:
                        st.metric("Frequência/Ano", f"{stats['frequencia_media']:.1f}")
                        
                    # 🆕 GRÁFICO DE LINHA DOS DIVIDENDOS AO LONGO DO TEMPO
                    st.subheader("📈 Evolução dos Dividendos ao Longo do Tempo")
                    
                    fig_dividendos_linha = px.line(
                        df_dividendos, 
                        x='Data', 
                        y='Dividendo',
                        title=f'Dividendos por Ação - {ticker_selecionado}',
                        markers=True
                    )
                    
                    # Formatação brasileira no eixo Y
                    fig_dividendos_linha.update_layout(
                        yaxis_title='Dividendo por Ação (R$)',
                        xaxis_title='Data',
                        height=400,
                        yaxis=dict(
                            tickformat=".4f",  # 4 casas decimais para dividendos
                            separatethousands=True
                        )
                    )
                    
                    st.plotly_chart(fig_dividendos_linha, use_container_width=True)
                    
                    # Gráfico de dividendos por ano (JÁ EXISTENTE)
                    dividendos_anuais = df_dividendos.groupby('Ano')['Dividendo'].sum().reset_index()
                    fig_divid = px.bar(dividendos_anuais, x='Ano', y='Dividendo', 
                                        title=f'Dividendos Totais Pagos por Ano para {ticker_selecionado}')
                    st.plotly_chart(fig_divid, use_container_width=True)
                    
                    # Tabela detalhada
                    st.subheader("📋 Pagamentos Detalhados")
                    df_dividendos_display = df_dividendos.copy()
                    df_dividendos_display['Data'] = df_dividendos_display['Data'].dt.strftime('%d/%m/%Y')
                    df_dividendos_display['Dividendo'] = df_dividendos_display['Dividendo'].apply(
                        lambda x: f"R$ {x:,.4f}".replace(".", ","))
                    st.dataframe(df_dividendos_display[['Data', 'Dividendo', 'Ano']], use_container_width=True)
                    
                    # 🆕 ANÁLISE DE DIVIDEND YIELD (se tivermos cotação)
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
                    st.warning(f"Não foram encontrados dados de dividendos para {ticker_selecionado} no Yahoo Finance.")

# ==============================
# TELA - ANÁLISE SETORIAL (ESCALAS CORRIGIDAS)
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    st.header(f"🏭 Análise do Setor: {setor_selecionado}")
    
    # Exibe indicadores consolidados
    st.subheader(f"Indicadores Consolidados - {ano_selecionado}")
    
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    
    # Calcula a média dos indicadores
    indicadores_setoriais = df_filtrado[[
        "ROE", "ROA", "Margem Líquida", "wacc", "Lucro/Prejuízo Consolidado do Período"
    ]].mean()
    
    with col_kpi1:
        st.metric("Média ROE", formatar_percentual_brasil(indicadores_setoriais.get("ROE", 0)))
    with col_kpi2:
        st.metric("Média Margem Líquida", formatar_percentual_brasil(indicadores_setoriais.get("Margem Líquida", 0)))
    with col_kpi3:
        st.metric("Média WACC", formatar_percentual_brasil(indicadores_setoriais.get("wacc", 0)))
    with col_kpi4:
        # Usa a soma total do Lucro no setor
        lucro_total_setor = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum()
        st.metric("Lucro Total (Setor)", formatar_moeda_brasil_correta(lucro_total_setor, 2))
        
    st.divider()

    # Gráfico de evolução do ROE do setor (média simples)
    st.subheader("Evolução do ROE do Setor (Média Simples)")
    df_evolucao_setor = df_setor_todos_anos.groupby("Ano")["ROE"].mean().reset_index()
    
    if not df_evolucao_setor.empty:
        fig_evolucao_roe = px.line(df_evolucao_setor, x='Ano', y='ROE', 
                                   title=f'Média de ROE do Setor {setor_selecionado}',
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
        fig_setor_roe = px.bar(ranking_setorial, x="Ticker", y="ROE", title="ROE das Empresas no Setor")
        fig_setor_roe.update_layout(yaxis_tickformat=',.2%')
        st.plotly_chart(fig_setor_roe, use_container_width=True)
    else:
        st.warning("Não há empresas com dados de rentabilidade para ranking neste setor.")

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
