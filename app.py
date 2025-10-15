# ==============================================================
# 📊 DASHBOARD CVM - Indicadores Financeiros (VERSÃO COMPLETA E FINAL)
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
# CONFIGURAÇÃO DE FORMATAÇÃO BRASILEIRA
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
# FUNÇÕES DE DIVIDENDOS E INVESTIMENTO
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

def simular_investimento_lotes(ticker, data_inicio, quantidade_acoes=100):
    """
    Simula um investimento por quantidade de ações (lotes)
    """
    try:
        if isinstance(data_inicio, date) and not isinstance(data_inicio, datetime):
            data_inicio = datetime(data_inicio.year, data_inicio.month, data_inicio.day)
        elif isinstance(data_inicio, str):
             data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        
        # Buscar histórico de preços
        historico = buscar_historico_precos(ticker, "max")
        if historico is None:
            return None
        
        # Buscar dividendos
        dividendos = buscar_dividendos_historicos(ticker)
        
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
        return None

# ==============================
# NOVAS FUNÇÕES PARA ANÁLISE DE CONSISTÊNCIA E CRESCIMENTO DE DIVIDENDOS
# ==============================
def calcular_consistencia_dividendos(df_dividendos_hist):
    """
    Calcula o número de anos consecutivos que a empresa pagou dividendos (desde 2010).
    """
    if df_dividendos_hist is None or df_dividendos_hist.empty:
        return 0, 0
    
    # 1. Agrupar por ano
    df_anual = df_dividendos_hist.groupby('Ano')['Dividendo'].sum().reset_index()
    # 2. Filtrar anos com pagamento (valor > 0)
    anos_com_pagamento = df_anual[df_anual['Dividendo'] > 0]['Ano'].unique()
    
    total_anos_pagando = len(anos_com_pagamento)
    
    # 2. Calcular Anos consecutivos
    if total_anos_pagando == 0:
        return total_anos_pagando, 0
    
    anos_pagos_sorted = sorted(anos_com_pagamento)
    
    max_consecutive = 0
    current_consecutive = 0
    
    for i in range(len(anos_pagos_sorted)):
        if i == 0:
            current_consecutive = 1
        # Verifica se o ano atual é o ano anterior + 1
        elif anos_pagos_sorted[i] == anos_pagos_sorted[i-1] + 1:
            current_consecutive += 1
        else:
            max_consecutive = max(max_consecutive, current_consecutive)
            current_consecutive = 1
            
    # Última verificação após o loop
    max_consecutive = max(max_consecutive, current_consecutive)
    
    return total_anos_pagando, max_consecutive

def calcular_crescimento_dividendos(df_dividendos_hist):
    """
    Calcula o crescimento anual composto (CAGR) do dividendo anual (desde 2010).
    """
    if df_dividendos_hist is None or df_dividendos_hist.empty:
        return None
        
    df_anual = df_dividendos_hist.groupby('Ano')['Dividendo'].sum().reset_index()
    df_anual.columns = ['Ano', 'Total Dividendo']
    
    # Filtrar anos com dividendo > 0
    df_anual = df_anual[df_anual['Total Dividendo'] > 0].reset_index(drop=True)
    
    if len(df_anual) < 2:
        return None
        
    primeiro_ano = df_anual.iloc[0]['Ano']
    ultimo_ano = df_anual.iloc[-1]['Ano']
    
    dividendo_inicio = df_anual.iloc[0]['Total Dividendo']
    dividendo_final = df_anual.iloc[-1]['Total Dividendo']
    
    n_anos = ultimo_ano - primeiro_ano
    
    if n_anos <= 0 or dividendo_inicio <= 0:
        return None
        
    # Calcular CAGR
    try:
        # Fórmula: (Valor Final / Valor Inicial)^(1/n_anos) - 1
        cagr = (pow(dividendo_final / dividendo_inicio, 1 / n_anos) - 1) * 100
        return cagr
    except:
        return None

