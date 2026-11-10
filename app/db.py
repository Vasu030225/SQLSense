"""Read-only DB access: SQLite opened in mode=ro (equivalent of a read-only DB user)."""
import sqlite3
from .config import DB_PATH, MAX_ROWS

def ro_connect():
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

def get_schema() -> str:
    con = ro_connect(); cur = con.cursor(); out = []
    for name, ddl in cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall():
        rows = cur.execute(f"SELECT * FROM {name} LIMIT 3").fetchall()
        out.append(f"{ddl};\n/* sample rows: {rows} */")
    con.close(); return "\n\n".join(out)

def run_query(sql: str):
    con = ro_connect()
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, cur.fetchmany(MAX_ROWS)
    finally:
        con.close()
