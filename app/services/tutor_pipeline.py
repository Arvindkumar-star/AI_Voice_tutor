import base64
import json
import wave
from pathlib import Path
from uuid import uuid4
from google.genai import types
from app.services.gemini_client import (
    client,
    STT_MODEL,
    LLM_MODEL,
    TTS_MODEL,
    TTS_VOICE,
    AUDIO_DIR,
)
from app.services.progress_store import get_recent_error_rate


def write_pcm_to_wav(filepath: Path, pcm_data: bytes,
                      channels: int = 1, rate: int = 24000, sample_width: int = 2):
    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)


def transcribe_audio(audio_path: Path, language: str) -> str:
    audio_bytes = audio_path.read_bytes()
    print("DEBUG - audio bytes length:", len(audio_bytes))

    # TEMP: save a copy so we can listen to exactly what was sent
    debug_copy = Path("data") / "debug_last_recording.webm"
    debug_copy.write_bytes(audio_bytes)
    print("DEBUG - saved copy to:", debug_copy)

    suffix = audio_path.suffix.lower().replace(".", "")
    mime_map = {"wav": "audio/wav", "mp3": "audio/mp3", "webm": "audio/webm", "m4a": "audio/mp4"}
    mime_type = mime_map.get(suffix, "audio/webm")

    response = client.models.generate_content(
        model=STT_MODEL,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            f"Transcribe the spoken {language} sentence exactly. Return only the raw transcript text, nothing else.",
        ],
    )
    return response.text.strip() if response.text else ""


def check_grammar(user_text: str, language: str, username: str) -> dict:
    error_rate = get_recent_error_rate(username, language, last_n=5)
    if error_rate <= 0.2:
        difficulty_note = "The learner has been doing well recently — you may gently note if their sentence was too simple."
    elif error_rate >= 0.6:
        difficulty_note = "The learner has been struggling recently — keep feedback extra encouraging and simple."
    else:
        difficulty_note = ""

    prompt = f"""You are a {language} language tutor. A learner said this sentence in {language}:
"{user_text}"

Check it for grammar and word-choice mistakes. {difficulty_note}

Respond with ONLY valid JSON in this exact shape, no markdown, no extra text:
{{"corrected": "the corrected sentence in {language}", "feedback": "one short sentence explaining what was fixed, or praise if no errors", "had_errors": true or false}}
"""

    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=prompt,
    )
    raw = response.text.strip() if response.text else "{}"

    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"corrected": user_text, "feedback": "Could not analyze this attempt.", "had_errors": False}

    return data


def generate_speech(text: str, language: str) -> Path:
    output_path = AUDIO_DIR / f"response_{uuid4().hex}.wav"

    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=TTS_VOICE)
                )
            ),
        ),
    )

    raw_audio_bytes = None
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                data = part.inline_data.data
                raw_audio_bytes = base64.b64decode(data) if isinstance(data, str) else data
                break

    if not raw_audio_bytes:
        raise ValueError("Gemini TTS did not return audio data.")

    write_pcm_to_wav(output_path, raw_audio_bytes)
    return output_path