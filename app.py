# ==============================================================
# 📊 DASHBOARD CVM CONSOLIDADO - Indicadores Financeiros (TODAS AS FUNCIONALIDADES E RANKING TOP 13)
# ==============================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os
import yfinance as yf
from datetime import datetime, timedelta, date
import locale
import time 

# ==============================
# CONFIGURAÇÕES GLOBAIS
# ==============================
# O usuário solicitou que todo ranking fosse TOP 13
RANKING_LIMIT = 13

# ==============================
# CONFIGURAÇÃO DE FORMATAÇÃO BRASILEIRA (De app_analise.py / app_cvms.py)
# ==============================
def configurar_locale_brasil():
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
        except:
            pass

configurar_locale_brasil()

# ==============================
# FUNÇÕES DE FORMATAÇÃO COM ESCALAS CORRIGIDAS (De app_analise.py / app_cvms.py)
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
# FUNÇÕES DE MERCADO E DIVIDENDOS (De app_cvms.py)
# ==============================
@st.cache_data(ttl=86400) # Cache por 24 horas
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
        
        if cotacao and cotacao > 0:
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
    except:
        pass # Falha silenciosamente
    
    return None

@st.cache_data(ttl=86400) # Cache por 24 horas
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
        
    except:
        return None # Falha silenciosamente

@st.cache_data(ttl=86400) # Cache por 24 horas
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
    except:
        return None # Falha silenciosamente

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

# ==============================
# PRÉ-SELEÇÃO DE TICKERS CONSISTENTES (De app_cvms.py)
# ==============================
@st.cache_data(ttl=86400) # Cache por 24 horas
def calcular_tickers_consistentes(df_cvm, ano_minimo_cvm=2010):
    """
    Identifica tickers que pagaram dividendos em TODOS os anos
    do período CVM (2010) até o ano fiscal mais recente.
    """
    st.info("🔎 **Pré-filtrando:** Buscando tickers que pagaram dividendos anualmente desde 2010. Esta etapa pode demorar.")

    ano_maximo_cvm = df_cvm['Ano'].max()
    anos_necessarios = list(range(ano_minimo_cvm, ano_maximo_cvm + 1))
    
    tickers_validos = df_cvm[df_cvm['Ano'] == ano_maximo_cvm]['Ticker'].unique()
    
    tickers_consistentes = []
    
    # Adicionando um mecanismo de progresso simplificado para a versão consolidada
    progress_text = "Verificando consistência anual de dividendos..."
    progress_bar = st.progress(0, text=progress_text)
    
    for i, ticker in enumerate(tickers_validos):
        df_dividendos = buscar_dividendos_historicos(ticker)
        
        if df_dividendos is not None and not df_dividendos.empty:
            anos_com_pagamento = df_dividendos[df_dividendos['Dividendo'] > 0]['Ano'].unique()
            
            if all(ano in anos_com_pagamento for ano in anos_necessarios):
                tickers_consistentes.append(ticker)
        
        # Atualiza a barra de progresso
        percent_complete = (i + 1) / len(tickers_validos)
        progress_bar.progress(percent_complete, text=f"Verificando {ticker} ({i+1}/{len(tickers_validos)})...")
    
    progress_bar.empty()
    st.success(f"✅ {len(tickers_consistentes)} tickers identificados com pagamento anual consistente desde {ano_minimo_cvm}.")
    return tickers_consistentes