# ==============================
# NOVO: SISTEMA DE RANKING DE DIVIDENDOS FLEXÍVEL (REFORMULADO)
# ==============================
def calcular_ranking_dividendos(df_filtrado, limite_empresas=10):
    """
    Calcula um conjunto completo de métricas de dividendos (DY, Consistência, Crescimento)
    para um limite de empresas, focando em robustez com yfinance.
    """
    
    # Garantir que só temos tickers válidos
    tickers_unicos = df_filtrado['Ticker'].dropna().unique()
    # Limitar a análise a, no máximo, 50 empresas por performance, mas ranquear o TOP 10
    tickers_analisar = tickers_unicos[:50] 
    
    dados_dy = []
    
    if not tickers_analisar.size:
        return pd.DataFrame()

    st.warning(f"⚠️ **Busca em tempo real (yfinance):** Analisando os primeiros {len(tickers_analisar)} tickers para ranking (limite de 50 para evitar rate limit). O limite de exibição é Top {limite_empresas}.")

    with st.spinner(f"Calculando métricas de dividendos para {len(tickers_analisar)} empresas..."):
        # Total de passos para a barra de progresso
        total_steps = len(tickers_analisar)
        
        progress_bar = st.progress(0, text="Buscando dados de mercado...")
        
        for i, ticker in enumerate(tickers_analisar):
            
            # 1. Buscar Cotação e Setor
            dados_cotacao = buscar_cotacao_atual(ticker)
            setor = df_filtrado[df_filtrado['Ticker'] == ticker]['SETOR_ATIV'].iloc[0] if not df_filtrado[df_filtrado['Ticker'] == ticker]['SETOR_ATIV'].empty else 'N/A'
            
            # 2. Buscar Histórico de Dividendos
            df_dividendos = buscar_dividendos_historicos(ticker)
            
            dy_12m = None
            anos_pagos = 0
            anos_consecutivos = 0
            cagr = None
            
            if dados_cotacao and df_dividendos is not None and not df_dividendos.empty:
                
                # A. Calcular DY (Últimos 12 meses)
                data_limite = datetime.now() - timedelta(days=365)
                dividendos_12m = df_dividendos[df_dividendos['Data'] >= data_limite]
                
                if not dividendos_12m.empty and dados_cotacao['cotacao'] > 0:
                    total_dividendos_12m = dividendos_12m['Dividendo'].sum()
                    dy_12m = (total_dividendos_12m / dados_cotacao['cotacao']) * 100
                    
                # B. Calcular Consistência
                anos_pagos, anos_consecutivos = calcular_consistencia_dividendos(df_dividendos)
                
                # C. Calcular Crescimento (CAGR)
                cagr = calcular_crescimento_dividendos(df_dividendos)
            
            if dados_cotacao is not None:
                dados_dy.append({
                    'Ticker': ticker,
                    'Setor': setor,
                    'Cotação': dados_cotacao['cotacao'],
                    'Dividend Yield (12M)': dy_12m,
                    'Anos Pagos (Total)': anos_pagos,
                    'Anos Consecutivos': anos_consecutivos,
                    'CAGR (Cresc. Dividendo)': cagr
                })
            
            # CORREÇÃO CRÍTICA: Atraso para evitar rate limit
            time.sleep(0.5) 
            
            # Atualiza a barra de progresso
            percent_complete = (i + 1) / total_steps
            progress_bar.progress(percent_complete, text=f"Buscando {ticker} ({i+1}/{total_steps})...")

        progress_bar.empty() # Remove a barra de progresso ao finalizar
    
    # Preenche NaNs (empresas que não pagaram) com 0 para que possam ser ranqueadas
    return pd.DataFrame(dados_dy).fillna(0) 

# ==============================
# FUNÇÃO PARA VALUATION POR LUCRO ECONÔMICO/SELIC
# ==============================
def calcular_valuation_lucro_economico_selic(lucro_economico, selic_percentual=15):
    """
    Calcula o valuation da empresa usando método Lucro Econômico/SELIC
    """
    if lucro_economico and lucro_economico > 0:
        valor_empresa = lucro_economico / (selic_percentual / 100)
        return valor_empresa
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

