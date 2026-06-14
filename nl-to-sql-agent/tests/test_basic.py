"""
test_basic.py
Basic happy-path tests for the NL-to-SQL Analytics Agent.

Tests that don't require an API key check schema reading and safety
validation. The agent test (test_run_agent_end_to_end) is skipped
automatically if GROQ_API_KEY is not set.
"""
import os
import sys

import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(override=True)

from src.schema_tool import get_schema, get_table_names
from src.safety_check import is_safe_sql
from src.sql_agent import execute_sql, run_agent

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample.db")


def test_database_exists():
    assert os.path.exists(DB_PATH), "Sample database not found. Run data/create_sample_db.py first."


def test_get_table_names():
    tables = get_table_names(DB_PATH)
    assert set(tables) == {"customers", "products", "orders"}


def test_get_schema_contains_columns():
    schema = get_schema(DB_PATH)
    assert "customer_id" in schema
    assert "product_name" in schema
    assert "order_date" in schema


def test_safety_check_allows_select():
    safe, _ = is_safe_sql("SELECT * FROM customers")
    assert safe is True


def test_safety_check_allows_cte():
    safe, _ = is_safe_sql("WITH t AS (SELECT * FROM orders) SELECT * FROM t")
    assert safe is True


@pytest.mark.parametrize("bad_sql", [
    "DROP TABLE customers",
    "DELETE FROM orders",
    "UPDATE customers SET name='x'",
    "SELECT * FROM customers; DROP TABLE customers",
    "",
])
def test_safety_check_blocks_dangerous_sql(bad_sql):
    safe, _ = is_safe_sql(bad_sql)
    assert safe is False


def test_execute_sql_returns_dataframe():
    df = execute_sql(DB_PATH, "SELECT * FROM customers")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 10
    assert "name" in df.columns


def test_execute_sql_rejects_write_at_db_level():
    """Even if safety_check were bypassed, the read-only connection
    must reject write operations at the SQLite level."""
    with pytest.raises(Exception):
        execute_sql(DB_PATH, "DELETE FROM customers")


@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set; skipping live LLM end-to-end test."
)
def test_run_agent_end_to_end():
    """Happy-path: a valid question should produce a working SQL query
    and a non-empty result."""
    result = run_agent("How many customers are there in total?", DB_PATH)
    assert result["success"] is True
    assert result["sql"] is not None
    assert result["dataframe"] is not None
    assert len(result["dataframe"]) >= 1
    assert "attempts" in result
    assert len(result["attempts"]) >= 1


def test_run_agent_self_healing():
    from unittest.mock import MagicMock

    mock_client = MagicMock()

    first_response = MagicMock()
    first_response.choices = [MagicMock()]
    first_response.choices[0].message.content = """{
        "sql": "SELECT invalid_col FROM customers",
        "explanation": "This query has an error.",
        "chart_suggestion": "none",
        "x_axis": null,
        "y_axis": null
    }"""

    second_response = MagicMock()
    second_response.choices = [MagicMock()]
    second_response.choices[0].message.content = """{
        "sql": "SELECT name FROM customers",
        "explanation": "This query is corrected.",
        "chart_suggestion": "none",
        "x_axis": null,
        "y_axis": null
    }"""

    mock_client.chat.completions.create.side_effect = [first_response, second_response]

    result = run_agent("Show customer names", DB_PATH, client=mock_client)

    assert result["success"] is True
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["status"] == "failed"
    assert "Database execution error" in result["attempts"][0]["error"]
    assert result["attempts"][1]["status"] == "success"
    assert result["sql"] == "SELECT name FROM customers"


def test_run_agent_rejects_modification():
    from unittest.mock import MagicMock

    mock_client = MagicMock()

    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = """{
        "sql": null,
        "explanation": "Database modifications are not supported.",
        "chart_suggestion": "none",
        "x_axis": null,
        "y_axis": null
    }"""

    mock_client.chat.completions.create.return_value = response

    result = run_agent("Insert Bob into customers", DB_PATH, client=mock_client)

    assert result["success"] is False
    assert result["sql"] is None
    assert "not supported" in result["error"]
    assert len(result["attempts"]) == 1
    assert result["attempts"][0]["status"] == "failed"
