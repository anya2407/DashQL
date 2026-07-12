import sqlite3
from config import PII_COLUMNS


def get_full_schema() -> str:
    """Returns the full database schema: every table and its columns,
    EXCLUDING sensitive/PII columns. Call this before writing any SQL
    query, to confirm exact table and column names."""

    conn = sqlite3.connect('database/northwind.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    schema_str = ""
    for table in tables:
        cursor.execute(f'PRAGMA table_info("{table}")')
        columns = cursor.fetchall()

        visible_columns = [col for col in columns if col[1] not in PII_COLUMNS]

        if not visible_columns:
            continue  # skip tables that are entirely PII (none in Northwind, but safe)

        schema_str += f"\nTable: {table}\nColumns:\n"
        for col in visible_columns:
            schema_str += f"  - {col[1]} ({col[2]})\n"
    conn.close()
    return schema_str