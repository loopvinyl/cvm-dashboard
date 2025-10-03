import streamlit as st

st.set_page_config(page_title="Dashboard CVM", layout="centered")
st.title("🚀 Dashboard CVM - NOVO REPOSITÓRIO")
st.success("✅ FINALMENTE FUNCIONANDO!")

st.write("""
## Teste Básico Concluído ✅

- Streamlit: ✅
- Pandas: ✅  
- Plotly: ✅

**Próximos passos:**
1. Adicionar leitura do Excel
2. Implementar análises
3. Adicionar gráficos interativos
""")

# Teste simples
import pandas as pd
import plotly.express as px

# Dados de exemplo
df = pd.DataFrame({
    'Setor': ['Comércio', 'Energia', 'Bancos', 'Construção'],
    'Empresas': [64, 64, 48, 58],
    'Receita (R$ Mi)': [45, 120, 89, 32]
})

st.write("### Dados de Exemplo")
st.dataframe(df)

fig = px.bar(df, x='Setor', y='Empresas', title='Empresas por Setor')
st.plotly_chart(fig)

st.balloons()