# Carregar dados
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
    
    df["Ativo Médio"] = (df["Ativo Total"] + df.groupby("Ticker")["Ativo Total"].shift(1)) / 2
    df["PL Médio"] = (df["Patrimônio Líquido Consolidado"] + df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1)) / 2

    df["Passivo Oneroso Atual"] = (
        df["Empréstimos e Financiamentos - Circulante"].fillna(0) + 
        df["Empréstimos e Financiamentos - Não Circulante"].fillna(0)
    )
    df["Passivo Oneroso Anterior"] = (
        df.groupby("Ticker")["Empréstimos e Financiamentos - Circulante"].shift(1).fillna(0) +
        df.groupby("Ticker")["Empréstimos e Financiamentos - Não Circulante"].shift(1).fillna(0)
    )
    df["Passivo Oneroso Médio"] = (df["Passivo Oneroso Atual"] + df["Passivo Oneroso Anterior"]) / 2

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
    # MARGENS - TODOS CORRETOS
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
    # ESTRUTURA DE CAPITAL - TODOS CORRETOS
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
    # CUSTO DE CAPITAL - TODOS CORRETOS
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
    # EBITDA CORRIGIDO
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
    # LUCRO ECONÔMICO - CORRIGIDOS
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
    # ANÁLISE DE ALAVANCAGEM
    # =============================================================
    
    # Verifica se a alavancagem é eficaz (ROE > ROA e ROE > ROI)
    df["Alavancagem Eficaz"] = np.where(
        (df["ROE"].notna()) & (df["ROA"].notna()) & (df["ROI"].notna()),
        (df["ROE"] > df["ROA"]) & (df["ROE"] > df["ROI"]),
        False
    )

    return df

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
    df_empresa_todos_anos = df[df["Ticker"] == ticker_selecionado].sort_values("Ano")
    
elif modo_analise == "🏭 Análise Setorial":
    setor_selecionado = st.sidebar.selectbox(
        "Selecione o Setor:",
        sorted(df["SETOR_ATIV"].dropna().unique())
    )
    df_filtrado = df[(df["SETOR_ATIV"] == setor_selecionado) & (df["Ano"] == ano_selecionado)]
    df_setor_todos_anos = df[df["SETOR_ATIV"] == setor_selecionado].sort_values(["Ano", "Ticker"])
    
else:  # Dados Gerais
    df_filtrado = df[df["Ano"] == ano_selecionado]

