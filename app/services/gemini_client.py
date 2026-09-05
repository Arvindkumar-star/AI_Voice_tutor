import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing. Check your .env file.")

client = genai.Client(api_key=api_key)

MODEL_ALIASES = {
    # Alias retired or strictly quota-limited models to reliable flash models
    "gemini-2.5-flash": "gemini-3.5-flash",
    "gemini-2.0-flash": "gemini-3.5-flash",
    "gemini-3.6-flash": "gemini-3.5-flash",
    "gemini-3.5-transcribe": "gemini-3.5-flash-lite",
    "gemini-2.5-flash-preview-tts": "gemini-3.1-flash-tts-preview",
}


def configured_model(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    return MODEL_ALIASES.get(value, value)


STT_MODEL = configured_model("STT_MODEL", "gemini-3.5-flash")
LLM_MODEL = configured_model("LLM_MODEL", "gemini-3.5-flash")
TTS_MODEL = configured_model("TTS_MODEL", "gemini-3.1-flash-tts-preview")
STT_FALLBACK_MODEL = configured_model("STT_FALLBACK_MODEL", "gemini-3.5-flash-lite")
LLM_FALLBACK_MODEL = configured_model("LLM_FALLBACK_MODEL", "gemini-3.5-flash-lite")
TTS_FALLBACK_MODEL = os.getenv("TTS_FALLBACK_MODEL", "gemini-2.5-flash-preview-tts").strip()
TTS_VOICE = os.getenv("TTS_VOICE", "Puck")

BASE_DIR = Path(__file__).resolve().parent.parent.parent

AUDIO_DIR = BASE_DIR / "audio_output"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE_DIR / "tutor.db"