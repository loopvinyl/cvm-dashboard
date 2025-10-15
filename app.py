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
# VISÃO POR EMPRESA (BLOCO RESTAURADO)
# ==============================
elif modo_analise == "📈 Visão por Empresa":
    if df_filtrado.empty:
        st.warning(f"Não há dados CVM para o ticker **{ticker_selecionado}** no ano de **{ano_selecionado}**.")
    else:
        dados_ano = df_filtrado.iloc[0]
        st.header(f"📈 {ticker_selecionado} - Visão Anual ({ano_selecionado})")
        
        # 1. KPIs
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Lucro Líquido", formatar_moeda_brasil_correta(dados_ano["Lucro/Prejuízo Consolidado do Período"]))
        with col2:
            st.metric("Receita", formatar_moeda_brasil_correta(dados_ano["Receita de Venda de Bens e/ou Serviços"]))
        with col3:
            st.metric("Patrimônio Líquido", formatar_moeda_brasil_correta(dados_ano["Patrimônio Líquido Consolidado"]))
        with col4:
            st.metric("ROE", formatar_percentual_brasil(dados_ano["ROE"]))

        st.divider()
        
        # 2. Tabs
        tab_ind, tab_hist, tab_val, tab_sim = st.tabs(["Indicadores", "Histórico", "Valuation", "Simulação Investimento"])
        
        # --- TAB INDICADORES ---
        with tab_ind:
            st.subheader("Indicadores de Rentabilidade e Estrutura")
            
            # Selecionar e formatar indicadores
            indicadores_basicos = {
                "ROE (Retorno sobre PL)": dados_ano["ROE"],
                "ROA (Retorno sobre Ativo)": dados_ano["ROA"],
                "ROI (Retorno sobre Investimento)": dados_ano["ROI"],
                "Margem Líquida": dados_ano["Margem Líquida"],
                "Margem Operacional": dados_ano["Margem Operacional"],
                "Margem Bruta": dados_ano["Margem Bruta"],
                "Capital Terceiros (%)": dados_ano["Percentual Capital Terceiros"],
                "Capital Próprio (%)": dados_ano["Percentual Capital Próprio"],
                "Alavancagem Eficaz": "Sim" if dados_ano["Alavancagem Eficaz"] else "Não"
            }
            
            df_indicadores = pd.DataFrame(indicadores_basicos.items(), columns=["Indicador", "Valor"])
            
            def formatar_indicador(row):
                if "%" in row["Indicador"]:
                    return formatar_percentual_brasil(row["Valor"])
                elif row["Indicador"] in ["Alavancagem Eficaz"]:
                    return row["Valor"]
                else:
                    return formatar_percentual_brasil(row["Valor"])
            
            df_indicadores["Valor Formatado"] = df_indicadores.apply(formatar_indicador, axis=1)
            st.dataframe(df_indicadores.set_index("Indicador")[["Valor Formatado"]], use_container_width=True)

        # --- TAB HISTÓRICO ---
        with tab_hist:
            st.subheader(f"Evolução Histórica de {ticker_selecionado}")
            
            df_grafico = df_empresa_todos_anos.copy()
            
            if not df_grafico.empty:
                
                # Gráfico de Lucro Líquido e Receita
                fig_ll_rec = make_subplots(specs=[[{"secondary_y": True}]])
                fig_ll_rec.add_trace(go.Bar(x=df_grafico["Ano"], y=df_grafico["Lucro/Prejuízo Consolidado do Período"], name='Lucro Líquido (R$ mil)'), secondary_y=False)
                fig_ll_rec.add_trace(go.Line(x=df_grafico["Ano"], y=df_grafico["Receita de Venda de Bens e/ou Serviços"], name='Receita (R$ mil)', line=dict(color='orange')), secondary_y=True)
                fig_ll_rec.update_layout(title_text="Lucro Líquido vs Receita (em R$ mil)")
                st.plotly_chart(fig_ll_rec, use_container_width=True)

                # Gráfico de Rentabilidade
                fig_rent = px.line(df_grafico, x="Ano", y=["ROE", "ROA", "ROI"], title="Evolução da Rentabilidade (ROE, ROA, ROI)")
                fig_rent.update_layout(yaxis_tickformat=".2%")
                st.plotly_chart(fig_rent, use_container_width=True)
            else:
                st.warning("Não há dados históricos disponíveis para esta empresa.")


        # --- TAB VALUATION ---
        with tab_val:
            st.subheader("Valuation Lucro Econômico vs. Preço de Mercado")
            
            # Buscar dados da cotação
            dados_cotacao = buscar_cotacao_atual(ticker_selecionado)
            
            if dados_cotacao and dados_cotacao['cotacao'] > 0:
                cotacao_atual = dados_cotacao['cotacao']
                
                # Pegar o Lucro Econômico mais recente disponível (do ano selecionado)
                lucro_economico = dados_ano.get("Lucro Econômico 1")
                
                if pd.notna(lucro_economico):
                    st.info(f"O **Lucro Econômico** de **{ticker_selecionado}** em **{ano_selecionado}** é de: **{formatar_moeda_brasil_correta(lucro_economico)}**.")
                    
                    # Número de ações e Taxa SELIC
                    num_acoes_col = "Numero Total de Ações" # Coluna do Excel
                    
                    # Tenta encontrar o número total de ações no dataframe CVM
                    num_acoes = dados_ano.get(num_acoes_col)
                    
                    if pd.notna(num_acoes) and num_acoes > 0:
                        
                        # Simulação da Taxa SELIC (assumida)
                        selic_assumida = st.slider("Taxa Anual (SELIC/WACC Assumido - %):", 5.0, 30.0, 15.0, 0.5)
                        
                        # 1. Calcular Valor da Empresa
                        valor_empresa_rs_mil = calcular_valuation_lucro_economico_selic(lucro_economico, selic_assumida)
                        
                        if valor_empresa_rs_mil:
                            valor_empresa_rs = valor_empresa_rs_mil * 1000 # Convertendo R$ mil para R$
                            
                            # 2. Calcular Preço por Ação
                            preco_calculado = valor_empresa_rs / num_acoes
                            
                            # 3. Exibir resultados e gráfico
                            st.subheader("Resultado do Valuation (Lucro Econômico/Custo de Capital)")
                            
                            col_val1, col_val2 = st.columns(2)
                            with col_val1:
                                st.metric("Valor Justo Calculado (R$)", f"{preco_calculado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                            with col_val2:
                                st.metric("Cotação Atual de Mercado (R$)", f"{cotacao_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                            
                            fig_comp = criar_grafico_comparativo(preco_calculado, cotacao_atual, ticker_selecionado)
                            st.plotly_chart(fig_comp, use_container_width=True)
                            
                            diferenca_percentual = ((cotacao_atual / preco_calculado) - 1) * 100
                            if diferenca_percentual < -20:
                                st.success(f"O ativo parece subvalorizado em {formatar_percentual_brasil(abs(diferenca_percentual)/100, 1)}.")
                            elif diferenca_percentual > 20:
                                st.error(f"O ativo parece sobrevalorizado em {formatar_percentual_brasil(diferenca_percentual/100, 1)}.")
                            else:
                                st.info("O preço de mercado está próximo do valor justo calculado.")

                        else:
                            st.warning("Não foi possível calcular o Valor da Empresa (Lucro Econômico <= 0).")
                            
                    else:
                        st.warning("Não foi possível encontrar o 'Número Total de Ações' no DFF para realizar o cálculo por ação.")
                else:
                    st.warning("Não há Lucro Econômico calculado para o ano e ticker selecionados.")
            else:
                st.warning("Não foi possível obter a cotação atual do ticker no Yahoo Finance.")

        # --- TAB SIMULAÇÃO ---
        with tab_sim:
            st.subheader(f"Simulação de Investimento em {ticker_selecionado}")
            
            col_q, col_d = st.columns(2)
            with col_q:
                quantidade_acoes = st.number_input("Quantidade de Ações (Lotes):", min_value=100, value=100, step=100)
            
            with col_d:
                data_minima = datetime(2010, 1, 1).date()
                data_hoje = date.today()
                data_compra = st.date_input(
                    "Data de Compra (Início do Período):",
                    value=data_hoje - timedelta(days=365 * 5),
                    min_value=data_minima,
                    max_value=data_hoje - timedelta(days=1)
                )

            # Simulação
            if st.button("Executar Simulação", key="btn_simular_lotes"):
                
                # Garantir que a data seja um objeto datetime.datetime
                data_para_simulacao = datetime.combine(data_compra, datetime.min.time())
                
                resultado = simular_investimento_lotes(ticker_selecionado, data_para_simulacao, quantidade_acoes)
                
                if resultado is None:
                    st.error("Não foi possível obter dados de preço ou dividendos para o período selecionado.")
                elif 'error' in resultado:
                    st.error(f"Erro na simulação: {resultado['message']}")
                else:
                    
                    st.markdown(f"#### Resultados da Simulação (Comprado em {resultado['data_compra'].strftime('%d/%m/%Y')})")

                    # KPIs da Simulação
                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        st.metric("Valor Investido Inicial", f"R$ {formatar_numero_brasil_correto(resultado['valor_investido'], 2)}")
                    with col_s2:
                        st.metric("Valor Total Atual", f"R$ {formatar_numero_brasil_correto(resultado['valor_investido_atual'] + resultado['total_dividendos_recebidos'], 2)}")
                    with col_s3:
                        st.metric("Rentabilidade Total", formatar_percentual_brasil(resultado['rentabilidade_total_percentual'] / 100))

                    st.markdown("---")
                    
                    col_r1, col_r2, col_r3 = st.columns(3)
                    with col_r1:
                        st.metric("Ganho por Valorização", f"R$ {formatar_numero_brasil_correto(resultado['ganho_preco'], 2)}", 
                                  delta=formatar_percentual_brasil(resultado['rentabilidade_preco_percentual'] / 100))
                    with col_r2:
                        st.metric("Total de Proventos", f"R$ {formatar_numero_brasil_correto(resultado['total_dividendos_recebidos'], 2)}", 
                                  delta=formatar_percentual_brasil(resultado['rentabilidade_dividendos_percentual'] / 100))
                    with col_r3:
                        st.metric("Ganho Total (R$)", f"R$ {formatar_numero_brasil_correto(resultado['ganho_total'], 2)}")

                    if resultado['sem_dividendos']:
                        st.info("⚠️ Não foram encontrados proventos pagos no período da simulação.")

# ==============================
# ANÁLISE SETORIAL (BLOCO RESTAURADO)
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    
    st.header(f"🏭 {setor_selecionado} - Análise Setorial ({ano_selecionado})")

    if df_filtrado.empty:
        st.warning(f"Não há dados CVM para o setor **{setor_selecionado}** no ano de **{ano_selecionado}**.")
    else:
        
        # 1. KPIs Setoriais
        receita_setor = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum()
        lucro_setor = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum()
        pl_setor = df_filtrado["Patrimônio Líquido Consolidado"].sum()
        roe_medio_setor = df_filtrado["ROE"].mean()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Empresas no Setor", df_filtrado["Ticker"].nunique())
        with col2:
            st.metric("Receita Total", formatar_moeda_brasil_correta(receita_setor))
        with col3:
            st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_setor))
        with col4:
            st.metric("ROE Médio", formatar_percentual_brasil(roe_medio_setor))

        st.divider()

        # 2. Tabs
        tab_rank_setor, tab_medias, tab_comp_hist = st.tabs(["Ranking Setorial", "Médias e Desvios", "Comparativo Histórico"])

        # --- TAB RANKING SETORIAL ---
        with tab_rank_setor:
            st.subheader(f"Top 10 Empresas no Setor {setor_selecionado}")
            
            col_r1, col_r2 = st.columns(2)
            
            with col_r1:
                st.markdown("##### Ranking por ROE")
                roe_ranking_setor = df_filtrado.nlargest(10, "ROE")[["Ticker", "ROE"]]
                roe_ranking_formatado = formatar_dataframe_percentual(roe_ranking_setor, ['ROE'])
                st.dataframe(roe_ranking_formatado, use_container_width=True)
            
            with col_r2:
                st.markdown("##### Ranking por Lucro Líquido")
                lucro_ranking_setor = df_filtrado.nlargest(10, "Lucro/Prejuízo Consolidado do Período")[["Ticker", "Lucro/Prejuízo Consolidado do Período"]]
                lucro_ranking_formatado = formatar_dataframe_moeda(lucro_ranking_setor, ["Lucro/Prejuízo Consolidado do Período"])
                lucro_ranking_formatado = lucro_ranking_formatado.rename(columns={"Lucro/Prejuízo Consolidado do Período": "Lucro"})
                st.dataframe(lucro_ranking_formatado, use_container_width=True)


        # --- TAB MÉDIAS E DESVIOS ---
        with tab_medias:
            st.subheader(f"Médias Setoriais de {setor_selecionado} ({ano_selecionado})")
            
            indicadores_setoriais = ["ROE", "ROA", "Margem Líquida", "Percentual Capital Terceiros"]
            df_medias = df_filtrado[indicadores_setoriais].mean().rename("Média Setorial")
            df_desvios = df_filtrado[indicadores_setoriais].std().rename("Desvio Padrão")
            
            df_analise = pd.concat([df_medias, df_desvios], axis=1).reset_index().rename(columns={"index": "Indicador"})
            
            # Formatação
            df_analise['Média Setorial Formatada'] = df_analise.apply(
                lambda row: formatar_percentual_brasil(row['Média Setorial']) if 'Margem' in row['Indicador'] or 'ROE' in row['Indicador'] or 'ROA' in row['Indicador'] or 'Percentual' in row['Indicador'] else formatar_percentual_brasil(row['Média Setorial']), axis=1
            )
            df_analise['Desvio Padrão Formatado'] = df_analise.apply(
                lambda row: formatar_percentual_brasil(row['Desvio Padrão']) if 'Margem' in row['Indicador'] or 'ROE' in row['Indicador'] or 'ROA' in row['Indicador'] or 'Percentual' in row['Indicador'] else formatar_percentual_brasil(row['Desvio Padrão']), axis=1
            )

            st.dataframe(df_analise[['Indicador', 'Média Setorial Formatada', 'Desvio Padrão Formatado']], use_container_width=True)

        # --- TAB COMPARATIVO HISTÓRICO ---
        with tab_comp_hist:
            st.subheader(f"Evolução Anual das Médias Setoriais")
            
            df_setor_anual = df_setor_todos_anos.groupby("Ano")[["ROE", "ROA", "Margem Líquida", "Lucro/Prejuízo Consolidado do Período"]].mean().reset_index()
            df_setor_anual = df_setor_anual.dropna()
            
            if not df_setor_anual.empty:
                # Gráfico de Rentabilidade
                fig_rent_setor = px.line(df_setor_anual, x="Ano", y=["ROE", "ROA"], title="Evolução da Rentabilidade Média Setorial")
                fig_rent_setor.update_layout(yaxis_tickformat=".2%")
                st.plotly_chart(fig_rent_setor, use_container_width=True)
                
                # Gráfico de Lucro Médio
                df_setor_anual['Lucro Médio (R$ mil)'] = df_setor_anual['Lucro/Prejuízo Consolidado do Período']
                fig_lucro_setor = px.bar(df_setor_anual, x="Ano", y="Lucro Médio (R$ mil)", title="Evolução do Lucro Líquido Médio (R$ mil)")
                st.plotly_chart(fig_lucro_setor, use_container_width=True)
            else:
                st.warning("Não há dados históricos consistentes para o setor selecionado.")
