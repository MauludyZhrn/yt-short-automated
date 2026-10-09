import os
from dotenv import load_dotenv

# Load environment variables dari file .env
load_dotenv()

# API Keys — WAJIB diisi lewat file .env, JANGAN ditulis langsung di kode.
# Contoh isi .env:
#   GEMINI_API_KEY=...
#   PEXELS_API_KEY=...
#   GROQ_API_KEY=...
#   HF_TOKEN=...
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

_missing = [
    name for name, value in {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "PEXELS_API_KEY": PEXELS_API_KEY,
        "GROQ_API_KEY": GROQ_API_KEY,
        
    }.items() if not value
]
if _missing:
    print(f"⚠️ API key belum diisi di .env: {', '.join(_missing)}")

# Path Direktori Project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "assets", "audio")
BG_DIR = os.path.join(BASE_DIR, "assets", "background")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Pengaturan Text-to-Speech (dipakai tts.py)
TTS_VOICE = "id-ID-ArdiNeural"   # alternatif: "id-ID-GadisNeural"
TTS_RATE = "+5%"                 # "+0%" = kecepatan normal
TTS_PITCH = "+0Hz"
TTS_VOLUME = "+0%"
SUBTITLE_LEAD = 0.04             # detik; naikkan (mis. 0.08) jika subtitle terasa telat