import os
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent

# Load DB
db = SQLDatabase.from_uri("sqlite:///groundwater.db")

# OpenAI LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",   # or "gpt-4o"
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")  # safer than hardcoding
)

# SQL Agent
agent_executor = create_sql_agent(
    llm=llm,
    db=db,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=10
)

def ask_database(question: str):

    prompt = f"""
You are a data analyst querying a SQLite groundwater database.

Database table: groundwater

CRITICAL SQL RULE: All column names MUST be wrapped in double quotes because they contain spaces and special characters.

Column names (always use exactly as shown, with double quotes):
- "STATE"
- "DISTRICT"
- "Rainfall (mm)"
- "Ground Water Recharge (ham)"
- "Annual Ground water Recharge (ham)"
- "Total Ground Water Availability in the area (ham)"
- "Annual Extractable Ground water Resource (ham)"
- "Ground Water Extraction for all uses (ha.m)"
- "Stage of Ground Water Extraction (%)"
- "Net Annual Ground Water Availability for Future Use (ham)"
- "Environmental Flows (ham)"
- "Total Geographical Area (ha)"
- "YEAR"

Example of a correct query:
SELECT "STATE", MAX("Total Ground Water Availability in the area (ham)")
FROM groundwater
GROUP BY "STATE"
ORDER BY 2 DESC
LIMIT 5;

User Question:
{question}

Generate the SQL query using double-quoted column names, execute it, and return the answer clearly.
"""

    response = agent_executor.invoke({"input": prompt})

    return response["output"]