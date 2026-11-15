import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.environ.get("TIMESHEETS_DB", "/data/timesheets.db")

DEFAULT_SETTINGS = {
    "base_rate": None,
    "currency": "AUD",
    "pay_cycle_type": "fortnightly",
    "pay_cycle_start_date": "",
    "custom_cycle_days": 14,
    "week_start_day": 0,
    "ordinary_hours": 38,
    "public_holiday_credit_hours": 10,
    "public_holiday_credit_days": [0, 1, 2, 3],
    "public_holiday_credit_counts_toward_overtime": None,
    "overtime_tiers": [
        {"after_hours": 38, "multiplier": 1.5, "label": "Overtime 1"},
        {"after_hours": 44, "multiplier": 2.0, "label": "Overtime 2"}
    ],
    "travel_rules": [
        {"after_hours": 0, "multiplier": 1.3, "label": "Travel ordinary"},
        {"after_hours": 38, "multiplier": 1.8, "label": "Travel overtime 1"},
        {"after_hours": 44, "multiplier": 2.3, "label": "Travel overtime 2"}
    ],
    "penalty_rules": [
        {"name": "Sunday", "enabled": True, "condition": "day_of_week", "day": 6,
         "scope": "work", "multiplier": 2.0, "mode": "replace"}
    ],
    "allowances": []
}

@contextmanager
def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            finish_time TEXT NOT NULL,
            break_minutes INTEGER NOT NULL DEFAULT 30,
            notes TEXT NOT NULL DEFAULT '',
            is_public_holiday INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS travel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_id INTEGER,
            travel_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            finish_time TEXT NOT NULL,
            break_minutes INTEGER NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(shift_id) REFERENCES shifts(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            holiday_date TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS allowance_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            notes TEXT NOT NULL DEFAULT ''
        );
        """)
        row = db.execute("SELECT id FROM settings WHERE id=1").fetchone()
        if not row:
            db.execute("INSERT INTO settings(id,payload) VALUES(1,?)",
                       (json.dumps(DEFAULT_SETTINGS),))

def get_settings(db):
    row = db.execute("SELECT payload FROM settings WHERE id=1").fetchone()
    return json.loads(row["payload"]) if row else DEFAULT_SETTINGS.copy()

def save_settings(db, settings):
    db.execute("INSERT INTO settings(id,payload) VALUES(1,?) "
               "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
               (json.dumps(settings),))

def now_iso():
    return datetime.now(timezone.utc).isoformat()