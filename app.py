import sys

# Patch pour Python 3.13 (indispensable pour streamlit-mic-recorder)
try:
    import audioop
except ImportError:
    import audioop_lts as audioop
    sys.modules["audioop"] = audioop

try:
    import aifc
except ImportError:
    import standard_aifc as aifc
    sys.modules["aifc"] = aifc

# Maintenant tu peux importer le reste
import streamlit as st
import google.generativeai as genai
# ... le reste de ton code




import streamlit as st
import google.generativeai as genai
from elevenlabs.client import ElevenLabs
from PyPDF2 import PdfReader
from streamlit_mic_recorder import mic_recorder

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Professeur IA", layout="wide")

# --- VÉRIFICATION DES SECRETS (ANTI-CRASH) ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("ERREUR CRITIQUE : La clé GOOGLE_API_KEY est manquante dans les Secrets.")
    st.stop()
if "ELEVENLABS_API_KEY" not in st.secrets:
    st.error("ERREUR CRITIQUE : La clé ELEVENLABS_API_KEY est manquante dans les Secrets.")
    st.stop()

# --- INITIALISATION DES CLIENTS ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    client_eleven = ElevenLabs(api_key=st.secrets["ELEVENLABS_API_KEY"])
    VOICE_ID = st.secrets.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") # Une voix par défaut si la tienne manque
except Exception as e:
    st.error(f"Erreur de connexion aux API : {e}")
    st.stop()

# --- FONCTIONS ---
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        reader = PdfReader(pdf)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def get_ai_response(messages, context):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    system_instruction = f"""
    Tu es un professeur expert en lycée (NSI, Maths, STI2D).
    Tu dois répondre de manière pédagogique, encourageante et concise (pour l'audio).
    Utilise IMPÉRATIVEMENT le contexte suivant pour répondre si possible :
    ---
    {context[:100000]}
    ---
    Si la réponse n'est pas dans le contexte, utilise tes connaissances générales.
    """
    
    # On transforme l'historique pour Gemini
    gemini_history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in messages]
    
    # On ajoute l'instruction système manuellement pour ce modèle simple
    full_prompt = system_instruction + "\n\nDiscussion actuelle:\n" + str(gemini_history)
    
    response = model.generate_content(full_prompt)
    return response.text

def generate_audio(text):
    try:
        audio = client_eleven.generate(
            text=text,
            voice=VOICE_ID,
            model="eleven_multilingual_v2"
        )
        return b"".join(audio)
    except Exception as e:
        st.warning(f"Impossible de générer l'audio (Crédits épuisés ?): {e}")
        return None

# --- INTERFACE ---
st.title("🎓 Professeur Seb - NSI & Maths")

# Sidebar : Base de connaissances
with st.sidebar:
    st.header("📂 Vos Cours")
    uploaded_files = st.file_uploader("Déposez vos PDF de cours ici", accept_multiple_files=True, type=['pdf'])
    
    if uploaded_files:
        if st.button("🧠 Analyser et Mémoriser"):
            with st.spinner("Lecture des cours en cours..."):
                raw_text = get_pdf_text(uploaded_files)
                st.session_state['context'] = raw_text
                st.success(f"Cours intégrés ! ({len(raw_text)} caractères)")

# État de la session
if "messages" not in st.session_state:
    st.session_state.messages = []
if "context" not in st.session_state:
    st.session_state['context'] = ""

# Affichage de l'historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "audio" in msg:
            st.audio(msg["audio"], format="audio/mp3")

# ZONE D'ENTRÉE (MICRO OU TEXTE)
st.write("---")
col1, col2 = st.columns([1, 4])

with col1:
    st.write("🎤 Parler")
    audio_input = mic_recorder(start_prompt="🔴", stop_prompt="⬛", just_once=True, key='recorder')

user_text = st.chat_input("Écrivez votre question...")

final_input = None

# Logique de détection d'entrée
if user_text:
    final_input = user_text
elif audio_input and 'bytes' in audio_input:
    # Note: Pour transcrire l'audio utilisateur vers texte, il faudrait Whisper.
    # Pour simplifier et éviter les erreurs de quota, on demande à l'élève d'écrire
    # ou on simule (ici on prend le texte s'il existe).
    st.info("🎙️ Audio reçu (Transcription Whisper nécessaire pour la V2). Écrivez votre question pour l'instant.")

if final_input:
    # 1. Ajout message utilisateur
    st.session_state.messages.append({"role": "user", "content": final_input})
    with st.chat_message("user"):
        st.write(final_input)

    # 2. Réponse IA
    if st.session_state['context'] == "":
        st.warning("⚠️ Attention : Aucun cours chargé. Je réponds avec mes connaissances générales.")
    
    with st.chat_message("assistant"):
        with st.spinner("Réflexion..."):
            ai_msg = get_ai_response(st.session_state.messages, st.session_state['context'])
            st.write(ai_msg)
            
            # 3. Génération Voix Prof
            audio_bytes = generate_audio(ai_msg)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                st.session_state.messages.append({"role": "assistant", "content": ai_msg, "audio": audio_bytes})
            else:
                st.session_state.messages.append({"role": "assistant", "content": ai_msg})
