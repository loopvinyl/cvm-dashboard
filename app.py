import streamlit as st

st.set_page_config(page_title="Dashboard CVM", layout="centered")
st.title("🚀 Dashboard CVM - NOVO REPOSITÓRIO")

try:
    import pandas as pd
    st.success("✅ Pandas carregado com sucesso!")
except ImportError as e:
    st.error(f"❌ Erro ao carregar pandas: {e}")

try:
    import plotly.express as px
    st.success("✅ Plotly carregado com sucesso!")
except ImportError as e:
    st.error(f"❌ Erro ao carregar plotly: {e}")

try:
    import numpy as np
    st.success("✅ Numpy carregado com sucesso!")
except ImportError as e:
    st.error(f"❌ Erro ao carregar numpy: {e}")

# Se todas as bibliotecas carregaram, mostrar o conteúdo principal
try:
    if 'pd' in locals() and 'px' in locals():
        st.success("✅ TODAS AS BIBLIOTECAS CARREGADAS!")
        
        st.write("""
        ## Teste Básico Concluído ✅

        - Streamlit: ✅
        - Pandas: ✅  
        - Plotly: ✅
        - Numpy: ✅

        **Próximos passos:**
        1. Adicionar leitura do Excel
        2. Implementar análises
        3. Adicionar gráficos interativos
        """)

        # Dados de exemplo SIMPLES
        df = pd.DataFrame({
            'Setor': ['Comércio', 'Energia', 'Bancos', 'Construção'],
            'Empresas': [64, 64, 48, 58]
        })

        st.write("### Dados de Exemplo")
        st.dataframe(df)

        # Gráfico básico do Streamlit (não precisa do Plotly ainda)
        st.bar_chart(df.set_index('Setor')['Empresas'])
        
        st.balloons()
    else:
        st.error("❌ Algumas bibliotecas não carregaram. Verifique o requirements.txt")
        
except Exception as e:
    st.error(f"❌ Erro durante a execução: {e}")