# ==============================
# TELA PRINCIPAL - RANKING COMPARATIVO
# ==============================
if modo_analise == "🏆 Dados Gerais":
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
        receita_total = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum()
        st.metric("Receita Total", formatar_moeda_brasil_correta(receita_total, 2))
    
    with col4:
        lucro_total = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum()
        st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_total, 2))
    
    st.divider()
    
    # Abas para diferentes rankings
    rank_tab1, rank_tab2, rank_tab3, rank_tab4, rank_tab5 = st.tabs([
        "📈 Rentabilidade", "💰 Lucro e Receita", "🏛️ Solidez", "📊 Eficiência", "💰 Dividendos"
    ])
    
    # --- RANKING DE RENTABILIDADE ---
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
        
        st.subheader("📋 Tabela de Rentabilidade - Top 20")
        rentabilidade_consolidado = df_filtrado[
            df_filtrado["ROE"].notna() & 
            df_filtrado["ROA"].notna() & 
            df_filtrado["ROI"].notna()
        ].nlargest(20, "ROE")[["Ticker", "SETOR_ATIV", "ROE", "ROA", "ROI", "Margem Líquida"]]
        
        if not rentabilidade_consolidado.empty:
            rentabilidade_formatado = formatar_dataframe_percentual(
                rentabilidade_consolidado, 
                ['ROE', 'ROA', 'ROI', 'Margem Líquida']
            )
            st.dataframe(rentabilidade_formatado, use_container_width=True)
        else:
            st.warning("Não há dados suficientes para exibir a tabela consolidada")
    
    # --- RANKING DE LUCRO E RECEITA ---
    with rank_tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 15 Empresas por Lucro Líquido")
            lucro_ranking = df_filtrado.nlargest(15, "Lucro/Prejuízo Consolidado do Período")[["Ticker", "SETOR_ATIV", "Lucro/Prejuízo Consolidado do Período"]]
            
            if not lucro_ranking.empty:
                lucro_ranking["Lucro (R$)"] = lucro_ranking["Lucro/Prejuízo Consolidado do Período"] * 1000 / 1e9  # Converter para bilhões
                
                fig_lucro_rank = px.bar(lucro_ranking, x="Ticker", y="Lucro (R$)", color="SETOR_ATIV",
                                      title="Ranking por Lucro Líquido (R$ Bilhões)")
                fig_lucro_rank.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig_lucro_rank, use_container_width=True)
                
                lucro_ranking["Lucro"] = lucro_ranking["Lucro/Prejuízo Consolidado do Período"].apply(formatar_moeda_brasil_correta)
                st.dataframe(lucro_ranking[["Ticker", "SETOR_ATIV", "Lucro"]], use_container_width=True)
            else:
                st.warning("Não há dados de lucro disponíveis para ranking")
        
        with col2:
            st.subheader("Top 15 Empresas por Receita")
            receita_ranking = df_filtrado.nlargest(15, "Receita de Venda de Bens e/ou Serviços")[["Ticker", "SETOR_ATIV", "Receita de Venda de Bens e/ou Serviços"]]
            
            if not receita_ranking.empty:
                receita_ranking["Receita (R$)"] = receita_ranking["Receita de Venda de Bens e/ou Serviços"] * 1000 / 1e9  # Converter para bilhões
                
                fig_receita_rank = px.bar(receita_ranking, x="Ticker", y="Receita (R$)", color="SETOR_ATIV",
                                        title="Ranking por Receita (R$ Bilhões)")
                fig_receita_rank.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig_receita_rank, use_container_width=True)
                
                receita_ranking["Receita"] = receita_ranking["Receita de Venda de Bens e/ou Serviços"].apply(formatar_moeda_brasil_correta)
                st.dataframe(receita_ranking[["Ticker", "SETOR_ATIV", "Receita"]], use_container_width=True)
            else:
                st.warning("Não há dados de receita disponíveis para ranking")
    
    # --- RANKING DE SOLIDEZ ---
    with rank_tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 15 Empresas por Patrimônio Líquido")
            pl_ranking = df_filtrado.nlargest(15, "Patrimônio Líquido Consolidado")[["Ticker", "SETOR_ATIV", "Patrimônio Líquido Consolidado"]]
            
            if not pl_ranking.empty:
                pl_ranking["PL (R$)"] = pl_ranking["Patrimônio Líquido Consolidado"] * 1000 / 1e9  # Converter para bilhões
                
                fig_pl_rank = px.bar(pl_ranking, x="Ticker", y="PL (R$)", color="SETOR_ATIV",
                                    title="Ranking de Patrimônio Líquido (R$ Bilhões)")
                fig_pl_rank.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig_pl_rank, use_container_width=True)
                
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

    # --- RANKING DE EFICIÊNCIA ---
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

    # --- RANKING DE DIVIDENDOS (NOVA ESTRUTURA) ---
    with rank_tab5:
        st.header("💰 Análise Avançada de Pagadores de Dividendos")

        # Controles para seleção de limite (afeta o limite de exibição final, a análise inicial é nos primeiros 50)
        col_limit, _ = st.columns(2)
        with col_limit:
            limite_empresas = st.selectbox(
                "Top X empresas para cada ranking:", 
                [10, 15, 20], 
                index=0, 
                format_func=lambda x: f"Top {x} empresas",
                key="limite_dy_final"
            )

        # Calcular todas as métricas em um único ciclo (máximo 50 tickers)
        df_dy_completo = calcular_ranking_dividendos(df_filtrado, limite_empresas)

        if not df_dy_completo.empty:
            
            # --- 1. RANKING POR DIVIDEND YIELD (DY) ---
            st.subheader(f"🥇 Top {limite_empresas} - Maior Dividend Yield (12M)")
            # FILTRO: Apenas com DY > 0
            df_dy_rank = df_dy_completo[df_dy_completo['Dividend Yield (12M)'] > 0].nlargest(limite_empresas, 'Dividend Yield (12M)')
            
            if not df_dy_rank.empty:
                df_dy_display = df_dy_rank.copy()
                df_dy_display['DY (12M)'] = df_dy_display['Dividend Yield (12M)'].apply(lambda x: f"{x:.2f}%".replace(".", ","))
                df_dy_display['Cotação'] = df_dy_display['Cotação'].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                
                st.dataframe(
                    df_dy_display[['Ticker', 'DY (12M)', 'Cotação', 'Setor']], 
                    use_container_width=True
                )
                
                fig_dy = px.bar(df_dy_rank, x='Ticker', y='Dividend Yield (12M)', color='Setor',
                                title='Ranking de Dividend Yield (Últimos 12 meses)')
                fig_dy.update_layout(yaxis_title='Dividend Yield (%)', yaxis_tickformat=',.2f', height=400)
                st.plotly_chart(fig_dy, use_container_width=True)
            else:
                st.info("Não há empresas com Dividend Yield positivo no período de 12 meses entre as analisadas.")
                
            st.markdown("---")
            
            # --- 2. RANKING POR CONSISTÊNCIA ---
            st.subheader(f"🥈 Top {limite_empresas} - Maior Consistência (Anos Consecutivos Pagando)")
            # FILTRO: Apenas com Anos Consecutivos > 0
            df_consistencia_rank = df_dy_completo[df_dy_completo['Anos Consecutivos'] > 0].nlargest(limite_empresas, 'Anos Consecutivos')
            
            if not df_consistencia_rank.empty:
                df_consistencia_display = df_consistencia_rank.copy()
                
                st.dataframe(
                    df_consistencia_display[['Ticker', 'Anos Consecutivos', 'Anos Pagos (Total)', 'Setor']], 
                    use_container_width=True
                )
                
                fig_consist = px.bar(df_consistencia_rank, x='Ticker', y='Anos Consecutivos', color='Setor',
                                     title='Ranking de Consistência (Anos Pagando Consecutivamente)')
                fig_consist.update_layout(yaxis_title='Anos Consecutivos', height=400)
                st.plotly_chart(fig_consist, use_container_width=True)
            else:
                st.info("Não há dados de consistência para ranking entre as empresas analisadas.")
                
            st.markdown("---")
            
            # --- 3. RANKING POR CRESCIMENTO (CAGR) ---
            st.subheader(f"🥉 Top {limite_empresas} - Maior Crescimento de Dividendo (CAGR)")
            # FILTRO: Apenas com CAGR > 0 (crescimento positivo)
            df_cagr_rank = df_dy_completo[df_dy_completo['CAGR (Cresc. Dividendo)'] > 0].nlargest(limite_empresas, 'CAGR (Cresc. Dividendo)')
            
            if not df_cagr_rank.empty:
                df_cagr_display = df_cagr_rank.copy()
                df_cagr_display['CAGR'] = df_cagr_display['CAGR (Cresc. Dividendo)'].apply(lambda x: f"{x:.2f}%".replace(".", ","))
                
                st.dataframe(
                    df_cagr_display[['Ticker', 'CAGR', 'Setor']], 
                    use_container_width=True
                )
                
                fig_cagr = px.bar(df_cagr_rank, x='Ticker', y='CAGR (Cresc. Dividendo)', color='Setor',
                                  title='Ranking de Crescimento (CAGR) do Dividendo Anual')
                fig_cagr.update_layout(yaxis_title='CAGR (%)', yaxis_tickformat=',.2f', height=400)
                st.plotly_chart(fig_cagr, use_container_width=True)
            else:
                st.info("Não há dados de crescimento (CAGR) positivos para ranking entre as empresas analisadas.")
                
        else:
            st.error("❌ Não foi possível calcular nenhuma métrica de dividendos. Verifique a conectividade com o Yahoo Finance.")

        st.markdown("---")
        st.info("""
**📝 Fonte de Dados de Dividendos:** A análise utiliza o pacote `yfinance` para buscar proventos por ação e cotação diretamente do Yahoo Finance.
""")
        
