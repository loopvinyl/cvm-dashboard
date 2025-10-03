import pandas as pd
import numpy as np
from datetime import datetime

# Configurações
TEMPLATE_PATH = '/content/template_scraping_2023_2024_completo.xlsx'
OUTPUT_PATH = '/content/dados_contabeis_reais_2009_2024_corrigido.xlsx'

# Arquivos CVM com os dados
ARQUIVOS_CVM = {
    'BP': '/content/BP_20250929_204332.xlsx',
    'DRE': '/content/DRE_20250929_205456.xlsx',
    'DFC': '/content/DFC_20250929_205808.xlsx'
}

# Carregar o template
print("📥 Carregando template...")
df_template = pd.read_excel(TEMPLATE_PATH)
print(f"✅ Template carregado: {len(df_template)} linhas")

# Definir os anos de interesse - DE 2009 ATÉ 2024
anos = list(range(2009, 2025))  # 2009 a 2024 inclusive

# Mapeamento das contas que queremos buscar
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

# Carregar dados dos arquivos CVM
print("📂 Carregando arquivos CVM...")
dados_cvm = {}

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
            df = pd.read_excel(arquivo, sheet_name=aba_nome)
            # Garantir que CD_CVM seja string para comparação
            df['CD_CVM'] = df['CD_CVM'].astype(str)
            
            # Se estamos buscando 2009 na aba de 2010, filtrar apenas os registros de 2009
            if ano == 2009:
                df = df[df['ANO'] == 2009]
            
            dados_cvm[demonstracao][ano] = df
            print(f"✅ {aba_nome} (para ano {ano}) carregado - {len(df)} linhas")
            print(f"   Empresas únicas: {df['CD_CVM'].nunique()}")
            
        except Exception as e:
            print(f"❌ Erro ao carregar {aba_nome} (para ano {ano}): {e}")
            dados_cvm[demonstracao][ano] = None

# Função para buscar valor de uma conta específica
def buscar_valor_conta(cd_cvm, conta_info, ano):
    """
    Busca o valor de uma conta específica para um CD_CVM e ano
    """
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
    """
    Calcula ROE apenas se:
    - Lucro Líquido > 0 E Patrimônio Líquido > 0
    Caso contrário, retorna NaN
    """
    if pd.isna(lucro_liquido) or pd.isna(patrimonio_liquido):
        return np.nan
    
    # Condição: Lucro Líquido > 0 E Patrimônio Líquido > 0
    if lucro_liquido > 0 and patrimonio_liquido > 0:
        return lucro_liquido / patrimonio_liquido
    else:
        return np.nan

# Processar o template
print("\n🚀 INICIANDO BUSCA DE DADOS CONTÁBEIS...")
print("=" * 60)

# Criar cópia do template para preencher
df_resultado = df_template.copy()

# Garantir que CD_CVM no template seja string
df_resultado['CD_CVM'] = df_resultado['CD_CVM'].astype(str)

# Contadores para estatísticas
total_linhas = len(df_resultado)
linhas_processadas = 0
empresas_com_dados = 0

# Agrupar por empresa e ano para evitar processamento duplicado
empresas_unicas = df_resultado[['CD_CVM', 'DENOM_CIA', 'Ano']].drop_duplicates()
empresas_unicas['CD_CVM'] = empresas_unicas['CD_CVM'].astype(str)

print(f"📊 Total de empresas/anos únicos para processar: {len(empresas_unicas)}")
print(f"📅 Período coberto: {min(anos)} a {max(anos)}")
print(f"💡 Nota: Dados de 2009 serão buscados nas abas de 2010")

# Para cada empresa/ano único no template
for idx, empresa in empresas_unicas.iterrows():
    cd_cvm = empresa['CD_CVM']
    denom_cia = empresa['DENOM_CIA']
    ano = empresa['Ano']
    
    # Pular se o ano não estiver no nosso range de interesse
    if ano not in anos:
        continue
        
    print(f"🔍 Processando: {denom_cia} ({cd_cvm}) - {ano}")
    
    # Buscar dados para cada conta
    dados_empresa = {}
    for conta_nome, conta_info in CONTAS_BUSCAR.items():
        valor = buscar_valor_conta(cd_cvm, conta_info, ano)
        dados_empresa[conta_nome] = valor
        
        if valor is not None:
            print(f"   ✅ {conta_nome}: {valor:,.0f}")
        # else:
        #     print(f"   ❌ {conta_nome}: Não encontrado")
    
    # Verificar se encontrou algum dado
    if any(valor is not None for valor in dados_empresa.values()):
        empresas_com_dados += 1
        
        # Atualizar todas as linhas com este CD_CVM e Ano
        mask = (df_resultado['CD_CVM'] == cd_cvm) & (df_resultado['Ano'] == ano)
        linhas_afetadas = mask.sum()
        linhas_processadas += linhas_afetadas
        
        for conta_nome, valor in dados_empresa.items():
            df_resultado.loc[mask, conta_nome] = valor
        
        print(f"   📈 Dados aplicados a {linhas_afetadas} linha(s)")
    else:
        print(f"   ⚠️  Nenhum dado encontrado")
    
    print("-" * 40)

# 🔧 CALCULAR ROE COM VALIDAÇÃO APÓS PREENCHER TODOS OS DADOS
print("\n📊 Calculando ROE com validação...")

