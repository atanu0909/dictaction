import streamlit as st
import random
import difflib
import tempfile
import os
import genai
from PIL import Image

# Configure Gemini API
API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else st.text_input("Enter your Gemini API Key:", type="password")
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.stop()

st.title("AI Dictation Practice from Book Images")

uploaded_file = st.file_uploader("Upload an image of a book page", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)
    # OCR using Gemini
    with st.spinner("Extracting text from image..."):
        ocr_prompt = "Extract all readable English text from this image. Return as plain text."
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            image.save(tmp.name)
            with open(tmp.name, "rb") as img_file:
                result = model.generate_content([ocr_prompt, img_file.read()])
        os.unlink(tmp.name)
        text = result.text.strip()
    st.subheader("Extracted Text")
    st.text_area("Text from image", text, height=200)
    # Pick a random line
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if lines:
        random_line = random.choice(lines)
        st.session_state["random_line"] = random_line
        st.subheader("Listen and Type the Dictation")
        # TTS using Gemini
        tts_prompt = f"Read aloud: {random_line}"
        audio_result = model.generate_content(tts_prompt, stream=True)
        audio_bytes = b"".join([chunk.audio for chunk in audio_result if hasattr(chunk, "audio")])
        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
        else:
            st.warning("Audio generation failed. Please try again.")
        user_input = st.text_input("Type what you hear:")
        if user_input:
            # Compare user input to original
            matcher = difflib.SequenceMatcher(None, random_line, user_input)
            output = ""
            for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
                if opcode == 'equal':
                    output += f'<span style="background-color:#d4f7d4">{user_input[b0:b1]}</span>'
                elif opcode == 'replace' or opcode == 'delete':
                    output += f'<span style="background-color:#f7d4d4">{random_line[a0:a1]}</span>'
                elif opcode == 'insert':
                    output += f'<span style="background-color:#d4e0f7">{user_input[b0:b1]}</span>'
            st.markdown(f"**Comparison:**<br>{output}", unsafe_allow_html=True)
    else:
        st.warning("No text found in image.")
