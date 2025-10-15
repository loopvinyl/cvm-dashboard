# ==============================================================
# 📊 DASHBOARD CVM - Indicadores Financeiros (VERSÃO CONSOLIDADA COMPLETA)
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

# ==============================
# FUNÇÃO PARA PRÉ-SELEÇÃO DE TICKERS CONSISTENTES
# ==============================
@st.cache_data(ttl=86400) # Cache por 24 horas
def calcular_tickers_consistentes(df_cvm, ano_minimo_cvm=2010):
    """
    Identifica tickers que pagaram dividendos em TODOS os anos
    do período CVM (2010) até o ano fiscal mais recente.
    """
    st.info("🔎 **Pré-filtrando:** Buscando tickers que pagaram dividendos anualmente desde 2010. Esta etapa pode demorar.")
    
    # 1. Definir o período de análise CVM
    ano_maximo_cvm = df_cvm['Ano'].max()
    anos_necessarios = list(range(ano_minimo_cvm, ano_maximo_cvm + 1))
    
    # Reduzir a lista de tickers a serem verificados (apenas os do último ano)
    tickers_validos = df_cvm[df_cvm['Ano'] == ano_maximo_cvm]['Ticker'].unique()
    
    tickers_consistentes = []
    
    total_steps = len(tickers_validos)
    progress_bar = st.progress(0, text="Verificando consistência anual de dividendos...")
    
    for i, ticker in enumerate(tickers_validos):
        df_dividendos = buscar_dividendos_historicos(ticker)
        
        if df_dividendos is not None and not df_dividendos.empty:
            
            # Anos em que houve pagamento de dividendo para este ticker
            anos_com_pagamento = df_dividendos[df_dividendos['Dividendo'] > 0]['Ano'].unique()
            
            # Verificar se o ticker pagou em todos os anos necessários
            if all(ano in anos_com_pagamento for ano in anos_necessarios):
                tickers_consistentes.append(ticker)
        
        time.sleep(0.01) # Pequeno atraso para não travar a barra
        
        percent_complete = (i + 1) / total_steps
        progress_bar.progress(percent_complete, text=f"Verificando {ticker} ({i+1}/{total_steps})...")

    progress_bar.empty()
    st.success(f"✅ {len(tickers_consistentes)} tickers identificados com pagamento anual consistente desde {ano_minimo_cvm}.")
    return tickers_consistentes

