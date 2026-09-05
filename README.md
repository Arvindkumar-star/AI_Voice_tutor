# AI Voice Language Tutor

An AI-powered voice tutor that helps learners practice a language by speaking. Record a sentence, and the app transcribes it, checks your grammar and word choice using an LLM, and speaks back a corrected version — while quietly tracking your progress across sessions to tailor its feedback over time.

Built for the "LLMs Meet Speech" take-home assessment (Project 4: AI Voice Language Tutor).
---

## Features

- Record a spoken sentence in any target language directly in the browser
- Speech-to-text transcription (Gemini)
- LLM-based grammar/vocabulary correction with feedback (Gemini)
- Text-to-speech playback of the corrected sentence (Gemini)
- Per-user, per-language attempt history stored in SQLite
- Feedback tone adapts based on the learner's recent error rate (stretch goal)

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI (Python) |
| STT | Gemini (`gemini-3.6-flash`) |
| LLM (grammar check) | Gemini (`gemini-3.6-flash`) |
| TTS | Gemini (`gemini-3.1-flash-tts-preview`) |
| Database | SQLite (file-based, no server needed) |
| Frontend | Vanilla HTML / CSS / JS, browser `MediaRecorder` API |

---

## Project Structure

```text
voice-tutor/
├── .env
├── .gitignore
├── requirements.txt
├── README.md
│
├── app/
│   └── main.py
│
├── services/
│   ├── gemini_client.py
│   ├── tutor_pipeline.py
│   └── progress_store.py
│
├── static/
│   ├── index.html
│   ├── app.js
│   └── style.css
│
└── data/
    ├── audio_output/
    └── tutor.db
```

## Setup

1. **Clone the repository**
git clone https://github.com/Arvindkumar-star/AI_Voice_tutor.git
cd AI_Voice_tutor

3. **Install dependencies**
pip install -r requirements.txt


3. **Create a `.env` file** in the project root:
   
GEMINI_API_KEY=your_key_here

STT_MODEL=gemini-3.6-flash

LLM_MODEL=gemini-3.6-flash

TTS_MODEL=gemini-3.1-flash-tts-preview

TTS_VOICE=Puck

Get a key from [Google AI Studio](https://aistudio.google.com) → **Get API key**.

4. **Run the server**
uvicorn app.main:app --reload


5. **Open the app**
   Go to `http://127.0.0.1:8000` in your browser.

---

**Live demo:** https://ai-voice-tutor-71v0.onrender.com/
   
## How to Use

1. Enter a **username** and a **target language** (e.g. "English", "Spanish").
2. Click **Start Recording**, speak a sentence, then **Stop Recording**.
3. Wait a few seconds — the app shows your transcript, the corrected sentence, written feedback, and plays the correction aloud.
4. Click **Load My History** to review past attempts for that username + language.

---

## Approach

The core of the app is a four-stage pipeline per request: **record → transcribe (STT) → grammar-check (LLM) → speak (TTS)**. Each stage is an independent function in `app/services/tutor_pipeline.py`, chained together by the `/api/practice` route in `app/main.py`. Keeping each stage isolated made it possible to test and debug them individually during development.

The LLM is prompted to return **structured JSON** (`corrected`, `feedback`, `had_errors`) instead of free text, so the response can be reliably parsed and stored rather than guessed at. The parser strips markdown code fences and falls back to a safe default if the model doesn't return valid JSON.

For the **stretch goal**, every attempt is saved to a local SQLite database (`app/services/progress_store.py`), keyed by username and language. Before generating feedback, the app calculates the learner's error rate over their last 5 attempts and passes a short instruction into the grammar-check prompt — encouraging more supportive feedback if they've been struggling, or gently nudging them toward complexity if they've been consistently correct.

---

## Assumptions

- No authentication — "username" is a free-text field with no password or identity verification, by design, to keep scope reasonable for a take-home assessment.
- Target language is entered as free text (e.g. "Spanish") rather than a fixed dropdown; the LLM interprets it directly.
- Single learner using the app at a time during testing — no concurrency/load testing was performed.

---

## Known Limitations / Gaps

- **Stretch goal is partially implemented.** The app adapts *feedback tone* based on recent performance, but does not yet vary the actual difficulty of what the learner is asked to say — the learner still chooses their own sentences.
- **Generated audio files are not automatically deleted** after being served; they accumulate in `audio_output/`. A production version would need a cleanup job or TTL.
- The TTS model (`gemini-3.1-flash-tts-preview`) is in **preview status** as of this writing — behavior may change without notice.
- No automated tests; all testing was manual, end-to-end.
- Gemini model names changed mid-development (some initially-referenced models were deprecated during the build); `.env` values above reflect what is confirmed working as of submission.
- **Live deployment (Render free tier) does not persist the SQLite database or generated audio files across server restarts/idle periods**, since Render's free tier doesn't support persistent disks. Within a single active session, history tracking works normally.
---

## AI Assistant Disclosure

I wrote the core backend logic (STT/LLM/TTS pipeline, database, API routes) myself. I used an AI coding assistant (Claude) for help with the frontend (HTML/CSS/JS) and for debugging along the way.

