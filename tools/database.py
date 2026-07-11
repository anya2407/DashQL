import sqlite3
import pandas as pd
import sqlglot


DATABASE_PATH = "database/northwind.db"


def is_safe_select(query: str) -> bool:
    """
    Returns True only for valid SELECT statements.
    """

    try:
        parsed = sqlglot.parse_one(query)
        return parsed.key.upper() == "SELECT"
    except Exception:
        return False


def execute_sql(query: str) -> pd.DataFrame:
    """
    Executes a read-only SQL query and returns
    the results as a pandas DataFrame.
    """

    if not is_safe_select(query):
        raise ValueError(
            "Only SELECT statements are allowed."
        )

    conn = sqlite3.connect(DATABASE_PATH)

    try:
        df = pd.read_sql_query(query, conn)
        return df

    finally:
        conn.close()