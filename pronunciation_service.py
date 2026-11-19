import io
import streamlit as st
from gtts import gTTS


@st.cache_data(show_spinner=False)
def generate_pronunciation_mp3(text: str, accent: str = "US") -> bytes:
    """
    Tạo âm thanh phát âm tiếng Anh chuẩn MP3 bằng Google TTS.
    accent: 'UK' (Anh-Anh, tld='co.uk') hoặc 'US' (Anh-Mỹ, tld='com').
    """
    if not text or not text.strip():
        return b""
    tld = "co.uk" if accent.upper() == "UK" else "com"
    tts = gTTS(text=text.strip(), lang="en", tld=tld, slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    return buf.getvalue()