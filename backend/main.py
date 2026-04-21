from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from backend.chatbot_v2 import ask_database
from backend.security import sanitize_input
import sqlite3
import os
import pandas as pd
from io import BytesIO
from datetime import datetime

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ─── CONFIGURATION ───────────────────────────────────────────
DATABASE_PATH = os.getenv("DATABASE_PATH", "groundwater.db")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# ─── RATE LIMIT ──────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="INGRES Groundwater Chatbot API",
    description="AI-powered chatbot for querying groundwater data from India's Central Ground Water Board",
    version="2.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── REQUEST MODELS ───────────────────────────────────────────
class Question(BaseModel):
    question: str

class FilterQuery(BaseModel):
    metric: str
    states: list[str] = []
    years: list[str] = []

class ExportRequest(BaseModel):
    metric: str
    states: list[str] = []
    years: list[str] = []
    data: list[dict] = []  # Optional: can pass existing data or re-query

# ─── DATABASE CONNECTION ─────────────────────────────────────
def get_db_connection():
    return sqlite3.connect(DATABASE_PATH)

# ─── RAW QUERY EXECUTION (OPTIONAL API) ──────────────────────
def run_query(query):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows

# ─── HOME ────────────────────────────────────────────────────
@app.get("/")
def home():
    return {
        "message": "INGRES Groundwater Chatbot API Running",
        "version": "2.0.0",
        "status": "healthy",
        "endpoints": {
            "chat": "/chat",
            "filter_query": "/filter_query",
            "top_states": "/top_states",
            "docs": "/docs"
        }
    }

