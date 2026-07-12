# PII / sensitive columns — the schema layer will hide these,
# and the governance node will reject any query that references them
# even if hallucinated.
PII_COLUMNS = {
    "ContactName",
    "Phone",
    "Fax",
    "HomePhone",
    "Address",
    "BirthDate",
    "Photo",
    "PhotoPath",
    "Notes",
}

FORBIDDEN_TABLES = set()

# Max rows any single query is allowed to request/return
MAX_ROWS = 200