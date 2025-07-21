import streamlit as st
import random
import difflib
import tempfile
import os
import google.generativeai as genai
from dotenv import load_dotenv

from PIL import Image
from gtts import gTTS



# Load environment variables from .env
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else st.text_input("Enter your Gemini API Key:", type="password")
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.stop()

st.title("AI Dictation Practice from Book Images")

uploaded_file = st.file_uploader("Upload an image of a book page", type=["jpg", "jpeg", "png"])

# Ask user for test duration
duration = st.selectbox("Select dictation duration:", ["1 min", "2 min", "3 min"])
duration_map = {"1 min": 1, "2 min": 2, "3 min": 3}
minutes = duration_map[duration]
# Estimate words per minute (WPM) for dictation: 100 WPM (slow, for students)
target_words = minutes * 100

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)
    # OCR using Gemini
    with st.spinner("Extracting text from image..."):
        ocr_prompt = "Extract all readable English text from this image. Return as plain text."
        result = model.generate_content([ocr_prompt, image])
        text = result.text.strip() if hasattr(result, 'text') else str(result)
    import re
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if len(p.strip()) > 0]
    # Find paragraphs with at least 2 sentences and close to the target word count
    smart_paragraphs = [p for p in paragraphs if (len(re.findall(r'[.!?]', p)) >= 2 and len(p.split()) >= target_words * 0.7)]
    # If none found, fallback to any paragraph with 2+ sentences
    if not smart_paragraphs:
        smart_paragraphs = [p for p in paragraphs if len(re.findall(r'[.!?]', p)) >= 2]
    if smart_paragraphs:
        # Pick the paragraph closest to the target word count
        random_para = min(smart_paragraphs, key=lambda p: abs(len(p.split()) - target_words))
        st.session_state["random_line"] = random_para
        st.subheader("Listen and Type the Dictation")
        tts = gTTS(text=random_para, lang='en', slow=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tts_fp:
            tts.save(tts_fp.name)
            tts_fp.flush()
            with open(tts_fp.name, 'rb') as audio_file:
                audio_bytes = audio_file.read()
        import time
        st.audio(audio_bytes, format='audio/mp3')
        time.sleep(0.5)
        st.audio(audio_bytes, format='audio/mp3')
        os.unlink(tts_fp.name)
        user_input = st.text_area("Type what you hear:")
        submitted = st.button("Submit")
        if submitted and user_input:
            ref_words = random_para.split()
            user_words = user_input.split()
            user_output = ""
            correct = 0
            for i, ref_word in enumerate(ref_words):
                if i < len(user_words):
                    if user_words[i] == ref_word:
                        user_output += f'<span style="background-color:#1b5e20;color:#fff;padding:2px 4px;border-radius:3px">{user_words[i]} </span>'
                        correct += 1
                    else:
                        user_output += f'<span style="background-color:#b71c1c;color:#fff;padding:2px 4px;border-radius:3px">{user_words[i]}</span> '
                else:
                    user_output += f'<span style="background-color:#b71c1c;color:#fff;padding:2px 4px;border-radius:3px">[missing]</span> '
            if len(user_words) > len(ref_words):
                for j in range(len(ref_words), len(user_words)):
                    user_output += f'<span style="background-color:#0d47a1;color:#fff;padding:2px 4px;border-radius:3px">{user_words[j]}</span> '

            orig_output = ""
            for i, ref_word in enumerate(ref_words):
                if i < len(user_words):
                    if user_words[i] == ref_word:
                        orig_output += f'<span style="background-color:#1b5e20;color:#fff;padding:2px 4px;border-radius:3px">{ref_word} </span>'
                    else:
                        orig_output += f'<span style="background-color:#b71c1c;color:#fff;padding:2px 4px;border-radius:3px">{ref_word}</span> '
                else:
                    orig_output += f'<span style="background-color:#b71c1c;color:#fff;padding:2px 4px;border-radius:3px">{ref_word}</span> '

            marks = int((correct / len(ref_words)) * 100) if ref_words else 0
            st.markdown(f"**Original Text:**<br>{orig_output}", unsafe_allow_html=True)
            st.markdown(f"**Your Input:**<br>{user_output}", unsafe_allow_html=True)
            st.markdown(f"**Marks:** {marks} / 100")
    else:
        st.warning("No suitable paragraph found in image.")