# ─── HEALTH CHECK ────────────────────────────────────────────
@app.get("/health")
def health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM groundwater")
        count = cursor.fetchone()[0]
        conn.close()
        return {
            "status": "healthy",
            "database": "connected",
            "records": count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

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

# ─── FILTER QUERY ENDPOINT (NEW - DIRECT SQL) ────────────────
@app.post("/filter_query")
@limiter.limit("20/minute")
def filter_query(request: Request, fq: FilterQuery):
    try:
        metric = fq.metric
        states = fq.states
        years = fq.years
        
        # Validate metric
        valid_metrics = [
            "Rainfall (mm) Total",
            "Total Geographical Area (ha) Total",
            "Ground Water Recharge (ham) Total",
            "Annual Ground water Recharge (ham) Total",
            "Annual Extractable Ground water Resource (ham) Total",
            "Ground Water Extraction for all uses (ha.m) Total",
            "Stage of Ground Water Extraction (%) Total",
            "Environmental Flows (ham) Total",
            "Net Annual Ground Water Availability for Future Use (ham) Total",
            "Total Ground Water Availability in the area (ham) Fresh"  # Use Fresh for total availability
        ]
        
        if metric not in valid_metrics:
            raise HTTPException(status_code=400, detail="Invalid metric")
        
        # CRITICAL: Detect multi-year query
        is_multi_year = len(years) > 1
        
        # Build SQL query
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # CRITICAL CHANGE: Always return year-wise breakdown for multi-year queries
        if is_multi_year:
            # MULTI-YEAR MODE: Return STATE, YEAR, VALUE (never aggregate across years)
            if years:
                year_filter = f"AND \"YEAR\" IN ({','.join(['?' for _ in years])})"
                params = years.copy()
            else:
                year_filter = ""
                params = []
            
            if states:
                state_filter = f"AND UPPER(\"STATE\") IN ({','.join(['?' for _ in states])})"
                params.extend([s.upper() for s in states])
            else:
                state_filter = ""
            
            # Always group by STATE and YEAR for multi-year queries
            query = f"""
            SELECT \"STATE\", \"YEAR\", SUM(\"{metric}\") as value
            FROM groundwater
            WHERE \"{metric}\" IS NOT NULL
            {year_filter}
            {state_filter}
            GROUP BY \"STATE\", \"YEAR\"
            ORDER BY \"STATE\", \"YEAR\"
            """
        else:
            # SINGLE-YEAR MODE: Return STATE, VALUE (aggregate districts)
            if years:
                year_filter = f"AND \"YEAR\" = '{years[0]}'"
                params = []
            else:
                # Use latest year (2024_25)
                year_filter = "AND \"YEAR\" = '2024_25'"
                params = []
            
            if states:
                state_filter = f"AND UPPER(\"STATE\") IN ({','.join(['?' for _ in states])})"
                params.extend([s.upper() for s in states])
            else:
                state_filter = ""
            
            query = f"""
            SELECT \"STATE\", SUM(\"{metric}\") as value
            FROM groundwater
            WHERE \"{metric}\" IS NOT NULL
            {year_filter}
            {state_filter}
            GROUP BY \"STATE\"
            ORDER BY value DESC
            """
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return {
                "success": True,
                "data": [],
                "message": "No data available for the selected query",
                "query_type": "multi_year" if is_multi_year else "single_year"
            }
        
        # Format results based on query type
        formatted_results = []
        if is_multi_year:
            # Multi-year: always include year in response
            for row in results:
                formatted_results.append({
                    "state": row[0],
                    "year": row[1],
                    "value": row[2]
                })
        else:
            # Single-year: no year field needed
            for row in results:
                formatted_results.append({
                    "state": row[0],
                    "value": row[1]
                })
        
        return {
            "success": True,
            "data": formatted_results,
            "metric": metric,
            "query_type": "multi_year" if is_multi_year else "single_year",
            "message": f"Found {len(formatted_results)} results"
        }
        
    except Exception as e:
        print(f"[filter_query error] {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── EXPORT TO EXCEL ENDPOINT ────────────────────────────────
@app.post("/export_excel")
@limiter.limit("10/minute")
def export_excel(request: Request, export_req: ExportRequest):
    """
    Export query results to Excel file.
    Supports both single-year and multi-year pivot table formats.
    """
    try:
        metric = export_req.metric
        states = export_req.states
        years = export_req.years
        data = export_req.data
        
        # If data is not provided, re-query from database
        if not data:
            # Validate metric
            valid_metrics = [
                "Rainfall (mm) Total",
                "Total Geographical Area (ha) Total",
                "Ground Water Recharge (ham) Total",
                "Annual Ground water Recharge (ham) Total",
                "Annual Extractable Ground water Resource (ham) Total",
                "Ground Water Extraction for all uses (ha.m) Total",
                "Stage of Ground Water Extraction (%) Total",
                "Environmental Flows (ham) Total",
                "Net Annual Ground Water Availability for Future Use (ham) Total",
                "Total Ground Water Availability in the area (ham) Fresh"
            ]
            
            if metric not in valid_metrics:
                raise HTTPException(status_code=400, detail="Invalid metric")
            
            # Detect multi-year query
            is_multi_year = len(years) > 1
            
            # Build SQL query (same logic as filter_query)
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if is_multi_year:
                # Multi-year: return year-wise breakdown
                if years:
                    year_filter = f"AND \"YEAR\" IN ({','.join(['?' for _ in years])})"
                    params = years.copy()
                else:
                    year_filter = ""
                    params = []
                
                if states:
                    state_filter = f"AND UPPER(\"STATE\") IN ({','.join(['?' for _ in states])})"
                    params.extend([s.upper() for s in states])
                else:
                    state_filter = ""
                
                query = f"""
                SELECT \"STATE\", \"YEAR\", SUM(\"{metric}\") as value
                FROM groundwater
                WHERE \"{metric}\" IS NOT NULL
                {year_filter}
                {state_filter}
                GROUP BY \"STATE\", \"YEAR\"
                ORDER BY \"STATE\", \"YEAR\"
                """
            else:
                # Single-year
                if years:
                    year_filter = f"AND \"YEAR\" = '{years[0]}'"
                    params = []
                else:
                    year_filter = "AND \"YEAR\" = '2024_25'"
                    params = []
                
                if states:
                    state_filter = f"AND UPPER(\"STATE\") IN ({','.join(['?' for _ in states])})"
                    params.extend([s.upper() for s in states])
                else:
                    state_filter = ""
                
                query = f"""
                SELECT \"STATE\", SUM(\"{metric}\") as value
                FROM groundwater
                WHERE \"{metric}\" IS NOT NULL
                {year_filter}
                {state_filter}
                GROUP BY \"STATE\"
                ORDER BY value DESC
                """
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                raise HTTPException(status_code=404, detail="No data available to export")
            
            # Convert to data format
            if is_multi_year:
                data = [{"state": row[0], "year": row[1], "value": row[2]} for row in results]
            else:
                data = [{"state": row[0], "value": row[1]} for row in results]
        
        # Check if we have data
        if not data:
            raise HTTPException(status_code=404, detail="No data available to export")
        
        # Get unit from metric
        def get_unit(metric_name):
            if '(mm)' in metric_name: return 'mm'
            if '(ha.m)' in metric_name: return 'ha.m'
            if '(ham)' in metric_name: return 'ham'
            if '(ha)' in metric_name: return 'ha'
            if '(%)' in metric_name: return '%'
            return ''
        
        unit = get_unit(metric)
        
        # Detect if multi-year data
        is_multi_year = any('year' in row for row in data)
        
        # Create DataFrame
        if is_multi_year:
            # Create pivot table
            df = pd.DataFrame(data)
            
            # Pivot: rows=state, columns=year, values=value
            pivot_df = df.pivot(index='state', columns='year', values='value')
            
            # Add TOTAL column
            pivot_df['TOTAL'] = pivot_df.sum(axis=1)
            
            # Format column names with units
            pivot_df.columns = [f"{col.replace('_', '-')} ({unit})" if col != 'TOTAL' else f"TOTAL ({unit})" 
                               for col in pivot_df.columns]
            
            # Reset index to make state a column
            pivot_df.reset_index(inplace=True)
            pivot_df.rename(columns={'state': 'STATE'}, inplace=True)
            
            final_df = pivot_df
        else:
            # Simple table
            df = pd.DataFrame(data)
            df.columns = ['STATE', f'VALUE ({unit})']
            df['STATE'] = df['STATE'].str.title()
            final_df = df
        
        # Create Excel file in memory
        output = BytesIO()
        
        # Use openpyxl engine for better formatting
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, sheet_name='Groundwater Data', index=False)
            
            # Get workbook and worksheet for formatting
            workbook = writer.book
            worksheet = writer.sheets['Groundwater Data']
            
            # Format headers (bold)
            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True)
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metric_short = metric.split('(')[0].strip().replace(' ', '_').lower()
        filename = f"groundwater_{metric_short}_{timestamp}.xlsx"
        
        # Return as streaming response
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[export_excel error] {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
