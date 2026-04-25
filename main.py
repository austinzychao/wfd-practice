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

# --- Short commute-friendly sentences  ---
SENTENCES = [
    "Technology has changed the way we live",
    "Education plays a key role in society",
    "The results will be published next week",
    "Climate change is a global concern",
    "Access to healthcare is a basic right",
    "The data was collected over several years",
    "Social media influences public opinion greatly",
    "Economic growth depends on many factors",
    "The government must address this issue",
    "Research shows a link between diet and health",
    "Many students struggle with time management",
    "The environment needs immediate protection",
    "Technology improves the quality of life",
    "Education is essential for social development",
    "The study found significant differences in results",
    "Public transport reduces carbon emissions",
    "Critical thinking is a valuable skill",
    "The population is growing at a rapid rate",
    "Renewable energy is becoming more affordable",
    "The findings suggest a need for further research",
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