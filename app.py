# ==============================
# 🏦 NOVA SEÇÃO: VALUATION POR EBITDA/SELIC (CORRIGIDO)
# ==============================
st.divider()
st.subheader("🏦 Valuation por EBITDA/SELIC")

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

# Cálculo do Valuation
valor_empresa = calcular_valuation_ebitda_selic(ebitda_valor, selic_percentual)

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
            f"R$ {valor_empresa_reais:,.0f}",
            help="EV = EBITDA ÷ (SELIC/100) - Convertido para R$"
        )
    
    with col_val2:
        # Converter para bilhões para melhor visualização
        valor_empresa_bi = valor_empresa_reais / 1e9
        st.metric(
            "Valor da Empresa (R$ Bi)",
            f"R$ {valor_empresa_bi:,.2f}",
            help="Valor em bilhões de reais"
        )
    
    with col_val3:
        if numero_acoes:
            st.metric(
                "Número de Ações",
                f"{numero_acoes:,.0f}",
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
                f"R$ {cotacao_esperada:.2f}",
                help="Preço por ação calculado"
            )
        else:
            st.metric(
                "Cotação Esperada*",
                "N/A",
                help="Necessário número de ações"
            )
    
    # Fórmula detalhada
    st.info(f"""
    **📊 Fórmula do Valuation:**
    ```
    Valor da Empresa = EBITDA ÷ (SELIC/100)
    Valor da Empresa = R$ {ebitda_valor:,.0f} mil ÷ ({selic_percentual}%/100)
    Valor da Empresa = R$ {ebitda_valor:,.0f} mil ÷ {selic_percentual/100:.3f}
    Valor da Empresa = R$ {valor_empresa:,.0f} mil
    Valor da Empresa (R$) = R$ {valor_empresa:,.0f} mil × 1.000 = R$ {valor_empresa_reais:,.0f}
    ```
    """)
    
    if cotacao_esperada:
        st.info(f"""
        **💰 Cálculo da Cotação Esperada:**
        ```
        Cotação Esperada = Valor da Empresa (R$) ÷ Número de Ações
        Cotação Esperada = R$ {valor_empresa_reais:,.0f} ÷ {numero_acoes:,.0f}
        Cotação Esperada = R$ {cotacao_esperada:.2f}
        ```
        """)
    
    # Se temos dados da cotação, fazer análise comparativa
    if dados_cotacao:
        st.divider()
        st.subheader("📈 Análise Comparativa com Cotação de Mercado")
        
        # Informações da empresa
        col_info1, col_info2, col_info3, col_info4 = st.columns(4)
        
        with col_info1:
            st.metric("Cotação Atual", f"R$ {dados_cotacao['cotacao']:.2f}")
        
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
                market_cap_bi = dados_cotacao['market_cap'] / 1e9
                st.metric("Market Cap", f"R$ {market_cap_bi:.2f} Bi")
        
        # Análise de valuation implícito
        st.write("**💡 Interpretação:**")
        
        if cotacao_esperada:
            st.write(f"""
            - **EBITDA Anual:** R$ {ebitda_valor:,.0f} mil (R$ {ebitda_valor * 1000:,.0f})
            - **Taxa de Desconto (SELIC):** {selic_percentual}% a.a.
            - **Valor Justo Calculado:** R$ {valor_empresa_reais:,.0f}
            - **Número de Ações:** {numero_acoes:,.0f}
            - **Cotação Esperada:** R$ {cotacao_esperada:.2f}
            - **Cotação Atual ({dados_cotacao['data_atualizacao']}):** R$ {dados_cotacao['cotacao']:.2f}
            - **Diferença:** {diferenca_percentual:+.1f}%
            """)
        else:
            st.write(f"""
            - **EBITDA Anual:** R$ {ebitda_valor:,.0f} mil (R$ {ebitda_valor * 1000:,.0f})
            - **Taxa de Desconto (SELIC):** {selic_percentual}% a.a.
            - **Valor Justo Calculado:** R$ {valor_empresa_reais:,.0f}
            - **Cotação Atual ({dados_cotacao['data_atualizacao']}):** R$ {dados_cotacao['cotacao']:.2f}
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
    st.warning("Não foi possível calcular o valuation. EBITDA inválido ou negativo.")
