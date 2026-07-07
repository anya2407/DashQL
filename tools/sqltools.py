import sqlite3
from langchain_core.tools import tool

@tool
def run_sql(query: str) -> str:
    """Executes a read-only SQL SELECT query against the Northwind database
    and returns the results. Only use this after confirming table/column names
    via get_full_schema. Only SELECT statements are allowed."""
    conn = sqlite3.connect('database/northwind.db')
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        return f"Columns: {columns}\nRows: {rows}"
    except Exception as e:
        conn.close()
        return f"SQL Error: {e}" 