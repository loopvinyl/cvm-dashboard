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

# =========================================================================================
# ADIÇÃO DO CONTEÚDO DE app.py_vellani.txt (Configurações e Funções CVM/Indicadores/Valuation)
# =========================================================================================

# ==============================
# CONFIGURAÇÕES INICIAIS
# ==============================
st.set_page_config(page_title="Dashboard CVM - Indicadores", layout="wide")
st.title("Dashboard CVM: Análise das Demonstrações Financeiras")

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

# ===============================================================================
# ADIÇÃO DO CONTEÚDO DE app.py_cvm.txt (Funções de Histórico, Simulação e Main App)
# ===============================================================================

# ==============================
# FUNÇÃO DE BUSCA DE HISTÓRICO DE PREÇOS (YFINANCE)
# ==============================
@st.cache_data(ttl=86400) # Cache por 24 horas
def buscar_historico_precos(ticker, periodo="max"):
    """
    Busca histórico de preços de fechamento para o ticker no Yahoo Finance.
    """
    try:
        # Adiciona .SA para ações brasileiras
        ticker_yf = f"{ticker}.SA"
        acao = yf.Ticker(ticker_yf)
        
        # 'max' busca todos os dados disponíveis
        historico = acao.history(period=periodo)
        
        if historico.empty:
            return None
            
        # Manter apenas as colunas de data e preço de fechamento (Close)
        df_historico = historico[['Close']].reset_index()
        df_historico.columns = ['Data', 'Preco Fechamento']
        
        # Remover timezone
        df_historico['Data'] = df_historico['Data'].dt.tz_localize(None)
        
        return df_historico.set_index('Data')
        
    except:
        return None # Falha silenciosamente

