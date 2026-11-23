"""Load the event log into DuckDB and build every table from the SQL files."""
from pathlib import Path

import duckdb

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
ORDER = ["events", "sessions", "funnel", "weekly_metrics", "retention"]


def run_sql(con, name, params=None):
    text = (SQL_DIR / f"{name}.sql").read_text()
    for statement in [s for s in text.split(";") if s.strip()]:
        body = "\n".join(
            line for line in statement.splitlines() if not line.strip().startswith("--")
        )
        if not body.strip():
            continue
        used = {k: v for k, v in (params or {}).items() if f"${k}" in body}
        con.execute(body, used) if used else con.execute(body)


def connect():
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    return con


def load_csv(con, path):
    con.execute(
        """
        CREATE OR REPLACE TABLE raw_events AS
        SELECT * FROM read_csv(?, header = true, columns = {
            'timestamp': 'BIGINT', 'visitorid': 'BIGINT', 'event': 'VARCHAR',
            'itemid': 'BIGINT', 'transactionid': 'BIGINT'})
        """,
        [str(path)],
    )


def build(con):
    for name in ORDER:
        run_sql(con, name)
    return con


def build_from_csv(path):
    con = connect()
    load_csv(con, path)
    return build(con)
