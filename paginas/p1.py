import streamlit as st
import google.generativeai as genai
from pydantic import BaseModel, Field
import json

# --- CONFIGURAÇÃO DA API DO GOOGLE ---
# Certifique-se de que sua GOOGLE_API_KEY está configurada nos secrets do Streamlit
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except (KeyError, FileNotFoundError):
    st.error("A GOOGLE_API_KEY não foi encontrada. Por favor, configure-a nos secrets do Streamlit.")
    st.stop()


# --- DEFINIÇÃO DO SCHEMA (ESTRUTURA) DO PERSONAGEM VIA PYDANTIC ---
class Personagem(BaseModel):
    """
    Schema para estruturar os dados do personagem gerado pela IA.
    """
    personagem: str = Field(description="O nome completo da persona.")
    descricao: str = Field(description="Um ou mais parágrafos detalhados com informações biográficas, características e feitos notáveis, SEM revelar o nome.")
    estilo: str = Field(description="Uma descrição sucinta do estilo de comunicação da persona (ex: 'Formal e enigmático', 'Alegre e um pouco caótico').")
    saudacao: str = Field(description="Uma frase curta de saudação que a persona diria ao iniciar o jogo.")


# --- FUNÇÕES DO JOGO ---

@st.cache_data(show_spinner="Estou buscando um novo personagem... 🕵️‍♂️")
def gerar_novo_personagem(lista_a_evitar: list) -> dict | None:
    """
    Chama a API do Gemini para gerar um novo personagem com base no prompt e no schema.
    Retorna um dicionário com os dados do personagem ou None em caso de falha.
    """
    # PROMPT PARA GERAR O PERSONAGEM
    prompt_gerador = """
    # Papel e Objetivo
    Você atua como roteirista e diretor de um jogo de adivinhação de personagens. Sua missão é selecionar secretamente uma figura conhecida (histórica, famosa ou fictícia) que seja amplamente reconhecida pelo público.
    **REGRA CRÍTICA:** O personagem escolhido NÃO PODE estar presente na seguinte lista de exclusão: {lista_geracao}
    
    Sua resposta deve ser um JSON contendo, rigorosamente, os seguintes campos:
    - "personagem": Nome do personagem selecionado.
    - "descricao": Narrativa clara e envolvente sobre a persona, destacando feitos e características marcantes, sem revelar explicitamente a identidade.
    - "estilo": Descrição detalhada do estilo de comunicação da persona.
    - "saudacao": Fala inicial, genérica o suficiente para não revelar a identidade.
    
    Verifique se a identidade não é explicitamente revelada na descrição ou saudação e que o personagem não está na lista de exclusão antes de retornar a saída final.
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
    except Exception as e:
        st.error(f"Ocorreu um erro ao contatar a API do Gemini: {e}")
        return None


def iniciar_novo_jogo():
    """
    Prepara o estado da sessão para um novo jogo.
    """
    if 'personagens_usados' not in st.session_state:
        st.session_state.personagens_usados = []

    novo_personagem = gerar_novo_personagem(st.session_state.personagens_usados)

    # Verificação robusta para garantir que a API retornou um personagem válido
    if not isinstance(novo_personagem, dict) or not all(k in novo_personagem for k in Personagem.model_fields):
        st.error("Não foi possível gerar um novo personagem. Por favor, tente novamente.")
        return # Interrompe a execução para evitar erros

    st.session_state.personagem_secreto = novo_personagem
    st.session_state.personagens_usados.append(novo_personagem['personagem'])
    
    # Limpa o histórico de mensagens e prepara o prompt do sistema para o novo personagem
    st.session_state.mensagens = []

    prompt_sistema = f"""
    ### Contexto do Jogo
    Você é um assistente de IA interpretando uma persona em um jogo de adivinhação.
    A identidade secreta que você deve assumir é: {st.session_state.personagem_secreto['personagem']}.
    Sua biografia para consulta (não para recitar) é: {st.session_state.personagem_secreto['descricao']}.
    Seu estilo de comunicação é: {st.session_state.personagem_secreto['estilo']}.

    ### Regras Cruciais
    1. **NUNCA REVELE SUA IDENTIDADE**: Sob nenhuma circunstância diga quem você é.
    2. **DÊ PISTAS INDIRETAS**: Responda com base no conhecimento e na perspectiva da sua persona.
    3. **SEJA O PERSONAGEM**: Incorpore a personalidade e o estilo de comunicação definidos.
    4. **GERENCIE PALPITES**: Se o usuário acertar, confirme de maneira criativa e parabenize-o. Se errar, negue sutilmente.

    Comece o jogo com a saudação definida. NADA MAIS.
    """

    # Cria a instância do chat com o prompt do sistema
    # Este objeto será a garantia de que o jogo foi iniciado corretamente
    st.session_state.chat = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=prompt_sistema
    ).start_chat()

    # Adiciona a saudação inicial do personagem ao histórico para exibição
    saudacao_inicial = st.session_state.personagem_secreto['saudacao']
    st.session_state.mensagens.append({"role": "assistant", "content": saudacao_inicial})


# --- INTERFACE GRÁFICA DO STREAMLIT ---

st.set_page_config(page_title="Quem Sou Eu?", page_icon="🕵️")

st.title("🕵️ Quem Sou Eu?")
st.markdown("""
Bem-vindo! Eu vou pensar em um personagem (real ou fictício) e você deve adivinhar quem é fazendo perguntas.
**Clique no botão abaixo para começar!**
""")

if st.button("🚀 Iniciar Novo Jogo", type="primary", use_container_width=True):
    # Limpa o estado antigo para garantir um novo começo
    for key in ["chat", "mensagens", "personagem_secreto"]:
        if key in st.session_state:
            del st.session_state[key]
    iniciar_novo_jogo()
    st.rerun()

# A interface de chat só aparece se o objeto 'chat' foi criado com sucesso.
# Esta é a correção principal para o AttributeError.
if "chat" in st.session_state:
    # Exibe o histórico de mensagens
    for mensagem in st.session_state.mensagens:
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])

    # Captura a entrada do usuário
    if prompt := st.chat_input("Faça sua pergunta ou dê um palpite..."):
        # Adiciona a mensagem do usuário ao histórico e à interface
        st.session_state.mensagens.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Envia a mensagem para a IA e obtém a resposta
        with st.spinner("Pensando..."):
            try:
                resposta = st.session_state.chat.send_message(prompt)
                resposta_texto = resposta.text
            except Exception as e:
                resposta_texto = f"Ocorreu um erro ao processar sua pergunta: {e}"

        # Adiciona a resposta da IA ao histórico e à interface
        with st.chat_message("assistant"):
            st.markdown(resposta_texto)
        st.session_state.mensagens.append({"role": "assistant", "content": resposta_texto})
        
        # Reinicia o script para atualizar a tela
        st.rerun()
else:
    st.info("O jogo ainda não começou. Clique no botão acima para iniciar.")

# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    st.header("Regras do Jogo")
    st.markdown("""
    1.  **Faça perguntas** de "sim" ou "não", ou perguntas abertas (Ex: "Em que século você viveu?").
    2.  **Dê um palpite** quando achar que sabe quem é o personagem.
    3.  **Use o botão 'Iniciar Novo Jogo'** para começar uma nova rodada a qualquer momento.
    4.  Divirta-se!
    """)
