import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.environ.get("TIMESHEETS_DB", "/data/timesheets.db")

DEFAULT_SETTINGS = {
    "base_rate": None,
    "pay_rate_history": [{"effective_from": "2026-07-01", "rate": None}],
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
    "public_holiday_credit_hours": 10,
    "public_holiday_credit_days": [0, 1, 2, 3],
    "public_holiday_credit_counts_toward_overtime": None,
    "overtime_tiers": [
        {"after_hours": 0, "multiplier": 1.0, "label": "Ordinary"},
        {"after_hours": 38, "multiplier": 1.5, "label": "Ord 1.5", "cost_code": "Ordinary 1.5"},
        {"after_hours": 40, "multiplier": 1.5, "label": "OT 1.5", "cost_code": "Overtime 1.5"},
        {"after_hours": 44, "multiplier": 2.0, "label": "OT 2.0", "cost_code": "Overtime 2.0"}
    ],
    "travel_rules": [
        {"after_hours": 0, "multiplier": 1.3, "label": "Travel ordinary", "cost_code": "Travel-OTH Ordinary"},
        {"after_hours": 38, "multiplier": 1.8, "label": "Travel overtime 1.5", "cost_code": "Travel-OTH OT 1.8"},
        {"after_hours": 44, "multiplier": 2.3, "label": "Travel overtime 2.0", "cost_code": "Travel-OTH OT 2.3"}
    ],
    "penalty_rules": [
        {"name": "Sunday", "enabled": True, "condition": "day_of_week", "day": 6,
         "scope": "work", "multiplier": 2.0, "mode": "replace"}
    ],
    "allowances": [],
    "payroll_codes": {"ordinary_1_0":"Ordinary 1.0","ordinary_1_5":"Ordinary 1.5","overtime_1_5":"Overtime 1.5","overtime_2_0":"Overtime 2.0","public_holiday":"Public Holiday","travel_ordinary":"Travel-OTH Ordinary","travel_overtime":"Travel-OTH OT","annual_leave":"Annual Leave","sick_leave":"Sick Leave"},
    "payg_annual_years": {"2026-27": {"resident_brackets": [
        {"lower": 0, "upper": 18200, "base_tax": 0, "rate": 0},
        {"lower": 18200, "upper": 45000, "base_tax": 0, "rate": 0.15},
        {"lower": 45000, "upper": 135000, "base_tax": 4020, "rate": 0.30},
        {"lower": 135000, "upper": 190000, "base_tax": 31020, "rate": 0.37},
        {"lower": 190000, "upper": None, "base_tax": 51370, "rate": 0.45}
    ]}},
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
        if "leave_type" not in columns:
            db.execute("ALTER TABLE shifts ADD COLUMN leave_type TEXT NOT NULL DEFAULT 'work'")
        if "project" not in columns:
            db.execute("ALTER TABLE shifts ADD COLUMN project TEXT NOT NULL DEFAULT ''")

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
    # Migrate a legacy single base rate to an editable effective-dated history.
    if not stored.get("pay_rate_history"):
        merged["pay_rate_history"] = [{"effective_from": "2026-07-01", "rate": stored.get("base_rate")}]
    else:
        merged["pay_rate_history"] = stored["pay_rate_history"]
    # Remove the legacy additive travel/overseas loading; travel tier multipliers are now authoritative.
    merged.pop("travel_loading", None)
    legacy_tiers = [{"after_hours": 38, "multiplier": 1.5, "label": "Overtime 1"}, {"after_hours": 44, "multiplier": 2.0, "label": "Overtime 2"}]
    if stored.get("overtime_tiers") == legacy_tiers:
        merged["overtime_tiers"] = DEFAULT_SETTINGS["overtime_tiers"]

    # Update only the original built-in tier descriptions to the current defaults.
    # Custom descriptions and all user-defined thresholds/rates are preserved.
    default_overtime_labels = {
        (38, 1.5): {"Ordinary 1.5x": "Ord 1.5"},
        (40, 1.5): {"Overtime 1.5x": "OT 1.5"},
        (44, 2.0): {"Overtime 2.0x": "OT 2.0"},
    }
    for tier in merged.get("overtime_tiers", []):
        key = (int(float(tier.get("after_hours", 0))), float(tier.get("multiplier", 1)))
        replacement = default_overtime_labels.get(key, {}).get(tier.get("label"))
        if replacement:
            tier["label"] = replacement
    default_travel_labels = {
        (38, 1.8, "Travel overtime 1"): "Travel overtime 1.5",
        (44, 2.3, "Travel overtime 2"): "Travel overtime 2.0",
    }
    for tier in merged.get("travel_rules", []):
        key = (int(float(tier.get("after_hours", 0))), float(tier.get("multiplier", 1)), tier.get("label"))
        if key in default_travel_labels:
            tier["label"] = default_travel_labels[key]

    # Bring the original built-in travel cost-code names up to date without
    # replacing any custom names.
    for tier in merged.get("travel_rules", []):
        after = int(float(tier.get("after_hours", 0) or 0))
        multiplier = float(tier.get("multiplier", 1) or 1)
        old_code = tier.get("cost_code")
        if after == 38 and multiplier == 1.8 and old_code == "Travel-OTH OT":
            tier["cost_code"] = "Travel-OTH OT 1.8"
        elif after == 44 and multiplier == 2.3 and old_code == "Travel-OTH OT":
            tier["cost_code"] = "Travel-OTH OT 2.3"

    # Migrate legacy standalone payroll-code labels onto their matching tiers.
    # This is an in-memory compatibility migration: existing settings and timesheets
    # remain intact, and the new fields are persisted the next time settings are saved.
    codes = dict(DEFAULT_SETTINGS.get("payroll_codes", {}))
    codes.update(stored.get("payroll_codes", {}) or {})
    overtime_tiers = []
    for tier in merged.get("overtime_tiers", []):
        item = dict(tier)
        if not item.get("cost_code"):
            after = float(item.get("after_hours", 0) or 0)
            multiplier = float(item.get("multiplier", 1) or 1)
            if after <= 0:
                item["cost_code"] = codes.get("ordinary_1_0", "Ordinary 1.0")
            elif multiplier >= 1.99:
                item["cost_code"] = codes.get("overtime_2_0", "Overtime 2.0")
            elif after <= 38:
                item["cost_code"] = codes.get("ordinary_1_5", "Ordinary 1.5")
            elif multiplier >= 1.49:
                item["cost_code"] = codes.get("overtime_1_5", "Overtime 1.5")
            else:
                item["cost_code"] = item.get("label", "Overtime")
        overtime_tiers.append(item)
    merged["overtime_tiers"] = overtime_tiers

    travel_tiers = []
    for tier in merged.get("travel_rules", []):
        item = dict(tier)
        if not item.get("cost_code"):
            after = float(item.get("after_hours", 0) or 0)
            label = str(item.get("label", "")).lower()
            is_overtime = after > 0 or "overtime" in label or label.startswith("ot")
            item["cost_code"] = codes.get("travel_overtime" if is_overtime else "travel_ordinary",
                                          "Travel-OTH OT" if is_overtime else "Travel-OTH Ordinary")
        travel_tiers.append(item)
    merged["travel_rules"] = travel_tiers
    return merged

def save_settings(db, settings):
    db.execute("INSERT INTO settings(id,payload) VALUES(1,?) "
               "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
               (json.dumps(settings),))

def now_iso():
    return datetime.now(timezone.utc).isoformat()