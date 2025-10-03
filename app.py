import streamlit as st

st.set_page_config(page_title="Dashboard CVM", layout="centered")
st.title("🚀 Dashboard CVM - TESTE MÍNIMO")

# Teste 1: Streamlit básico
st.success("✅ Streamlit funcionando!")

# Teste 2: Pandas básico
try:
    import pandas as pd
    st.success("✅ Pandas importado!")
    
    # Criar dados mínimos
    data = {'Setor': ['Comércio', 'Energia'], 'Empresas': [64, 64]}
    df = pd.DataFrame(data)
    
    st.write("### DataFrame de teste:")
    st.dataframe(df)
    
    st.write("### Gráfico básico:")
    st.bar_chart(df.set_index('Setor'))
    
except Exception as e:
    st.error(f"❌ Erro com pandas: {e}")

st.info("🎉 Versão mínima funcionando! Podemos evoluir agora.")
