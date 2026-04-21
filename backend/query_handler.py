"""
Direct Query Handler - Bypasses LLM for common query patterns
==============================================================

This module handles common query patterns directly without LLM,
falling back to LLM only for complex queries.
"""

import re
import sqlite3
from typing import Optional, Dict, List, Any

# Column mappings
COLUMN_MAP = {
    "availability": "Total Ground Water Availability in the area (ham) Fresh",
    "groundwater availability": "Total Ground Water Availability in the area (ham) Fresh",
    "rainfall": "Rainfall (mm) Total",
    "recharge": "Ground Water Recharge (ham) Total",
    "groundwater recharge": "Ground Water Recharge (ham) Total",
    "extraction": "Stage of Ground Water Extraction (%) Total",
    "extraction rate": "Stage of Ground Water Extraction (%) Total",
    "environmental flows": "Environmental Flows (ham) Total",
    "future availability": "Net Annual Ground Water Availability for Future Use (ham) Total",
}

# Aggregation rules
AGG_RULES = {
    "Total Ground Water Availability in the area (ham) Fresh": "SUM",  # STOCK
    "Rainfall (mm) Total": "AVG",  # AVERAGE
    "Ground Water Recharge (ham) Total": "SUM",  # FLOW
    "Stage of Ground Water Extraction (%) Total": "AVG",  # PERCENTAGE
    "Environmental Flows (ham) Total": "SUM",  # FLOW
    "Net Annual Ground Water Availability for Future Use (ham) Total": "SUM",  # STOCK
}

# Units
UNITS = {
    "Total Ground Water Availability in the area (ham) Fresh": "ham",
    "Rainfall (mm) Total": "mm",
    "Ground Water Recharge (ham) Total": "ham",
    "Stage of Ground Water Extraction (%) Total": "%",
    "Environmental Flows (ham) Total": "ham",
    "Net Annual Ground Water Availability for Future Use (ham) Total": "ham",
}


def extract_query_params(question: str) -> Dict[str, Any]:
    """
    Extract parameters from natural language question.
    Returns: {metric, states, years, query_type}
    """
    question_lower = question.lower()
    
    # Extract metric
    metric = None
    for key, col in COLUMN_MAP.items():
        if key in question_lower:
            metric = col
            break
    
    # Extract states
    states = []
    state_patterns = [
        r'\b(punjab|haryana|assam|andhra pradesh|uttar pradesh|madhya pradesh|gujarat|maharashtra|rajasthan|bihar|west bengal|tamil nadu|karnataka|kerala|odisha|telangana|jharkhand|chhattisgarh|uttarakhand|himachal pradesh|goa|manipur|meghalaya|tripura|nagaland|mizoram|sikkim|arunachal pradesh|jammu and kashmir|ladakh|delhi|chandigarh|puducherry|andaman and nicobar islands|lakshadweep|dadra and nagar haveli and daman and diu)\b'
    ]
    
    for pattern in state_patterns:
        matches = re.findall(pattern, question_lower, re.IGNORECASE)
        states.extend([m.upper() for m in matches])
    
    # Extract years
    years = []
    year_patterns = [
        r'(\d{4})[_-](\d{2})',  # 2023-24 or 2023_24
        r'(\d{4})',  # 2023
    ]
    
    for pattern in year_patterns:
        matches = re.findall(pattern, question)
        for match in matches:
            if isinstance(match, tuple):
                years.append(f"{match[0]}_{match[1]}")
            else:
                # Convert 2023 to 2023_24 (assume current year)
                years.append(f"{match}_25")
    
    # Determine query type
    query_type = "single"
    if "top" in question_lower or "highest" in question_lower or "maximum" in question_lower:
        query_type = "ranking_top"
    elif "bottom" in question_lower or "lowest" in question_lower or "minimum" in question_lower:
        query_type = "ranking_bottom"
    elif "compare" in question_lower or "comparison" in question_lower:
        query_type = "comparison"
    elif "all states" in question_lower:
        query_type = "all_states"
    
    return {
        "metric": metric,
        "states": list(set(states)),  # Remove duplicates
        "years": list(set(years)),
        "query_type": query_type,
    }


def can_handle_directly(params: Dict[str, Any]) -> bool:
    """Check if query can be handled directly without LLM."""
    # Must have a metric
    if not params["metric"]:
        return False
    
    # Simple queries we can handle
    if params["query_type"] in ["single", "ranking_top", "ranking_bottom", "all_states"]:
        return True
    
    # Comparison with specific states
    if params["query_type"] == "comparison" and len(params["states"]) > 0:
        return True
    
    return False