# ==============================
# VISÃO POR EMPRESA
# ==============================
elif modo_analise == "📈 Visão por Empresa":
    
    if df_filtrado.empty:
        st.warning(f"Não há dados disponíveis para o Ticker {ticker_selecionado} no ano {ano_selecionado}.")
        st.stop()
        
    st.header(f"📊 Análise Detalhada - {ticker_selecionado}")
    
    # Busca de dados de mercado
    dados_cotacao = buscar_cotacao_atual(ticker_selecionado)
    
    # Informações da empresa
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        st.metric("Ano Fiscal", ano_selecionado)
    with col2:
        st.metric("Setor", df_filtrado["SETOR_ATIV"].iloc[0] if not df_filtrado.empty else "N/A")
    with col3:
        st.markdown(f"**Cotação Atual:** R$ {dados_cotacao['cotacao']:,.2f} em {dados_cotacao['data_atualizacao']}".replace(",", "X").replace(".", ",").replace("X", ".") if dados_cotacao else "Cotação: N/A")
        
    st.divider()

    # Abas de Análise Detalhada
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Análise do Ano", "📈 Evolução Temporal", "💰 Dividendos", "💵 Simulação Investimento"])

    with tab1:
        st.subheader("Indicadores de Rentabilidade e Lucratividade")
        
        row = df_filtrado.iloc[-1]
        
        col_roe, col_roa, col_margem, col_wacc = st.columns(4)
        
        with col_roe:
            st.metric("ROE (Retorno s/ PL)", formatar_percentual_brasil(row["ROE"]), delta=f"Margem Líquida: {formatar_percentual_brasil(row['Margem Líquida'])}")
        with col_roa:
            st.metric("ROA (Retorno s/ Ativo)", formatar_percentual_brasil(row["ROA"]), delta=f"ROI: {formatar_percentual_brasil(row['ROI'])}")
        with col_margem:
            st.metric("Margem Operacional", formatar_percentual_brasil(row["Margem Operacional"]), delta=f"Margem Bruta: {formatar_percentual_brasil(row['Margem Bruta'])}")
        with col_wacc:
            st.metric("WACC (Custo de Capital)", formatar_percentual_brasil(row["wacc"]), delta=f"ke: {formatar_percentual_brasil(row['ke'])}")

        st.markdown("---")
        st.subheader("Lucro e Caixa")
        
        col_lucro, col_ebitda, col_le = st.columns(3)
        
        with col_lucro:
            st.metric("Lucro Líquido", formatar_moeda_brasil_correta(row["Lucro/Prejuízo Consolidado do Período"], 2))
        
        with col_ebitda:
            st.metric("EBITDA", formatar_moeda_brasil_correta(row["EBITDA"], 2))
            
        with col_le:
            le_valor = row["Lucro Econômico 2"]
            le_delta = row["Diferença Lucro Econômico"]
            st.metric("Lucro Econômico", formatar_moeda_brasil_correta(le_valor, 2), delta=f"Diferença LE: {formatar_moeda_brasil_correta(le_delta, 2)}", delta_color="off")
        
        # Valuation por Lucro Econômico
        st.markdown("---")
        st.subheader("Valuation por Lucro Econômico/SELIC (15%)")
        
        le_calculado = row["Lucro Econômico 2"]
        valor_empresa = calcular_valuation_lucro_economico_selic(le_calculado, selic_percentual=15)
        
        if valor_empresa and dados_cotacao and dados_cotacao.get('market_cap'):
            market_cap_estimado = valor_empresa * 1000 # Converter de R$ mil para R$
            market_cap_atual = dados_cotacao.get('market_cap')
            
            if market_cap_atual and market_cap_atual > 0:
                diferenca_percentual = ((market_cap_estimado - market_cap_atual) / market_cap_atual)
                
                col_cap_estimado, col_cap_atual, col_diferenca = st.columns(3)
                
                with col_cap_estimado:
                    st.metric("Market Cap Estimado (LE/SELIC)", formatar_moeda_brasil_correta(valor_empresa, 2))
                
                with col_cap_atual:
                    market_cap_formatado = formatar_moeda_brasil_correta(market_cap_atual / 1000, 2)
                    st.metric("Market Cap Atual", market_cap_formatado)
                
                with col_diferenca:
                    st.metric("Diferença Estimado/Atual", f"{diferenca_percentual:.2%}".replace(".", ","), 
                              delta_color=("inverse" if diferenca_percentual < 0 else "normal"))

                st.info(f"O Market Cap estimado pelo modelo LE/SELIC (15%) é **{diferenca_percentual:.2%}".replace(".", ",") + f"** diferente do Market Cap de mercado.")
            else:
                st.warning("Market Cap atual não encontrado via Yahoo Finance.")
        else:
            st.warning("Não foi possível calcular o Valuation por Lucro Econômico (LE precisa ser > 0 ou Market Cap não disponível).")


    with tab2:
        st.subheader("Evolução Temporal dos Indicadores")
        
        # Filtro de anos
        anos_historico = st.slider("Selecione o período histórico (anos):", 
                                   min_value=df_empresa_todos_anos["Ano"].min(),
                                   max_value=df_empresa_todos_anos["Ano"].max(),
                                   value=(df_empresa_todos_anos["Ano"].min(), df_empresa_todos_anos["Ano"].max()),
                                   key="slider_anos_evolucao")
        
        df_historico_filtrado = df_empresa_todos_anos[(df_empresa_todos_anos["Ano"] >= anos_historico[0]) & (df_empresa_todos_anos["Ano"] <= anos_historico[1])]
        
        if not df_historico_filtrado.empty:
            
            # Gráfico de Rentabilidade
            st.markdown("---")
            st.subheader("Rentabilidade (ROE, ROA, ROI)")
            df_rentabilidade = df_historico_filtrado[["Ano", "ROE", "ROA", "ROI"]].melt(
                id_vars="Ano", var_name="Indicador", value_name="Valor"
            )
            fig_rent = px.line(df_rentabilidade, x="Ano", y="Valor", color="Indicador", 
                               title="Evolução Anual dos Indicadores de Retorno")
            fig_rent.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_rent, use_container_width=True)
            
            # Gráfico de Margens
            st.markdown("---")
            st.subheader("Margens (Bruta, Operacional, Líquida)")
            df_margem = df_historico_filtrado[["Ano", "Margem Bruta", "Margem Operacional", "Margem Líquida"]].melt(
                id_vars="Ano", var_name="Indicador", value_name="Valor"
            )
            fig_margem = px.line(df_margem, x="Ano", y="Valor", color="Indicador",
                                 title="Evolução Anual das Margens")
            fig_margem.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_margem, use_container_width=True)
            
            # Gráfico de Lucro Líquido vs EBITDA
            st.markdown("---")
            st.subheader("Lucro Líquido e EBITDA (R$ Mil)")
            df_lucro_ebitda = df_historico_filtrado[["Ano", "Lucro/Prejuízo Consolidado do Período", "EBITDA"]].copy()
            df_lucro_ebitda.columns = ["Ano", "Lucro Líquido (R$ mil)", "EBITDA (R$ mil)"]
            df_lucro_ebitda_melt = df_lucro_ebitda.melt(
                id_vars="Ano", var_name="Conta", value_name="Valor"
            )
            fig_lucro_ebitda = px.bar(df_lucro_ebitda_melt, x="Ano", y="Valor", color="Conta", barmode="group",
                                      title="Evolução Anual do Lucro Líquido e EBITDA")
            fig_lucro_ebitda.update_layout(yaxis_tickformat=',.0f')
            st.plotly_chart(fig_lucro_ebitda, use_container_width=True)
            
        else:
            st.info("Filtro de anos muito restritivo. Ajuste o seletor.")


    with tab3:
        st.subheader("💰 Dividendos")
        
        # Buscar dados de dividendos
        df_dividendos = buscar_dividendos_historicos(ticker_selecionado)
        
        if df_dividendos is not None:
            # Calcular estatísticas
            stats = calcular_estatisticas_dividendos(df_dividendos)
            
            st.subheader(f"Estatísticas Históricas de Dividendos de {ticker_selecionado}")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Pago (desde 2010)", f"R$ {stats['total_dividendos']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            with col2:
                st.metric("Média Anual", f"R$ {stats['media_anual']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            with col3:
                st.metric("Último Provento", f"R$ {stats['ultimo_dividendo']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), help=f"Data: {stats['data_ultimo'].strftime('%d/%m/%Y') if stats['data_ultimo'] else 'N/A'}")
            
            # Calcular Dividend Yield (últimos 12 meses)
            # Como a função calcular_ranking_dividendos foi removida, usamos a lógica direta para o DY:
            cotacao_atual = buscar_cotacao_atual(ticker_selecionado)['cotacao'] if buscar_cotacao_atual(ticker_selecionado) else 0
            
            data_limite_dy = datetime.now() - timedelta(days=365)
            dividendos_12m = df_dividendos[df_dividendos['Data'] >= data_limite_dy]
            
            dy_12m = None
            if not dividendos_12m.empty and cotacao_atual > 0:
                total_dividendos_12m = dividendos_12m['Dividendo'].sum()
                dy_12m = (total_dividendos_12m / cotacao_atual) * 100
            
            with col4:
                st.metric("Dividend Yield (12M)", formatar_percentual_brasil(dy_12m / 100) if dy_12m is not None else "N/A")

            st.markdown("---")
            
            # Agrupar dividendos por ano para o gráfico
            df_dividendos_anual = df_dividendos.groupby('Ano')['Dividendo'].sum().reset_index()
            df_dividendos_anual.columns = ['Ano', 'Total Dividendo (R$)']
            
            fig_dividendo = px.bar(df_dividendos_anual, x='Ano', y='Total Dividendo (R$)',
                                   title=f"Total de Proventos Pagos por Ano - {ticker_selecionado}")
            fig_dividendo.update_layout(yaxis_tickformat=',.2f')
            st.plotly_chart(fig_dividendo, use_container_width=True)
            
            st.subheader("Histórico Detalhado")
            df_dividendos_display = df_dividendos[['Data', 'Dividendo']].copy()
            df_dividendos_display.columns = ['Data (Ex)', 'Valor (R$)']
            df_dividendos_display['Valor (R$)'] = df_dividendos_display['Valor (R$)'].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
            df_dividendos_display['Data (Ex)'] = df_dividendos_display['Data (Ex)'].dt.strftime('%d/%m/%Y')
            st.dataframe(df_dividendos_display.sort_values('Data (Ex)', ascending=False), use_container_width=True)
            
        else:
            st.warning(f"Não foi possível buscar dados históricos de dividendos para {ticker_selecionado} no Yahoo Finance.")


    with tab4:
        st.subheader("💵 Simulação de Investimento por Lotes")
        st.write("Simule a compra de lotes de ações desde uma data específica")
        
        col_data, col_lote = st.columns(2)
        
        with col_data:
            data_compra_simulacao = st.date_input("Data da compra", 
                                                  value=datetime(2015, 1, 1).date(), 
                                                  min_value=datetime(2000, 1, 1).date(), 
                                                  max_value=datetime.now().date() - timedelta(days=365),
                                                  key="data_simulacao")
            
        with col_lote:
            lote_selecionado = st.selectbox(
                "Tamanho do lote:",
                [100, 1000, 10000],
                index=0,
                format_func=lambda x: f"{x} ações",
                key="lote_simulacao"
            )

        st.markdown("""
💡 **Tipos de lote:**
* 100 ações: Lote padrão
* 1.000 ações: Lote intermediário
* 10.000 ações: Lote grande
        """)
        
        if st.button("Executar Simulação", key="btn_simulacao"):
            
            st.subheader("Resultados da Simulação")
            
            # Execução da simulação
            resultados = simular_investimento_lotes(
                ticker_selecionado, 
                data_compra_simulacao,
                lote_selecionado
            )
            
            if resultados:
                
                col_investido, col_atual, col_dividendo, col_ganho_total = st.columns(4)
                
                with col_investido:
                    st.metric("Valor Investido", f"R$ {resultados['valor_investido']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    st.caption(f"Preço de compra: R$ {resultados['preco_compra']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                with col_atual:
                    st.metric("Valor Atual", f"R$ {resultados['valor_investido_atual']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    st.caption(f"Preço atual: R$ {resultados['preco_atual']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    
                with col_dividendo:
                    st.metric("Total Dividendos", f"R$ {resultados['total_dividendos_recebidos']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    
                with col_ganho_total:
                    st.metric("Ganho Total", f"R$ {resultados['ganho_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), 
                              delta=f"Rentabilidade Total: {resultados['rentabilidade_total_percentual']:,.2f}%".replace(".", ","))
                              
                
                st.markdown("---")
                st.subheader("Detalhamento da Rentabilidade")
                
                col_rent_preco, col_rent_dividendo, col_rent_total = st.columns(3)
                
                with col_rent_preco:
                    st.metric("Rentabilidade (Apreciação)", f"{resultados['rentabilidade_preco_percentual']:,.2f}%".replace(".", ","))
                
                with col_rent_dividendo:
                    st.metric("Rentabilidade (Dividendos)", f"{resultados['rentabilidade_dividendos_percentual']:,.2f}%".replace(".", ","))
                
                with col_rent_total:
                    st.metric("Rentabilidade Total", f"{resultados['rentabilidade_total_percentual']:,.2f}%".replace(".", ","))
                
            else:
                st.error("""
❌ Não foi possível realizar a simulação
""")

# ==============================
# ANÁLISE SETORIAL
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    
    st.header(f"🏭 Análise Setorial - {setor_selecionado}")
    
    # Adicionar aqui a lógica de análise setorial, caso deseje (não estava no escopo inicial)
    st.info("Funcionalidade de Análise Setorial não implementada neste momento. Filtre por setor na aba 'Dados Gerais' para rankings.")

# FIM DO SCRIPT
