import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing. Check your .env file.")

client = genai.Client(api_key=api_key)

STT_MODEL = os.getenv("STT_MODEL", "gemini-3.5-transcribe")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
TTS_MODEL = os.getenv("TTS_MODEL", "gemini-3.1-flash-tts-preview")
TTS_VOICE = os.getenv("TTS_VOICE", "Puck")

AUDIO_DIR = Path("audio_output")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "tutor.db"