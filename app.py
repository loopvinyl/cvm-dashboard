# ==============================
# FUNÇÕES DE DIVIDENDOS E INVESTIMENTO (CORRIGIDAS)
# ==============================
def buscar_dividendos_historicos(ticker):
    """
    Busca dividendos históricos usando yfinance ATÉ A DATA ATUAL
    """
    try:
        # Adiciona .SA para ações brasileiras
        ticker_yf = f"{ticker}.SA"
        acao = yf.Ticker(ticker_yf)
        
        # Busca dividendos históricos ATÉ HOJE com período máximo
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

def calcular_dividend_yield(ticker):
    """
    Calcula o dividend yield de uma ação - CORRIGIDA para buscar desde 2010
    """
    try:
        # Buscar dados da ação
        dados_cotacao = buscar_cotacao_atual(ticker)
        if not dados_cotacao:
            return None
            
        # Buscar dividendos históricos (agora busca desde 2010)
        dividendos = buscar_dividendos_historicos(ticker)
        if dividendos is None or dividendos.empty:
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

# NO LOCAL DO GRÁFICO DE DIVIDENDOS (na aba "💰 Dividendos"), substitua a parte do gráfico:
with tab_dividendos:
    st.subheader("💰 Histórico de Dividendos")
    
    # Buscar dividendos ATÉ A DATA ATUAL
    with st.spinner("Buscando dados de dividendos..."):
        df_dividendos = buscar_dividendos_historicos(ticker_selecionado)
    
    if df_dividendos is not None and not df_dividendos.empty:
        # Estatísticas rápidas
        stats = calcular_estatisticas_dividendos(df_dividendos)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Último Dividendo", 
                f"R$ {stats['ultimo_dividendo']:.4f}".replace(".", ","),
                help=f"Data: {stats['data_ultimo'].strftime('%d/%m/%Y') if stats['data_ultimo'] else 'N/A'}"
            )
        
        with col2:
            st.metric(
                "Total Distribuído", 
                formatar_moeda_brasil_correta(stats['total_dividendos'] * 1000),  # Converter para R$
                help="Soma histórica de dividendos"
            )
        
        with col3:
            st.metric(
                "Média Anual", 
                formatar_moeda_brasil_correta(stats['media_anual'] * 1000),
                help="Média de dividendos por ano"
            )
        
        with col4:
            st.metric(
                "Frequência/Ano", 
                f"{stats['frequencia_media']:.1f}",
                help="Pagamentos médios por ano"
            )
        
        # Gráfico de dividendos ao longo do tempo
        st.subheader("📈 Evolução dos Dividendos")
        
        fig_dividendos = px.line(
            df_dividendos, 
            x='Data', 
            y='Dividendo',
            title=f'Dividendos por Ação - {ticker_selecionado}',
            markers=True
        )
        
        # CORREÇÃO MELHORADA: Formatação brasileira no eixo Y com vírgula
        fig_dividendos.update_layout(
            yaxis_title='Dividendo por Ação (R$)',
            xaxis_title='Data',
            height=400,
            yaxis=dict(
                tickformat=".4f",  # 4 casas decimais
                separatethousands=True,
                tickmode='auto'
            )
        )
        
        # CORREÇÃO ADICIONAL: Formatar os ticks do eixo Y manualmente para usar vírgula
        fig_dividendos.update_yaxes(
            tickformat=".4f",
            ticktext=[f"{y:.4f}".replace('.', ',') for y in fig_dividendos.data[0].y]
        )
        
        st.plotly_chart(fig_dividendos, use_container_width=True)
        
        # ... (o restante do código da aba dividendos permanece igual)

# NO SIMULADOR DE INVESTIMENTO, substitua o date_input:
with tab_simulacao:
    st.subheader("💵 Simulação de Investimento")
    st.write("**Simule um investimento de R$ 1.000,00 desde uma data específica até hoje**")
    
    # Configuração da simulação
    col1, col2 = st.columns(2)
    
    with col1:
        # CORREÇÃO: Usar formato brasileiro explicitamente
        data_inicio = st.date_input(
            "Data do investimento inicial",
            min_value=datetime(2010, 1, 1),
            max_value=datetime.now(),
            value=datetime(2015, 1, 1),
            format="DD/MM/YYYY",  # FORÇAR FORMATO BRASILEIRO
            help="Data em que o investimento de R$ 1.000,00 seria feito (formato DD/MM/AAAA)"
        )
    
    with col2:
        valor_investido = st.number_input(
            "Valor investido (R$)",
            min_value=100,
            value=1000,
            step=100,
            help="Valor inicial do investimento"
        )
    
    # ... (o restante do código da simulação permanece igual)

# NA SEÇÃO DE DIVIDEND YIELD NO MODO "DADOS GERAIS", vamos melhorar o tratamento de erros:
with rank_tab5:
    st.header("💰 Top 10 Pagadores de Dividendos")
    st.write("**Ranking baseado no Dividend Yield (últimos 12 meses)**")
    
    # Buscar dados de dividend yield para todas as empresas
    tickers_unicos = df_filtrado['Ticker'].unique()
    
    # Aumentar limite para 50 empresas
    tickers_analisar = tickers_unicos[:50]
    
    dados_dy = []
    
    with st.spinner("Calculando dividend yields... Isso pode levar alguns minutos"):
        progress_bar = st.progress(0)
        for i, ticker in enumerate(tickers_analisar):
            try:
                dy = calcular_dividend_yield(ticker)
                if dy is not None and dy > 0:  # Só incluir se tiver dividend yield positivo
                    dados_cotacao = buscar_cotacao_atual(ticker)
                    if dados_cotacao:
                        dados_dy.append({
                            'Ticker': ticker,
                            'Dividend Yield': dy,
                            'Cotação': dados_cotacao['cotacao'],
                            'Setor': dados_cotacao['setor']
                        })
            except Exception as e:
                # Silenciosamente ignora erros e continua
                pass
            
            # Atualizar barra de progresso
            progress_bar.progress((i + 1) / len(tickers_analisar))
    
    if dados_dy:
        # Criar DataFrame e ordenar por Dividend Yield
        df_dy = pd.DataFrame(dados_dy)
        df_dy = df_dy.nlargest(10, 'Dividend Yield')
        
        # Gráfico de barras
        fig_dy = px.bar(
            df_dy, 
            x='Ticker', 
            y='Dividend Yield',
            color='Setor',
            title='Top 10 Empresas por Dividend Yield'
        )
        fig_dy.update_layout(
            yaxis_title='Dividend Yield (%)',
            yaxis_tickformat=',.2f',
            height=500
        )
        st.plotly_chart(fig_dy, use_container_width=True)
        
        # ... (o restante do código do ranking de dividendos permanece igual)
        
    else:
        st.warning("""
        **ℹ️ Não foi possível calcular dividend yields**
        
        Possíveis razões:
        - Limitações na API do Yahoo Finance (pode estar temporariamente indisponível)
        - Empresas não pagam dividendos regularmente
        - Dados históricos insuficientes
        - Conexão com a internet pode estar instável
        
        **Solução:** Tente recarregar a página ou verificar posteriormente.
        """)