# ==============================
# SISTEMA DE RANKING DE DIVIDENDOS (De app_cvms.py)
# ==============================
def calcular_ranking_dividendos(tickers_consistentes, periodo_dy_anos=10):
    """
    Calcula o Dividend Yield médio dos últimos 10 anos (ou período disponível)
    para o conjunto de tickers consistentes.
    """
    
    dados_ranking = []
    
    if not tickers_consistentes:
        return pd.DataFrame()

    st.warning(f"⚠️ **Busca em tempo real (yfinance):** Calculando DY médio de {periodo_dy_anos} anos para {len(tickers_consistentes)} tickers.")

    with st.spinner(f"Calculando DY médio para {len(tickers_consistentes)} empresas..."):
        
        # Adicionando um mecanismo de progresso simplificado
        progress_text = "Buscando dados de mercado para DY..."
        progress_bar = st.progress(0, text=progress_text)

        for i, ticker in enumerate(tickers_consistentes):
            
            dados_cotacao = buscar_cotacao_atual(ticker)
            data_inicio = datetime.now() - timedelta(days=365 * periodo_dy_anos)
            
            df_historico_precos = buscar_historico_precos(ticker, "max")
            df_dividendos = buscar_dividendos_historicos(ticker)
            
            dy_medio_10a = None
            
            if dados_cotacao and df_historico_precos is not None and df_dividendos is not None and not df_dividendos.empty:
                
                df_historico_precos_filtrado = df_historico_precos[df_historico_precos.index >= data_inicio]
                df_dividendos_filtrado = df_dividendos[df_dividendos['Data'] >= data_inicio]
                
                if not df_historico_precos_filtrado.empty and not df_dividendos_filtrado.empty:
                    
                    df_dividendos_anual = df_dividendos_filtrado.groupby(df_dividendos_filtrado['Data'].dt.year)['Dividendo'].sum()
                    precos_anuais = df_historico_precos_filtrado.resample('Y').last()['Close'].dropna()
                    
                    dy_anuais = []
                    for ano, dividendo_total in df_dividendos_anual.items():
                        ano_fiscal_end = datetime(ano, 12, 31)
                        if ano_fiscal_end.year in precos_anuais.index.year:
                            preco_final = precos_anuais[precos_anuais.index.year == ano].iloc[0]
                            if preco_final > 0:
                                dy_anual = (dividendo_total / preco_final) * 100
                                dy_anuais.append(dy_anual)
                    
                    if dy_anuais:
                        dy_medio_10a = np.mean(dy_anuais)
            
            if dados_cotacao is not None:
                dados_ranking.append({
                    'Ticker': ticker,
                    'Setor': dados_cotacao.get('setor', 'N/A'),
                    'Cotação Atual': dados_cotacao['cotacao'],
                    f'DY Médio ({periodo_dy_anos}A)': dy_medio_10a
                })
            
            # Pequeno atraso para evitar rate limit
            time.sleep(0.01) 
            
            # Atualiza a barra de progresso
            percent_complete = (i + 1) / len(tickers_consistentes)
            progress_bar.progress(percent_complete, text=f"Buscando {ticker} ({i+1}/{len(tickers_consistentes)})...")
    
        progress_bar.empty()
    
    return pd.DataFrame(dados_ranking).fillna(0)

# ==============================
# FUNÇÕES DE VALUATION E SIMULAÇÃO (De app_analise.py e app_cvms.py)
# ==============================

def calcular_valuation_lucro_economico_selic(lucro_economico, selic_percentual=15):
    """
    Calcula o valuation da empresa usando método Lucro Econômico/SELIC
    
    Fórmula CORRETA: Valor da Empresa = Lucro Econômico ÷ (SELIC/100)
    """
    if lucro_economico and lucro_economico > 0:
        # Lucro Econômico é em R$ mil. Valor da Empresa também será em R$ mil.
        valor_empresa_mil = lucro_economico / (selic_percentual / 100)
        return valor_empresa_mil
    return None

