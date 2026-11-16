import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.environ.get("TIMESHEETS_DB", "/data/timesheets.db")

DEFAULT_SETTINGS = {
    "base_rate": None,
    "presence_entity": "",
    "work_zone_entities": [],
    "presence_grace_minutes": 30,
    "presence_start_time": "05:30",
    "presence_rounding_minutes": 15,
    "presence_session": None,
    "currency": "AUD",
    "pay_cycle_type": "fortnightly",
    "pay_cycle_start_date": "",
    "custom_cycle_days": 14,
    "week_start_day": 0,
    "ordinary_hours": 38,
    "normal_hours_schedule": [
        {"day": 0, "label": "Monday", "enabled": True, "start_time": "05:30", "finish_time": "16:00"},
        {"day": 1, "label": "Tuesday", "enabled": True, "start_time": "05:30", "finish_time": "16:00", "break_minutes": 30},
        {"day": 2, "label": "Wednesday", "enabled": True, "start_time": "05:30", "finish_time": "16:00", "break_minutes": 30},
        {"day": 3, "label": "Thursday", "enabled": True, "start_time": "05:30", "finish_time": "16:00", "break_minutes": 30},
        {"day": 4, "label": "Friday", "enabled": False, "start_time": "05:30", "finish_time": "16:00", "break_minutes": 30},
        {"day": 5, "label": "Saturday", "enabled": False, "start_time": "05:30", "finish_time": "16:00", "break_minutes": 30},
        {"day": 6, "label": "Sunday", "enabled": False, "start_time": "05:30", "finish_time": "16:00", "break_minutes": 30}
    ],
    "travel_loading": 0.3,
    "public_holiday_credit_hours": 10,
    "public_holiday_credit_days": [0, 1, 2, 3],
    "public_holiday_credit_counts_toward_overtime": None,
    "overtime_tiers": [
        {"after_hours": 0, "multiplier": 1.0, "label": "Ordinary"},
        {"after_hours": 38, "multiplier": 1.5, "label": "Ordinary 1.5x"},
        {"after_hours": 40, "multiplier": 1.5, "label": "Overtime 1.5x"},
        {"after_hours": 44, "multiplier": 2.0, "label": "Overtime 2.0x"}
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
    "allowances": [],
    "payg_tax_free_threshold": True,
    "payg_extra_withholding": 0,
    "payg_years": {"2026-27":{"scale1":[{"upper":188,"a":0.15,"b":0.15},{"upper":371,"a":0.2084,"b":11.0185},{"upper":515,"a":0.179,"b":0.1066},{"upper":932,"a":0.3227,"b":74.1674},{"upper":2246,"a":0.32,"b":71.6508},{"upper":3303,"a":0.39,"b":228.8816},{"upper":None,"a":0.47,"b":493.1893}],"scale2":[{"upper":362,"a":0,"b":0},{"upper":538,"a":0.15,"b":54.3462},{"upper":673,"a":0.25,"b":108.2135},{"upper":721,"a":0.17,"b":54.3473},{"upper":865,"a":0.179,"b":60.8377},{"upper":1282,"a":0.3227,"b":185.1935},{"upper":2596,"a":0.32,"b":181.7319},{"upper":3653,"a":0.39,"b":363.4627},{"upper":None,"a":0.47,"b":655.7704}],"help_scale1":[{"upper":987,"a":0,"b":0},{"upper":2144,"a":0.15,"b":148.0615},{"upper":2727,"a":0.17,"b":190.9527},{"upper":None,"a":0.1,"b":0}],"help_scale2":[{"upper":1337,"a":0,"b":0},{"upper":2494,"a":0.15,"b":200.5615},{"upper":3577,"a":0.17,"b":250.4527},{"upper":None,"a":0.1,"b":0}]}}
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
        # Additive migrations preserve existing Home Assistant installations and entries.
        columns = {row["name"] for row in db.execute("PRAGMA table_info(shifts)").fetchall()}
        if "is_travelling" not in columns:
            db.execute("ALTER TABLE shifts ADD COLUMN is_travelling INTEGER NOT NULL DEFAULT 0")
        if "is_overseas" not in columns:
            db.execute("ALTER TABLE shifts ADD COLUMN is_overseas INTEGER NOT NULL DEFAULT 0")

        row = db.execute("SELECT id FROM settings WHERE id=1").fetchone()
        if not row:
            db.execute("INSERT INTO settings(id,payload) VALUES(1,?)",
                       (json.dumps(DEFAULT_SETTINGS),))

def get_settings(db):
    row = db.execute("SELECT payload FROM settings WHERE id=1").fetchone()
    if not row:
        return DEFAULT_SETTINGS.copy()
    stored = json.loads(row["payload"])
    merged = DEFAULT_SETTINGS.copy()
    merged.update(stored)
    legacy_tiers = [{"after_hours": 38, "multiplier": 1.5, "label": "Overtime 1"}, {"after_hours": 44, "multiplier": 2.0, "label": "Overtime 2"}]
    if stored.get("overtime_tiers") == legacy_tiers:
        merged["overtime_tiers"] = DEFAULT_SETTINGS["overtime_tiers"]
    return merged

def save_settings(db, settings):
    db.execute("INSERT INTO settings(id,payload) VALUES(1,?) "
               "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
               (json.dumps(settings),))

def now_iso():
    return datetime.now(timezone.utc).isoformat()