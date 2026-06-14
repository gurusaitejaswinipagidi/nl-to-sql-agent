"""
sql_agent.py
Core agent logic:
  1. Read schema (tool call)
  2. Send NL question + schema to Groq LLM
  3. LLM returns SQL
  4. Validate SQL (safety_check)
  5. Execute against read-only SQLite connection
  6. Self-heal and retry if validation or execution fails (up to 2 retries)
  7. Return results + SQL + chart suggestion + attempt details
"""
import os
import re
import sqlite3
import json
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

from src.schema_tool import get_schema
from src.safety_check import is_safe_sql

GROQ_MODEL = "llama-3.3-70b-versatile"


SYSTEM_PROMPT = """You are a SQL generation agent for a SQLite database.
You will be given the database schema and a natural language question.

Your job:
1. Write ONE valid SQLite SELECT query that answers the question.
2. Only use tables/columns that exist in the schema provided.
3. Never write INSERT, UPDATE, DELETE, DROP, ALTER or any modifying statement.
4. Only output a single SELECT (or WITH ... SELECT) statement.
5. If the user's question asks to insert, update, delete, drop, alter, or modify data in any way, or if it is not a query to retrieve data, you MUST set the "sql" field to null and explain in the "explanation" field that database modifications are not supported.

Respond ONLY in this strict JSON format, with no extra text, no markdown fences:
{
  "sql": "<the SQL query, or null if database modification is requested>",
  "explanation": "<one sentence explaining what the query does, or why the request was rejected>",
  "chart_suggestion": "<one of: bar, line, pie, none>",
  "x_axis": "<column name to use for chart x-axis, or null>",
  "y_axis": "<column name to use for chart y-axis, or null>"
}
"""

CORRECTION_SYSTEM_PROMPT = """You are an expert SQLite debugging assistant.
You previously generated a SQLite query that failed validation or execution.
You will be given:
1. The database schema.
2. The user's original natural language question.
3. The SQL query that failed.
4. The error message/reason for failure.

Your job:
1. Identify and fix the error (e.g. wrong column names, syntax issues, JOIN mismatches, or safety violations).
2. Generate a CORRECTED, valid SQLite SELECT query that answers the user's question.
3. Ensure the corrected query only uses existing tables/columns and only SELECT or CTE statements.
4. Do NOT use any modifying statement (DROP, DELETE, UPDATE, INSERT, ALTER, etc.).
5. If the request cannot be answered with a safe SELECT query, you MUST set the "sql" field to null and explain in the "explanation" field that database modifications are not supported.

Respond ONLY in this strict JSON format, with no extra text, no markdown fences:
{
  "sql": "<the corrected SQL query, or null if database modification is requested>",
  "explanation": "<one sentence explaining the correction made, or why the request was rejected>",
  "chart_suggestion": "<one of: bar, line, pie, none>",
  "x_axis": "<column name to use for chart x-axis, or null>",
  "y_axis": "<column name to use for chart y-axis, or null>"
}
"""


def get_groq_client():
    # Load dotenv overriding existing environment variables to ensure the .env key is respected
    load_dotenv(override=True)
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set.")
    return Groq(api_key=api_key)


def _extract_json(text: str) -> dict:
    """Extracts a JSON object from the LLM response, stripping markdown fences if present."""
    text = text.strip()
    # Remove markdown code fences if the model added them anyway
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    # Find the first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {text}")
    return json.loads(match.group(0))


def generate_sql(question: str, schema: str, client: Groq = None) -> dict:
    """
    Calls the Groq LLM to convert a natural language question into SQL,
    grounded by the provided schema. Returns a dict with sql, explanation,
    and chart suggestion fields.
    """
    if client is None:
        client = get_groq_client()

    user_prompt = f"""Database Schema:
{schema}

Question: {question}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        max_tokens=512,
    )

    raw_text = response.choices[0].message.content
    return _extract_json(raw_text)


def generate_corrected_sql(question: str, schema: str, failed_sql: str, error_message: str, client: Groq = None) -> dict:
    """
    Calls the Groq LLM to debug and correct a failed SQL query, using the schema, original question,
    failed query, and the error details.
    """
    if client is None:
        client = get_groq_client()

    user_prompt = f"""Database Schema:
{schema}

User's Original Question: {question}

Failed SQL Query:
{failed_sql}

