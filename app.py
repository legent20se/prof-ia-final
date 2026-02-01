import streamlit as st
import google.generativeai as genai
from elevenlabs.client import ElevenLabs
from pypdf import PdfReader

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Professeur IA Virtuel",
    page_icon="🎓",
    layout="wide"
)

# --- RÉCUPÉRATION DES SECRETS ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]
    VOICE_ID = st.secrets["ELEVENLABS_VOICE_ID"]
except KeyError as e:
    st.error(f"Erreur : La clé {e} est manquante dans les Secrets Streamlit.")
    st.stop()

# Initialisation des clients API
genai.configure(api_key=GOOGLE_API_KEY)
client_eleven = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# --- FONCTIONS TECHNIQUES ---

def get_pdf_text(pdf_docs):
    """Extrait le texte de tous les fichiers PDF téléchargés."""
    text = ""
    for pdf in pdf_docs:
        try:
            reader = PdfReader(pdf)
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    text += content + "\n"
        except Exception as e:
            st.error(f"Erreur lors de la lecture d'un PDF : {e}")
    return text

def process_interaction(user_input, context, is_audio=False):
    """Envoie la requête (audio ou texte) à Gemini avec le contexte du cours."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Consigne pédagogique pour l'IA
    system_instruction = (
        "Tu es un professeur expert en NSI et Mathématiques. "
        "Réponds de manière claire, concise et pédagogique. "
        f"Utilise ce contexte de cours pour tes réponses : \n\n{context[:50000]}"
    )
    
    if is_audio:
        # Gemini 1.5 Flash traite l'audio nativement
        response = model.generate_content([system_instruction, user_input])
    else:
        response = model.generate_content(f"{system_instruction}\n\nQuestion de l'élève : {user_input}")
    
    return response.text

def play_voice(text):
    """Génère la synthèse vocale avec ton clone ElevenLabs."""
    try:
        audio = client_eleven.generate(
            text=text,
            voice=VOICE_ID,
            model="eleven_multilingual_v2"
        )
        return b"".join(audio)
    except Exception as e:
        st.warning(f"Note : La synthèse vocale a échoué (vérifie tes crédits ElevenLabs). Erreur : {e}")
        return None

# --- INTERFACE UTILISATEUR (UI) ---

st.title("🎓 Assistant Professeur IA")
st.info("Posez vos questions par écrit ou au micro. Je vous répondrai avec ma propre voix en m'appuyant sur vos cours.")

# Barre latérale pour charger les cours
with st.sidebar:
    st.header("📚 Documents de cours")
    uploaded_files = st.file_uploader(
        "Déposez vos PDF ici", 
        accept_multiple_files=True, 
        type=['pdf']
    )
    
    if uploaded_files:
        if st.button("🧠 Mémoriser les cours"):
            with st.spinner("Analyse des documents en cours..."):
                st.session_state['context'] = get_pdf_text(uploaded_files)
                st.success(f"Cours intégrés ({len(st.session_state['context'])} caractères) !")

# Initialisation du contexte dans la session
if 'context' not in st.session_state:
    st.session_state['context'] = ""

# Zone d'interaction
st.divider()
col_mic, col_text = st.columns([1, 2])

with col_mic:
    # Composant natif pour l'enregistrement audio
    audio_data = st.audio_input("🎤 Parler au professeur")

with col_text:
    # Entrée texte classique
    text_data = st.chat_input("Ou écrivez votre question ici...")

# Logique de traitement des entrées
user_content = None
is_audio_input = False

if audio_data:
    user_content = {"mime_type": "audio/wav", "data": audio_data.read()}
    is_audio_input = True
elif text_data:
    user_content = text_data
    is_audio_input = False

# Génération et affichage de la réponse
if user_content:
    with st.spinner("Réflexion..."):
        # 1. Obtenir la réponse de l'IA
        answer = process_interaction(user_content, st.session_state['context'], is_audio=is_audio_input)
        
        # 2. Afficher la réponse écrite
        with st.chat_message("assistant"):
            st.write(answer)
        
        # 3. Générer et jouer l'audio
        audio_bytes = play_voice(answer)
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3", autoplay=True)