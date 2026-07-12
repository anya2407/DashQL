import sqlglot
from sqlglot import expressions as exp
from config import PII_COLUMNS, FORBIDDEN_TABLES


class GovernanceViolation(Exception):
    """Raised when a query fails governance checks."""
    pass


def is_select_only(parsed) -> bool:
    return parsed.key.upper() == "SELECT"


def uses_pii_columns(parsed) -> list:
    """Returns a list of PII column names referenced in the query, if any."""
    found = []
    for column in parsed.find_all(exp.Column):
        if column.name in PII_COLUMNS:
            found.append(column.name)
    return found


def uses_forbidden_tables(parsed) -> list:
    """Returns a list of forbidden table names referenced in the query, if any."""
    found = []
    for table in parsed.find_all(exp.Table):
        if table.name in FORBIDDEN_TABLES:
            found.append(table.name)
    return found


def check_query(query: str) -> dict:
    """
    Runs all governance checks on a single SQL query.

    Returns
    -------
    dict
        {
            "passed": bool,
            "violations": list[str]   # human-readable reasons, empty if passed
        }
    """

    violations = []

    try:
        parsed = sqlglot.parse_one(query)
    except Exception as e:
        return {"passed": False, "violations": [f"Query failed to parse: {e}"]}

    if not is_select_only(parsed):
        violations.append("Only SELECT statements are allowed.")

    pii_hits = uses_pii_columns(parsed)
    if pii_hits:
        violations.append(f"Query references restricted PII columns: {', '.join(pii_hits)}")

    forbidden_hits = uses_forbidden_tables(parsed)
    if forbidden_hits:
        violations.append(f"Query references forbidden tables: {', '.join(forbidden_hits)}")

    return {
        "passed": len(violations) == 0,
        "violations": violations
    }


def check_all_components(components: list) -> dict:
    """
    Runs governance checks on every component's SQL query.

    Parameters
    ----------
    components : list
        List of dashboard components, each with an "id" and "sql" field.

    Returns
    -------
    dict
        {
            "passed": bool,
            "failed_components": list[dict]  # [{"id": ..., "violations": [...]}]
        }
    """

    failed = []

    for component in components:
        result = check_query(component["sql"])
        if not result["passed"]:
            failed.append({
                "id": component["id"],
                "violations": result["violations"]
            })

    return {
        "passed": len(failed) == 0,
        "failed_components": failed
    }