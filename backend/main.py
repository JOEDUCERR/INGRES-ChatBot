from fastapi import FastAPI
from pydantic import BaseModel
from backend.chatbot import ask_database
import sqlite3

from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(title="INGRES Groundwater Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# request body for chatbot
class Question(BaseModel):
    question: str


# helper function for manual SQL queries
def run_query(query):
    conn = sqlite3.connect("groundwater.db")
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows


# root endpoint
@app.get("/")
def home():
    return {"message": "INGRES Groundwater Chatbot API Running"}


# example SQL endpoint
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


# AI chatbot endpoint
@app.post("/chat")
def chat(q: Question):
    answer = ask_database(q.question)
    return {
        "question": q.question,
        "answer": answer
    }