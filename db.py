import sqlite3
from exercise_mapping import EXERCISE_MAPPING

DB_PATH = "lifts_tracker.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with open("schema.sql", "r") as f:
        schema = f.read()
    with get_conn() as conn:
        conn.executescript(schema)
        for split_day in ("S/L", "C/T", "B/B"):
            conn.execute("INSERT OR IGNORE INTO split_days (name) VALUES (?)", (split_day,))
        for primary, aliases in EXERCISE_MAPPING.items():
            conn.execute("INSERT OR IGNORE INTO exercises (primary_name) VALUES (?)", (primary,))
            exercise_id = conn.execute("SELECT exercise_id FROM exercises WHERE primary_name = ?", (primary,)).fetchone()[0]
            for alias in aliases:
                conn.execute("INSERT OR IGNORE INTO exercise_aliases (exercise_id, alias) VALUES (?, ?)", (exercise_id, alias))
