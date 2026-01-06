import sqlite3
from datetime import datetime

DB_PATH = "svx.db"

def _conn():
    # timeout + WAL = évite les "database is locked"
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=3.0)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA synchronous=NORMAL;")
    c.execute("PRAGMA busy_timeout=3000;")
    return c

def init_db():
    c = _conn()
    cur = c.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transmissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_ts INTEGER NOT NULL,
        end_ts INTEGER NOT NULL,
        duration_s INTEGER NOT NULL,
        day TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    # Valeurs par défaut
    cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('relay_mode','AUTO')")     # AUTO / MANUAL
    cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('relay_manual','OFF')")   # ON / OFF
    cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('relay_state','OFF')")    # ON / OFF (état réel)

    c.commit()
    c.close()

def set_setting(key: str, value: str):
    c = _conn()
    c.execute("""
        INSERT INTO settings(key,value) VALUES(?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))
    c.commit()
    c.close()

def get_setting(key: str, default=None):
    c = _conn()
    r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    c.close()
    return r["value"] if r else default

def insert_tx(start_ts: int, end_ts: int):
    dur = max(0, end_ts - start_ts)
    day = datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d")
    c = _conn()
    c.execute(
        "INSERT INTO transmissions(start_ts,end_ts,duration_s,day) VALUES(?,?,?,?)",
        (start_ts, end_ts, dur, day),
    )
    c.commit()
    c.close()
    return dur, day

def daily_stats(day: str):
    c = _conn()
    r = c.execute("""
        SELECT
          COUNT(*) AS n_tx,
          COALESCE(SUM(duration_s),0) AS total_s,
          COALESCE(MAX(duration_s),0) AS max_s
        FROM transmissions
        WHERE day=?
    """, (day,)).fetchone()
    c.close()
    return dict(r)

