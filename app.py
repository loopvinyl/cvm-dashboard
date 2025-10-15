# ==============================================================
# 📊 DASHBOARD CVM - Indicadores Financeiros (VERSÃO COMPLETA E CONSOLIDADA)
# ==============================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os
import yfinance as yf
from datetime import datetime, timedelta, date # ADIÇÃO: timedelta e date
import locale
import time # ADIÇÃO: time

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
# (Mantidas do app_analise.py)
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
# FUNÇÕES DE MERCADO E DIVIDENDOS (NOVAS DO app_cvms.py)
# ==============================
@st.cache_data(ttl=86400) # Cache por 24 horas
def buscar_cotacao_atual(ticker):
    """
    Busca a cotação atual do ticker no Yahoo Finance (Versão com cache)
    """
    try:
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

@st.cache_data(ttl=86400) # Cache por 24 horas
def buscar_dividendos_historicos(ticker):
    """
    Busca dividendos históricos usando yfinance ATÉ A DATA ATUAL
    """
    try:
        ticker_yf = f"{ticker}.SA"
        acao = yf.Ticker(ticker_yf)
        dividendos = acao.dividends
        
        if dividendos.empty:
            return None
            
        df_dividendos = dividendos.reset_index()
        df_dividendos.columns = ['Data', 'Dividendo']
        
        df_dividendos['Data'] = df_dividendos['Data'].dt.tz_localize(None)
        df_dividendos = df_dividendos[df_dividendos['Data'] >= datetime(2010, 1, 1)]
        
        df_dividendos['Ano'] = df_dividendos['Data'].dt.year
        df_dividendos['Mes'] = df_dividendos['Data'].dt.month
        
        df_dividendos = df_dividendos.sort_values('Data')
        
        return df_dividendos
        
    except:
        return None # Falha silenciosamente

def calcular_estatisticas_dividendos(df_dividendos):
    """
    Calcula estatísticas dos dividendos, incluindo proventos por ação (DPS)
    """
    if df_dividendos is None or df_dividendos.empty:
        return None
    
    # Adicionar cálculo anual
    dividendos_anual = df_dividendos.groupby('Ano')['Dividendo'].sum()
    
    stats = {
        'total_dividendos': df_dividendos['Dividendo'].sum(),
        # Proventos por Ação (DPS) - Aqui a "ação" é o próprio dividendo por cota
        'media_anual': dividendos_anual.mean() if not dividendos_anual.empty else 0,
        'maior_dividendo_ano': dividendos_anual.max() if not dividendos_anual.empty else 0,
        'menor_dividendo_ano': dividendos_anual.min() if not dividendos_anual.empty else 0,
        'frequencia_media': len(df_dividendos) / df_dividendos['Ano'].nunique() if df_dividendos['Ano'].nunique() > 0 else 0,
        'ultimo_dividendo': df_dividendos.iloc[-1]['Dividendo'] if len(df_dividendos) > 0 else 0,
        'data_ultimo': df_dividendos.iloc[-1]['Data'] if len(df_dividendos) > 0 else None,
        'ultimos_12m_dps': df_dividendos[df_dividendos['Data'] >= (datetime.now() - timedelta(days=365))]['Dividendo'].sum()
    }
    
    return stats

# Simulação de Investimento em Lotes (Somulador)
def simular_investimento_lotes(ticker, data_inicio, quantidade_acoes=100):
    """
    Simula um investimento por quantidade de ações (lotes).
    Retorna None se os dados de preço (histórico) não puderem ser obtidos.
    """
    try:
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
        
        preco_compra = precos_apos_inicio['Close'].iloc[0]
        if preco_compra == 0:
            return {'error': True, 'message': "Preço de compra zero, simulação impossível."}

        # 4. Calcular valor investido
        valor_investido = quantidade_acoes * preco_compra 

        # 5. Preço atual
        preco_atual = historico['Close'].iloc[-1]
        
        # 6. Calcular dividendos recebidos
        total_dividendos_recebidos = 0
        if dividendos is not None and not dividendos.empty:
            dividendos_apos_compra = dividendos[dividendos['Data'] >= data_inicio]
            total_dividendos_recebidos = dividendos_apos_compra['Dividendo'].sum() * quantidade_acoes

        # 7. Resultados
        valor_atual_acoes = quantidade_acoes * preco_atual
        rentabilidade_preco = valor_atual_acoes - valor_investido
        patrimonio_final = valor_atual_acoes + total_dividendos_recebidos
        
        rentabilidade_total = (patrimonio_final / valor_investido) - 1
        rentabilidade_preco_percentual = (rentabilidade_preco / valor_investido) * 100
        rentabilidade_dividendos_percentual = (total_dividendos_recebidos / valor_investido) * 100
        rentabilidade_total_percentual = rentabilidade_preco_percentual + rentabilidade_dividendos_percentual
        
        return {
            'data_inicio': data_inicio.strftime('%d/%m/%Y'),
            'preco_compra': preco_compra,
            'quantidade_acoes': quantidade_acoes,
            'valor_investido': valor_investido,
            'preco_atual': preco_atual,
            'valor_atual_acoes': valor_atual_acoes,
            'total_dividendos_recebidos': total_dividendos_recebidos,
            'patrimonio_final': patrimonio_final,
            'rentabilidade_total': rentabilidade_total,
            'rentabilidade_total_percentual': rentabilidade_total_percentual,
            'rentabilidade_preco_percentual': rentabilidade_preco_percentual,
            'rentabilidade_dividendos_percentual': rentabilidade_dividendos_percentual,
        }
    except Exception as e:
        return {'error': True, 'message': f"Erro inesperado na simulação: {str(e)}"}