# ==============================
# SISTEMA DE RANKING DE DIVIDENDOS OTIMIZADO (Foco em DY de 10 Anos)
# ==============================
@st.cache_data(ttl=86400) # Cache por 24 horas
def calcular_ranking_dividendos(tickers_consistentes, periodo_dy_anos=10):
    """
    Calcula o Dividend Yield médio dos últimos 10 anos (ou período disponível)
    para o conjunto de tickers consistentes e ranqueia o Top 10.
    """
    
    dados_ranking = []
    
    if not tickers_consistentes:
        return pd.DataFrame()

    st.warning(f"⚠️ **Busca em tempo real (yfinance):** Calculando DY médio de {periodo_dy_anos} anos para {len(tickers_consistentes)} tickers consistentes.")

    with st.spinner(f"Calculando DY médio para {len(tickers_consistentes)} empresas..."):
        
        total_steps = len(tickers_consistentes)
        progress_bar = st.progress(0, text="Buscando dados de mercado...")
        
        for i, ticker in enumerate(tickers_consistentes):
            
            # 1. Buscar Cotação e Setor
            dados_cotacao = buscar_cotacao_atual(ticker)
            
            # 2. Buscar Histórico de Preços e Dividendos
            data_inicio = datetime.now() - timedelta(days=365 * periodo_dy_anos)
            
            # Buscando todo o histórico (max) para garantir preço final do ano
            df_historico_precos = buscar_historico_precos(ticker, "max")
            df_dividendos = buscar_dividendos_historicos(ticker)
            
            dy_medio_10a = None
            
            if dados_cotacao and df_historico_precos is not None and df_dividendos is not None and not df_dividendos.empty:
                
                # Filtrar histórico e dividendos para os últimos 10 anos (ou menos se não houver dados)
                df_historico_precos_filtrado = df_historico_precos[df_historico_precos.index >= data_inicio]
                df_dividendos_filtrado = df_dividendos[df_dividendos['Data'] >= data_inicio]
                
                if not df_historico_precos_filtrado.empty and not df_dividendos_filtrado.empty:
                    
                    # 1. Agrupar dividendos por ano
                    df_dividendos_anual = df_dividendos_filtrado.groupby(df_dividendos_filtrado['Data'].dt.year)['Dividendo'].sum()
                    
                    # 2. Pegar o preço de fechamento do final de cada ano
                    precos_anuais = df_historico_precos_filtrado.resample('Y').last()['Close'].dropna()
                    
                    # 3. Calcular o DY anual (Soma Dividendo Anual / Preço Final do Ano)
                    dy_anuais = []
                    for ano, dividendo_total in df_dividendos_anual.items():
                        # Tenta encontrar o preço de fechamento no ano fiscal
                        ano_fiscal_end = datetime(ano, 12, 31)
                        if ano_fiscal_end.year in precos_anuais.index.year:
                            preco_final = precos_anuais[precos_anuais.index.year == ano].iloc[0]
                            if preco_final > 0:
                                # DY = (Dividendo total do ano) / (Preço final do ano)
                                dy_anual = (dividendo_total / preco_final) * 100
                                dy_anuais.append(dy_anual)
                    
                    if dy_anuais:
                        dy_medio_10a = np.mean(dy_anuais)
            
            # Incluir dados no ranking
            if dados_cotacao is not None:
                dados_ranking.append({
                    'Ticker': ticker,
                    'Setor': dados_cotacao.get('setor', 'N/A'),
                    'Cotação Atual': dados_cotacao['cotacao'],
                    f'DY Médio ({periodo_dy_anos}A)': dy_medio_10a
                })
            
            # Atraso para evitar rate limit
            time.sleep(0.5) 
            
            # Atualiza a barra de progresso
            percent_complete = (i + 1) / total_steps
            progress_bar.progress(percent_complete, text=f"Buscando {ticker} ({i+1}/{total_steps})...")

        progress_bar.empty()
    
    return pd.DataFrame(dados_ranking).fillna(0)


# ==============================
# NOVO: FUNÇÃO PARA CALCULAR RANKING DE RETORNO TOTAL
# ==============================
@st.cache_data(ttl=3600, show_spinner=False) # Cache por 1 hora
def calcular_ranking_retorno_total(tickers_validos, data_inicio, valor_investido_inicial):
    """
    Calcula o ranking de retorno total (valorização + dividendos) para todos os tickers válidos.
    """
    dados_ranking = []
    
    # Placeholder para progresso
    st.info(f"⏳ **Calculando Ranking:** Buscando histórico de preços e proventos para {len(tickers_validos)} tickers. Aguarde...")
    progress_bar = st.progress(0, text="Iniciando simulação...")
    
    for i, ticker in enumerate(tickers_validos):
        resultado = simular_investimento_valor(ticker, data_inicio, valor_investido_inicial)
        
        if resultado is not None:
            dados_ranking.append(resultado)
        
        # Atualiza a barra de progresso
        percent_complete = (i + 1) / len(tickers_validos)
        progress_bar.progress(percent_complete, text=f"Simulando {ticker} ({i+1}/{len(tickers_validos)})...")

    progress_bar.empty()
    
    df_ranking = pd.DataFrame(dados_ranking)
    
    if df_ranking.empty:
        st.warning("⚠️ Não foi possível obter dados para simulação com a data e tickers selecionados.")
        return pd.DataFrame()
    
    # Classificar pelo maior retorno total
    df_ranking = df_ranking.sort_values('Rentabilidade Total (%)', ascending=False)
    
    # Top 13
    return df_ranking.head(13).reset_index(drop=True)