def criar_grafico_comparativo(preco_calculado, cotacao_atual, ticker):
    """
    Cria gráfico bullet chart comparativo entre preço calculado e cotação atual
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

# Função de Simulação de Investimento (De app_cvms.py)
def simular_investimento_lotes(ticker, data_inicio, quantidade_acoes=100):
    """ 
    Simula um investimento por quantidade de ações (lotes).
    Retorna None se os dados de preço (histórico) não puderem ser obtidos.
    """
    try:
        # Normalizar a data de início
        if isinstance(data_inicio, date) and not isinstance(data_inicio, datetime):
            data_inicio = datetime(data_inicio.year, data_inicio.month, data_inicio.day)
        elif isinstance(data_inicio, str):
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            
        # 1. Buscar histórico de preços
        historico = buscar_historico_precos(ticker, "max")
        if historico is None:
            return None 

        # 2. Buscar dividendos
        dividendos = buscar_dividendos_historicos(ticker)

        # 3. Encontrar o primeiro preço disponível após a data de início
        precos_apos_inicio = historico[historico.index >= data_inicio]
        if precos_apos_inicio.empty:
            return None 

        primeira_data = precos_apos_inicio.index[0]
        preco_compra = precos_apos_inicio['Close'].iloc[0]

        if preco_compra == 0:
            return {'error': True, 'message': "Preço de compra zero, simulação impossível."}

        # 4. Calcular valor investido
        valor_investido = quantidade_acoes * preco_compra

        # 5. Preço atual (último preço disponível)
        preco_atual = historico['Close'].iloc[-1]
        
        # 6. Calcular dividendos recebidos
        total_dividendos_recebidos = 0
        if dividendos is not None and not dividendos.empty:
            dividendos_apos_compra = dividendos[dividendos['Data'] >= primeira_data]
            total_dividendos_recebidos = dividendos_apos_compra['Dividendo'].sum() * quantidade_acoes

        # 7. Calcular resultados
        valor_atual_acoes = quantidade_acoes * preco_atual
        rentabilidade_preco = valor_atual_acoes - valor_investido
        rentabilidade_total = rentabilidade_preco + total_dividendos_recebidos
        
        # Previne divisão por zero
        if valor_investido == 0:
            return {'error': True, 'message': "Valor investido zero, simulação impossível."}

        rentabilidade_preco_percentual = (rentabilidade_preco / valor_investido) * 100
        rentabilidade_dividendos_percentual = (total_dividendos_recebidos / valor_investido) * 100
        rentabilidade_total_percentual = (rentabilidade_total / valor_investido) * 100
        
        return {
            'data_compra': primeira_data.strftime("%d/%m/%Y"),
            'preco_compra': preco_compra,
            'preco_atual': preco_atual,
            'valor_investido': valor_investido,
            'valor_atual_acoes': valor_atual_acoes,
            'total_dividendos_recebidos': total_dividendos_recebidos,
            'rentabilidade_preco_percentual': rentabilidade_preco_percentual,
            'rentabilidade_dividendos_percentual': rentabilidade_dividendos_percentual,
            'rentabilidade_total_percentual': rentabilidade_total_percentual
        }

    except Exception as e:
        return {'error': True, 'message': f"Erro inesperado: {str(e)}"}

# ==============================
# LEITURA E CÁLCULOS DE DADOS CVM (De app_analise.py)
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
    # MAPEAMENTO EXATO DAS CONTAS E CÁLCULOS DE MÉDIAS
    # =============================================================
    df = df.sort_values(['Ticker', 'Ano']).reset_index(drop=True)

    # Ativo Médio
    df["Ativo Médio"] = (df["Ativo Total"] + df.groupby("Ticker")["Ativo Total"].shift(1)) / 2
    # PL Médio
    df["PL Médio"] = (df["Patrimônio Líquido Consolidado"] + df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1)) / 2
    
    # Passivo Oneroso Médio
    df["Passivo Oneroso Atual"] = (
        df["Empréstimos e Financiamentos - Circulante"].fillna(0) + 
        df["Empréstimos e Financiamentos - Não Circulante"].fillna(0)
    )
    df["Passivo Oneroso Anterior"] = (
        df.groupby("Ticker")["Empréstimos e Financiamentos - Circulante"].shift(1).fillna(0) +
        df.groupby("Ticker")["Empréstimos e Financiamentos - Não Circulante"].shift(1).fillna(0)
    )
    df["Passivo Oneroso Médio"] = (df["Passivo Oneroso Atual"] + df["Passivo Oneroso Anterior"]) / 2

    # Investimento Médio (Capital Total)
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
    # INDICADORES DE RENTABILIDADE
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
    # MARGENS
    # =============================================================
    
    # Margem Bruta
    df["Margem Bruta"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] > 0,
        df["Resultado Bruto"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )

    # Margem Operacional
    df["Margem Operacional"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] > 0,
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )

    # Margem Líquida
    df["Margem Líquida"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] > 0,
        df["Lucro/Prejuízo Consolidado do Período"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )

    # =============================================================
    # ESTRUTURA DE CAPITAL
    # =============================================================
    
    # Total do Passivo
    df["Total Passivo"] = (
        df["Passivo Circulante"].fillna(0) + 
        df["Passivo Não Circulante"].fillna(0) + 
        df["Patrimônio Líquido Consolidado"].fillna(0)
    )

    # Percentual Capital Terceiros
    df["Percentual Capital Terceiros"] = np.where(
        df["Total Passivo"] > 0,
        (df["Passivo Circulante"].fillna(0) + df["Passivo Não Circulante"].fillna(0)) / df["Total Passivo"],
        np.nan
    )

    # Percentual Capital Próprio
    df["Percentual Capital Próprio"] = np.where(
        df["Total Passivo"] > 0,
        df["Patrimônio Líquido Consolidado"] / df["Total Passivo"],
        np.nan
    )

    # =============================================================
    # CUSTO DE CAPITAL
    # =============================================================
    
    # ki (Custo da Dívida)
    df["ki"] = np.where(
        (df["Passivo Oneroso Médio"] > 0) & (df["Despesas Financeiras"].notna()),
        df["Despesas Financeiras"].abs() / df["Passivo Oneroso Médio"],
        np.nan
    )

    # ke (Custo do Capital Próprio)
    df["ke"] = np.where(
        (df["PL Médio"] > 0) & (df["Pagamento de Dividendos"].notna()),
        df["Pagamento de Dividendos"].abs() / df["PL Médio"],
        np.nan
    )

    # WACC
    df["wacc"] = np.where(
        (df["ki"].notna()) & (df["ke"].notna()) & 
        (df["Percentual Capital Terceiros"].notna()) & (df["Percentual Capital Próprio"].notna()),
        (df["ki"] * df["Percentual Capital Terceiros"]) + (df["ke"] * df["Percentual Capital Próprio"]),
        np.nan
    )

    # =============================================================
    # EBITDA
    # =============================================================
    
    nome_coluna_da = None
    for col in df.columns:
        if 'depreciação' in col.lower() and 'amortização' in col.lower():
            nome_coluna_da = col
            break

    if nome_coluna_da:
        depreciacao_amortizacao = abs(df[nome_coluna_da].fillna(0))
        df["EBITDA"] = np.where(
            df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna(),
            df["Resultado Antes do Resultado Financeiro e dos Tributos"] + depreciacao_amortizacao,
            np.nan
        )
    else:
        df["EBITDA"] = df["Resultado Antes do Resultado Financeiro e dos Tributos"]
        st.warning("⚠️ Dados de Depreciação/Amortização não encontrados. EBITDA calculado como aproximação do Resultado Operacional.")

    # =============================================================
    # LUCRO ECONÔMICO
    # =============================================================
    
    # LUCRO ECONÔMICO 1
    df["Lucro Econômico 1"] = np.where(
        (df["ROI"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()),
        (df["ROI"] - df["wacc"]) * df["Investimento Médio"],
        np.nan
    )

    # LUCRO ECONÔMICO 2
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
    # ANÁLISE DE ALAVANCAGEM
    # =============================================================
    
    # Alavancagem Eficaz (ROE > ROA e ROE > ROI)
    df["Alavancagem Eficaz"] = np.where(
        (df["ROE"].notna()) & (df["ROA"].notna()) & (df["ROI"].notna()),
        (df["ROE"] > df["ROA"]) & (df["ROE"] > df["ROI"]),
        False
    )

    return df

# ==============================
# CONFIGURAÇÕES INICIAIS E FLUXO PRINCIPAL
# ==============================

st.set_page_config(page_title="Dashboard CVM Consolidado", layout="wide")
st.title("Dashboard CVM Consolidado: Análise e Dividendos (Ranking TOP 13)")

# Carregar dados
df = load_data()

# ==============================
# SIDEBAR - FILTROS PRINCIPAIS
# ==============================
st.sidebar.header("🔧 Filtros Principais")

# Seleção de modo de análise
modo_analise = st.sidebar.radio(
    "Modo de Análise:",
    ["🏆 Dados Gerais e Rankings CVM", "📈 Visão por Empresa e Simulação", "💰 Ranking de Dividendos (DY)"]
)

# Filtro de ano
anos_disponiveis = sorted(df["Ano"].unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Selecione o Ano:", anos_disponiveis)

df_filtrado = df[df["Ano"] == ano_selecionado]

# ==============================
# TELA PRINCIPAL - MODO "DADOS GERAIS" (CVM)
# ==============================
if modo_analise == "🏆 Dados Gerais e Rankings CVM":
    st.header(f"🏆 Rankings de Indicadores CVM - Ano: {ano_selecionado}")
    
    # KPIs Gerais no Topo
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        empresas_ativas = df_filtrado["Ticker"].nunique()
        st.metric("Empresas Analisadas", empresas_ativas)
    
    with col2:
        setores_ativos = df_filtrado["SETOR_ATIV"].nunique()
        st.metric("Setores Representados", setores_ativos)
    
    with col3:
        receita_total = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum()
        st.metric("Receita Total", formatar_moeda_brasil_correta(receita_total, 2))
    
    with col4:
        lucro_total = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum()
        st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_total, 2))
        
    st.divider()

    # Abas para diferentes rankings (COM LIMITE TOP 13)
    rank_tab1, rank_tab2, rank_tab3, rank_tab4 = st.tabs(["📈 Rentabilidade", "💰 Lucro e Receita", "🏛️ Solidez", "📊 Eficiência"])

    with rank_tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"Top {RANKING_LIMIT} Empresas por ROE")
            roe_ranking = df_filtrado[df_filtrado["ROE"].notna()].nlargest(RANKING_LIMIT, "ROE")[["Ticker", "SETOR_ATIV", "ROE"]]
            if not roe_ranking.empty:
                fig_roe_rank = px.bar(roe_ranking, x="Ticker", y="ROE", color="SETOR_ATIV", title="Ranking de ROE (Return on Equity)")
                fig_roe_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_roe_rank, use_container_width=True)
            else:
                st.warning("Não há dados de ROE disponíveis para ranking")

        with col2:
            st.subheader(f"Top {RANKING_LIMIT} Empresas por ROA")
            roa_ranking = df_filtrado[df_filtrado["ROA"].notna()].nlargest(RANKING_LIMIT, "ROA")[["Ticker", "SETOR_ATIV", "ROA"]]
            if not roa_ranking.empty:
                fig_roa_rank = px.bar(roa_ranking, x="Ticker", y="ROA", color="SETOR_ATIV", title="Ranking de ROA (Return on Assets)")
                fig_roa_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_roa_rank, use_container_width=True)
            else:
                st.warning("Não há dados de ROA disponíveis para ranking")

        # Tabela consolidada de rentabilidade
        st.subheader(f"📋 Tabela de Rentabilidade - Top {RANKING_LIMIT}")
        rentabilidade_consolidado = df_filtrado[
            df_filtrado["ROE"].notna() & df_filtrado["ROA"].notna() & df_filtrado["ROI"].notna()
        ].nlargest(RANKING_LIMIT, "ROE")[["Ticker", "SETOR_ATIV", "ROE", "ROA", "ROI", "Margem Líquida"]]
        if not rentabilidade_consolidado.empty:
            rentabilidade_formatado = formatar_dataframe_percentual(
                rentabilidade_consolidado, ['ROE', 'ROA', 'ROI', 'Margem Líquida']
            )
            st.dataframe(rentabilidade_formatado, use_container_width=True)
        else:
            st.warning("Não há dados suficientes para exibir a tabela consolidada")

    with rank_tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"Top {RANKING_LIMIT} Empresas por Lucro Líquido")
            lucro_ranking = df_filtrado.nlargest(RANKING_LIMIT, "Lucro/Prejuízo Consolidado do Período")[["Ticker", "SETOR_ATIV", "Lucro/Prejuízo Consolidado do Período"]]
            if not lucro_ranking.empty:
                fig_lucro_rank = px.bar(lucro_ranking, x="Ticker", y="Lucro/Prejuízo Consolidado do Período", color="SETOR_ATIV", title="Ranking de Lucro Líquido (R$ mil)")
                fig_lucro_rank.update_layout(yaxis_tickformat='.2s')
                st.plotly_chart(fig_lucro_rank, use_container_width=True)
            else:
                st.warning("Não há dados de Lucro Líquido disponíveis para ranking")

        with col2:
            st.subheader(f"Top {RANKING_LIMIT} Empresas por Receita")
            receita_ranking = df_filtrado.nlargest(RANKING_LIMIT, "Receita de Venda de Bens e/ou Serviços")[["Ticker", "SETOR_ATIV", "Receita de Venda de Bens e/ou Serviços"]]
            if not receita_ranking.empty:
                fig_receita_rank = px.bar(receita_ranking, x="Ticker", y="Receita de Venda de Bens e/ou Serviços", color="SETOR_ATIV", title="Ranking de Receita (R$ mil)")
                fig_receita_rank.update_layout(yaxis_tickformat='.2s')
                st.plotly_chart(fig_receita_rank, use_container_width=True)
            else:
                st.warning("Não há dados de Receita disponíveis para ranking")
        
        # Tabela de Lucro Econômico
        st.subheader(f"📋 Tabela de Lucro Econômico - Top {RANKING_LIMIT}")
        lucro_economico_consolidado = df_filtrado[
            df_filtrado["Lucro Econômico 2"].notna()
        ].nlargest(RANKING_LIMIT, "Lucro Econômico 2")[["Ticker", "SETOR_ATIV", "Lucro/Prejuízo Consolidado do Período", "Lucro Econômico 2"]]
        if not lucro_economico_consolidado.empty:
            lucro_economico_formatado = formatar_dataframe_moeda(
                lucro_economico_consolidado, ['Lucro/Prejuízo Consolidado do Período', 'Lucro Econômico 2']
            )
            st.dataframe(lucro_economico_formatado, use_container_width=True)
        else:
            st.warning("Não há dados suficientes para exibir a tabela de Lucro Econômico")

    with rank_tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"Top {RANKING_LIMIT} Empresas por Capital Próprio")
            capital_proprio_ranking = df_filtrado[df_filtrado["Percentual Capital Próprio"].notna()].nlargest(RANKING_LIMIT, "Percentual Capital Próprio")[["Ticker", "SETOR_ATIV", "Percentual Capital Próprio"]]
            if not capital_proprio_ranking.empty:
                fig_cp_rank = px.bar(capital_proprio_ranking, x="Ticker", y="Percentual Capital Próprio", color="SETOR_ATIV", title="Ranking de % Capital Próprio (Solidez)")
                fig_cp_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_cp_rank, use_container_width=True)
            else:
                st.warning("Não há dados de Capital Próprio disponíveis para ranking")
        
        with col2:
            st.subheader(f"Top {RANKING_LIMIT} Empresas por EBITDA")
            ebitda_ranking = df_filtrado.nlargest(RANKING_LIMIT, "EBITDA")[["Ticker", "SETOR_ATIV", "EBITDA"]]
            if not ebitda_ranking.empty:
                fig_ebitda_rank = px.bar(ebitda_ranking, x="Ticker", y="EBITDA", color="SETOR_ATIV", title="Ranking de EBITDA (R$ mil)")
                fig_ebitda_rank.update_layout(yaxis_tickformat='.2s')
                st.plotly_chart(fig_ebitda_rank, use_container_width=True)
            else:
                st.warning("Não há dados de EBITDA disponíveis para ranking")
                
    with rank_tab4:
        st.subheader(f"Top {RANKING_LIMIT} Empresas por Margem Operacional")
        mo_ranking = df_filtrado[df_filtrado["Margem Operacional"].notna()].nlargest(RANKING_LIMIT, "Margem Operacional")[["Ticker", "SETOR_ATIV", "Margem Operacional"]]
        if not mo_ranking.empty:
            fig_mo_rank = px.bar(mo_ranking, x="Ticker", y="Margem Operacional", color="SETOR_ATIV", title="Ranking de Margem Operacional")
            fig_mo_rank.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_mo_rank, use_container_width=True)
        else:
            st.warning("Não há dados de Margem Operacional disponíveis para ranking")

# ==============================
# TELA PRINCIPAL - MODO "VISÃO POR EMPRESA E SIMULAÇÃO"
# ==============================
elif modo_analise == "📈 Visão por Empresa e Simulação":

    ticker_selecionado = st.sidebar.selectbox(
        "Selecione a Empresa:",
        sorted(df["Ticker"].dropna().unique())
    )
    
    # Filtrar dados da empresa para o ano selecionado
    df_filtrado = df[(df["Ticker"] == ticker_selecionado) & (df["Ano"] == ano_selecionado)]
    
    st.header(f"📈 Visão Detalhada e Simulação - {ticker_selecionado}")
    
    # Exibe estatísticas básicas de dividendos se não houver dados CVM do ano
    if df_filtrado.empty:
        st.warning(f"Não há dados CVM para o Ticker {ticker_selecionado} no ano {ano_selecionado}.")
        
        df_dividendos = buscar_dividendos_historicos(ticker_selecionado)
        if df_dividendos is not None and not df_dividendos.empty:
            stats = calcular_estatisticas_dividendos(df_dividendos)
            st.subheader("Estatísticas de Dividendos (Histórico)")
            col1, col2, col3, col4 = st.columns(4)
            if stats:
                with col1:
                    st.metric("Total Dividendos (Acumulado)", f"R$ {stats['total_dividendos']:,.2f}".replace(".", ","))
                with col2:
                    st.metric("Média Anual de Dividendos", f"R$ {stats['media_anual']:,.2f}".replace(".", ","))
                with col3:
                    st.metric("Último Dividendo Pago", f"R$ {stats['ultimo_dividendo']:,.2f}".replace(".", ","))
                with col4:
                    st.metric("Frequência Média de Pagamento", f"{stats['frequencia_media']:,.2f} vezes/ano".replace(".", ","))
    
    # Se houver dados CVM, continua com a análise detalhada (de app_analise.py)
    if not df_filtrado.empty:
        
        # 1. KPIs da Empresa (Ano Selecionado)
        st.subheader(f"Indicadores Principais - {ano_selecionado}")
        row = df_filtrado.iloc[0]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("ROE (Retorno sobre PL)", formatar_percentual_brasil(row['ROE'], 2))
        with col2:
            st.metric("Lucro Líquido (R$ mil)", formatar_moeda_brasil_correta(row['Lucro/Prejuízo Consolidado do Período'], 2))
        with col3:
            st.metric("Margem Líquida", formatar_percentual_brasil(row['Margem Líquida'], 2))
        with col4:
            st.metric("Alavancagem Eficaz", "Sim" if row['Alavancagem Eficaz'] else "Não", 
                      help="ROE > ROA e ROE > ROI")
            
        st.divider()
        
        # 2. Valuation e Comparação com Mercado
        st.subheader("Valuation e Comparação com Mercado")
        
        lucro_economico_2 = row['Lucro Econômico 2']
        valor_empresa_mil = calcular_valuation_lucro_economico_selic(lucro_economico_2)
        
        if valor_empresa_mil is not None and row['Número de Ações'].notna() and row['Número de Ações'] > 0:
            valor_empresa_reais = valor_empresa_mil * 1000
            cotacao_calculada = valor_empresa_reais / row['Número de Ações']
            
            dados_cotacao_atual = buscar_cotacao_atual(ticker_selecionado)
            
            if dados_cotacao_atual:
                cotacao_atual = dados_cotacao_atual['cotacao']
                
                st.markdown(f"**Valuation pelo Lucro Econômico:** R$ {cotacao_calculada:,.2f}".replace(".", ","))
                st.plotly_chart(criar_grafico_comparativo(cotacao_calculada, cotacao_atual, ticker_selecionado), use_container_width=True)

                col_val1, col_val2, col_val3 = st.columns(3)
                with col_val1:
                    st.metric("Cotação Atual", f"R$ {cotacao_atual:,.2f}".replace(".", ","))
                with col_val2:
                    st.metric("Preço Justo (Modelo)", f"R$ {cotacao_calculada:,.2f}".replace(".", ","))
                with col_val3:
                    market_cap_justo = cotacao_calculada * row['Número de Ações']
                    
                    st.metric("Capitalização Justa (R$ mi)", 
                             formatar_numero_brasil_correto(market_cap_justo / 1000, 2), # Exibe em R$ mi
                             delta=f"{((cotacao_atual / cotacao_calculada) - 1) * 100:,.1f}%" if cotacao_calculada > 0 else "N/A",
                             delta_color="normal",
                             help="Comparação do Preço Atual em relação ao Preço Justo. Negativo = subavaliada.")
            else:
                st.warning("Não foi possível buscar a cotação atual para a comparação de valuation.")
                
        else:
            st.warning("Não há dados de Lucro Econômico ou Número de Ações para realizar o Valuation.")
            
        st.divider()

    # 3. Simulação de Investimento (Do app_cvms.py)
    st.subheader("Simulação de Investimento")
    
    col_qnt, col_data = st.columns(2)
    with col_qnt:
        quantidade_acoes = st.number_input("Quantidade de Ações (Lotes de 100) - Simulação", min_value=100, step=100, value=1000)
    with col_data:
        data_minima = datetime(2010, 1, 1) 
        data_maxima = datetime.now() - timedelta(days=365)
        data_inicio_simulacao = st.date_input("Data de Compra (Início da Simulação):", 
                                                value=data_maxima, 
                                                min_value=data_minima, 
                                                max_value=data_maxima)
    
    if st.button(f"Executar Simulação de Investimento em {ticker_selecionado}"):
        resultados = simular_investimento_lotes(ticker_selecionado, data_inicio_simulacao, quantidade_acoes)
        if resultados and not resultados.get('error'):
            st.success(f"Simulação concluída em {resultados['data_compra']}")
            
            col_i, col_a, col_d, col_r = st.columns(4)
            with col_i:
                st.metric("Valor Investido", f"R$ {resultados['valor_investido']:,.2f}".replace(".", ","))
            with col_a:
                st.metric("Valor Atual das Ações", f"R$ {resultados['valor_atual_acoes']:,.2f}".replace(".", ","))
            with col_d:
                st.metric("Total Dividendos Recebidos", f"R$ {resultados['total_dividendos_recebidos']:,.2f}".replace(".", ","))
            with col_r:
                st.metric("Rentabilidade Total", f"{resultados['rentabilidade_total_percentual']:,.2f}%".replace(".", ","))
                
            st.subheader("Detalhamento da Rentabilidade")
            col_rent_preco, col_rent_dividendo, col_rent_total = st.columns(3)
            
            with col_rent_preco:
                st.metric("Rentabilidade (Apreciação)", f"{resultados['rentabilidade_preco_percentual']:,.2f}%".replace(".", ","))
            with col_rent_dividendo:
                st.metric("Rentabilidade (Dividendos)", f"{resultados['rentabilidade_dividendos_percentual']:,.2f}%".replace(".", ","))
            with col_rent_total:
                st.metric("Rentabilidade Total", f"{resultados['rentabilidade_total_percentual']:,.2f}%".replace(".", ","))
        
        elif resultados and resultados.get('error'):
            st.error(f"❌ Não foi possível realizar a simulação: {resultados['message']}")
        else:
            st.error(f"❌ Não foi possível realizar a simulação. Dados de preço não encontrados para o período.")

# ==============================
# TELA PRINCIPAL - MODO "RANKING DE DIVIDENDOS (DY)"
# ==============================
elif modo_analise == "💰 Ranking de Dividendos (DY)":
    
    st.header(f"💰 Ranking de Dividendos (Dividend Yield)")
    st.info("Este ranking utiliza dados históricos de preço e dividendo do Yahoo Finance para calcular o Dividend Yield médio, priorizando empresas com pagamento consistente desde 2010.")

    # Usar st.session_state para evitar recalcular a lista de consistentes a cada interação
    if 'df_consistentes' not in st.session_state:
        st.session_state.df_consistentes = calcular_tickers_consistentes(df)

    if not st.session_state.df_consistentes:
        st.error("Não foram encontrados tickers com pagamento anual consistente desde 2010.")
        st.stop()

    # Opção de selecionar o período de DY
    periodo_dy_anos = st.selectbox(
        "Período de Análise do DY:",
        [10, 5, 3],
        format_func=lambda x: f"{x} Anos"
    )
    
    # Executar o cálculo de ranking de dividendos
    df_ranking_dy = calcular_ranking_dividendos(st.session_state.df_consistentes, periodo_dy_anos)
    
    if not df_ranking_dy.empty:
        # Filtrar por DY > 0 e ranquear
        df_ranking_dy = df_ranking_dy[df_ranking_dy[f'DY Médio ({periodo_dy_anos}A)'] > 0].sort_values(
            by=f'DY Médio ({periodo_dy_anos}A)', ascending=False
        )
        
        # Aplicar o limite TOP 13
        df_ranking_dy = df_ranking_dy.head(RANKING_LIMIT)
        
        st.subheader(f"Top {RANKING_LIMIT} Empresas Consistentes por DY Médio ({periodo_dy_anos} Anos)")

        if not df_ranking_dy.empty:
            # Formatação
            df_ranking_formatado = df_ranking_dy.copy()
            df_ranking_formatado['Cotação Atual'] = df_ranking_formatado['Cotação Atual'].apply(lambda x: f"R$ {x:,.2f}".replace(".", ","))
            df_ranking_formatado[f'DY Médio ({periodo_dy_anos}A)'] = df_ranking_formatado[f'DY Médio ({periodo_dy_anos}A)'].apply(lambda x: f"{x:,.2f}%".replace(".", ","))
            
            # Adicionar Rank
            df_ranking_formatado.insert(0, 'Rank', range(1, len(df_ranking_formatado) + 1))

            st.dataframe(df_ranking_formatado, use_container_width=True)

            # Gráfico do Ranking
            fig_dy_rank = px.bar(
                df_ranking_dy, 
                x='Ticker', 
                y=f'DY Médio ({periodo_dy_anos}A)', 
                color='Setor', 
                title=f'Ranking de Dividend Yield Médio ({periodo_dy_anos} Anos) - Top {RANKING_LIMIT}'
            )
            fig_dy_rank.update_layout(yaxis_tickformat=',.2f%')
            st.plotly_chart(fig_dy_rank, use_container_width=True)

        else:
            st.warning(f"Nenhuma empresa consistente tem um DY médio positivo nos últimos {periodo_dy_anos} anos para ranqueamento.")
    else:
        st.warning("Não foi possível calcular o Ranking de Dividendos. Verifique a conexão ou tente novamente mais tarde.")

# FIM DO SCRIPT