# Funções de Ranking de Consistência
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
    
    total_steps = len(tickers_validos)
    progress_bar = st.progress(0, text="Verificando consistência anual de dividendos...")
    
    for i, ticker in enumerate(tickers_validos):
        df_dividendos = buscar_dividendos_historicos(ticker)
        
        if df_dividendos is not None and not df_dividendos.empty:
            anos_com_pagamento = df_dividendos[df_dividendos['Dividendo'] > 0]['Ano'].unique()
            
            if all(ano in anos_com_pagamento for ano in anos_necessarios):
                tickers_consistentes.append(ticker)
        
        time.sleep(0.01) # Pequeno atraso
        percent_complete = (i + 1) / total_steps
        progress_bar.progress(percent_complete, text=f"Verificando {ticker} ({i+1}/{total_steps})...")

    progress_bar.empty()
    st.success(f"✅ {len(tickers_consistentes)} tickers identificados com pagamento anual consistente desde {ano_minimo_cvm}.")
    return tickers_consistentes

def calcular_ranking_dividendos(tickers_consistentes, periodo_dy_anos=10):
    """
    Calcula o Dividend Yield médio dos últimos 10 anos para os tickers consistentes.
    """
    
    dados_ranking = []
    if not tickers_consistentes:
        return pd.DataFrame()

    with st.spinner(f"Calculando DY médio para {len(tickers_consistentes)} empresas..."):
        total_steps = len(tickers_consistentes)
        progress_bar = st.progress(0, text="Buscando dados de mercado para ranking...")
        
        for i, ticker in enumerate(tickers_consistentes):
            dados_cotacao = buscar_cotacao_atual(ticker)
            data_inicio = datetime.now() - timedelta(days=365 * periodo_dy_anos)
            df_historico_precos = buscar_historico_precos(ticker, "max")
            df_dividendos = buscar_dividendos_historicos(ticker)
            
            dy_medio_10a = None
            
            if dados_cotacao and df_historico_precos is not None and df_dividendos is not None and not df_dividendos.empty:
                df_dividendos_filtrado = df_dividendos[df_dividendos['Data'] >= data_inicio]
                df_dividendos_anual = df_dividendos_filtrado.groupby(df_dividendos_filtrado['Data'].dt.year)['Dividendo'].sum()
                precos_anuais = df_historico_precos.resample('Y').last()['Close'].dropna()
                
                dy_anuais = []
                for ano, dividendo_total in df_dividendos_anual.items():
                    if ano in precos_anuais.index.year:
                        preco_final = precos_anuais[precos_anuais.index.year == ano].iloc[0]
                        if preco_final > 0:
                            dy_anual = (dividendo_total / preco_final)
                            dy_anuais.append(dy_anual)
                
                if dy_anuais:
                    # Multiplicar por 100 para converter para porcentagem ANTES de calcular a média
                    dy_medio_10a = np.mean([dy * 100 for dy in dy_anuais])
            
            if dados_cotacao is not None:
                dados_ranking.append({
                    'Ticker': ticker,
                    'Setor': dados_cotacao.get('setor', 'N/A'),
                    'Cotação Atual': dados_cotacao['cotacao'],
                    f'DY Médio ({periodo_dy_anos}A)': dy_medio_10a if dy_medio_10a is not None else 0
                })
            
            time.sleep(0.01)
            percent_complete = (i + 1) / total_steps
            progress_bar.progress(percent_complete, text=f"Buscando {ticker} ({i+1}/{total_steps})...")

        progress_bar.empty()
    
    return pd.DataFrame(dados_ranking).fillna(0) 

