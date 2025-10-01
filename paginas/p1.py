import streamlit as st
import google.generativeai as genai
from pydantic import BaseModel, Field
import json

# --- CONFIGURAÇÃO DA PÁGINA E API DO GOOGLE ---

st.set_page_config(layout="wide", page_title="🕵️ Quem Sou Eu?")

# Carrega a chave da API a partir dos segredos do Streamlit de forma segura
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except (KeyError, FileNotFoundError):
    st.error("Chave da API do Google (GOOGLE_API_KEY) não encontrada. Por favor, configure-a nos segredos do seu app no Streamlit Cloud.")
    st.stop()


# --- DEFINIÇÃO DO SCHEMA (ESTRUTURA) DO PERSONAGEM ---

class Personagem(BaseModel):
    """
    Schema para estruturar os dados do personagem gerado pela IA.
    """
    personagem: str = Field(description="O nome completo da persona.")
    descricao: str = Field(description="Um ou mais parágrafos detalhados com informações biográficas, características e feitos notáveis, SEM revelar o nome.")
    estilo: str = Field(description="Uma descrição sucinta do estilo de comunicação da persona (ex: 'Formal e enigmático', 'Alegre e um pouco caótico').")
    # A instrução foi reforçada para garantir que a saudação seja neutra
    saudacao: str = Field(description="Uma frase curta de saudação que a persona diria. A saudação DEVE SER genérica e NÃO PODE conter nomes, títulos ou referências óbvias que revelem a identidade.")

# --- PROMPT PARA GERAR O PERSONAGEM (REFORÇADO) ---

PROMPT_GERADOR = """
# Papel e Objetivo
Você é um roteirista para um jogo de adivinhação. Sua missão é escolher secretamente uma figura (histórica, famosa ou fictícia) e criar seus dados.
**REGRA CRÍTICA:** O personagem escolhido NÃO PODE estar na lista de exclusão: {lista_geracao}

Sua resposta DEVE ser um JSON com os seguintes campos:
- "personagem": Nome completo do personagem.
- "descricao": Narrativa sobre a persona, com feitos e características, mas SEM revelar o nome.
- "estilo": O estilo de comunicação da persona.
- "saudacao": Uma saudação inicial. **IMPORTANTE: A saudação precisa ser genérica e não pode entregar a identidade do personagem de forma alguma. Evite nomes, títulos ou jargões muito específicos.**
"""

# --- FUNÇÕES OTIMIZADAS DO JOGO ---

@st.cache_data(show_spinner="Gerando um novo personagem...")
def gerar_novo_personagem(lista_a_evitar):
    """
    Chama a API do Gemini para gerar um novo personagem.
    - Usa o modelo 'gemini-1.5-flash' para alta velocidade de resposta.
    - Utiliza o cache do Streamlit para otimização.
    - Inclui tratamento de erro para falhas na API.
    """
    # Usar gemini-1.5-flash é ideal para aplicações de chat devido à sua baixa latência.
    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    
    nomes_a_evitar = ", ".join(lista_a_evitar) if lista_a_evitar else "Nenhum"
    prompt_formatado = PROMPT_GERADOR.format(lista_geracao=nomes_a_evitar)

    try:
        response = model.generate_content(
            prompt_formatado,
            generation_config=genai.types.GenerationConfig(
                response_mime_type='application/json',
                response_schema=Personagem,
            )
        )
        return json.loads(response.text)
    except Exception as e:
        st.error(f"Ocorreu um erro ao gerar o personagem: {e}")
        return None

def iniciar_novo_jogo():
    """
    Prepara o estado da sessão para um novo jogo.
    """
    st.session_state.mensagens = []
    
    if 'personagens_usados' not in st.session_state:
        st.session_state.personagens_usados = []

    novo_personagem = gerar_novo_personagem(st.session_state.personagens_usados)
    
    # Validação robusta para evitar erros (KeyError) se a API falhar
    if novo_personagem and all(k in novo_personagem for k in ['personagem', 'descricao', 'estilo', 'saudacao']):
        st.session_state.personagem_secreto = novo_personagem
        st.session_state.personagens_usados.append(novo_personagem['personagem'])
        
        prompt_sistema = f"""
        ### Contexto do Jogo
        Você está interpretando uma persona secreta em um jogo de adivinhação.
        - Identidade Secreta: {st.session_state.personagem_secreto['personagem']}
        - Biografia (para sua consulta, não para recitar): {st.session_state.personagem_secreto['descricao']}
        - Estilo de Comunicação: {st.session_state.personagem_secreto['estilo']}

        ### Regras Cruciais
        1. **NUNCA REVELE A IDENTIDADE**: Seja evasivo a perguntas diretas.
        2. **DÊ PISTAS INDIRETAS**: Responda sempre sob a perspectiva da sua persona.
        3. **SEJA O PERSONAGEM**: Incorpore a personalidade definida.
        4. **GERENCIE PALPITES**: Se o usuário errar, negue sutilmente. Se acertar, confirme de forma criativa.
        
        **Comece o jogo APENAS com a sua saudação definida.**
        """
        
        st.session_state.chat = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=prompt_sistema
        ).start_chat(history=[])

        saudacao_inicial = st.session_state.personagem_secreto['saudacao']
        st.session_state.mensagens.append({"role": "assistant", "content": saudacao_inicial})
    else:
        st.error("Falha ao carregar o novo personagem. Por favor, tente iniciar um novo jogo.")
        if "mensagens" in st.session_state:
            del st.session_state.mensagens

# --- INTERFACE GRÁFICA DO STREAMLIT ---

with st.sidebar:
    st.header("🕵️ Quem Sou Eu?")
    st.markdown("Adivinhe o personagem secreto fazendo perguntas!")
    
    if st.button("🚀 Iniciar Novo Jogo", type="primary", use_container_width=True):
        iniciar_novo_jogo()
        st.rerun()

    st.markdown("---")
    st.header("Regras")
    st.markdown("1. Faça perguntas abertas ou de sim/não.\n2. Dê um palpite quando estiver confiante.\n3. Divirta-se!")
    
    if "personagens_usados" in st.session_state and st.session_state.personagens_usados:
        with st.expander("Personagens já utilizados"):
            for p in st.session_state.personagens_usados[:-1]:
                st.write(f"- {p}")

st.title("🕵️ Quem Sou Eu?")

if "mensagens" in st.session_state:
    for mensagem in st.session_state.mensagens:
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])

    if prompt := st.chat_input("Faça sua pergunta ou dê um palpite..."):
        st.session_state.mensagens.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Pensando..."):
            try:
                # Tratamento de erro na resposta do chat para evitar crashes
                resposta = st.session_state.chat.send_message(prompt)
                response_text = resposta.text
            except Exception as e:
                response_text = f"Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente. (Erro: {e})"
                st.error(response_text)
            
            st.session_state.mensagens.append({"role": "assistant", "content": response_text})
            # Forçar o rerun após adicionar a mensagem da IA garante a atualização da tela
            st.rerun()

else:
    st.info("Clique em 'Iniciar Novo Jogo' na barra lateral para começar a diversão!")