import streamlit as st
import google.generativeai as genai
from pydantic import BaseModel, Field
import json

# --- CONFIGURAÇÃO DA API DO GOOGLE ---

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)
client = genai.GenerativeModel(model_name="gemini-2.5-flash")


# --- DEFINIÇÃO DO SCHEMA (ESTRUTURA) DO PERSONAGEM ---
class Personagem(BaseModel):
    """
    Schema para estruturar os dados do personagem gerado pela IA.
    """
    personagem: str = Field(description="O nome completo da persona.")
    descricao: str = Field(description="Um ou mais parágrafos detalhados com informações biográficas, características e feitos notáveis, SEM revelar o nome.")
    estilo: str = Field(description="Uma descrição sucinta do estilo de comunicação da persona (ex: 'Formal e enigmático', 'Alegre e um pouco caótico').")
    saudacao: str = Field(description="Uma frase curta de saudação que a persona diria ao iniciar o jogo.")

# --- PROMPT PARA GERAR O PERSONAGEM ---
PROMPT_GERADOR = """
# Papel e Objetivo
Você atua como roteirista e diretor de um jogo de adivinhação de personagens. Sua missão é selecionar secretamente uma figura conhecida (histórica, famosa ou fictícia) que seja amplamente reconhecida pelo público.
**REGRA CRÍTICA:** O personagem escolhido NÃO PODE estar presente na seguinte lista de exclusão: {lista_geracao}
Sua resposta deve conter, rigorosamente nesta ordem, os seguintes campos:
- "personagem": Nome do personagem selecionado.
- "descricao": Narrativa clara e envolvente sobre a persona, destacando feitos e características marcantes, mas sem revelar explicitamente a identidade. Use nível moderado de detalhe: seja específico, porém evite informar dados que entreguem o nome de forma explícita.
- "estilo": Descrição detalhada do estilo de comunicação da persona.
- "saudacao": Fala inicial, dando oi/olá ao jogador com a personalidade do personagem, mas sem revelar nenhuma de suas principais caracteristicas, genérico o suficiente para não revelar a identidade — não inclua nomes, títulos óbvios ou referências únicas facilmente reconhecíveis.
Após definir a resposta, verifique se todos os campos estão preenchidos corretamente, que a identidade não é explicitamente revelada e que o personagem selecionado atende à regra crítica de exclusão. Se algum critério falhar, faça uma auto-correção antes de retornar a saída final.
"""

# --- FUNÇÕES DO JOGO ---

@st.cache_data(show_spinner=False)
def gerar_novo_personagem(lista_a_evitar):
    """
    Chama a API do Gemini para gerar um novo personagem com base no prompt e no schema.
    Utiliza o cache do Streamlit para não gerar o mesmo personagem repetidamente.
    """
    nomes_a_evitar = ", ".join(lista_a_evitar) if lista_a_evitar else "Nenhum"
    prompt_formatado = PROMPT_GERADOR.format(lista_geracao=nomes_a_evitar)

    response = client.generate_content(
      prompt_formatado,
      generation_config=genai.types.GenerationConfig(
          response_mime_type='application/json',
          response_schema=Personagem,
      )
    )
    return json.loads(response.text)


def iniciar_novo_jogo():
    """
    Prepara o estado da sessão para um novo jogo.
    """
    st.session_state.mensagens = []
    
    if 'personagens_usados' not in st.session_state:
        st.session_state.personagens_usados = []

    with st.spinner("Estou pensando em um novo personagem... 🕵️‍♂️"):
        novo_personagem = gerar_novo_personagem(st.session_state.personagens_usados)
        
        # --- INÍCIO DA CORREÇÃO ---
        # Verificação para garantir que a API retornou um dicionário com todas as chaves esperadas.
        required_keys = ['personagem', 'descricao', 'estilo', 'saudacao']
        if not isinstance(novo_personagem, dict) or not all(key in novo_personagem for key in required_keys):
            st.error("Houve um erro ao gerar um novo personagem. Por favor, tente novamente.")
            # Para depuração, você pode descomentar a linha abaixo para ver o que a API retornou:
            # st.write("Resposta inesperada da API:", novo_personagem) 
            return # Interrompe a execução da função para evitar o KeyError
        # --- FIM DA CORREÇÃO ---
            
        st.session_state.personagem_secreto = novo_personagem
        
        # Adiciona o novo personagem à lista de exclusão para jogos futuros
        st.session_state.personagens_usados.append(novo_personagem['personagem'])

    # Monta o prompt do sistema para o chatbot
    prompt_sistema = f"""
    ### Contexto do Jogo
    Você é um assistente de IA interpretando uma persona em um jogo de adivinhação.
    A identidade secreta que você deve assumir é: {st.session_state.personagem_secreto['personagem']}.
    Sua biografia para consulta (não para recitar) é: {st.session_state.personagem_secreto['descricao']}.
    Seu estilo de comunicação é: {st.session_state.personagem_secreto['estilo']}.

    ### Regras Cruciais
    1. **NUNCA REVELE SUA IDENTIDADE**: Sob nenhuma circunstância diga quem você é. Responda a perguntas diretas de forma evasiva e criativa.
    2. **DÊ PISTAS INDIRETAS**: Responda com base no conhecimento e na perspectiva da sua persona.
    3. **SEJA O PERSONAGEM**: Incorpore a personalidade e o estilo de comunicação definidos.
    4. **GERENCIE PALPITES**:
        - Se o usuário errar, negue de forma sutil e dentro do personagem.
        - Se o usuário acertar, confirme de maneira criativa e encerre o jogo parabenizando-o.

    Comece o jogo com a saudação definida. NADA MAIS.
    """
    
    # Cria a instância do chat com o prompt do sistema
    st.session_state.chat = genai.GenerativeModel(
        model_name="gemini-2.5-flash", # Recomendo usar gemini-1.5-flash para melhor performance
        system_instruction=prompt_sistema
    ).start_chat()

    # Adiciona a saudação inicial do personagem ao histórico
    saudacao_inicial = st.session_state.personagem_secreto['saudacao']
    st.session_state.mensagens.append({"role": "assistant", "content": saudacao_inicial})
# --- INTERFACE DO STREAMLIT ---

st.title("🕵️ Quem Sou Eu?")
st.markdown("---")
st.markdown("""
Bem-vindo ao jogo de adivinhação! Eu vou pensar em um personagem e você terá que descobrir quem é fazendo perguntas.
**Clique em 'Iniciar Novo Jogo' para começar!**
""")

if st.button("🚀 Iniciar Novo Jogo", type="primary", use_container_width=True):
    iniciar_novo_jogo()
    st.rerun() # Reinicia o script para atualizar a interface

# Se o jogo já começou, exibe a interface de chat
if "mensagens" in st.session_state:
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
            resposta = st.session_state.chat.send_message(prompt)
        
        # Adiciona a resposta da IA ao histórico e à interface
        with st.chat_message("assistant"):
            st.markdown(resposta.text)
        st.session_state.mensagens.append({"role": "assistant", "content": resposta.text})
        
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