# ==============================
# FUNÇÃO PARA VALUATION POR LUCRO ECONÔMICO/SELIC (Mantida do app_analise.py)
# ==============================
def calcular_valuation_lucro_economico_selic(lucro_economico, selic_percentual=15):
    """
    Calcula o valuation da empresa usando método Lucro Econômico/SELIC
    """
    if lucro_economico and lucro_economico > 0:
        # Valor em R$ mil convertido para R$ normais
        valor_empresa_em_reais = (lucro_economico * 1000) / (selic_percentual / 100)
        return valor_empresa_em_reais
    return None

# ==============================
# FUNÇÃO PARA GRÁFICO COMPARATIVO (Mantida do app_analise.py)
# ==============================
def criar_grafico_comparativo(preco_calculado, cotacao_atual, ticker):
    """
    Cria gráfico bullet chart comparativo entre preço calculado e cotação atual
    COM FORMATAÇÃO BRASILEIRA
    """
    fig = go.Figure()
    
    max_val = max(preco_calculado, cotacao_atual) * 1.3
    min_val = min(preco_calculado, cotacao_atual) * 0.7
    
    preco_formatado = f"R$ {preco_calculado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    cotacao_formatada = f"R$ {cotacao_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
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
# CONFIGURAÇÕES INICIAIS
# ==============================
st.set_page_config(page_title="Dashboard CVM - Indicadores", layout="wide")
st.title("Dashboard CVM: Análise das Demonstrações Financeiras")

# ==============================
# LEITURA E CÁLCULO DE DADOS CVM (Mantido do app_analise.py)
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

    # Ordenar por Ticker e Ano para garantir que shift() funcione corretamente
    df = df.sort_values(['Ticker', 'Ano']).reset_index(drop=True)

    # =============================================================
    # CÁLCULOS DE MÉDIAS - Mantidos do app_analise.py
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
    # INDICADORES DE RENTABILIDADE / MARGENS / ESTRUTURA / CUSTO / LUCRO ECONÔMICO
    # (Mantidos do app_analise.py)
    # =============================================================
    # ROA
    df["ROA"] = np.where(df["Ativo Médio"] > 0, df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Ativo Médio"], np.nan)
    # ROI
    df["ROI"] = np.where(df["Investimento Médio"] > 0, df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Investimento Médio"], np.nan)
    # ROE
    df["ROE"] = np.where(df["PL Médio"] > 0, df["Lucro/Prejuízo Consolidado do Período"] / df["PL Médio"], np.nan)
    # Margem Bruta
    df["Margem Bruta"] = np.where(df["Receita de Venda de Bens e/ou Serviços"] > 0, df["Resultado Bruto"] / df["Receita de Venda de Bens e/ou Serviços"], np.nan)
    # Margem Operacional
    df["Margem Operacional"] = np.where(df["Receita de Venda de Bens e/ou Serviços"] > 0, df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Receita de Venda de Bens e/ou Serviços"], np.nan)
    # Margem Líquida
    df["Margem Líquida"] = np.where(df["Receita de Venda de Bens e/ou Serviços"] > 0, df["Lucro/Prejuízo Consolidado do Período"] / df["Receita de Venda de Bens e/ou Serviços"], np.nan)
    
    # Estrutura de Capital
    df["Total Passivo"] = (
        df["Passivo Circulante"].fillna(0) + 
        df["Passivo Não Circulante"].fillna(0) + 
        df["Patrimônio Líquido Consolidado"].fillna(0)
    )
    df["Percentual Capital Terceiros"] = np.where(df["Total Passivo"] > 0, (df["Passivo Circulante"].fillna(0) + df["Passivo Não Circulante"].fillna(0)) / df["Total Passivo"], np.nan)
    df["Percentual Capital Próprio"] = np.where(df["Total Passivo"] > 0, df["Patrimônio Líquido Consolidado"] / df["Total Passivo"], np.nan)
    
    # Custo de Capital
    df["ki"] = np.where((df["Passivo Oneroso Médio"] > 0) & (df["Despesas Financeiras"].notna()), df["Despesas Financeiras"].abs() / df["Passivo Oneroso Médio"], np.nan)
    df["ke"] = np.where((df["PL Médio"] > 0) & (df["Pagamento de Dividendos"].notna()), df["Pagamento de Dividendos"].abs() / df["PL Médio"], np.nan)
    df["wacc"] = np.where(
        (df["ki"].notna()) & (df["ke"].notna()) & 
        (df["Percentual Capital Terceiros"].notna()) & (df["Percentual Capital Próprio"].notna()),
        (df["ki"] * df["Percentual Capital Terceiros"]) + (df["ke"] * df["Percentual Capital Próprio"]),
        np.nan
    )
    
    # EBITDA
    nome_coluna_da = next((col for col in df.columns if 'depreciação' in col.lower() and 'amortização' in col.lower()), None)
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

    # LUCRO ECONÔMICO
    df["Lucro Econômico 1"] = np.where(
        (df["ROI"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()),
        (df["ROI"] - df["wacc"]) * df["Investimento Médio"],
        np.nan
    )
    df["Lucro Econômico 2"] = np.where(
        (df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna()) & 
        (df["wacc"].notna()) & 
        (df["Investimento Médio"].notna()),
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] - (df["wacc"] * df["Investimento Médio"]),
        np.nan
    )
    df["Diferença Lucro Econômico"] = abs(df["Lucro Econômico 1"] - df["Lucro Econômico 2"])

    # ANÁLISE DE ALAVANCAGEM
    df["Alavancagem Eficaz"] = np.where(
        (df["ROE"].notna()) & (df["ROA"].notna()) & (df["ROI"].notna()),
        (df["ROE"] > df["ROA"]) & (df["ROE"] > df["ROI"]),
        False
    )

    return df

# Carregar dados
df = load_data()

# ==============================
# SIDEBAR - FILTROS PRINCIPAIS
# ==============================
st.sidebar.header("🔧 Filtros Principais")

# Seleção de modo de análise
# ADIÇÃO: Inclusão de um novo modo se necessário, mas mantendo a estrutura original
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
    df_filtrado_ano = df[(df["Ticker"] == ticker_selecionado) & (df["Ano"] == ano_selecionado)]
    df_empresa_todos_anos = df[df["Ticker"] == ticker_selecionado].sort_values("Ano")
    
elif modo_analise == "🏭 Análise Setorial":
    setor_selecionado = st.sidebar.selectbox(
        "Selecione o Setor:",
        sorted(df["SETOR_ATIV"].dropna().unique())
    )
    df_filtrado_ano = df[(df["SETOR_ATIV"] == setor_selecionado) & (df["Ano"] == ano_selecionado)]
    df_setor_todos_anos = df[df["SETOR_ATIV"] == setor_selecionado].sort_values(["Ano", "Ticker"])
    
else:  # Dados Gerais
    df_filtrado_ano = df[df["Ano"] == ano_selecionado]

# ==============================
# TELA PRINCIPAL - RANKING COMPARATIVO (Mantido do app_analise.py)
# ==============================
if modo_analise == "🏆 Dados Gerais":
    st.header(f"🏆 Dados Consolidados - {ano_selecionado}")
    
    # KPIs Gerais no Topo
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Empresas Analisadas", df_filtrado_ano["Ticker"].nunique())
    with col2:
        st.metric("Setores Representados", df_filtrado_ano["SETOR_ATIV"].nunique())
    with col3:
        receita_total = df_filtrado_ano["Receita de Venda de Bens e/ou Serviços"].sum()
        st.metric("Receita Total", formatar_moeda_brasil_correta(receita_total, 2))
    with col4:
        lucro_total = df_filtrado_ano["Lucro/Prejuízo Consolidado do Período"].sum()
        st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_total, 2))
        
    st.divider()

    # Abas para diferentes rankings - ADIÇÃO DA ABA DE DIVIDENDOS
    rank_tab1, rank_tab2, rank_tab3, rank_tab4, rank_tab_dividendos = st.tabs([
        "📈 Rentabilidade", "💰 Lucro e Receita", "🏛️ Solidez", "📊 Eficiência", "💎 Ranking de Dividendos"
    ])
    
    # ... (Conteúdo das abas Rentabilidade, Lucro, Solidez, Eficiência - Mantido do app_analise.py) ...
    # (O código para as 4 primeiras abas deve ser mantido idêntico ao app_analise.py)
    with rank_tab1:
        st.subheader("Top 15 Empresas por ROE")
        roe_ranking = df_filtrado_ano[df_filtrado_ano["ROE"].notna()].nlargest(15, "ROE")[["Ticker", "SETOR_ATIV", "ROE"]]
        if not roe_ranking.empty:
            fig_roe_rank = px.bar(roe_ranking, x="Ticker", y="ROE", color="SETOR_ATIV", title="Ranking de ROE (Return on Equity)")
            fig_roe_rank.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_roe_rank, use_container_width=True)
        else:
            st.warning("Não há dados de ROE disponíveis para ranking")
            
        st.subheader("📋 Tabela de Rentabilidade - Top 20")
        rentabilidade_consolidado = df_filtrado_ano[
            df_filtrado_ano["ROE"].notna() & df_filtrado_ano["ROA"].notna() & df_filtrado_ano["ROI"].notna()
        ].nlargest(20, "ROE")[["Ticker", "SETOR_ATIV", "ROE", "ROA", "ROI", "Margem Líquida"]]
        if not rentabilidade_consolidado.empty:
            rentabilidade_formatado = formatar_dataframe_percentual(
                rentabilidade_consolidado, ['ROE', 'ROA', 'ROI', 'Margem Líquida']
            )
            st.dataframe(rentabilidade_formatado, use_container_width=True)
        else:
            st.warning("Não há dados suficientes para exibir a tabela consolidada")
            
    with rank_tab2:
        st.subheader("Top 15 Empresas por Lucro Líquido")
        lucro_ranking = df_filtrado_ano.nlargest(15, "Lucro/Prejuízo Consolidado do Período")[["Ticker", "SETOR_ATIV", "Lucro/Prejuízo Consolidado do Período"]]
        if not lucro_ranking.empty:
            # Converter para R$ e formatar
            lucro_ranking['Lucro/Prejuízo Consolidado do Período_R'] = lucro_ranking['Lucro/Prejuízo Consolidado do Período'] * 1000
            fig_lucro_rank = px.bar(lucro_ranking, x="Ticker", y="Lucro/Prejuízo Consolidado do Período_R", color="SETOR_ATIV", title="Ranking de Lucro Líquido (R$)")
            fig_lucro_rank.update_layout(yaxis=dict(tickformat=',.0f')) # Formato monetário grande
            st.plotly_chart(fig_lucro_rank, use_container_width=True)
        else:
            st.warning("Não há dados de Lucro Líquido disponíveis para ranking")

    with rank_tab3:
        st.subheader("Top 15 Empresas por Estrutura de Capital (Menor % Capital Terceiros)")
        estrutura_ranking = df_filtrado_ano[df_filtrado_ano["Percentual Capital Terceiros"].notna()].nsmallest(15, "Percentual Capital Terceiros")[["Ticker", "SETOR_ATIV", "Percentual Capital Terceiros", "Percentual Capital Próprio"]]
        if not estrutura_ranking.empty:
            fig_estrutura_rank = px.bar(estrutura_ranking, x="Ticker", y="Percentual Capital Terceiros", color="SETOR_ATIV", title="Ranking de Capital de Terceiros")
            fig_estrutura_rank.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_estrutura_rank, use_container_width=True)
        else:
            st.warning("Não há dados de Estrutura de Capital disponíveis para ranking")

    with rank_tab4:
        st.subheader("Top 15 Empresas por Margem Operacional")
        margem_op_ranking = df_filtrado_ano[df_filtrado_ano["Margem Operacional"].notna()].nlargest(15, "Margem Operacional")[["Ticker", "SETOR_ATIV", "Margem Operacional", "Margem Líquida"]]
        if not margem_op_ranking.empty:
            fig_margem_op_rank = px.bar(margem_op_ranking, x="Ticker", y="Margem Operacional", color="SETOR_ATIV", title="Ranking de Margem Operacional")
            fig_margem_op_rank.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_margem_op_rank, use_container_width=True)
        else:
            st.warning("Não há dados de Margem Operacional disponíveis para ranking")

    # ==============================================================
    # NOVO CONTEÚDO: ABA RANKING DE DIVIDENDOS (do app_cvms.py)
    # ==============================================================
    with rank_tab_dividendos:
        st.header("💎 Ranking de Consistência de Dividendos")
        st.markdown(f"""
        Esta análise busca empresas listadas que apresentaram **pagamento de dividendos consistente em todos os anos** desde o ano fiscal inicial ({df["Ano"].min()}) até o ano fiscal mais recente publicado ({df["Ano"].max()}).
        """)
        
        if st.button("Executar Análise de Consistência e Ranking"):
            # 1. Calcular tickers consistentes
            tickers_consistentes = calcular_tickers_consistentes(df)
            
            if tickers_consistentes:
                # 2. Calcular Ranking de DY (Busca em tempo real)
                df_ranking_dy = calcular_ranking_dividendos(tickers_consistentes)
                
                if not df_ranking_dy.empty:
                    st.subheader("Top 10 Empresas por Dividend Yield Médio (10 Anos)")
                    # Filtrar e ranquear
                    df_ranking_final = df_ranking_dy[df_ranking_dy[f'DY Médio (10A)'].notna() & (df_ranking_dy[f'DY Médio (10A)'] > 0)].nlargest(10, f'DY Médio (10A)').reset_index(drop=True)
                    
                    if not df_ranking_final.empty:
                        # Formatação
                        df_ranking_final[f'DY Médio (10A)'] = df_ranking_final[f'DY Médio (10A)'].apply(lambda x: formatar_percentual_brasil(x/100, 2))
                        df_ranking_final['Cotação Atual'] = df_ranking_final['Cotação Atual'].apply(lambda x: f"R$ {x:,.2f}".replace(".", ","))
                        
                        st.dataframe(df_ranking_final, use_container_width=True)
                        
                        fig_dy_rank = px.bar(df_ranking_final.head(10), x="Ticker", y=f'DY Médio (10A)', color="Setor", title="Ranking de DY Médio (10 Anos)")
                        # A formatação com a função 'formatar_percentual_brasil' no DF já resolve o problema,
                        # mas o Plotly precisa do valor numérico original (ou ajustado para a escala de porcentagem).
                        # Para o gráfico, vamos usar o valor original (sem a formatação em string)
                        df_ranking_for_plot = df_ranking_dy.nlargest(10, f'DY Médio (10A)').reset_index(drop=True)
                        fig_dy_rank = px.bar(df_ranking_for_plot, x="Ticker", y=f'DY Médio (10A)', color="Setor", title="Ranking de DY Médio (10 Anos)")
                        fig_dy_rank.update_layout(yaxis_tickformat=',.2f%')
                        st.plotly_chart(fig_dy_rank, use_container_width=True)
                    else:
                        st.warning("Nenhuma empresa consistente encontrada com DY positivo nos últimos 10 anos.")
                else:
                    st.warning("Não foi possível calcular o Ranking de DY devido a falta de dados de mercado.")
            else:
                st.info("Nenhuma empresa foi consistente no pagamento de dividendos anualmente desde 2010.")


