import sqlite3

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
