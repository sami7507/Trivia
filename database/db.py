"""
database/db.py — one small data layer, two engines.

  • SQLite (default, zero setup):  file at database/data/triavia.db  (override: TRIAVIA_DB_PATH)
  • PostgreSQL (production):       set DATABASE_URL=postgresql://user:pass@host:5432/dbname

All SQL in the project is written once with `?` placeholders; `Conn` translates for Postgres.
Every query is parameterised. The schema is created automatically on first connect.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "database" / "data" / "triavia.db"
_ready: set = set()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


def is_postgres() -> bool:
    return database_url().startswith(("postgres://", "postgresql://"))


def db_path() -> Path:
    return Path(os.getenv("TRIAVIA_DB_PATH", DEFAULT_DB_PATH))


def engine_name() -> str:
    return "postgresql" if is_postgres() else "sqlite"


class Conn:
    """Uniform wrapper: execute(sql, params) → cursor with dict rows, `?` placeholders on both engines."""

    def __init__(self, raw, postgres: bool):
        self.raw, self.pg = raw, postgres

    def execute(self, sql: str, params: tuple = ()):
        if self.pg:
            return self.raw.execute(sql.replace("?", "%s"), params)
        return self.raw.execute(sql, params)

    def insert_id(self, sql: str, params: tuple = ()) -> int:
        """INSERT and return the new row's id (RETURNING on Postgres, lastrowid on SQLite)."""
        if self.pg:
            return int(self.execute(sql + " RETURNING id", params).fetchone()["id"])
        return int(self.execute(sql, params).lastrowid)


def _schema_statements(pg: bool) -> List[str]:
    text = (Path(__file__).parent / ("schema.postgres.sql" if pg else "schema.sqlite.sql")).read_text("utf-8")
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def _init(conn: Conn) -> None:
    for stmt in _schema_statements(conn.pg):
        conn.execute(stmt)
    if not conn.pg:  # migrate SQLite databases created by v2.0 (no user_id column)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(assessments)").fetchall()}
        if "user_id" not in cols:
            conn.execute("ALTER TABLE assessments ADD COLUMN user_id INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assessments_user ON assessments(user_id, id DESC)")


@contextmanager
def connect():
    pg = is_postgres()
    if pg:
        import psycopg
        from psycopg.rows import dict_row
        raw = psycopg.connect(database_url(), row_factory=dict_row, connect_timeout=10)
        key = database_url()
    else:
        path = db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = sqlite3.connect(path, timeout=10)
        raw.row_factory = lambda cur, row: {d[0]: v for d, v in zip(cur.description, row)}
        key = str(path)
    conn = Conn(raw, pg)
    try:
        if key not in _ready:
            _init(conn)
            raw.commit()
            _ready.add(key)
        yield conn
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def init_db() -> None:
    with connect():
        pass


def ping() -> bool:
    try:
        with connect() as c:
            c.execute("SELECT 1")
        return True
    except Exception:
        return False


# ── Assessments (scoped per user; user_id=None means "all", used by service/anon access) ──
def save_assessment(inputs: Dict[str, Any], prediction: Dict[str, Any],
                    user_id: Optional[int] = None) -> int:
    with connect() as c:
        return c.insert_id(
            """INSERT INTO assessments
               (user_id, created_at, age, chief_complaint, triage_level, triage_label, confidence,
                safety_override, inputs_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (user_id, now_iso(), inputs["age"], inputs["chief_complaint"], prediction["triage_level"],
             prediction["triage_label"], prediction["confidence"],
             int(prediction.get("safety_override", False)), json.dumps(inputs)))


def _scope(user_id: Optional[int]):
    return ("WHERE user_id = ?", (user_id,)) if user_id is not None else ("", ())


def list_assessments(limit: int = 50, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    where, args = _scope(user_id)
    with connect() as c:
        return c.execute(
            f"""SELECT id, created_at, age, chief_complaint, triage_level,
                       triage_label, confidence, safety_override
                FROM assessments {where} ORDER BY id DESC LIMIT ?""", (*args, limit)).fetchall()


def stats(user_id: Optional[int] = None) -> Dict[str, Any]:
    where, args = _scope(user_id)
    with connect() as c:
        total = c.execute(f"SELECT COUNT(*) AS n FROM assessments {where}", args).fetchone()["n"]
        by_level = {r["triage_label"]: r["n"] for r in c.execute(
            f"SELECT triage_label, COUNT(*) AS n FROM assessments {where} GROUP BY triage_label", args).fetchall()}
        avg = c.execute(f"SELECT AVG(confidence) AS a FROM assessments {where}", args).fetchone()["a"]
    return {"total": int(total), "by_level": by_level,
            "avg_confidence": round(float(avg), 4) if avg is not None else None}


def clear_assessments(user_id: Optional[int] = None) -> int:
    where, args = _scope(user_id)
    with connect() as c:
        return c.execute(f"DELETE FROM assessments {where}", args).rowcount


# ── Feedback ──────────────────────────────────────────────────────────────────
def save_feedback(message: str, rating: Optional[int] = None, contact: Optional[str] = None,
                  user_id: Optional[int] = None) -> int:
    with connect() as c:
        return c.insert_id(
            "INSERT INTO feedback (created_at, user_id, rating, message, contact) VALUES (?,?,?,?,?)",
            (now_iso(), user_id, rating, message, contact))


def list_feedback(limit: int = 100) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), 1000))
    with connect() as c:
        return c.execute("SELECT id, created_at, user_id, rating, message, contact FROM feedback "
                         "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