# ==============================
# FUNÇÕES DE VALUATION E SIMULAÇÃO
# ==============================
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
    Simula um investimento por quantidade de ações (lotes).
    Retorna None se os dados de preço (histórico) não puderem ser obtidos.
    Retorna um dicionário com 'error': True se ocorrer um erro inesperado.
    """
    try:
        if isinstance(data_inicio, date) and not isinstance(data_inicio, datetime):
            data_inicio = datetime(data_inicio.year, data_inicio.month, data_inicio.day)
        elif isinstance(data_inicio, str):
             data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        
        # 1. Buscar histórico de preços
        historico = buscar_historico_precos(ticker, "max")
        
        if historico is None:
            return None # FALHA CRÍTICA: SEM DADOS DE PREÇO
        
        # 2. Buscar dividendos
        dividendos = buscar_dividendos_historicos(ticker)
        
        # 3. Encontrar o primeiro preço disponível após a data de início
        precos_apos_inicio = historico[historico.index >= data_inicio]
        if precos_apos_inicio.empty:
            return None # FALHA CRÍTICA: NENHUM DADO DE PREÇO ENCONTRADO NO PERÍODO
        
        primeira_data = precos_apos_inicio.index[0]
        preco_compra = precos_apos_inicio['Close'].iloc[0]
        
        # Se o preço de compra ser zero, abortar para evitar divisão por zero
        if preco_compra == 0:
            return {'error': True, 'message': "Preço de compra zero, simulação impossível."}
        
        # 4. Calcular valor investido baseado na quantidade de ações
        valor_investido = quantidade_acoes * preco_compra
        
        # 5. Preço atual (último preço disponível)
        preco_atual = historico['Close'].iloc[-1]
        
        # 6. Calcular dividendos recebidos desde a data de compra
        total_dividendos_recebidos = 0
        
        # Se houver dados de dividendos
        if dividendos is not None and not dividendos.empty:
            dividendos_apos_compra = dividendos[dividendos['Data'] >= primeira_data]
            total_dividendos_recebidos = (dividendos_apos_compra['Dividendo'] * quantidade_acoes).sum()
        
        # 7. Calcular valores atuais
        valor_investido_atual = quantidade_acoes * preco_atual
        ganho_preco = valor_investido_atual - valor_investido
        # O Ganho Total inclui o Ganho de Preço + Dividendos (que será 0 se não houver proventos)
        ganho_total = ganho_preco + total_dividendos_recebidos
        
        # 8. Calcular percentuais
        rentabilidade_dividendos_percentual = (total_dividendos_recebidos / valor_investido) * 100
        rentabilidade_preco_percentual = (ganho_preco / valor_investido) * 100
        rentabilidade_total_percentual = (ganho_total / valor_investido) * 100
        
        # Adicionar uma flag para indicar se os dividendos foram zero
        sem_dividendos = total_dividendos_recebidos == 0
        
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
            'rentabilidade_total_percentual': rentabilidade_total_percentual,
            'sem_dividendos': sem_dividendos # NOVA FLAG
        }
        
    except Exception as e:
        # Erro inesperado no meio do cálculo
        return {'error': True, 'message': f"Erro inesperado no cálculo: {e}"}

# ==============================
# NOVO: FUNÇÃO PARA SIMULAR INVESTIMENTO POR VALOR (PARA RANKING DE RETORNO)
# ==============================
def simular_investimento_valor(ticker, data_inicio, valor_investido_inicial):
    """
    Simula um investimento baseado em um valor monetário inicial.
    Retorna o dicionário de resultados para o ranking, ou None/Erro.
    """
    try:
        if isinstance(data_inicio, date) and not isinstance(data_inicio, datetime):
            data_inicio = datetime(data_inicio.year, data_inicio.month, data_inicio.day)
        elif isinstance(data_inicio, str):
             data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        
        # 1. Buscar histórico de preços
        historico = buscar_historico_precos(ticker, "max")
        if historico is None:
            return None # FALHA CRÍTICA: SEM DADOS DE PREÇO
        
        # 2. Encontrar o primeiro preço disponível após a data de início
        precos_apos_inicio = historico[historico.index >= data_inicio]
        if precos_apos_inicio.empty:
            return None # FALHA CRÍTICA: NENHUM DADO DE PREÇO ENCONTRADO NO PERÍODO
        
        primeira_data = precos_apos_inicio.index[0]
        preco_compra = precos_apos_inicio['Close'].iloc[0]
        
        # Se o preço de compra for zero, abortar
        if preco_compra == 0:
            return None
        
        # CÁLCULO CHAVE: Quantidade de ações compradas (pode ser fracionária)
        quantidade_acoes = valor_investido_inicial / preco_compra
        
        # 3. Buscar dividendos
        dividendos = buscar_dividendos_historicos(ticker)
        
        # 4. Preço atual (último preço disponível)
        preco_atual = historico['Close'].iloc[-1]
        
        # 5. Calcular dividendos recebidos desde a data de compra
        total_dividendos_recebidos = 0
        if dividendos is not None and not dividendos.empty:
            dividendos_apos_compra = dividendos[dividendos['Data'] >= primeira_data]
            # Usa a quantidade de ações calculada (pode ser fracionária)
            total_dividendos_recebidos = (dividendos_apos_compra['Dividendo'] * quantidade_acoes).sum()
        
        # 6. Calcular valores atuais
        valor_investido_atual = quantidade_acoes * preco_atual
        # Ganho Total: (Valor Final Ações - Valor Inicial) + Dividendos
        ganho_total = (valor_investido_atual - valor_investido_inicial) + total_dividendos_recebidos
        
        # 7. Calcular percentual de retorno total
        rentabilidade_total_percentual = (ganho_total / valor_investido_inicial) * 100
        
        # 8. Buscar setor para exibição
        dados_cotacao = buscar_cotacao_atual(ticker)
        setor = dados_cotacao.get('setor', 'N/A') if dados_cotacao else 'N/A'
        
        return {
            'Ticker': ticker,
            'Setor': setor,
            'Data Compra': primeira_data,
            'Valor Investido Inicial': valor_investido_inicial,
            'Valor Final Ações': valor_investido_atual,
            'Total Dividendos': total_dividendos_recebidos,
            'Ganho Total': ganho_total,
            'Rentabilidade Total (%)': rentabilidade_total_percentual
        }
        
    except Exception:
        # Erro silencioso para que o ranking continue o cálculo
        return None

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

# ==============================
# CARREGAMENTO E PRÉ-PROCESSAMENTO DOS DADOS CVM
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
# CONFIGURAÇÃO INICIAL DO STREAMLIT
# ==============================
st.set_page_config(page_title="Dashboard CVM - Indicadores", layout="wide")
st.title("Dashboard CVM: Análise das Demonstrações Financeiras")

# ==============================
# PRÉ-FILTRO DE CONSISTÊNCIA (EXECUÇÃO INICIAL)
# ==============================
# Esta etapa é executada uma vez devido ao @st.cache_data
with st.sidebar:
    st.header("🔧 Filtros Principais")
    
    # Controle para executar o pré-filtro de dividendos
    executar_pre_filtro = st.checkbox("Executar pré-filtro de dividendos consistentes", value=False,
                                     help="Busca tickers que pagaram dividendos anualmente desde 2010")

TICKERS_CONSISTENTES = []
if executar_pre_filtro:
    TICKERS_CONSISTENTES = calcular_tickers_consistentes(df)

# ==============================
# SIDEBAR - FILTROS PRINCIPAIS
# ==============================
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
else:
    # Dados Gerais
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
    rank_tab1, rank_tab2, rank_tab3, rank_tab4, rank_tab5, rank_tab6 = st.tabs([ 
        "📈 Rentabilidade", 
        "💰 Lucro, Receita e Caixa", 
        "🏛️ Solidez", 
        "📊 Eficiência", 
        "👑 Dividendos Consistentes",
        "🚀 Maior Retorno" # NOVA ABA
    ])

    # --- RANKING DE RENTABILIDADE ---
    with rank_tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 15 Empresas por ROE")
            roe_ranking = df_filtrado[df_filtrado["ROE"].notna()].nlargest(15, "ROE")[["Ticker", "SETOR_ATIV", "ROE"]]
            if not roe_ranking.empty:
                fig_roe_rank = px.bar(roe_ranking, x="Ticker", y="ROE", color="SETOR_ATIV", title="Ranking de ROE (Return on Equity)")
                fig_roe_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_roe_rank, use_container_width=True)
            else:
                st.warning("Não há dados de ROE disponíveis para ranking")
        with col2:
            st.subheader("Top 15 Empresas por ROA")
            roa_ranking = df_filtrado[df_filtrado["ROA"].notna()].nlargest(15, "ROA")[["Ticker", "SETOR_ATIV", "ROA"]]
            if not roa_ranking.empty:
                fig_roa_rank = px.bar(roa_ranking, x="Ticker", y="ROA", color="SETOR_ATIV", title="Ranking de ROA (Return on Assets)")
                fig_roa_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_roa_rank, use_container_width=True)
            else:
                st.warning("Não há dados de ROA disponíveis para ranking")

        st.subheader("📋 Tabela de Rentabilidade - Top 20")
        rentabilidade_consolidado = df_filtrado[
            df_filtrado["ROE"].notna() & df_filtrado["ROA"].notna() & df_filtrado["ROI"].notna()
        ].nlargest(20, "ROE")[["Ticker", "SETOR_ATIV", "ROE", "ROA", "ROI", "Margem Líquida"]]
        
        if not rentabilidade_consolidado.empty:
            rentabilidade_formatado = formatar_dataframe_percentual(
                rentabilidade_consolidado, ['ROE', 'ROA', 'ROI', 'Margem Líquida']
            )
            st.dataframe(rentabilidade_formatado, use_container_width=True)
        else:
            st.warning("Não há dados suficientes para exibir a tabela consolidada")


    # --- RANKING DE LUCRO, RECEITA E CAIXA ---
    with rank_tab2:
        
        # --- RANKING DE CAIXA OPERACIONAL (TOP 13) ---
        st.subheader("🥇 Top 13 Empresas por Geração de Caixa Operacional")
        
        # Coluna do FCO no seu Excel
        coluna_fco = "Caixa Líquido Atividades Operacionais"
        fco_ranking = df_filtrado[df_filtrado[coluna_fco].notna()].nlargest(13, coluna_fco)[["Ticker", "SETOR_ATIV", coluna_fco]]
        
        if not fco_ranking.empty:
            fco_ranking["Caixa Op (R$)"] = fco_ranking[coluna_fco] * 1000 / 1e9 # Converter R$ mil para R$ bilhões
            fig_fco_rank = px.bar(fco_ranking, x="Ticker", y="Caixa Op (R$)", color="SETOR_ATIV", title="Ranking de Caixa Líquido de Atividades Operacionais (R$ Bilhões)")
            fig_fco_rank.update_layout(yaxis_tickformat=',.2f')
            st.plotly_chart(fig_fco_rank, use_container_width=True)
            
            fco_ranking["Caixa Operacional"] = fco_ranking[coluna_fco].apply(formatar_moeda_brasil_correta)
            st.dataframe(fco_ranking[["Ticker", "SETOR_ATIV", "Caixa Operacional"]], use_container_width=True)
        else:
            st.warning("Não há dados de Caixa Líquido Atividades Operacionais disponíveis para ranking.")

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 15 Empresas por Lucro Líquido")
            lucro_ranking = df_filtrado.nlargest(15, "Lucro/Prejuízo Consolidado do Período")[["Ticker", "SETOR_ATIV", "Lucro/Prejuízo Consolidado do Período"]]
            if not lucro_ranking.empty:
                lucro_ranking["Lucro (R$)"] = lucro_ranking["Lucro/Prejuízo Consolidado do Período"] * 1000 / 1e9 # Converter para bilhões
                fig_lucro_rank = px.bar(lucro_ranking, x="Ticker", y="Lucro (R$)", color="SETOR_ATIV", title="Ranking por Lucro Líquido (R$ Bilhões)")
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
                receita_ranking["Receita (R$)"] = receita_ranking["Receita de Venda de Bens e/ou Serviços"] * 1000 / 1e9 # Converter para bilhões
                fig_receita_rank = px.bar(receita_ranking, x="Ticker", y="Receita (R$)", color="SETOR_ATIV", title="Ranking por Receita (R$ Bilhões)")
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
                pl_ranking["PL (R$)"] = pl_ranking["Patrimônio Líquido Consolidado"] * 1000 / 1e9 # Converter para bilhões
                fig_pl_rank = px.bar(pl_ranking, x="Ticker", y="PL (R$)", color="SETOR_ATIV", title="Ranking de Patrimônio Líquido (R$ Bilhões)")
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
                fig_roi_rank = px.bar(roi_ranking, x="Ticker", y="ROI", color="SETOR_ATIV", title="Ranking de ROI (Return on Investment)")
                fig_roi_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_roi_rank, use_container_width=True)
            else:
                st.warning("Não há dados de ROI disponíveis para ranking")

    # --- RANKING DE EFICIÊNCIA ---
    with rank_tab4:
        st.subheader("Top 15 Empresas por Margem Líquida")
        margem_liquida_ranking = df_filtrado[df_filtrado["Margem Líquida"].notna()].nlargest(15, "Margem Líquida")[["Ticker", "SETOR_ATIV", "Margem Líquida"]]
        if not margem_liquida_ranking.empty:
            fig_margem_liquida_rank = px.bar(margem_liquida_ranking, x="Ticker", y="Margem Líquida", color="SETOR_ATIV", title="Ranking de Margem Líquida")
            fig_margem_liquida_rank.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_margem_liquida_rank, use_container_width=True)
            
            margem_liquida_formatado = formatar_dataframe_percentual(margem_liquida_ranking, ['Margem Líquida'])
            st.dataframe(margem_liquida_formatado, use_container_width=True)
        else:
            st.warning("Não há dados de Margem Líquida disponíveis para ranking")


    # --- RANKING DE DIVIDENDOS CONSISTENTES ---
    with rank_tab5:
        st.subheader("👑 Top 10 - Dividend Yield Médio (Empresas Consistentes)")
        
        if TICKERS_CONSISTENTES:
            df_ranking_dy = calcular_ranking_dividendos(TICKERS_CONSISTENTES, periodo_dy_anos=10)
            
            if not df_ranking_dy.empty:
                # Rankeia Top 10 e formata para exibição
                df_top_10_dy = df_ranking_dy[df_ranking_dy[f'DY Médio (10A)'].notna()].nlargest(10, f'DY Médio (10A)').reset_index(drop=True)
                
                if not df_top_10_dy.empty:
                    
                    df_top_10_dy.index = df_top_10_dy.index + 1
                    df_top_10_dy = df_top_10_dy.rename(columns={f'DY Médio (10A)': 'DY Médio (10 Anos)'})
                    df_top_10_dy_formatado = df_top_10_dy.copy()
                    
                    # Formatar Percentual (DY) e Moeda (Cotação)
                    df_top_10_dy_formatado['DY Médio (10 Anos)'] = df_top_10_dy_formatado['DY Médio (10 Anos)'].apply(lambda x: formatar_percentual_brasil(x/100, 2) if pd.notna(x) else 'N/A')
                    df_top_10_dy_formatado['Cotação Atual'] = df_top_10_dy_formatado['Cotação Atual'].apply(lambda x: f"R$ {formatar_numero_brasil_correto(x, 2)}")

                    st.dataframe(df_top_10_dy_formatado, use_container_width=True)
                    
                    # Gráfico
                    fig_dy_rank = px.bar(df_top_10_dy, x="Ticker", y="DY Médio (10 Anos)", color="Setor", title="DY Médio dos Últimos 10 Anos")
                    fig_dy_rank.update_layout(yaxis_tickformat='.2f')
                    st.plotly_chart(fig_dy_rank, use_container_width=True)
                
                else:
                    st.warning("Nenhum ticker consistente encontrado com DY calculado.")
            else:
                st.warning("Não foi possível calcular o DY médio para os tickers consistentes. Tente novamente mais tarde.")
        else:
            st.info("O filtro de 'dividendos consistentes' na barra lateral está desativado. Ative para calcular o ranking.")

    # --- NOVO RANKING DE MAIOR RETORNO ---
    with rank_tab6:
        st.header("🚀 Top 13 - Maior Retorno Total (Valorização + Dividendos)")
        st.markdown("""
            Esta simulação calcula a Rentabilidade Total (Valorização do Ativo + Proventos Recebidos)
            para todos os tickers com cotação disponível no período selecionado,
            assumindo um investimento inicial fixo.
        """)
        
        col_data, col_valor = st.columns(2)

        with col_data:
            data_minima = datetime(2010, 1, 1).date() # Filtro yfinance, convertido para date
            data_hoje = date.today()
            # Garante que a data inicial não seja futura ou hoje, se for o caso de não ter cotação. 
            data_investimento = st.date_input(
                "Selecione a Data de Início do Investimento:",
                value=data_hoje - timedelta(days=365 * 5), # Sugestão: 5 anos atrás
                min_value=data_minima,
                max_value=data_hoje - timedelta(days=1)
            )
            
        with col_valor:
            valores_sugeridos = [1_000, 10_000, 100_000, 1_000_000, 10_000_000]
            valor_selecionado = st.selectbox(
                "Selecione o Valor a ser Investido:",
                options=valores_sugeridos,
                index=2, # R$100.000
                format_func=lambda x: f"R$ {formatar_numero_brasil_correto(x, 0)}"
            )
        
        # Botão de execução é necessário devido à busca em tempo real e à quantidade de tickers
        if st.button(f"✨ Calcular TOP 13 Retorno para R$ {formatar_numero_brasil_correto(valor_selecionado, 0)}", key="btn_retorno_total"):
            
            # Garante que a data seja um objeto datetime.datetime
            data_para_simulacao = datetime.combine(data_investimento, datetime.min.time())
            
            # 5. Gerar a lista de todos os tickers CVM para o ranking
            todos_tickers = df["Ticker"].dropna().unique()

            df_retorno = calcular_ranking_retorno_total(list(todos_tickers), data_para_simulacao, valor_selecionado)

            if not df_retorno.empty:
                st.subheader(f"🥇 TOP 13 Tickers em Retorno Total (Investimento em {data_para_simulacao.strftime('%d/%m/%Y')})")
                
                # Formatação dos dados para exibição
                df_exibicao = df_retorno.copy()
                df_exibicao.index = df_exibicao.index + 1
                df_exibicao = df_exibicao.rename(columns={
                    'Rentabilidade Total (%)': 'Retorno Total (%)', 
                    'Valor Investido Inicial': f'Investido (R$)',
                    'Valor Final Ações': 'Valor Atual (R$)',
                    'Total Dividendos': 'Proventos (R$)',
                    'Ganho Total': 'Ganho Total (R$)'
                })
                df_exibicao = df_exibicao[['Ticker', 'Setor', 'Retorno Total (%)', f'Investido (R$)', 'Valor Atual (R$)', 'Proventos (R$)', 'Ganho Total (R$)']]
                
                # Aplicar formatações
                df_exibicao['Retorno Total (%)'] = df_exibicao['Retorno Total (%)'].apply(lambda x: formatar_percentual_brasil(x/100, 2) if pd.notna(x) else 'N/A')
                df_exibicao[f'Investido (R$)'] = df_exibicao[f'Investido (R$)'].apply(lambda x: formatar_numero_brasil_correto(x, 0))
                df_exibicao['Valor Atual (R$)'] = df_exibicao['Valor Atual (R$)'].apply(lambda x: formatar_numero_brasil_correto(x, 2))
                df_exibicao['Proventos (R$)'] = df_exibicao['Proventos (R$)'].apply(lambda x: formatar_numero_brasil_correto(x, 2))
                df_exibicao['Ganho Total (R$)'] = df_exibicao['Ganho Total (R$)'].apply(lambda x: formatar_numero_brasil_correto(x, 2))

                st.dataframe(
                    df_exibicao,
                    use_container_width=True
                )

                # Gráfico
                df_retorno_top = df_retorno.copy().head(13)
                fig_retorno = px.bar(
                    df_retorno_top, 
                    x='Ticker', 
                    y='Rentabilidade Total (%)', 
                    color='Setor', 
                    title=f"Rentabilidade Total do TOP 13 (Investido R$ {formatar_numero_brasil_correto(valor_selecionado, 0)})"
                )
                fig_retorno.update_layout(yaxis_tickformat='.2f')
                st.plotly_chart(fig_retorno, use_container_width=True)
                
            else:
                st.warning(f"Não foi possível calcular o retorno para nenhum ticker com a data de início {data_para_simulacao.strftime('%d/%m/%Y')}.")

# ==============================
# TELA - VISÃO POR EMPRESA (EXPANDIDA COM TODAS AS FUNCIONALIDADES)
# ==============================
elif modo_analise == "📈 Visão por Empresa":
    st.header(f"📊 Análise Detalhada - {ticker_selecionado}")
    
    if not df_empresa_todos_anos.empty:
        # Buscar dados de mercado
        dados_cotacao = buscar_cotacao_atual(ticker_selecionado)
        
        # Informações da empresa
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            st.metric("Ano Fiscal", ano_selecionado)
        with col2:
            st.metric("Setor", df_filtrado["SETOR_ATIV"].iloc[0] if not df_filtrado.empty else "N/A")
        with col3:
            if dados_cotacao:
                st.metric("Cotação Atual", f"R$ {dados_cotacao['cotacao']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                         delta=f"Atualizado: {dados_cotacao['data_atualizacao']}")
            else:
                st.metric("Cotação", "N/A")
        
        st.divider()

        # Abas para análise atual vs evolução temporal
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
                
                # Abas para diferentes categorias de indicadores
                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                    "📈 Rentabilidade", "💰 EBITDA", "🏛️ Estrutura Capital", "💸 Custo Capital", 
                    "📊 Lucro Econômico", "💵 Fluxo de Caixa"
                ])
                
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
                                    - Com o número de ações, podemos calcular o preço por ação teórico
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
                
                # QUARTA LINHA - FLUXO DE CAIXA OPERACIONAL
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
                                    'Caixa Líquido Atividades Operacionais']
                df_resumo = df_empresa_todos_anos[['Ano'] + [col for col in indicadores_resumo if col in df_empresa_todos_anos.columns]]
                
                # Formatar para porcentagem e valores monetários
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
        
        with tab_simulacao:
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
                
                # Modificação da lógica de exibição para tratar a nova flag 'error'
                if resultados and 'error' in resultados:
                    st.error(f"❌ Não foi possível realizar a simulação. **Detalhes:** {resultados['message']}")
                elif resultados:
                    
                    # Exibe a nota sobre a falta de dividendos, se for o caso
                    if resultados.get('sem_dividendos', False):
                        st.warning("⚠️ **Nota:** Nenhum provento (dividendo/JCP) foi distribuído ou registrado pelo Yahoo Finance para este ticker no período selecionado. O Ganho Total reflete apenas a valorização/desvalorização da cotação.")
                    
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
                    # Caso a função retorne None (falha crítica - falta de dados de preço)
                    st.error(f"""
    ❌ Não foi possível realizar a simulação.
    **Possíveis causas:** Dados de preço da ação não foram encontrados pelo Yahoo Finance para o período selecionado, a ação não possui histórico de negociação na bolsa ou a data de compra está fora do período disponível.
    """)

# ==============================
# TELA - ANÁLISE SETORIAL (EXPANDIDA COM TODAS AS FUNCIONALIDADES)
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    st.header(f"🏭 Análise Setorial - {setor_selecionado}")
    
    if not df_setor_todos_anos.empty:
        # Abas para análise atual vs evolução temporal
        tab_atual_setor, tab_evolucao_setor = st.tabs(["📊 Análise do Ano", "📈 Evolução Temporal"])
        
        with tab_atual_setor:
            st.subheader(f"Ano {ano_selecionado}")
            
            if not df_filtrado.empty:
                # KPIs do Setor
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
# RODAPÉ
# ==============================
st.divider()
st.caption(f"📊 Dashboard CVM - Indicadores Financeiros | Dados atualizados para {ano_selecionado} | Total de empresas na base: {df['Ticker'].nunique()}")
