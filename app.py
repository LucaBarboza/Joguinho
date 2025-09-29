import streamlit as st

st.set_page_config(
    page_title="Joguinho",  # Novo Título
    page_icon="👍", # Alterado para usar o avatar do assistente
    layout='wide',                       # Melhor aproveitamento do espaço
    initial_sidebar_state="expanded"
)

paginas = {
    "Home": [st.Page("paginas/p1.py", title="Jogo", icon='🏠', default=True)]
}

pg = st.navigation(paginas)
pg.run()