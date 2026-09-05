import base64
import json
import logging
import time
import wave
from pathlib import Path
from uuid import uuid4
from google.genai import types
from app.services.gemini_client import (
    client,
    STT_MODEL,
    LLM_MODEL,
    TTS_MODEL,
    STT_FALLBACK_MODEL,
    LLM_FALLBACK_MODEL,
    TTS_FALLBACK_MODEL,
    TTS_VOICE,
    AUDIO_DIR,
)
from app.services.progress_store import get_recent_error_rate

logger = logging.getLogger(__name__)
MAX_GEMINI_ATTEMPTS = 5


def generate_content_with_retry(*, model: str, fallback_model: str | None, contents, config=None):
    """Retry temporary errors, then use a lighter fallback model if needed."""
    models = [model]
    if fallback_model and fallback_model != model and fallback_model not in models:
        models.append(fallback_model)
    last_error = None

    for model_name in models:
        for attempt in range(3):
            try:
                kwargs = {"model": model_name, "contents": contents}
                if config is not None:
                    kwargs["config"] = config
                return client.models.generate_content(**kwargs)
            except Exception as exc:
                last_error = exc
                message = str(exc).upper()
                retryable = any(
                    marker in message
                    for marker in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "DEADLINE_EXCEEDED")
                )
                if not retryable:
                    break
                if attempt < 2:
                    delay = 1.5 ** (attempt + 1)
                    logger.warning(
                        "Gemini model %s is temporarily unavailable; retrying in %.1fs (%s/2)",
                        model_name,
                        delay,
                        attempt + 1,
                    )
                    time.sleep(delay)

        if model_name != models[-1]:
            logger.warning("Falling back from Gemini model %s to %s", model_name, models[-1])

    if last_error is not None:
        raise last_error
    raise RuntimeError("Failed to generate content: all attempts exhausted without response.")


def write_pcm_to_wav(filepath: Path, pcm_data: bytes,
                      channels: int = 1, rate: int = 24000, sample_width: int = 2):
    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)


def transcribe_audio(audio_path: Path, language: str) -> str:
    audio_bytes = audio_path.read_bytes()
    if len(audio_bytes) < 100:
        return ""

    suffix = audio_path.suffix.lower().replace(".", "")
    mime_map = {"wav": "audio/wav", "mp3": "audio/mp3", "webm": "audio/webm", "m4a": "audio/mp4", "ogg": "audio/ogg"}
    mime_type = mime_map.get(suffix, "audio/webm")

    prompt = (
        f"You are a speech transcription engine. "
        f"Transcribe all spoken words in this audio exactly as spoken in {language}. "
        f"Transcribe whatever the user said even if there are pronunciation or grammar errors or words in another language. "
        f"Return ONLY the verbatim spoken transcript text, nothing else."
    )

    response = generate_content_with_retry(
        model=STT_MODEL,
        fallback_model=STT_FALLBACK_MODEL,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            prompt,
        ],
    )

    text = ""
    if response and hasattr(response, "text") and response.text:
        text = response.text.strip()
    elif response and hasattr(response, "candidates") and response.candidates:
        parts = []
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                parts.append(part.text)
        text = "".join(parts).strip()

    return text


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

    response = generate_content_with_retry(
        model=LLM_MODEL,
        fallback_model=LLM_FALLBACK_MODEL,
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

    response = generate_content_with_retry(
        model=TTS_MODEL,
        fallback_model=TTS_FALLBACK_MODEL,
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