Error/Failure Reason:
{error_message}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": CORRECTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        max_tokens=512,
    )

    raw_text = response.choices[0].message.content
    return _extract_json(raw_text)


def execute_sql(db_path: str, sql: str) -> pd.DataFrame:
    """
    Executes a SELECT query against the SQLite database in read-only mode
    and returns the result as a pandas DataFrame.
    """
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return df


def run_agent(question: str, db_path: str, client: Groq = None) -> dict:
    """
    Full agent loop with self-healing retry capability:
      read schema -> [ask LLM -> validate -> execute -> (retry if fails)] -> return results

    Returns a dict with keys:
      success (bool)
      sql (str)
      explanation (str)
      chart_suggestion (str)
      x_axis, y_axis (str or None)
      dataframe (pd.DataFrame or None)
      error (str or None)
      attempts (list of dicts)
    """
    result = {
        "success": False,
        "sql": None,
        "explanation": None,
        "chart_suggestion": "none",
        "x_axis": None,
        "y_axis": None,
        "dataframe": None,
        "error": None,
        "attempts": []
    }

    # Step 1: read schema (tool call)
    try:
        schema = get_schema(db_path)
    except Exception as e:
        result["error"] = f"Failed to read schema from database: {e}"
        return result

    max_attempts = 3
    current_attempt = 1

    while current_attempt <= max_attempts:
        attempt_info = {
            "attempt": current_attempt,
            "sql": None,
            "error": None,
            "explanation": None,
            "status": "pending"
        }

        try:
            # Step 2: Generate (or correct) SQL
            if current_attempt == 1:
                llm_output = generate_sql(question, schema, client=client)
            else:
                last_failed_sql = result["attempts"][-1]["sql"]
                last_error = result["attempts"][-1]["error"]
                llm_output = generate_corrected_sql(question, schema, last_failed_sql, last_error, client=client)

            sql = llm_output.get("sql")
            explanation = llm_output.get("explanation", "")
            chart_suggestion = llm_output.get("chart_suggestion", "none")
            x_axis = llm_output.get("x_axis")
            y_axis = llm_output.get("y_axis")

            attempt_info["sql"] = sql
            attempt_info["explanation"] = explanation

            # Check if LLM explicitly rejected the query as modification/unsupported
            if sql is None or sql == "null" or (isinstance(sql, str) and not sql.strip()):
                reject_reason = explanation or "Database modification requests are not supported."
                attempt_info["status"] = "failed"
                attempt_info["error"] = reject_reason
                result["attempts"].append(attempt_info)
                
                result["success"] = False
                result["explanation"] = reject_reason
                result["error"] = reject_reason
                return result

        except Exception as e:
            error_msg = f"LLM generation error: {e}"
            attempt_info["error"] = error_msg
            attempt_info["status"] = "failed"
            result["attempts"].append(attempt_info)
            result["error"] = error_msg
            current_attempt += 1
            continue

        # Step 3: validate SQL
        safe, reason = is_safe_sql(sql)
        if not safe:
            error_msg = f"Safety check failed: {reason}"
            attempt_info["error"] = error_msg
            attempt_info["status"] = "failed"
            result["attempts"].append(attempt_info)
            result["error"] = error_msg
            current_attempt += 1
            continue

        # Step 4: execute
        try:
            df = execute_sql(db_path, sql)
            attempt_info["status"] = "success"
            result["attempts"].append(attempt_info)

            # Update final success result details
            result["success"] = True
            result["sql"] = sql
            result["explanation"] = explanation
            result["chart_suggestion"] = chart_suggestion
            result["x_axis"] = x_axis
            result["y_axis"] = y_axis
            result["dataframe"] = df
            result["error"] = None
            break

        except Exception as e:
            error_msg = f"Database execution error: {e}"
            attempt_info["error"] = error_msg
            attempt_info["status"] = "failed"
            result["attempts"].append(attempt_info)
            result["error"] = error_msg
            current_attempt += 1

    return result


if __name__ == "__main__":
    # Quick manual test (requires GROQ_API_KEY in .env file)
    db_path = "data/sample.db"
    question = "Which 3 customers have spent the most money in total?"
    res = run_agent(question, db_path)
    print("Success:", res["success"])
    print("SQL:", res["sql"])
    print("Explanation:", res["explanation"])
    print("Error:", res["error"])
    print("Attempts count:", len(res["attempts"]))
    if res["dataframe"] is not None:
        print(res["dataframe"])
