import asyncio
import hashlib
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

VOICE = "en-AU-NatashaNeural"

# --- Stage 1: Foundations (collocations, 2-5 words) ---
STAGE1 = [
    "conduct research",
    "daily living",
    "demonstrate competence",
    "take notes",
    "carry out a study",
    "draw a conclusion",
    "raise awareness",
    "make a decision",
    "provide evidence",
    "apply for admission",
    "collect data",
    "reach an agreement",
    "free access",
    "give a presentation",
    "take responsibility",
    "play an important role",
    "in addition to this",
    "as a result of",
    "on a regular basis",
    "in recent years",
    "a significant impact on",
    "currently available",
    "higher education",
    "economic growth",
    "social development",
    "public health",
    "renewable energy",
    "critical thinking",
    "standard of living",
    "climate change",
]

# --- Stage 2: Sentences (6-8 words) ---
STAGE2 = [
    "Scientists conduct research on cancer",
    "Routine is the heart of daily living",
    "She demonstrated competence under pressure.",
    "Always take notes during important meetings",
    "They carried out a study on sleep",
    "We can draw a conclusion from the data",
    "The campaign raised awareness about hunger",
    "She needs to make a decision today.",
    "Provide evidence to support your claim",
    "She applied for admission to a local college",
    "Sensors collect data continuously",
    "Both sides reached an agreement",
    "The library offers free access to journals",
    "She gave a presentation to the board",
    "Leaders must take responsibility for mistakes",
    "Diet plays an important role in health",
    "In addition to this, costs are rising",
    "As a result of rain, the game was cancelled",
    "Exercise on a regular basis",
    "In recent years, AI has advanced rapidly",
    "Stress has a significant impact on health",
    "Several vaccines are currently available",
    "Higher education improves career prospects",
    "Trade drives economic growth",
    "Schools support social development",
    "Smoking threatens public health",
    "Solar is a form of renewable energy",
    "Solving puzzles develops critical thinking",
    "Wages affect the standard of living",
    "Climate change threatens coastal cities",
]

# --- Stage 3: Academic (9-12 words) ---
STAGE3 = [
    "Technology has a significant impact on society and the economy",
    "Research has shown that education plays an important role in development",
    "Public health is influenced by a range of social and economic factors",
    "Economic growth is closely related to the sustainable use of resources",
    "This policy is based on recent studies and research findings",
    "A variety of methods can be used to solve this problem",
    "The data is collected and analyzed over an extended period of time",
    "The majority of people are influenced by social media in some way",
    "Climate change poses a significant threat to the natural environment",
    "Critical thinking is an important skill in both academic and professional settings",
    "The findings suggest a need for further research in this area",
    "Access to quality education is essential for long term social development",
    "The government has introduced a range of policies to address this issue",
    "Environmental protection plays an important role in ensuring sustainable development",
    "A growing body of evidence supports the need for policy reform",
    "The study found a significant correlation between lifestyle and health outcomes",
    "Higher levels of education are associated with improved economic outcomes",
    "Urban development must take into account the needs of local communities",
    "The results of the experiment were consistent with previous research findings",
    "Social inequality continues to be a major challenge in many countries",
    "The introduction of new technology has transformed the modern workplace",
    "Researchers have identified a number of factors that contribute to this trend",
    "The long term effects of climate change are still being studied",
    "A significant proportion of the population lacks access to basic healthcare",
    "The relationship between economic growth and environmental sustainability is complex",
    "Students who engage in regular study tend to perform better academically",
    "The government has a responsibility to ensure equal access to education",
    "Advances in medical research have led to improved treatment outcomes",
    "The findings of this study have important implications for public health policy",
    "Effective communication is essential for success in both academic and professional contexts",
]

STAGES = {
    "1": STAGE1,
    "2": STAGE2,
    "3": STAGE3,
}

STAGE_NAMES = {
    "1": "Foundations",
    "2": "Sentences",
    "3": "Academic",
}


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
def get_sentences(stage: str = "1", n: int = 30):
    bank = STAGES.get(stage, STAGE1)
    picked = random.sample(bank, min(n, len(bank)))
    return {
        "sentences": picked,
        "stage": stage,
        "stage_name": STAGE_NAMES.get(stage, "Foundations"),
    }


@app.get("/api/audio")
async def get_audio(text: str):
    all_sentences = STAGE1 + STAGE2 + STAGE3
    if text not in all_sentences:
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