# ==============================
# TELA PRINCIPAL - VISÃO POR EMPRESA (Adaptada)
# ==============================
elif modo_analise == "📈 Visão por Empresa":
    st.header(f"📈 Análise Detalhada: {ticker_selecionado} - {ano_selecionado}")
    
    # Abas para Análise Fundamentalista e Análise de Mercado
    analise_tab1, analise_tab2, analise_tab3 = st.tabs(["🏛️ Indicadores CVM", "⏳ Evolução Histórica", "💰 Análise de Mercado e Simulação"])
    
    # ==============================================================
    # ABA 1: Indicadores CVM (Mantida do app_analise.py)
    # ==============================================================
    with analise_tab1:
        st.subheader("Resumo de Indicadores Financeiros (CVM)")

        # Exibir Indicadores de Rentabilidade e Margens
        col_roe, col_roa, col_roi = st.columns(3)
        with col_roe:
            roe = df_filtrado_ano["ROE"].iloc[0] if not df_filtrado_ano.empty and df_filtrado_ano["ROE"].notna().any() else np.nan
            st.metric("ROE", formatar_percentual_brasil(roe) if pd.notna(roe) else "N/A")
        with col_roa:
            roa = df_filtrado_ano["ROA"].iloc[0] if not df_filtrado_ano.empty and df_filtrado_ano["ROA"].notna().any() else np.nan
            st.metric("ROA", formatar_percentual_brasil(roa) if pd.notna(roa) else "N/A")
        with col_roi:
            roi = df_filtrado_ano["ROI"].iloc[0] if not df_filtrado_ano.empty and df_filtrado_ano["ROI"].notna().any() else np.nan
            st.metric("ROI", formatar_percentual_brasil(roi) if pd.notna(roi) else "N/A")

        col_ml, col_mo, col_mb = st.columns(3)
        with col_ml:
            ml = df_filtrado_ano["Margem Líquida"].iloc[0] if not df_filtrado_ano.empty and df_filtrado_ano["Margem Líquida"].notna().any() else np.nan
            st.metric("Margem Líquida", formatar_percentual_brasil(ml) if pd.notna(ml) else "N/A")
        with col_mo:
            mo = df_filtrado_ano["Margem Operacional"].iloc[0] if not df_filtrado_ano.empty and df_filtrado_ano["Margem Operacional"].notna().any() else np.nan
            st.metric("Margem Operacional", formatar_percentual_brasil(mo) if pd.notna(mo) else "N/A")
        with col_mb:
            mb = df_filtrado_ano["Margem Bruta"].iloc[0] if not df_filtrado_ano.empty and df_filtrado_ano["Margem Bruta"].notna().any() else np.nan
            st.metric("Margem Bruta", formatar_percentual_brasil(mb) if pd.notna(mb) else "N/A")

        st.subheader("Estrutura e Custo de Capital")
        col_wacc, col_le = st.columns(2)
        with col_wacc:
            wacc = df_filtrado_ano["wacc"].iloc[0] if not df_filtrado_ano.empty and df_filtrado_ano["wacc"].notna().any() else np.nan
            st.metric("WACC", formatar_percentual_brasil(wacc) if pd.notna(wacc) else "N/A")
        with col_le:
            le = df_filtrado_ano["Lucro Econômico 2"].iloc[0] if not df_filtrado_ano.empty and df_filtrado_ano["Lucro Econômico 2"].notna().any() else np.nan
            st.metric("Lucro Econômico (R$ mil)", formatar_numero_brasil_correto(le, 0) if pd.notna(le) else "N/A")
        
        # Tabela de contas
        st.subheader("Principais Contas (R$ mil)")
        contas_principais = df_filtrado_ano[[
            "Receita de Venda de Bens e/ou Serviços", 
            "Lucro/Prejuízo Consolidado do Período",
            "Ativo Total",
            "Patrimônio Líquido Consolidado",
            "Passivo Oneroso Atual",
            "Investimento Atual"
        ]].T.reset_index()
        contas_principais.columns = ["Conta", "Valor"]
        contas_principais['Valor Formatado'] = contas_principais['Valor'].apply(lambda x: formatar_moeda_brasil_correta(x, 0))
        st.dataframe(contas_principais[['Conta', 'Valor Formatado']].set_index('Conta'), use_container_width=True)

    # ==============================================================
    # ABA 2: Evolução Histórica (Mantida do app_analise.py)
    # ==============================================================
    with analise_tab2:
        st.subheader("Evolução Histórica dos Indicadores")
        
        col_hist1, col_hist2 = st.columns(2)
        
        with col_hist1:
            fig_roe_hist = px.line(df_empresa_todos_anos, x="Ano", y="ROE", title="Evolução do ROE")
            fig_roe_hist.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_roe_hist, use_container_width=True)
            
            fig_lucro_hist = px.line(df_empresa_todos_anos, x="Ano", y="Lucro/Prejuízo Consolidado do Período", title="Evolução do Lucro Líquido (R$ mil)")
            fig_lucro_hist.update_layout(yaxis_tickformat=',.0f')
            st.plotly_chart(fig_lucro_hist, use_container_width=True)

        with col_hist2:
            fig_margem_hist = px.line(df_empresa_todos_anos, x="Ano", y=["Margem Líquida", "Margem Operacional", "Margem Bruta"], 
                                      title="Evolução das Margens", markers=True)
            fig_margem_hist.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig_margem_hist, use_container_width=True)
            
            fig_caixa_hist = px.line(df_empresa_todos_anos, x="Ano", y="Caixa Líquido de Atividades Operacionais", 
                                     title="Evolução do Fluxo de Caixa Operacional (R$ mil)")
            fig_caixa_hist.update_layout(yaxis_tickformat=',.0f')
            st.plotly_chart(fig_caixa_hist, use_container_width=True)


    # ==============================================================
    # NOVO CONTEÚDO: ABA ANÁLISE DE MERCADO E SIMULAÇÃO (do app_cvms.py)
    # ==============================================================
    with analise_tab3:
        st.subheader("1. Valuation e Cotação Atual")

        # 1. Obter Lucro Econômico
        lucro_economico = df_filtrado_ano["Lucro Econômico 2"].iloc[0] if not df_filtrado_ano.empty and df_filtrado_ano["Lucro Econômico 2"].notna().any() else None
        
        # 2. Calcular Valuation e Preço por Ação
        valor_empresa = calcular_valuation_lucro_economico_selic(lucro_economico) if lucro_economico else None

        # 3. Buscar Cotação Atual e Número de Ações
        dados_cotacao = buscar_cotacao_atual(ticker_selecionado)
        
        # Tentar obter o número de ações da CVM (coluna "Número de Ações Ordinárias")
        num_acoes = df_filtrado_ano.get("Número de Ações Ordinárias").iloc[0] if "Número de Ações Ordinárias" in df_filtrado_ano.columns and not df_filtrado_ano.empty and df_filtrado_ano["Número de Ações Ordinárias"].notna().any() else None

        col_val_kpi1, col_val_kpi2, col_val_kpi3 = st.columns(3)
        
        if valor_empresa is not None and num_acoes is not None and num_acoes > 0:
            preco_calculado = valor_empresa / num_acoes
            
            with col_val_kpi1:
                st.metric("Cotação Atual (R$)", f"R$ {dados_cotacao['cotacao']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if dados_cotacao else "N/A")
            with col_val_kpi2:
                st.metric("Preço Justo (Lucro Econômico)", f"R$ {preco_calculado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            with col_val_kpi3:
                st.metric("Valor da Empresa (Calculado)", formatar_moeda_brasil_correta(valor_empresa / 1000, 2)) # Exibir em escala

            st.subheader("Comparativo de Valuation")
            if dados_cotacao:
                st.plotly_chart(criar_grafico_comparativo(preco_calculado, dados_cotacao['cotacao'], ticker_selecionado), use_container_width=True)
            else:
                st.warning("⚠️ Não foi possível obter a cotação atual para a comparação.")
        else:
            st.warning("⚠️ Não foi possível calcular o preço justo (Lucro Econômico) devido a dados incompletos (Lucro Econômico ou Número de Ações).")
            
        st.divider()
        
        # 4. Estatísticas de Dividendos (Proventos por Ação)
        df_dividendos_historico = buscar_dividendos_historicos(ticker_selecionado)
        st.subheader("2. Proventos por Ação (DPS) e Estatísticas")

        if df_dividendos_historico is not None:
            stats = calcular_estatisticas_dividendos(df_dividendos_historico)
            
            col_dps1, col_dps2, col_dps3, col_dps4 = st.columns(4)
            with col_dps1:
                st.metric("DPS (Últimos 12M)", f"R$ {stats['ultimos_12m_dps']:,.4f}".replace(".", ","))
            with col_dps2:
                st.metric("Média Anual (DPS)", f"R$ {stats['media_anual']:,.4f}".replace(".", ","))
            with col_dps3:
                st.metric("Total Pago (Histórico)", f"R$ {stats['total_dividendos']:,.2f}".replace(".", ","))
            with col_dps4:
                st.metric("Frequência Média (Pagamentos/Ano)", f"{stats['frequencia_media']:,.2f}".replace(".", ","))

            st.markdown("---")
            st.subheader("Evolução Histórica dos Proventos por Ação (Anual)")
            
            df_dps_anual = df_dividendos_historico.groupby('Ano')['Dividendo'].sum().reset_index()
            df_dps_anual.columns = ['Ano', 'DPS (Provento por Ação)']
            
            fig_dps_hist = px.bar(df_dps_anual, x="Ano", y="DPS (Provento por Ação)", title="Soma Anual dos Proventos por Ação (DPS)")
            fig_dps_hist.update_layout(yaxis_tickformat=',.4f')
            st.plotly_chart(fig_dps_hist, use_container_width=True)

        else:
            st.warning("⚠️ Não foi possível buscar o histórico de proventos por ação (DPS) para esta empresa.")


        st.divider()

        # 5. Simulador de Investimento (Somulador)
        st.subheader("3. Simulador de Investimento em Lotes (Somulador)")
        st.markdown(f"""
        Simule o retorno total (cotação + proventos) de um investimento inicial no ticker **{ticker_selecionado}**.
        """)
        
        col_sim1, col_sim2 = st.columns(2)
        with col_sim1:
            data_inicial_sim = st.date_input("Data de Compra (Início)", value=datetime.now().date() - timedelta(days=365 * 5), min_value=datetime(2010, 1, 1).date())
        with col_sim2:
            quantidade_lote = st.number_input("Quantidade de Ações (Lotes)", min_value=1, value=100, step=100)
        
        if st.button("Simular Investimento"):
            st.info("Calculando simulação, aguarde...")
            
            resultados = simular_investimento_lotes(ticker_selecionado, data_inicial_sim, quantidade_lote)
            
            if resultados is None:
                st.error("❌ Não foi possível realizar a simulação. Dados de preço da ação não foram encontrados pelo Yahoo Finance para o período selecionado.")
            elif resultados.get('error'):
                 st.error(f"❌ Erro na simulação: {resultados['message']}")
            else:
                st.success(f"✅ Simulação de {quantidade_lote} ações realizada com sucesso!")
                
                col_res1, col_res2, col_res3 = st.columns(3)
                
                with col_res1:
                    st.metric("Investimento Inicial", f"R$ {resultados['valor_investido']:,.2f}".replace(".", ","))
                    st.metric("Preço de Compra", f"R$ {resultados['preco_compra']:,.2f}".replace(".", ","))
                
                with col_res2:
                    st.metric("Patrimônio Total Final", f"R$ {resultados['patrimonio_final']:,.2f}".replace(".", ","))
                    st.metric("Valor Atual das Ações", f"R$ {resultados['valor_atual_acoes']:,.2f}".replace(".", ","))

                with col_res3:
                    st.metric("Total de Proventos Recebidos", f"R$ {resultados['total_dividendos_recebidos']:,.2f}".replace(".", ","))
                    st.metric("Rentabilidade Total", f"{resultados['rentabilidade_total_percentual']:,.2f}%".replace(".", ","))
                
                st.markdown("---")
                st.subheader("Detalhamento da Rentabilidade")
                
                col_rent_preco, col_rent_dividendo, col_rent_total = st.columns(3)
                
                with col_rent_preco:
                    st.metric("Rentabilidade (Apreciação)", f"{resultados['rentabilidade_preco_percentual']:,.2f}%".replace(".", ","))
                
                with col_rent_dividendo:
                    st.metric("Rentabilidade (Proventos)", f"{resultados['rentabilidade_dividendos_percentual']:,.2f}%".replace(".", ","))
                
                with col_rent_total:
                    st.metric("Rentabilidade Total", f"{resultados['rentabilidade_total_percentual']:,.2f}%".replace(".", ","))


# ==============================
# ANÁLISE SETORIAL (Mantido)
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    
    st.header(f"🏭 Análise Setorial - {setor_selecionado}")
    
    st.info("Funcionalidade de Análise Setorial não implementada. Filtre por setor na aba 'Dados Gerais' para rankings consolidados.")

# FIM DO SCRIPT
