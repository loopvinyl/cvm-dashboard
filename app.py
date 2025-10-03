import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st
import os

def main():
    st.title("📊 Dashboard de Dados Contábeis - CVM")
    st.write("Processamento de dados contábeis de 2009 a 2024")
    
    # Configurações com verificação de arquivos
    TEMPLATE_PATH = '/content/template_scraping_2023_2024_completo.xlsx'
    
    # Verificar se o arquivo existe
    if not os.path.exists(TEMPLATE_PATH):
        st.error(f"❌ Arquivo template não encontrado: {TEMPLATE_PATH}")
        st.info("""
        **Solução:**
        1. Verifique se o arquivo está no diretório correto
        2. Confirme o nome do arquivo
        3. Ou faça upload do arquivo usando a opção abaixo
        """)
        
        # Opção para upload do template
        uploaded_template = st.file_uploader("Faça upload do arquivo template (XLSX)", type="xlsx")
        if uploaded_template is not None:
            TEMPLATE_PATH = uploaded_template
            st.success("✅ Template carregado via upload!")
        else:
            return
    
    # Arquivos CVM com verificação
    ARQUIVOS_CVM = {
        'BP': '/content/BP_20250929_204332.xlsx',
        'DRE': '/content/DRE_20250929_205456.xlsx',
        'DFC': '/content/DFC_20250929_205808.xlsx'
    }
    
    # Verificar quais arquivos CVM existem
    arquivos_faltantes = []
    for demonstracao, arquivo in ARQUIVOS_CVM.items():
        if not os.path.exists(arquivo):
            arquivos_faltantes.append(f"{demonstracao}: {arquivo}")
    
    if arquivos_faltantes:
        st.warning(f"⚠️ {len(arquivos_faltantes)} arquivo(s) CVM não encontrado(s):")
        for arquivo in arquivos_faltantes:
            st.write(f"   - {arquivo}")
        
        st.info("""
        **Para continuar, faça upload dos arquivos CVM necessários:**
        - BP_*.xlsx (Balanço Patrimonial)
        - DRE_*.xlsx (Demonstração do Resultado)
        - DFC_*.xlsx (Demonstração do Fluxo de Caixa)
        """)
        
        # Upload dos arquivos CVM
        uploaded_bp = st.file_uploader("Upload BP_*.xlsx", type="xlsx", key="bp")
        uploaded_dre = st.file_uploader("Upload DRE_*.xlsx", type="xlsx", key="dre")
        uploaded_dfc = st.file_uploader("Upload DFC_*.xlsx", type="xlsx", key="dfc")
        
        # Atualizar caminhos se os arquivos foram uploadados
        if uploaded_bp:
            ARQUIVOS_CVM['BP'] = uploaded_bp
        if uploaded_dre:
            ARQUIVOS_CVM['DRE'] = uploaded_dre
        if uploaded_dfc:
            ARQUIVOS_CVM['DFC'] = uploaded_dfc
            
        # Verificar se todos os arquivos necessários estão disponíveis
        arquivos_disponiveis = all([
            ARQUIVOS_CVM['BP'] is not None,
            ARQUIVOS_CVM['DRE'] is not None, 
            ARQUIVOS_CVM['DFC'] is not None
        ])
        
        if not arquivos_disponiveis:
            st.error("❌ Todos os arquivos CVM são necessários para continuar.")
            return
    else:
        st.success("✅ Todos os arquivos CVM encontrados!")

    # Carregar o template
    st.write("📥 Carregando template...")
    try:
        df_template = pd.read_excel(TEMPLATE_PATH)
        st.success(f"✅ Template carregado: {len(df_template)} linhas")
    except Exception as e:
        st.error(f"❌ Erro ao carregar template: {e}")
        return

    # Definir os anos de interesse - DE 2009 ATÉ 2024
    anos = list(range(2009, 2025))

    # Mapeamento das contas (mesmo do código anterior)
    CONTAS_BUSCAR = {
        # BP - Balanço Patrimonial
        'Ativo Total': {'demonstracao': 'BP', 'cd_conta': '1', 'ds_conta': 'Ativo Total'},
        'Ativo Circulante': {'demonstracao': 'BP', 'cd_conta': '1.01', 'ds_conta': 'Ativo Circulante'},
        'Passivo Total': {'demonstracao': 'BP', 'cd_conta': '2', 'ds_conta': 'Passivo Total'},
        'Passivo Circulante': {'demonstracao': 'BP', 'cd_conta': '2.01', 'ds_conta': 'Passivo Circulante'},
        'Empréstimos e Financiamentos - Circulante': {'demonstracao': 'BP', 'cd_conta': '2.01.01', 'ds_conta': 'Empréstimos e Financiamentos'},
        'Passivo Não Circulante': {'demonstracao': 'BP', 'cd_conta': '2.02', 'ds_conta': 'Passivo Não Circulante'},
        'Empréstimos e Financiamentos - Não Circulante': {'demonstracao': 'BP', 'cd_conta': '2.02.01', 'ds_conta': 'Empréstimos e Financiamentos'},
        'Patrimônio Líquido Consolidado': {'demonstracao': 'BP', 'cd_conta': '2.03', 'ds_conta': 'Patrimônio Líquido Consolidado'},

        # DRE - Demonstração do Resultado
        'Receita de Venda de Bens e/ou Serviços': {'demonstracao': 'DRE', 'cd_conta': '3.01', 'ds_conta': 'Receita de Venda de Bens e/ou Serviços'},
        'Custo dos Bens e/ou Serviços Vendidos': {'demonstracao': 'DRE', 'cd_conta': '3.02', 'ds_conta': 'Custo dos Bens e/ou Serviços Vendidos'},
        'Resultado Bruto': {'demonstracao': 'DRE', 'cd_conta': '3.03', 'ds_conta': 'Resultado Bruto'},
        'Resultado Antes do Resultado Financeiro e dos Tributos': {'demonstracao': 'DRE', 'cd_conta': '3.04', 'ds_conta': 'Resultado Antes do Resultado Financeiro e dos Tributos'},
        'Resultado Financeiro': {'demonstracao': 'DRE', 'cd_conta': '3.05', 'ds_conta': 'Resultado Financeiro'},
        'Receitas Financeiras': {'demonstracao': 'DRE', 'cd_conta': '3.05.01', 'ds_conta': 'Receitas Financeiras'},
        'Despesas Financeiras': {'demonstracao': 'DRE', 'cd_conta': '3.05.02', 'ds_conta': 'Despesas Financeiras'},
        'Resultado Antes dos Tributos sobre o Lucro': {'demonstracao': 'DRE', 'cd_conta': '3.06', 'ds_conta': 'Resultado Antes dos Tributos sobre o Lucro'},
        'Lucro/Prejuízo Consolidado do Período': {'demonstracao': 'DRE', 'cd_conta': '3.07', 'ds_conta': 'Lucro/Prejuízo Consolidado do Período'},

        # DFC - Demonstração do Fluxo de Caixa
        'Caixa Líquido Atividades Operacionais': {'demonstracao': 'DFC', 'cd_conta': '6.01', 'ds_conta': 'Caixa Líquido Atividades Operacionais'}
    }

    # Barra de progresso
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Carregar dados dos arquivos CVM
    status_text.text("📂 Carregando arquivos CVM...")
    dados_cvm = {}

    total_arquivos = len(ARQUIVOS_CVM) * len(anos)
    arquivos_carregados = 0

    for demonstracao, arquivo in ARQUIVOS_CVM.items():
        dados_cvm[demonstracao] = {}
        
        for ano in anos:
            # Para 2009, buscar na aba de 2010 (que contém dados de 2009 e 2010)
            if ano == 2009:
                aba_para_buscar = 2010
            else:
                aba_para_buscar = ano
                
            aba_nome = f"{demonstracao}_{aba_para_buscar}"
            
            try:
                # Verificar se é um arquivo uploadado ou caminho local
                if hasattr(arquivo, 'read'):
                    # É um arquivo uploadado
                    df = pd.read_excel(arquivo, sheet_name=aba_nome)
                else:
                    # É um caminho local
                    df = pd.read_excel(arquivo, sheet_name=aba_nome)
                
                # Garantir que CD_CVM seja string para comparação
                df['CD_CVM'] = df['CD_CVM'].astype(str)
                
                # Se estamos buscando 2009 na aba de 2010, filtrar apenas os registros de 2009
                if ano == 2009:
                    df = df[df['ANO'] == 2009]
                
                dados_cvm[demonstracao][ano] = df
                st.success(f"✅ {aba_nome} (para ano {ano}) carregado - {len(df)} linhas")
                
            except Exception as e:
                st.warning(f"⚠️ Erro ao carregar {aba_nome} (para ano {ano}): {e}")
                dados_cvm[demonstracao][ano] = None
            
            arquivos_carregados += 1
            progress_bar.progress(arquivos_carregados / total_arquivos)

    # Função para buscar valor de uma conta específica
    def buscar_valor_conta(cd_cvm, conta_info, ano):
        demonstracao = conta_info['demonstracao']
        cd_conta = conta_info['cd_conta']
        ds_conta = conta_info['ds_conta']
        
        if dados_cvm.get(demonstracao, {}).get(ano) is None:
            return None
        
        df = dados_cvm[demonstracao][ano]
        
        # Buscar pelo CD_CVM e CD_CONTA
        resultado = df[(df['CD_CVM'] == cd_cvm) & (df['CD_CONTA'] == cd_conta)]
        
        if resultado.empty:
            # Tentar buscar pela descrição da conta
            resultado = df[(df['CD_CVM'] == cd_cvm) & 
                          (df['DS_CONTA'].str.contains(ds_conta, na=False))]
        
        if not resultado.empty:
            valor = resultado['VL_CONTA'].iloc[0]
            return valor
        
        return None

    # Função para calcular ROE com validação
    def calcular_roe_se_aplicavel(lucro_liquido, patrimonio_liquido):
        if pd.isna(lucro_liquido) or pd.isna(patrimonio_liquido):
            return np.nan
        
        # Condição: Lucro Líquido > 0 E Patrimônio Líquido > 0
        if lucro_liquido > 0 and patrimonio_liquido > 0:
            return lucro_liquido / patrimonio_liquido
        else:
            return np.nan

    # Processar o template
    status_text.text("🚀 INICIANDO BUSCA DE DADOS CONTÁBEIS...")
    
    # Criar cópia do template para preencher
    df_resultado = df_template.copy()
    df_resultado['CD_CVM'] = df_resultado['CD_CVM'].astype(str)

    # Contadores para estatísticas
    total_linhas = len(df_resultado)
    linhas_processadas = 0
    empresas_com_dados = 0

    # Agrupar por empresa e ano para evitar processamento duplicado
    empresas_unicas = df_resultado[['CD_CVM', 'DENOM_CIA', 'Ano']].drop_duplicates()
    empresas_unicas['CD_CVM'] = empresas_unicas['CD_CVM'].astype(str)

    st.write(f"📊 Total de empresas/anos únicos para processar: {len(empresas_unicas)}")
    st.write(f"📅 Período coberto: {min(anos)} a {max(anos)}")

    # Barra de progresso para processamento das empresas
    progress_bar_empresas = st.progress(0)
    status_empresas = st.empty()

    # Para cada empresa/ano único no template
    for idx, empresa in enumerate(empresas_unicas.iterrows()):
        _, empresa_data = empresa
        cd_cvm = empresa_data['CD_CVM']
        denom_cia = empresa_data['DENOM_CIA']
        ano = empresa_data['Ano']
        
        # Pular se o ano não estiver no nosso range de interesse
        if ano not in anos:
            continue
            
        status_empresas.text(f"🔍 Processando: {denom_cia} ({cd_cvm}) - {ano}")
        
        # Buscar dados para cada conta
        dados_empresa = {}
        for conta_nome, conta_info in CONTAS_BUSCAR.items():
            valor = buscar_valor_conta(cd_cvm, conta_info, ano)
            dados_empresa[conta_nome] = valor
        
        # Verificar se encontrou algum dado
        if any(valor is not None for valor in dados_empresa.values()):
            empresas_com_dados += 1
            
            # Atualizar todas as linhas com este CD_CVM e Ano
            mask = (df_resultado['CD_CVM'] == cd_cvm) & (df_resultado['Ano'] == ano)
            linhas_afetadas = mask.sum()
            linhas_processadas += linhas_afetadas
            
            for conta_nome, valor in dados_empresa.items():
                df_resultado.loc[mask, conta_nome] = valor
        
        # Atualizar barra de progresso
        progress_bar_empresas.progress((idx + 1) / len(empresas_unicas))

    # Calcular ROE com validação
    status_text.text("📊 Calculando ROE com validação...")
    
    if 'Lucro/Prejuízo Consolidado do Período' in df_resultado.columns and 'Patrimônio Líquido Consolidado' in df_resultado.columns:
        df_resultado['ROE'] = df_resultado.apply(
            lambda row: calcular_roe_se_aplicavel(
                row['Lucro/Prejuízo Consolidado do Período'], 
                row['Patrimônio Líquido Consolidado']
            ), 
            axis=1
        )
        
        roe_calculados = df_resultado['ROE'].notna().sum()
        roe_nao_calculados = len(df_resultado) - roe_calculados
        
        st.success(f"✅ ROE calculado para {roe_calculados} linhas")
        st.info(f"📊 ROE não calculado (devido a LL ≤ 0 ou PL ≤ 0): {roe_nao_calculados} linhas")

    # Salvar resultados
    status_text.text("💾 Salvando resultados...")
    
    OUTPUT_PATH = 'dados_contabeis_reais_2009_2024_corrigido.xlsx'
    df_resultado.to_excel(OUTPUT_PATH, index=False)

    # Estatísticas finais
    st.success("🎯 PROCESSAMENTO CONCLUÍDO!")
    
    # Mostrar estatísticas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Período Analisado", f"{min(anos)}-{max(anos)}")
        st.metric("Total de Anos", len(anos))
        
    with col2:
        st.metric("Linhas no Template", total_linhas)
        st.metric("Linhas Processadas", linhas_processadas)
        
    with col3:
        st.metric("Empresas com Dados", empresas_com_dados)
        taxa_sucesso = (empresas_com_dados/len(empresas_unicas))*100 if len(empresas_unicas) > 0 else 0
        st.metric("Taxa de Sucesso", f"{taxa_sucesso:.1f}%")

    # Mostrar preenchimento das contas
    st.subheader("📈 Dados Obtidos por Conta")
    for conta_nome in CONTAS_BUSCAR.keys():
        if conta_nome in df_resultado.columns:
            preenchidas = df_resultado[conta_nome].notna().sum()
            total = len(df_resultado)
            percentual = (preenchidas / total) * 100
            st.write(f"**{conta_nome}**: {preenchidas}/{total} ({percentual:.1f}%)")

    # Download do arquivo
    st.subheader("💾 Download dos Resultados")
    
    with open(OUTPUT_PATH, "rb") as file:
        btn = st.download_button(
            label="📥 Baixar arquivo processado",
            data=file,
            file_name=OUTPUT_PATH,
            mime="application/vnd.ms-excel"
        )

    # Mostrar amostra dos resultados
    st.subheader("🔍 Amostra dos Resultados")
    colunas_amostra = ['CD_CVM', 'DENOM_CIA', 'Ticker', 'Ano', 'Ativo Total', 'Lucro/Prejuízo Consolidado do Período']
    if 'ROE' in df_resultado.columns:
        colunas_amostra.append('ROE')
    
    st.dataframe(df_resultado[colunas_amostra].head(10))

    # Distribuição por ano
    st.subheader("📅 Distribuição de Dados por Ano")
    for ano in sorted(df_resultado['Ano'].unique()):
        if ano in anos:
            linhas_ano = len(df_resultado[df_resultado['Ano'] == ano])
            dados_preenchidos = df_resultado[df_resultado['Ano'] == ano]['Ativo Total'].notna().sum()
            percentual = (dados_preenchidos/linhas_ano*100) if linhas_ano > 0 else 0
            fonte = " (busca em 2010)" if ano == 2009 else ""
            
            if 'ROE' in df_resultado.columns:
                roe_valido_ano = df_resultado[(df_resultado['Ano'] == ano) & (df_resultado['ROE'].notna())].shape[0]
                st.write(f"**{ano}**: {dados_preenchidos}/{linhas_ano} empresas com dados ({percentual:.1f}%) - {roe_valido_ano} ROEs válidos{fonte}")
            else:
                st.write(f"**{ano}**: {dados_preenchidos}/{linhas_ano} empresas com dados ({percentual:.1f}%){fonte}")

if __name__ == "__main__":
    main()
