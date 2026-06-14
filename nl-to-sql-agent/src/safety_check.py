"""
safety_check.py
Validates that LLM-generated SQL is safe to execute against a
read-only database connection. Only SELECT statements (and CTEs
starting WITH ... SELECT) are allowed.
"""
import re

# Keywords that must never appear in generated SQL
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "REPLACE", "TRUNCATE", "ATTACH", "DETACH", "PRAGMA",
    "VACUUM", "REINDEX", "GRANT", "REVOKE",
]


def is_safe_sql(sql: str) -> tuple[bool, str]:
    """
    Returns (is_safe, reason).
    Checks that the SQL:
      1. Is non-empty.
      2. Starts with SELECT or WITH (for CTEs).
      3. Does not contain any forbidden keywords.
      4. Does not contain multiple statements (no ';' except trailing).
    """
    if not sql or not sql.strip():
        return False, "Empty SQL query."

    cleaned = sql.strip().rstrip(";").strip()

    # Must start with SELECT or WITH
    first_word = cleaned.split(None, 1)[0].upper() if cleaned.split() else ""
    if first_word not in ("SELECT", "WITH"):
        return False, f"Query must start with SELECT or WITH, got '{first_word}'."

    # Check for multiple statements
    if ";" in cleaned:
        return False, "Multiple SQL statements are not allowed."

    # Check forbidden keywords (word-boundary match, case-insensitive)
    upper_sql = cleaned.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            return False, f"Forbidden keyword detected: {keyword}"

    return True, "OK"


if __name__ == "__main__":
    tests = [
        "SELECT * FROM customers",
        "DROP TABLE customers",
        "SELECT * FROM customers; DELETE FROM orders",
        "WITH t AS (SELECT * FROM orders) SELECT * FROM t",
        "UPDATE customers SET name='x'",
    ]
    for t in tests:
        print(t, "->", is_safe_sql(t))
