import os
import re
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent

DB_URI = "sqlite:///groundwater.db"
MODEL = "gpt-4o-mini"
MAX_ITERATIONS = 10

# ─── DATABASE ────────────────────────────────────────────────
db = SQLDatabase.from_uri(DB_URI)

# ─── GET SCHEMA ──────────────────────────────────────────────
def get_schema_hint(db: SQLDatabase) -> str:
    try:
        result = db.run('PRAGMA table_info(groundwater);')
        rows = eval(result) if isinstance(result, str) else result
        return "\n".join(f'- "{row[1]}"' for row in rows)
    except Exception:
        return "(schema unavailable)"

SCHEMA_HINT = get_schema_hint(db)

# ─── SYSTEM PROMPT (FIXED) ───────────────────────────────────
SYSTEM_PROMPT = f"""
You are a data analyst querying a SQLite groundwater database.

STRICT RULES:

1. Table name: groundwater

2. Columns:
{SCHEMA_HINT}

3. NEVER use markdown (NO ```)

4. ALWAYS return ONLY raw SQL query

5. IMPORTANT: Handle multi-year data:
   - General questions → use AVG or MAX
   - Avoid duplicate rows
   - Use GROUP BY when needed

6. Ignore NULL values:
   → add WHERE column IS NOT NULL

7. STATE is uppercase:
   WHERE UPPER("STATE") = UPPER('Punjab')

8. YEAR format:
   WHERE "YEAR" LIKE '2022%'

9. LIMIT 20 unless specified

────────────────────
EXAMPLES:

-- Top districts by recharge
SELECT "DISTRICT", MAX("Ground Water Recharge (ham)") AS recharge
FROM groundwater
GROUP BY "DISTRICT"
ORDER BY recharge DESC
LIMIT 5;

-- Rainfall in Punjab
SELECT "STATE", "DISTRICT", "Rainfall (mm)"
FROM groundwater
WHERE UPPER("STATE") = UPPER('Punjab')
AND "YEAR" LIKE '2022%';

-- Average extraction for a state (IMPORTANT)
SELECT AVG("Stage of Ground Water Extraction (%)") AS avg_extraction
FROM groundwater
WHERE UPPER("STATE") = UPPER('Rajasthan')
AND "Stage of Ground Water Extraction (%)" IS NOT NULL;

-- Top districts by extraction
SELECT "DISTRICT",
MAX("Stage of Ground Water Extraction (%)") AS extraction
FROM groundwater
WHERE UPPER("STATE") = UPPER('Rajasthan')
AND "Stage of Ground Water Extraction (%)" IS NOT NULL
GROUP BY "DISTRICT"
ORDER BY extraction DESC
LIMIT 5;
"""



# ─── LLM ─────────────────────────────────────────────────────
llm = ChatOpenAI(
    model=MODEL,
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
)

# ─── CLEAN SQL (CRITICAL FIX) ────────────────────────────────
def clean_sql(query: str) -> str:
    query = re.sub(r"```sql", "", query, flags=re.IGNORECASE)
    query = re.sub(r"```", "", query)
    return query.strip()

# ─── AGENT (NO AgentType → FIXED ERROR) ──────────────────────
agent_executor = create_sql_agent(
    llm=llm,
    db=db,
    verbose=True,
    max_iterations=MAX_ITERATIONS,
)

# ─── MAIN FUNCTION ───────────────────────────────────────────
def ask_database(question: str) -> str:
    if not question or not question.strip():
        return "Please provide a valid question."

    if len(question) > 1000:
        return "Question too long."

    try:
        full_input = f"{SYSTEM_PROMPT}\n\nUser Question:\n{question.strip()}"
        response = agent_executor.invoke({"input": full_input})

        output = response.get("output", "")

        # Clean any markdown formatting
        cleaned_output = clean_sql(output)

        return cleaned_output if cleaned_output else "No result found."

    except Exception as e:
        print(f"[ask_database error] {type(e).__name__}: {e}")
        return f"Error: {type(e).__name__}"


# ─── TEST ────────────────────────────────────────────────────
if __name__ == "__main__":
    print(ask_database("Top 5 districts by ground water recharge"))

