import sys
import os


# --- PATCH POUR PYTHON 3.13 (À mettre AVANT tout le reste) ---
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules["audioop"] = audioop
    except ImportError:
        pass # Sera géré par Streamlit si manquant

try:
    import aifc
except ImportError:
    try:
        import standard_aifc as aifc
        sys.modules["aifc"] = aifc
    except ImportError:
        pass
# -----------------------------------------------------------


import streamlit as st
import google.generativeai as genai
from elevenlabs.client import ElevenLabs
from PyPDF2 import PdfReader

# --- CONFIGURATION ---
st.set_page_config(page_title="Professeur IA Virtuel", layout="wide")

# Récupération des clés dans les Secrets Streamlit
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]
VOICE_ID = st.secrets["ELEVENLABS_VOICE_ID"]

genai.configure(api_key=GOOGLE_API_KEY)
client_eleven = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# --- FONCTIONS ---

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        reader = PdfReader(pdf)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def process_interaction(user_input, context, is_audio=False):
    """Envoie le texte ou l'audio à Gemini et récupère la réponse"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"Tu es un prof expert. Utilise ce contexte pour répondre : {context[:50000]}"
    
    if is_audio:
        # Gemini peut recevoir une liste [texte, données_audio]
        response = model.generate_content([prompt, user_input])
    else:
        response = model.generate_content(prompt + "\n\nQuestion : " + user_input)
    
    return response.text

def play_voice(text):
    """Génère l'audio avec ta voix ElevenLabs"""
    audio = client_eleven.generate(
        text=text,
        voice=VOICE_ID,
        model="eleven_multilingual_v2"
    )
    return b"".join(audio)

# --- INTERFACE ---
st.title("🎓 Mon Assistant  (NSI/Maths)")

# 1. Gestion des fichiers PDF (La base de connaissances)
with st.sidebar:
    st.header("📚 Tes documents de cours")
    uploaded_files = st.file_uploader("Upload tes PDF", accept_multiple_files=True, type=['pdf'])
    if uploaded_files:
        if st.button("Analyser les documents"):
            st.session_state['context'] = get_pdf_text(uploaded_files)
            st.success("Cours mémorisés !")

if 'context' not in st.session_state:
    st.session_state['context'] = ""

# 2. Entrée de l'élève (Audio ou Texte)
st.write("### Pose ta question au prof")
col1, col2 = st.columns(2)

with col1:
    # Nouveau composant natif de Streamlit (très stable)
    audio_file = st.audio_input("🎤 Parle au prof")

with col2:
    text_input = st.chat_input("Ou écris ta question ici...")

# 3. Logique de réponse
user_content = None
is_audio_input = False

if audio_file:
    # On prépare l'audio pour Gemini
    user_content = {"mime_type": "audio/wav", "data": audio_file.read()}
    is_audio_input = True
elif text_input:
    user_content = text_input
    is_audio_input = False

if user_content:
    with st.spinner("Le prof réfléchit..."):
        # Génération de la réponse texte
        answer = process_interaction(user_content, st.session_state['context'], is_audio=is_audio_input)
        
        st.chat_message("assistant").write(answer)
        
        # Génération de ta voix
        voice_bytes = play_voice(answer)
        st.audio(voice_bytes, format="audio/mp3", autoplay=True)
