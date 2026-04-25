import asyncio
import hashlib
import os
import random
from pathlib import Path

import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

AUDIO_DIR = Path("audio_cache")
AUDIO_DIR.mkdir(exist_ok=True)

# --- Short commute-friendly sentences (5-8 words) ---
SENTENCES = [
    "The class starts at nine",
    "Please submit your work online",
    "The exam has been postponed",
    "Read the handout before class",
    "Turn off your mobile phones",
    "The library is now closed",
    "Results will be posted online",
    "Attendance is mandatory this week",
    "The meeting room is booked",
    "Please bring your student ID",
    "The deadline has been extended",
    "Check your email for updates",
    "The course notes are online",
    "Late submissions will not count",
    "The lecture starts in five",
    "All fees must be paid",
    "Register before the end date",
    "The campus café is closed",
    "Bring a pen and paper",
    "The test covers three chapters",
]

VOICE = "en-AU-NatashaNeural"


def sentence_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


async def generate_audio(text: str) -> Path:
    fpath = AUDIO_DIR / f"{sentence_hash(text)}.mp3"
    if not fpath.exists():
        communicate = edge_tts.Communicate(text, VOICE, rate="-10%")
        await communicate.save(str(fpath))
    return fpath


class AnswerIn(BaseModel):
    sentence: str
    answer: str


@app.get("/api/sentences")
def get_sentences(n: int = 10):
    picked = random.sample(SENTENCES, min(n, len(SENTENCES)))
    return {"sentences": picked}


@app.get("/api/audio")
async def get_audio(text: str):
    if text not in SENTENCES:
        raise HTTPException(status_code=400, detail="Sentence not in bank")
    fpath = await generate_audio(text)
    return FileResponse(str(fpath), media_type="audio/mpeg")


@app.post("/api/check")
def check_answer(payload: AnswerIn):
    def normalize(s):
        return s.lower().replace(",", "").replace(".", "").replace("'", "").split()

    correct_words = normalize(payload.sentence)
    given_words = normalize(payload.answer)
    correct_set = set(correct_words)
    given_set = set(given_words)

    hits = [w for w in correct_words if w in given_set]
    missed = [w for w in correct_words if w not in given_set]
    extra = [w for w in given_words if w not in correct_set]
    score = round(len(hits) / len(correct_words) * 100) if correct_words else 0

    return {
        "score": score,
        "hits": hits,
        "missed": missed,
        "extra": extra,
        "total_words": len(correct_words),
        "correct_words": len(hits),
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")