"""
tools.py — SQL validation and execution tools.

nodes.py -- LangGraph nodes function to write the NL2SQL agent 

1.generate sql - this is able ti take the user's query and convert them to SQL queries
2.validate sql - Checks SQL safety and syntax for the ones generated from the function above
3.synthesize sql - Calls Claude to narrate the result in plain English

"""

import sqlite3
import sqlglot
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "hotel_bookings_100k.db"

# ── Blocked keywords — prevent any write operations ───────────────────────────
BLOCKED_KEYWORDS = {"DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "CREATE"}


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validate SQL syntax using sqlglot.

    Returns:
        (True, "OK")              → safe to execute
        (False, "reason string")  → do not execute, send reason back to LLM
    """
    if not sql or not sql.strip():
        return False, "No SQL was generated."

    tokens = set(sql.upper().split())
    blocked = tokens & BLOCKED_KEYWORDS
    if blocked:
        return False, f"Blocked keywords detected: {blocked}. Only SELECT is allowed."

    # 2. Must start with SELECT
    VALID_START_KEYWORDS = {"SELECT", "WITH", "EXPLAIN"}

    if not sql.strip().upper().split()[0] in VALID_START_KEYWORDS:
        return False, "Query must start with SELECT or WITH. Only read operations are allowed."

    # 3. sqlglot syntax check (dialect=sqlite)
    try:
        sqlglot.parse_one(sql, dialect="sqlite")

    # To this:
    except (sqlglot.errors.ParseError, sqlglot.errors.TokenError, Exception) as e:
        return False, f"SQL syntax error: {e}"

    return True, "OK"


def execute_sql(sql: str) -> tuple[bool, str]:
    """
    Execute a validated SQL query against hotel_bookings.db.

    Returns:
        (True,  formatted results as string)
        (False, error message)
    """
    
    if not DB_PATH.exists():
        return False, f"Database not found at {DB_PATH}. Run data/seed.py first."

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return True, "Query ran successfully but returned no results."

        # Format as a readable table string for the LLM to summarize
        headers = rows[0].keys()
        lines = [", ".join(headers)]                          # header row
        for row in rows:
            lines.append(", ".join(str(row[h]) for h in headers))

        return True, "\n".join(lines)

    except sqlite3.Error as e:
        return False, f"Database error: {e}"


# ── Quick smoke test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        # (label, sql, expect_valid)
        ("Valid SELECT",
         "SELECT region_name FROM regions;",
         True),

        ("Syntax error",
         "SELEC region_name FORM regions;",
         False),

        ("Blocked keyword",
         "DROP TABLE bookings;",
         False),

        ("Sample question",
         """SELECT r.region_name, COUNT(*) AS bookings
            FROM bookings b
            JOIN hotels h ON b.hotel_id = h.hotel_id
            JOIN regions r ON h.region_id = r.region_id
            WHERE strftime('%Y-%m', b.check_in_date) = '2026-08'
            GROUP BY r.region_name
            ORDER BY bookings DESC;""",
         True),
    ]

    print("\n── Validation tests ────────────────────────────────────────────")
    for label, sql, expect in test_cases:
        valid, msg = validate_sql(sql)
        status = "✅" if valid == expect else "❌"
        print(f"  {status}  {label}: {msg}")

    print("\n── Execution test (sample question) ────────────────────────────")
    _, sql = test_cases[3][0], test_cases[3][1]
    ok, result = execute_sql(test_cases[3][1])
    print(result if ok else f"ERROR: {result}")
    print()

def execute_sql_raw(sql: str) -> tuple[bool, list[dict], str]:
    """
    Like execute_sql but returns rows as list of dicts for JSON serialization.
    Returns: (ok, rows, error_message)
    """
    if not DB_PATH.exists():
        return False, [], f"Database not found at {DB_PATH}."
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql)
        rows = [dict(row) for row in cur.fetchall()]
        conn.close()
        return True, rows, ""
    except sqlite3.Error as e:
        return False, [], f"Database error: {e}"