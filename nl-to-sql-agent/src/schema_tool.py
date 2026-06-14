"""
schema_tool.py
Reads and formats the SQLite database schema so it can be passed to the LLM
as grounding context. This acts as the "tool" the agent calls before
generating SQL.
"""
import sqlite3


def get_schema(db_path: str) -> str:
    """
    Returns a human-readable string describing all tables and columns
    in the given SQLite database, including data types and a few
    sample rows per table for extra context.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cur.fetchall()]

    schema_parts = []
    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        columns = cur.fetchall()
        col_defs = ", ".join(f"{col[1]} ({col[2]})" for col in columns)
        schema_parts.append(f"Table: {table}\n  Columns: {col_defs}")

        # Add a couple of sample rows for context
        cur.execute(f"SELECT * FROM {table} LIMIT 2")
        sample_rows = cur.fetchall()
        col_names = [col[1] for col in columns]
        schema_parts.append(f"  Sample rows ({', '.join(col_names)}):")
        for row in sample_rows:
            schema_parts.append(f"    {row}")

    conn.close()
    return "\n".join(schema_parts)


def get_table_names(db_path: str) -> list:
    """Returns a simple list of table names in the database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cur.fetchall()]
    conn.close()
    return tables


if __name__ == "__main__":
    print(get_schema("data/sample.db"))