def generate_sql(params: Dict[str, Any]) -> str:
    """Generate SQL query from parameters."""
    metric = params["metric"]
    states = params["states"]
    years = params["years"]
    query_type = params["query_type"]
    
    # Get aggregation function
    agg_func = AGG_RULES.get(metric, "SUM")
    
    # CRITICAL: Detect multi-year query
    is_multi_year = len(years) > 1
    
    # Base query
    if query_type == "ranking_top" or query_type == "ranking_bottom":
        # Ranking query (always single year)
        year = years[0] if years else "2024_25"
        order = "DESC" if query_type == "ranking_top" else "ASC"
        
        sql = f'''
        SELECT "STATE", {agg_func}("{metric}") AS value
        FROM groundwater
        WHERE "YEAR" = '{year}'
        AND "{metric}" IS NOT NULL
        GROUP BY "STATE"
        ORDER BY value {order}
        LIMIT 5
        '''
    
    elif query_type == "all_states":
        # All states query
        year = years[0] if years else "2024_25"
        
        sql = f'''
        SELECT "STATE", {agg_func}("{metric}") AS value
        FROM groundwater
        WHERE "YEAR" = '{year}'
        AND "{metric}" IS NOT NULL
        GROUP BY "STATE"
        ORDER BY value DESC
        '''
    
    elif is_multi_year:
        # MULTI-YEAR MODE: Always return year-wise breakdown
        state_list = "', '".join([s.upper() for s in states]) if states else None
        year_list = "', '".join(years)
        
        if states:
            state_filter = f"AND UPPER(\"STATE\") IN ('{state_list}')"
        else:
            state_filter = ""
        
        # CRITICAL: GROUP BY STATE, YEAR (never aggregate across years)
        sql = f'''
        SELECT "STATE", "YEAR", {agg_func}("{metric}") AS value
        FROM groundwater
        WHERE "YEAR" IN ('{year_list}')
        AND "{metric}" IS NOT NULL
        {state_filter}
        GROUP BY "STATE", "YEAR"
        ORDER BY "STATE", "YEAR"
        '''
    
    elif len(states) > 0 and len(years) == 1:
        # Single year, specific states
        state_list = "', '".join([s.upper() for s in states])
        
        sql = f'''
        SELECT "STATE", {agg_func}("{metric}") AS value
        FROM groundwater
        WHERE UPPER("STATE") IN ('{state_list}')
        AND "YEAR" = '{years[0]}'
        AND "{metric}" IS NOT NULL
        GROUP BY "STATE"
        ORDER BY "STATE"
        '''
    
    elif len(states) > 0:
        # States specified, use latest year
        state_list = "', '".join([s.upper() for s in states])
        
        sql = f'''
        SELECT "STATE", {agg_func}("{metric}") AS value
        FROM groundwater
        WHERE UPPER("STATE") IN ('{state_list}')
        AND "YEAR" = '2024_25'
        AND "{metric}" IS NOT NULL
        GROUP BY "STATE"
        ORDER BY "STATE"
        '''
    
    else:
        # Default: highest value, latest year
        year = years[0] if years else "2024_25"
        
        sql = f'''
        SELECT "STATE", {agg_func}("{metric}") AS value
        FROM groundwater
        WHERE "YEAR" = '{year}'
        AND "{metric}" IS NOT NULL
        GROUP BY "STATE"
        ORDER BY value DESC
        LIMIT 1
        '''
    
    return sql.strip()


def execute_sql(sql: str) -> List[tuple]:
    """Execute SQL query and return results."""
    try:
        conn = sqlite3.connect("groundwater.db")
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"[SQL ERROR] {e}")
        return []


def format_results(results: List[tuple], params: Dict[str, Any]) -> str:
    """Format query results into natural language with units always included."""
    if not results:
        return "No data available for the selected query parameters."
    
    metric = params["metric"]
    unit = UNITS.get(metric, "")
    query_type = params["query_type"]
    
    # Get metric name for display
    metric_name = None
    for key, col in COLUMN_MAP.items():
        if col == metric:
            metric_name = key
            break
    
    if not metric_name:
        metric_name = metric
    
    # Ensure unit is always present (fallback if not found)
    if not unit:
        unit = ""
    
    # Format based on query type
    if query_type in ["ranking_top", "ranking_bottom"]:
        # Ranking format
        direction = "highest" if query_type == "ranking_top" else "lowest"
        year = params["years"][0] if params["years"] else "2024-25"
        year_display = year.replace("_", "-")
        
        lines = [f"Top states by {metric_name} in {year_display}:"]
        for i, (state, value) in enumerate(results, 1):
            # Always include unit, even if empty string
            value_str = f"{value:,.2f} {unit}".strip()
            lines.append(f"{i}. {state.title()}: {value_str}")
        
        return "\n".join(lines)
    
    elif len(results) == 1 and len(results[0]) == 2:
        # Single value
        state, value = results[0]
        year = params["years"][0] if params["years"] else "2024-25"
        year_display = year.replace("_", "-")
        
        value_str = f"{value:,.2f} {unit}".strip()
        return f"The {metric_name} in {state.title()} in {year_display} is {value_str}."
    
    elif len(results[0]) == 3:
        # Multi-year results (state, year, value)
        lines = []
        current_state = None
        
        for state, year, value in results:
            if state != current_state:
                if current_state:
                    lines.append("")  # Blank line between states
                lines.append(f"{metric_name.title()} in {state.title()}:")
                current_state = state
            
            year_display = year.replace("_", "-")
            value_str = f"{value:,.2f} {unit}".strip()
            lines.append(f"  - {year_display}: {value_str}")
        
        return "\n".join(lines)
    
    else:
        # Multiple states, single year
        year = params["years"][0] if params["years"] else "2024-25"
        year_display = year.replace("_", "-")
        
        lines = [f"{metric_name.title()} in {year_display}:"]
        for state, value in results:
            value_str = f"{value:,.2f} {unit}".strip()
            lines.append(f"  - {state.title()}: {value_str}")
        
        return "\n".join(lines)


def handle_query_direct(question: str) -> Optional[str]:
    """
    Try to handle query directly without LLM.
    Returns None if query is too complex for direct handling.
    """
    # Extract parameters
    params = extract_query_params(question)
    
    # Check if we can handle it
    if not can_handle_directly(params):
        return None
    
    print(f"[DIRECT HANDLER] Handling query directly")
    print(f"[PARAMS] {params}")
    
    # Generate SQL
    sql = generate_sql(params)
    print(f"[SQL] {sql[:200]}...")
    
    # Execute
    results = execute_sql(sql)
    print(f"[RESULTS] {len(results)} rows")
    
    # Format
    response = format_results(results, params)
    
    return response
