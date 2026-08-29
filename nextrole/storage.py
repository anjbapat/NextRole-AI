import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

DB_PATH = Path("data/nextrole.db")


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS applications(
      id TEXT PRIMARY KEY, company TEXT, role TEXT, fit_score INTEGER,
      recommendation TEXT, status TEXT, current_stage TEXT,
      state_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    conn.commit()
    return conn


def save_journey(state):
    jid = state["journey_id"]
    safe = {k: v for k, v in state.items() if k != "resume_text"}
    fit = safe.get("fit_analysis", {})
    job = safe.get("job_analysis", {})
    now = datetime.now(UTC).isoformat()
    with connect() as conn:
        conn.execute(
            """INSERT INTO applications(id,company,role,fit_score,recommendation,status,current_stage,state_json,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET company=excluded.company,role=excluded.role,
        fit_score=excluded.fit_score,recommendation=excluded.recommendation,status=excluded.status,
        current_stage=excluded.current_stage,state_json=excluded.state_json,updated_at=excluded.updated_at""",
            (
                jid,
                job.get("company", "Unknown"),
                job.get("title", "Target role"),
                fit.get("overall_score", 0),
                fit.get("recommendation", ""),
                safe.get("status", ""),
                safe.get("current_step", ""),
                json.dumps(safe, default=str),
                now,
                now,
            ),
        )
        conn.commit()
    return jid


def load_journeys():
    with connect() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT id,company,role,fit_score,recommendation,status,current_stage,updated_at FROM applications ORDER BY updated_at DESC"
            )
        ]
