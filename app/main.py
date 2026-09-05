from pathlib import Path
import logging
from uuid import uuid4
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.services.gemini_client import AUDIO_DIR, DATA_DIR
from app.services.progress_store import init_db, save_attempt, get_history
from app.services.tutor_pipeline import transcribe_audio, check_grammar, generate_speech

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="AI Voice Language Tutor", version="1.0.0")

init_db()

static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def home():
    index_file = static_dir / "index.html"
    if not index_file.exists():
        return {"message": "AI Voice Language Tutor API is running."}
    return FileResponse(index_file)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/practice")
async def practice(
    username: str = Form(...),
    language: str = Form(...),
    audio: UploadFile = File(...),
):
    if not username.strip():
        raise HTTPException(status_code=400, detail="Username is required.")
    if not language.strip():
        raise HTTPException(status_code=400, detail="Language is required.")
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file is required.")

    suffix = Path(audio.filename).suffix or ".webm"
    temp = DATA_DIR / f"input_{uuid4().hex}{suffix}"

    try:
        temp.write_bytes(await audio.read())

        transcript = transcribe_audio(temp, language)
        if not transcript:
            raise HTTPException(status_code=422, detail="No speech could be recognized in the audio.")

        result = check_grammar(transcript, language, username)
        corrected = result.get("corrected", transcript)
        feedback = result.get("feedback", "")
        had_errors = result.get("had_errors", False)

        output = generate_speech(corrected, language)

        save_attempt(
            username=username,
            language=language,
            original_text=transcript,
            corrected_text=corrected,
            feedback=feedback,
            had_errors=had_errors,
        )

        return {
            "transcript": transcript,
            "corrected": corrected,
            "feedback": feedback,
            "had_errors": had_errors,
            "audio_url": f"/api/audio/{output.name}",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Practice request failed")
        message = str(exc).upper()
        status_code = 503 if any(
            marker in message
            for marker in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")
        ) else 502
        detail = (
            "Gemini is temporarily busy. Please try again in a few seconds."
            if status_code == 503
            else f"Practice request failed: {exc}"
        )
        raise HTTPException(
            status_code=status_code,
            detail=detail,
        ) from exc
    finally:
        temp.unlink(missing_ok=True)


@app.get("/api/history/{username}/{language}")
def history(username: str, language: str):
    return {"history": get_history(username, language, limit=10)}


@app.get("/api/audio/{filename}")
def get_audio(filename: str):
    path = AUDIO_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(path, media_type="audio/wav", filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)