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
    "Technology has a significant impact on society",
    "Research has shown that education plays an important role",
    "Public health is influenced by social and economic factors",
    "Economic growth is closely related to the use of resources",
    "This policy is based on recent studies and research findings",
    "The quality of life has improved in recent years",
    "A variety of methods can be used to solve this problem",
    "The data is collected and analyzed over time",
    "This approach can lead to better performance",
    "Education contributes to economic and social development",
    "Many people use mobile phones on a daily basis",
    "Environmental protection is a major concern in modern society",
    "This change may result in long term benefits",
    "The majority of people are influenced by social media",
    "This system is used on a regular basis",
    "Results are based on a range of data sources",
    "The government plays a key role in public policy",
    "Access to education is essential for social development",
    "Climate change poses a significant threat to the environment",
    "Critical thinking is an important skill in academic settings",
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