# Verificar se as colunas necessárias existem
if 'Lucro/Prejuízo Consolidado do Período' in df_resultado.columns and 'Patrimônio Líquido Consolidado' in df_resultado.columns:
    
    # Aplicar a função de cálculo de ROE com validação
    df_resultado['ROE'] = df_resultado.apply(
        lambda row: calcular_roe_se_aplicavel(
            row['Lucro/Prejuízo Consolidado do Período'], 
            row['Patrimônio Líquido Consolidado']
        ), 
        axis=1
    )
    
    # Contar quantos ROEs foram calculados
    roe_calculados = df_resultado['ROE'].notna().sum()
    roe_nao_calculados = len(df_resultado) - roe_calculados
    
    print(f"✅ ROE calculado para {roe_calculados} linhas")
    print(f"📊 ROE não calculado (devido a LL ≤ 0 ou PL ≤ 0): {roe_nao_calculados} linhas")
    
    # Mostrar exemplos de casos onde ROE não foi calculado
    casos_nao_calculados = df_resultado[
        (df_resultado['Lucro/Prejuízo Consolidado do Período'].notna()) & 
        (df_resultado['Patrimônio Líquido Consolidado'].notna()) & 
        (df_resultado['ROE'].isna())
    ].head(5)
    
    if len(casos_nao_calculados) > 0:
        print(f"\n🔍 EXEMPLOS DE CASOS ONDE ROE NÃO FOI CALCULADO:")
        for _, caso in casos_nao_calculados.iterrows():
            ll = caso['Lucro/Prejuízo Consolidado do Período']
            pl = caso['Patrimônio Líquido Consolidado']
            print(f"   • {caso['DENOM_CIA']} ({caso['Ano']}): LL = {ll:,.0f}, PL = {pl:,.0f}")
else:
    print("⚠️  Colunas necessárias para cálculo do ROE não encontradas")

# Salvar resultados
print("\n💾 Salvando resultados...")
df_resultado.to_excel(OUTPUT_PATH, index=False)

# Estatísticas finais
print("\n🎯 PROCESSAMENTO CONCLUÍDO!")
print("=" * 60)
print(f"📊 ESTATÍSTICAS:")
print(f"   • Período analisado: {min(anos)} a {max(anos)}")
print(f"   • Total de anos: {len(anos)}")
print(f"   • Total de linhas no template: {total_linhas}")
print(f"   • Linhas processadas: {linhas_processadas}")
print(f"   • Empresas/anos com dados encontrados: {empresas_com_dados}")
print(f"   • Taxa de sucesso: {(empresas_com_dados/len(empresas_unicas))*100:.1f}%")

# Verificar preenchimento das contas
print(f"\n📈 DADOS OBTIDOS POR CONTA:")
for conta_nome in CONTAS_BUSCAR.keys():
    preenchidas = df_resultado[conta_nome].notna().sum()
    total = len(df_resultado)
    percentual = (preenchidas / total) * 100
    print(f"   • {conta_nome}: {preenchidas}/{total} ({percentual:.1f}%)")

# Mostrar também o ROE se foi calculado
if 'ROE' in df_resultado.columns:
    preenchidas_roe = df_resultado['ROE'].notna().sum()
    total_roe = len(df_resultado)
    percentual_roe = (preenchidas_roe / total_roe) * 100
    print(f"   • ROE (válido): {preenchidas_roe}/{total_roe} ({percentual_roe:.1f}%)")

print(f"\n💾 ARQUIVO SALVO: {OUTPUT_PATH}")
print(f"📅 HORÁRIO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Mostrar amostra dos resultados
print(f"\n🔍 AMOSTRA DOS RESULTADOS:")
colunas_amostra = ['CD_CVM', 'DENOM_CIA', 'Ticker', 'Ano', 'Ativo Total', 
                   'Lucro/Prejuízo Consolidado do Período', 'Patrimônio Líquido Consolidado']
if 'ROE' in df_resultado.columns:
    colunas_amostra.append('ROE')
amostra = df_resultado[colunas_amostra].head(10)

# Formatando os valores para melhor visualização
for col in amostra.columns:
    if col in ['Ativo Total', 'Lucro/Prejuízo Consolidado do Período', 'Patrimônio Líquido Consolidado']:
        amostra[col] = amostra[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) and isinstance(x, (int, float)) else x)
    elif col == 'ROE':
        amostra[col] = amostra[col].apply(lambda x: f"{x:.4f}" if pd.notna(x) and isinstance(x, (int, float)) else "N/A")

print(amostra)

# Mostrar distribuição por ano
print(f"\n📅 DISTRIBUIÇÃO DE DADOS POR ANO:")
for ano in sorted(df_resultado['Ano'].unique()):
    if ano in anos:  # Apenas anos que tentamos buscar
        linhas_ano = len(df_resultado[df_resultado['Ano'] == ano])
        dados_preenchidos = df_resultado[df_resultado['Ano'] == ano]['Ativo Total'].notna().sum()
        percentual = (dados_preenchidos/linhas_ano*100) if linhas_ano > 0 else 0
        fonte = " (busca em 2010)" if ano == 2009 else ""
        
        # Adicionar info sobre ROE válido por ano
        if 'ROE' in df_resultado.columns:
            roe_valido_ano = df_resultado[(df_resultado['Ano'] == ano) & (df_resultado['ROE'].notna())].shape[0]
            print(f"   • {ano}: {dados_preenchidos}/{linhas_ano} empresas com dados ({percentual:.1f}%) - {roe_valido_ano} ROEs válidos{fonte}")
        else:
            print(f"   • {ano}: {dados_preenchidos}/{linhas_ano} empresas com dados ({percentual:.1f}%){fonte}")

# Mostrar algumas empresas que foram processadas com sucesso
print(f"\n🏢 EMPRESAS COM DADOS ENCONTRADOS:")
empresas_com_dados_df = df_resultado[df_resultado['Ativo Total'].notna()][['CD_CVM', 'DENOM_CIA', 'Ano']].drop_duplicates()
print(empresas_com_dados_df.head(10))