# ==============================
# SISTEMA DE RANKING DE DIVIDENDOS OTIMIZADO (Foco em DY de 10 Anos)
# *FUNÇÃO COMPLETA*
# ==============================
@st.cache_data(ttl=86400) # Cache por 24 horas
def calcular_ranking_dividendos_completo(tickers_consistentes, periodo_dy_anos=10):
    """ 
    Calcula o Dividend Yield médio dos últimos 10 anos (ou período disponível) para o conjunto de tickers consistentes e ranqueia o Top 10. 
    (Versão completa para uso no app)
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
                    
                    # 2. Pegar o preço de fechamento no final de cada ano (ou o preço de fechamento mais próximo)
                    precos_anuais = {}
                    
                    # Obter a lista de anos com pagamentos para iterar
                    anos_com_pagamento = df_dividendos_anual.index.unique().tolist()
                    
                    for ano in anos_com_pagamento:
                        data_fim_ano = datetime(ano, 12, 31)
                        
                        # Tentar encontrar a cotação exata na data ou o dia de negociação mais próximo
                        try:
                            # Encontrar a data mais próxima no histórico de preços
                            idx = df_historico_precos.index.get_indexer([data_fim_ano], method='nearest')[0]
                            # Pegar a data e o preço correspondente
                            data_real = df_historico_precos.index[idx]
                            preco = df_historico_precos.iloc[idx]['Preco Fechamento']
                            
                            # Apenas aceitar se a data real for razoavelmente próxima (máx. 30 dias após o final do ano)
                            if abs((data_real - data_fim_ano).days) <= 30:
                                precos_anuais[ano] = preco
                                
                        except:
                            pass # Ignorar anos sem cotação válida

                    # 3. Calcular o DY para cada ano
                    dy_anuais = {}
                    for ano, dividendo in df_dividendos_anual.items():
                        if ano in precos_anuais:
                            preco = precos_anuais[ano]
                            if preco > 0:
                                dy_anuais[ano] = dividendo / preco
                                
                    # 4. Calcular o DY médio (apenas se houver dados)
                    if dy_anuais:
                        dy_medio_10a = pd.Series(dy_anuais).mean()

            if dy_medio_10a is not None:
                dados_ranking.append({
                    'Ticker': ticker,
                    'Nome': dados_cotacao['nome'],
                    'Setor': dados_cotacao['setor'],
                    'Industria': dados_cotacao['industria'],
                    'DY Médio (10a)': dy_medio_10a,
                    'Cotação Atual': dados_cotacao['cotacao'],
                })

            percent_complete = (i + 1) / total_steps
            progress_bar.progress(percent_complete, text=f"Calculando DY médio para {ticker} ({i+1}/{total_steps})...")

        progress_bar.empty()
        
    df_ranking = pd.DataFrame(dados_ranking)
    
    if df_ranking.empty:
        st.error("❌ Não foi possível calcular o ranking de DY Médio para os tickers consistentes.")
        return pd.DataFrame()
        
    df_ranking = df_ranking.sort_values('DY Médio (10a)', ascending=False).reset_index(drop=True)
    df_ranking['Rank'] = df_ranking.index + 1
    
    st.success(f"✅ Ranking de DY Médio de {periodo_dy_anos} anos calculado com sucesso.")

    return df_ranking

# ==============================
# FUNÇÃO DE SIMULAÇÃO DE INVESTIMENTO (YFINANCE)
# ==============================
def calcular_simulacao_investimento(ticker, data_compra, valor_investido):
    """
    Simula o investimento no ticker, calculando rentabilidade de preço e dividendos.
    Retorna um dicionário com os resultados.
    """
    try:
        data_compra = pd.to_datetime(data_compra)
        data_atual = datetime.now().date()
        
        # 1. Buscar cotação atual
        dados_cotacao = buscar_cotacao_atual(ticker)
        if not dados_cotacao:
            return None
        
        preco_atual = dados_cotacao['cotacao']

        # 2. Buscar histórico de preços
        df_historico = buscar_historico_precos(ticker, periodo="max")
        if df_historico is None or df_historico.empty:
            return None
            
        # 3. Encontrar preço na data de compra
        # Tenta encontrar a data de compra exata ou o dia de negociação mais próximo
        idx_compra = df_historico.index.get_indexer([data_compra], method='ffill')[0]
        
        if idx_compra == -1: # Caso a data seja anterior ao primeiro registro
            idx_compra = 0
            
        preco_compra = df_historico.iloc[idx_compra]['Preco Fechamento']
        data_compra_real = df_historico.index[idx_compra].date()
        
        # 4. Calcular número de ações compradas
        if preco_compra <= 0:
            return None
            
        num_acoes = valor_investido / preco_compra
        
        # 5. Calcular valor atual do investimento
        valor_atual = num_acoes * preco_atual
        
        # 6. Buscar dividendos pagos no período
        df_dividendos = buscar_dividendos_historicos(ticker)
        if df_dividendos is not None:
            df_dividendos_periodo = df_dividendos[df_dividendos['Data'].dt.date >= data_compra_real]
            proventos_por_acao = df_dividendos_periodo['Dividendo'].sum()
        else:
            proventos_por_acao = 0

        proventos_total = proventos_por_acao * num_acoes
        
        # 7. Calcular ganhos
        ganho_preco = valor_atual - valor_investido
        ganho_total = ganho_preco + proventos_total
        
        # 8. Calcular rentabilidade
        rentabilidade_preco_percentual = (ganho_preco / valor_investido) * 100
        rentabilidade_dividendos_percentual = (proventos_total / valor_investido) * 100
        rentabilidade_total_percentual = (ganho_total / valor_investido) * 100
        
        return {
            'ticker': ticker,
            'data_compra_real': data_compra_real.strftime('%d/%m/%Y'),
            'data_atual': data_atual.strftime('%d/%m/%Y'),
            'preco_compra': preco_compra,
            'preco_atual': preco_atual,
            'valor_investido': valor_investido,
            'num_acoes': num_acoes,
            'valor_atual': valor_atual,
            'proventos_total': proventos_total,
            'ganho_total': ganho_total,
            'rentabilidade_preco_percentual': rentabilidade_preco_percentual,
            'rentabilidade_dividendos_percentual': rentabilidade_dividendos_percentual,
            'rentabilidade_total_percentual': rentabilidade_total_percentual,
            'nome': dados_cotacao.get('nome', ticker),
            'setor': dados_cotacao.get('sector', 'N/A'),
            'industria': dados_cotacao.get('industry', 'N/A'),
        }

    except Exception as e:
        # st.error(f"Erro na simulação para {ticker}: {e}")
        return None

# ==============================
# MAIN APP
# ==============================
# 1. Carregar os dados CVM
df_cvm = load_data()

# 2. Sidebar para seleção de modo e filtros
st.sidebar.header("⚙️ Configurações e Filtros")
st.sidebar.markdown("---")

# Seleção do Ticker Global
ticker_opcoes = sorted(df_cvm['Ticker'].unique())

# Filtros para o modo 'Dados Gerais' e 'Ranking'
setor_opcoes = ['Todos'] + sorted(df_cvm['Setor'].dropna().unique())
setor_selecionado = st.sidebar.selectbox("Filtro por Setor", setor_opcoes)

industria_opcoes = ['Todas'] + sorted(df_cvm[df_cvm['Setor'] == setor_selecionado]['Indústria'].dropna().unique())
industria_selecionada = st.sidebar.selectbox("Filtro por Indústria", industria_opcoes)

# Aplicar filtros
df_cvm_filtrado = df_cvm.copy()
if setor_selecionado != 'Todos':
    df_cvm_filtrado = df_cvm_filtrado[df_cvm_filtrado['Setor'] == setor_selecionado]

if industria_selecionada != 'Todas':
    df_cvm_filtrado = df_cvm_filtrado[df_cvm_filtrado['Indústria'] == industria_selecionada]

# Seleção de Modo de Análise
modo_analise = st.sidebar.radio(
    "Selecione o Modo de Análise",
    ("📊 Dados Gerais e Indicadores", "🏆 Ranking de Dividendos", "💰 Simulador de Investimento", "🏭 Análise Setorial"),
    index=0
)

# 3. Lógica de Exibição Principal
if modo_analise == "📊 Dados Gerais e Indicadores":
    
    st.header("📊 Dados Gerais e Indicadores")
    
    # Seleção de Ticker na página principal (apenas para este modo)
    ticker_selecionado = st.selectbox("Selecione o Ticker para Análise Detalhada", sorted(df_cvm_filtrado['Ticker'].unique()))
    
    if not ticker_selecionado:
        st.warning("Selecione um ticker para iniciar a análise.")
        st.stop()
        
    df_empresa = df_cvm_filtrado[df_cvm_filtrado['Ticker'] == ticker_selecionado].sort_values('Ano', ascending=False)
    dados_atuais = df_empresa.iloc[0].to_dict()

    # ==============================
    # METADADOS E COTAÇÃO ATUAL
    # ==============================
    st.subheader(f"Informações de {ticker_selecionado}")
    
    # Busca cotação em tempo real
    dados_cotacao = buscar_cotacao_atual(ticker_selecionado)
    
    col1, col2, col3, col4 = st.columns(4)
    
    if dados_cotacao:
        col1.metric("Cotação Atual", f"R$ {dados_cotacao['cotacao']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        col2.metric("Market Cap", formatar_moeda_brasil_correta(dados_cotacao['market_cap']/1000, 2))
        col3.metric("Setor", dados_cotacao['setor'])
        col4.metric("Última Atualização", dados_cotacao['data_atualizacao'])
        st.markdown(f"**Nome:** {dados_cotacao['nome']} | **Indústria:** {dados_cotacao['industria']}")
    else:
        col1.warning("Cotação indisponível (YFinance)")
        col2.metric("Setor (CVM)", dados_atuais.get('Setor', 'N/A'))
        col3.metric("Indústria (CVM)", dados_atuais.get('Indústria', 'N/A'))
        col4.metric("Ano Fiscal Mais Recente", dados_atuais.get('Ano', 'N/A'))

    st.markdown("---")

    # ==============================
    # INDICADORES DE RENTABILIDADE E MARGENS
    # ==============================
    st.subheader("Indicadores de Rentabilidade e Margens")
    
    cols_rent = st.columns(3)
    cols_marg = st.columns(3)

    cols_rent[0].metric("ROE (Ano Recente)", formatar_percentual_brasil(dados_atuais.get('ROE')))
    cols_rent[1].metric("ROA (Ano Recente)", formatar_percentual_brasil(dados_atuais.get('ROA')))
    cols_rent[2].metric("ROI (Ano Recente)", formatar_percentual_brasil(dados_atuais.get('ROI')))

    cols_marg[0].metric("Margem Líquida", formatar_percentual_brasil(dados_atuais.get('Margem Líquida')))
    cols_marg[1].metric("Margem Operacional", formatar_percentual_brasil(dados_atuais.get('Margem Operacional')))
    cols_marg[2].metric("Margem Bruta", formatar_percentual_brasil(dados_atuais.get('Margem Bruta')))

    # Tabela com EBITDA, WACC e Lucro Econômico
    st.markdown("---")
    st.subheader("Custos e Lucro Econômico (EVA)")
    
    col_custo, col_lucro = st.columns(2)
    
    col_custo.metric("EBITDA", formatar_moeda_brasil_correta(dados_atuais.get('EBITDA'), 2))
    col_custo.metric("WACC (Custo Médio de Capital)", formatar_percentual_brasil(dados_atuais.get('wacc')))
    col_custo.metric("Alavancagem Eficaz?", "✅ Sim" if dados_atuais.get('Alavancagem Eficaz') else "❌ Não")
    
    # Calcular Valuation
    lucro_economico_2 = dados_atuais.get('Lucro Econômico 2')
    valor_empresa = calcular_valuation_lucro_economico_selic(lucro_economico_2, selic_percentual=15)
    
    if valor_empresa:
        col_lucro.metric("Lucro Econômico (R$ mil)", formatar_moeda_brasil_correta(lucro_economico_2, 2))
        col_lucro.metric("Valuation (LE/SELIC 15%)", formatar_moeda_brasil_correta(valor_empresa, 0))
    else:
        col_lucro.metric("Lucro Econômico (R$ mil)", formatar_moeda_brasil_correta(lucro_economico_2, 2))
        col_lucro.warning("Valuation (LE/SELIC) indisponível.")

    st.markdown("---")
    st.subheader("Evolução Histórica dos Indicadores")
    
    # Reorganizar DataFrame para o gráfico
    df_grafico = df_empresa.sort_values('Ano').reset_index(drop=True)

    # 1. Gráfico de Rentabilidade
    fig_rent = make_subplots(specs=[[{"secondary_y": False}]])
    
    fig_rent.add_trace(
        go.Bar(
            x=df_grafico['Ano'], 
            y=df_grafico['ROE'] * 100, 
            name='ROE', 
            marker_color='#1f77b4'
        ),
        secondary_y=False,
    )
    fig_rent.add_trace(
        go.Scatter(
            x=df_grafico['Ano'], 
            y=df_grafico['ROA'] * 100, 
            name='ROA', 
            mode='lines+markers', 
            line=dict(color='red', width=2)
        ),
        secondary_y=False,
    )
    fig_rent.add_trace(
        go.Scatter(
            x=df_grafico['Ano'], 
            y=df_grafico['ROI'] * 100, 
            name='ROI', 
            mode='lines+markers', 
            line=dict(color='orange', width=2)
        ),
        secondary_y=False,
    )
    
    fig_rent.update_layout(
        title_text="Evolução do ROE, ROA e ROI (%)",
        xaxis_title="Ano",
        yaxis_title="Rentabilidade (%)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_rent, use_container_width=True)

    # 2. Gráfico de Margens
    fig_marg = px.line(
        df_grafico, 
        x='Ano', 
        y=['Margem Líquida', 'Margem Operacional', 'Margem Bruta'], 
        title="Evolução das Margens (%)",
        labels={'value': 'Margem (%)', 'variable': 'Tipo de Margem'},
        markers=True
    )
    fig_marg.update_yaxes(tickformat=".2%")
    fig_marg.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_marg, use_container_width=True)
    
    # 3. Gráfico de Lucro Econômico
    fig_le = px.bar(
        df_grafico, 
        x='Ano', 
        y='Lucro Econômico 2', 
        title="Evolução do Lucro Econômico (R$ mil)",
        labels={'Lucro Econômico 2': 'Lucro Econômico (R$ mil)'},
        color_discrete_sequence=['#2ca02c']
    )
    fig_le.update_layout(hovermode="x unified")
    fig_le.update_yaxes(tickprefix="R$ ", separatethousands=True)
    st.plotly_chart(fig_le, use_container_width=True)
    
    # ==============================
    # DADOS BRUTOS (TABELA)
    # ==============================
    st.markdown("---")
    st.subheader("Dados Financeiros Históricos (R$ mil)")
    
    # Selecionar e formatar colunas importantes
    colunas_exibicao = [
        'Ano', 'Receita de Venda de Bens e/ou Serviços', 'Resultado Bruto',
        'Resultado Antes do Resultado Financeiro e dos Tributos', 
        'EBITDA', 'Lucro/Prejuízo Consolidado do Período', 
        'Ativo Total', 'Patrimônio Líquido Consolidado', 
        'Empréstimos e Financiamentos - Circulante', 'Empréstimos e Financiamentos - Não Circulante'
    ]
    df_exibicao = df_empresa[colunas_exibicao].copy()
    
    colunas_moeda = [
        'Receita de Venda de Bens e/ou Serviços', 'Resultado Bruto',
        'Resultado Antes do Resultado Financeiro e dos Tributos', 
        'EBITDA', 'Lucro/Prejuízo Consolidado do Período', 
        'Ativo Total', 'Patrimônio Líquido Consolidado', 
        'Empréstimos e Financiamentos - Circulante', 'Empréstimos e Financiamentos - Não Circulante'
    ]
    df_exibicao = formatar_dataframe_moeda(df_exibicao, colunas_moeda)

    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)


elif modo_analise == "🏆 Ranking de Dividendos":
    
    st.header("🏆 Ranking: Melhores Pagadoras de Dividendos (Consistência e DY)")

    # 1. Pré-filtrar tickers consistentes (apenas uma vez)
    tickers_consistentes = calcular_tickers_consistentes(df_cvm_filtrado)
    
    if tickers_consistentes:
        # 2. Calcular Ranking de DY Médio
        periodo_dy = st.slider("Período para DY Médio (Anos)", min_value=1, max_value=15, value=10)
        
        # Chamada à função completa
        df_ranking = calcular_ranking_dividendos_completo(tickers_consistentes, periodo_dy_anos=periodo_dy)
        
        if not df_ranking.empty:
            
            st.subheader(f"Top 10 Empresas com Melhor DY Médio de {periodo_dy} Anos")
            
            df_top_10 = df_ranking.head(10).copy()
            
            # Formatação para exibição
            df_exibicao = df_top_10[['Rank', 'Ticker', 'Nome', 'Setor', 'DY Médio (10a)', 'Cotação Atual']].copy()
            df_exibicao['DY Médio (10a)'] = df_exibicao['DY Médio (10a)'].apply(lambda x: formatar_percentual_brasil(x, 2))
            df_exibicao['Cotação Atual'] = df_exibicao['Cotação Atual'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            st.dataframe(df_exibicao, hide_index=True, use_container_width=True)

            # Gráfico do Ranking
            fig_ranking = px.bar(
                df_top_10,
                x='Ticker',
                y='DY Médio (10a)',
                color='Setor',
                title=f"Dividend Yield Médio dos Últimos {periodo_dy} Anos - Top 10",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_ranking.update_yaxes(tickformat=".2%")
            st.plotly_chart(fig_ranking, use_container_width=True)


elif modo_analise == "💰 Simulador de Investimento":
    
    st.header("💰 Simulador de Investimento e Rentabilidade")
    
    col_input, col_info = st.columns([1, 2])
    
    with col_input:
        ticker_selecionado = st.selectbox(
            "Selecione o Ticker", 
            ticker_opcoes
        )
        
        # Data de compra (mínimo de 1 ano atrás)
        data_minima = (datetime.now() - timedelta(days=365*1)).date()
        data_selecionada = st.date_input(
            "Data de Compra (Mínima: 1 ano atrás)",
            value=data_minima,
            min_value=datetime(2000, 1, 1).date(),
            max_value=datetime.now().date()
        )
        
        valor_selecionado = st.number_input(
            "Valor Total Investido (R$)",
            min_value=100.0,
            value=1000.0,
            step=100.0
        )
        
        st.markdown(f"Investimento: **R$ {valor_selecionado:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
        
        botao_simular = st.button("🚀 Simular Investimento")
        
    with col_info:
        st.subheader(f"Resultados da Simulação para {ticker_selecionado}")
        
        if botao_simular:
            
            # Realizar simulação
            resultados = calcular_simulacao_investimento(
                ticker_selecionado, 
                data_selecionada, 
                valor_selecionado
            )
            
            if resultados:
                
                col_compra, col_atual, col_variacao = st.columns(3)
                
                col_compra.metric("Preço na Compra", f"R$ {resultados['preco_compra']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col_compra.metric("Data de Compra (Real)", resultados['data_compra_real'])

                col_atual.metric("Preço Atual", f"R$ {resultados['preco_atual']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col_atual.metric("Data Atual", resultados['data_atual'])
                
                col_variacao.metric("Ações Compradas", f"{resultados['num_acoes']:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col_variacao.metric("Valor Atual Total", f"R$ {resultados['valor_atual']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                st.markdown("---")
                st.subheader("Ganhos e Rentabilidade")
                
                col_ganho, col_proventos, col_total = st.columns(3)
                
                col_ganho.metric("Ganho (Apreciação)", f"R$ {resultados['ganho_total'] - resultados['proventos_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col_proventos.metric("Proventos Recebidos", f"R$ {resultados['proventos_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col_total.metric("Ganho Total", f"R$ {resultados['ganho_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                st.markdown("---")
                st.subheader("Rentabilidade do Investimento")
                
                col_rent_preco, col_rent_dividendo, col_rent_total = st.columns(3)
                
                col_rent_preco.metric("Rentabilidade (Apreciação)", f"{resultados['rentabilidade_preco_percentual']:,.2f}%".replace(".", ","))
                
                col_rent_dividendo.metric("Rentabilidade (Dividendos)", f"{resultados['rentabilidade_dividendos_percentual']:,.2f}%".replace(".", ","))
                
                col_rent_total.metric("Rentabilidade Total", f"{resultados['rentabilidade_total_percentual']:,.2f}%".replace(".", ","))
                
            else:
                # Caso a função retorne None (falha crítica - falta de dados de preço)
                st.error(f"""
❌ Não foi possível realizar a simulação.
**Possíveis causas:** Dados de preço da ação não foram encontrados pelo Yahoo Finance para o período selecionado, a ação não possui histórico de negociação na bolsa ou a data de compra está fora do período disponível.
""")
# ==============================
# ANÁLISE SETORIAL (Mantido)
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    
    st.header(f"🏭 Análise Setorial - {setor_selecionado}")
    
    st.info("Funcionalidade de Análise Setorial não implementada neste momento. Filtre por setor na aba 'Dados Gerais' para rankings.")
