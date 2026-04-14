from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from backend.chatbot import ask_database
from backend.security import sanitize_input
import sqlite3

from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ─── RATE LIMIT ──────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="INGRES Groundwater Chatbot API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── REQUEST MODEL ───────────────────────────────────────────
class Question(BaseModel):
    question: str

# ─── RAW QUERY EXECUTION (OPTIONAL API) ──────────────────────
def run_query(query):
    conn = sqlite3.connect("groundwater.db")
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows

# ─── HOME ────────────────────────────────────────────────────
@app.get("/")
def home():
    return {"message": "INGRES Groundwater Chatbot API Running"}

# ─── SAMPLE ENDPOINT ─────────────────────────────────────────
@app.get("/top_states")
def top_states():
    query = """
    SELECT STATE,
    MAX("Total Ground Water Availability in the area (ham)")
    FROM groundwater
    GROUP BY STATE
    ORDER BY 2 DESC
    LIMIT 10
    """
    result = run_query(query)
    return {"result": result}

# ─── CHAT ENDPOINT ───────────────────────────────────────────
@app.post("/chat")
@limiter.limit("10/minute")
def chat(request: Request, q: Question):
    try:
        clean_question = sanitize_input(q.question)

        answer = ask_database(clean_question)

        if not answer:
            answer = "No data found."

        return {
            "question": clean_question,
            "answer": answer
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
