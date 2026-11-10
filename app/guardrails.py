"""Layer 1 safety: static SQL validation with sqlglot before anything hits the DB.
Layer 2 safety: the DB connection itself is read-only (see db.py)."""
import re
import sqlglot
from sqlglot import exp

BLOCKED = (exp.Drop, exp.Delete, exp.Update, exp.Insert, exp.Create, exp.Alter,
           exp.Command, exp.Merge, exp.TruncateTable)
BLOCKED_KEYWORDS = re.compile(r"\b(ATTACH|DETACH|PRAGMA|VACUUM|REPLACE\s+INTO)\b", re.I)

class UnsafeSQLError(ValueError):
    pass

def extract_sql(text: str) -> str:
    """Local models often wrap SQL in ```sql fences or add explanations - pull out just the SQL."""
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    if m:
        text = m.group(1)
    if not BLOCKED_KEYWORDS.search(text) and not re.search(r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE)\b", text, re.I):
        m = re.search(r"\b(WITH|SELECT)\b.*", text, re.S | re.I)   # strip leading prose only for read queries
        text = m.group(0) if m else text
    return text.strip()

def validate_sql(sql: str) -> str:
    sql = sql.strip().rstrip(";").strip()
    if BLOCKED_KEYWORDS.search(sql):
        raise UnsafeSQLError("Blocked keyword detected.")
    try:
        stmts = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
    except sqlglot.errors.ParseError as e:
        if re.search(r"\b(DROP|DELETE|UPDATE|INSERT|CREATE|ALTER|MERGE|TRUNCATE)\b", sql, re.I):
            raise UnsafeSQLError("Only read-only SELECT queries are allowed.") from e
        raise ValueError(f"SQL parse error: {e}")
    if len(stmts) != 1:
        raise UnsafeSQLError("Only a single statement is allowed.")
    stmt = stmts[0]
    if any(stmt.find(t) for t in BLOCKED) or not isinstance(stmt, (exp.Select, exp.Union, exp.With)):
        raise UnsafeSQLError("Only read-only SELECT queries are allowed.")
    return sql
