import streamlit as st
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPICallError
from pydantic import BaseModel, Field
import json

# --- CONFIGURAÇÃO DA API DO GOOGLE ---
st.set_page_config(page_title="Quem Sou Eu?", page_icon="🕵️")

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except (KeyError, FileNotFoundError):
    st.error("A GOOGLE_API_KEY não foi encontrada. Por favor, configure-a nos secrets do Streamlit.")
    st.stop()

# --- DEFINIÇÃO DO SCHEMA (ESTRUTURA) DO PERSONAGEM ---
class Personagem(BaseModel):
    personagem: str = Field(description="O nome completo da persona.")
    descricao: str = Field(description="Um ou mais parágrafos detalhados com informações biográficas, SEM revelar o nome.")
    estilo: str = Field(description="Uma descrição sucinta do estilo de comunicação da persona.")
    saudacao: str = Field(description="Uma frase curta de saudação que a persona diria ao iniciar o jogo.")

# --- FUNÇÕES DO JOGO ---

@st.cache_data(show_spinner="Estou buscando um novo personagem... 🕵️‍♂️")
def gerar_novo_personagem(lista_a_evitar: list) -> dict | None:
    prompt_gerador = """
    # Papel e Objetivo
    Você é um roteirista de um jogo de adivinhação. Selecione uma figura conhecida (real ou fictícia) que não esteja na lista: {lista_geracao}.
    Sua resposta deve ser um JSON com os campos: "personagem", "descricao", "estilo", "saudacao".
    """
    try:
        client = genai.GenerativeModel(model_name="gemini-1.5-flash")
        nomes_a_evitar = ", ".join(lista_a_evitar) if lista_a_evitar else "Nenhum"
        prompt_formatado = prompt_gerador.format(lista_geracao=nomes_a_evitar)
        response = client.generate_content(
            prompt_formatado,
            generation_config=genai.types.GenerationConfig(
                response_mime_type='application/json',
                response_schema=Personagem,
            )
        )
        return json.loads(response.text)
    except GoogleAPICallError as e:
        st.error(f"Erro na API do Google ao gerar personagem: {e}")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao gerar personagem: {e}")
        return None

def iniciar_novo_jogo():
    if 'personagens_usados' not in st.session_state:
        st.session_state.personagens_usados = []

    novo_personagem = gerar_novo_personagem(st.session_state.personagens_usados)

    if not isinstance(novo_personagem, dict) or not all(k in novo_personagem for k in Personagem.model_fields):
        st.warning("Não foi possível gerar um novo personagem no momento. Por favor, tente novamente.")
        return

    st.session_state.personagem_secreto = novo_personagem
    st.session_state.personagens_usados.append(novo_personagem['personagem'])
    
    st.session_state.mensagens = []
    prompt_sistema = f"""
    ### Contexto do Jogo
    Você está interpretando uma persona em um jogo de adivinhação.
    Sua identidade secreta é: {st.session_state.personagem_secreto['personagem']}.
    Sua biografia para consulta (não para recitar) é: {st.session_state.personagem_secreto['descricao']}.
    Seu estilo de comunicação é: {st.session_state.personagem_secreto['estilo']}.

    ### Regras Cruciais
    1. **NUNCA REVELE SUA IDENTIDADE**.
    2. Dê pistas indiretas com base na sua persona.
    3. Incorpore a personalidade e o estilo definidos.
    4. Se o usuário acertar, confirme e parabenize-o. Se errar, negue sutilmente.
    Comece o jogo com a saudação definida. NADA MAIS.
    """
    
    st.session_state.chat = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=prompt_sistema
    ).start_chat()
    
    saudacao_inicial = st.session_state.personagem_secreto['saudacao']
    st.session_state.mensagens.append({"role": "assistant", "content": saudacao_inicial})

# --- INTERFACE GRÁFICA DO STREAMLIT ---
st.title("🕵️ Quem Sou Eu?")
st.markdown("Bem-vindo! Tente adivinhar o personagem que eu escolhi.")

if st.button("🚀 Iniciar Novo Jogo", type="primary", use_container_width=True):
    for key in ["chat", "mensagens", "personagem_secreto"]:
        if key in st.session_state:
            del st.session_state[key]
    iniciar_novo_jogo()
    st.rerun()

if "chat" in st.session_state:
    for mensagem in st.session_state.mensagens:
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])

    if prompt := st.chat_input("Faça sua pergunta ou dê um palpite..."):
        st.session_state.mensagens.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    resposta = st.session_state.chat.send_message(prompt)
                    # ADICIONADO: Verificação se a resposta não foi bloqueada
                    if resposta.parts:
                        resposta_texto = resposta.text
                    else:
                        # Resposta foi bloqueada por filtros de segurança
                        resposta_texto = "Não posso responder a isso. Por favor, tente outra pergunta."
                        # Opcional: registrar o motivo do bloqueio, se disponível
                        # print(resposta.prompt_feedback) 
                except GoogleAPICallError as e:
                    resposta_texto = f"Houve um problema com a API do Google. Tente novamente. (Erro: {e})"
                except Exception as e:
                    resposta_texto = f"Ocorreu um erro inesperado. Por favor, reinicie o jogo. (Erro: {e})"
                
                st.markdown(resposta_texto)
        
        st.session_state.mensagens.append({"role": "assistant", "content": resposta_texto})
        
        # REMOVIDO: st.rerun() não é estritamente necessário e torna a UI mais fluida.
        # O Streamlit irá inserir a nova mensagem na tela automaticamente.
else:
    st.info("O jogo ainda não começou. Clique no botão acima para iniciar.")

with st.sidebar:
    st.header("Regras do Jogo")
    st.markdown("""
    1.  Faça perguntas para descobrir a identidade secreta.
    2.  Dê um palpite quando se sentir confiante.
    3.  Use o botão 'Iniciar Novo Jogo' para recomeçar.
    4.  Divirta-se!
    """)