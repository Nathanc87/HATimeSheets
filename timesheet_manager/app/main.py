import csv
import io
import json
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openpyxl import Workbook

from .db import connect, init_db, get_settings, save_settings, now_iso
from .payroll import calculate, cycle_bounds

app = FastAPI(title="HATimeSheets")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

class ShiftIn(BaseModel):
    work_date: str
    start_time: str
    finish_time: str
    break_minutes: int = Field(default=30, ge=0, le=1440)
    notes: str = ""
    is_public_holiday: bool = False
    is_travelling: bool = False
    is_overseas: bool = False

class TravelIn(BaseModel):
    shift_id: int | None = None
    travel_date: str
    start_time: str
    finish_time: str
    break_minutes: int = Field(default=0, ge=0, le=1440)
    notes: str = ""

class HolidayIn(BaseModel):
    holiday_date: str
    name: str

class AllowanceIn(BaseModel):
    entry_date: str
    name: str
    amount: float
    notes: str = ""

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def index():
    with open("app/static/index.html", encoding="utf-8") as f:
        return f.read()

@app.get("/api/settings")
def settings_get():
    with connect() as db:
        return get_settings(db)

@app.put("/api/settings")
def settings_put(payload: dict):
    with connect() as db:
        current = get_settings(db)
        current.update(payload)
        if current.get("base_rate") in ("", None):
            current["base_rate"] = None
        else:
            current["base_rate"] = float(current["base_rate"])
            if current["base_rate"] < 0:
                raise HTTPException(400, "Base rate cannot be negative")
        save_settings(db, current)
        return current

@app.get("/api/shifts")
def shifts_get(start: str | None = None, end: str | None = None):
    with connect() as db:
        sql = "SELECT * FROM shifts"
        params = []
        if start and end:
            sql += " WHERE work_date BETWEEN ? AND ?"
            params = [start, end]
        sql += " ORDER BY work_date DESC, start_time DESC"
        return [dict(r) for r in db.execute(sql, params).fetchall()]

@app.post("/api/shifts")
def shifts_post(item: ShiftIn):
    try:
        date.fromisoformat(item.work_date)
    except ValueError:
        raise HTTPException(400, "Invalid date")
    now = now_iso()
    with connect() as db:
        cur = db.execute("""INSERT INTO shifts
          (work_date,start_time,finish_time,break_minutes,notes,is_public_holiday,is_travelling,is_overseas,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?)""",
          (item.work_date,item.start_time,item.finish_time,item.break_minutes,item.notes,
           int(item.is_public_holiday),int(item.is_travelling),int(item.is_overseas),now,now))
        return {"id": cur.lastrowid}

@app.put("/api/shifts/{shift_id}")
def shifts_put(shift_id: int, item: ShiftIn):
    with connect() as db:
        cur = db.execute("""UPDATE shifts SET work_date=?,start_time=?,finish_time=?,
          break_minutes=?,notes=?,is_public_holiday=?,is_travelling=?,is_overseas=?,updated_at=? WHERE id=?""",
          (item.work_date,item.start_time,item.finish_time,item.break_minutes,item.notes,
           int(item.is_public_holiday),int(item.is_travelling),int(item.is_overseas),now_iso(),shift_id))
        if not cur.rowcount:
            raise HTTPException(404, "Shift not found")
        return {"ok": True}

@app.delete("/api/shifts/{shift_id}")
def shifts_delete(shift_id: int):
    with connect() as db:
        db.execute("DELETE FROM travel WHERE shift_id=?", (shift_id,))
        cur = db.execute("DELETE FROM shifts WHERE id=?", (shift_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Shift not found")
        return {"ok": True}

@app.get("/api/travel")
def travel_get():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM travel ORDER BY travel_date DESC,start_time DESC").fetchall()]

@app.post("/api/travel")
def travel_post(item: TravelIn):
    with connect() as db:
        if item.shift_id and not db.execute("SELECT id FROM shifts WHERE id=?", (item.shift_id,)).fetchone():
            raise HTTPException(404, "Linked shift not found")
        cur = db.execute("""INSERT INTO travel
          (shift_id,travel_date,start_time,finish_time,break_minutes,notes,created_at)
          VALUES(?,?,?,?,?,?,?)""",
          (item.shift_id,item.travel_date,item.start_time,item.finish_time,item.break_minutes,item.notes,now_iso()))
        return {"id": cur.lastrowid}

@app.delete("/api/travel/{travel_id}")
def travel_delete(travel_id: int):
    with connect() as db:
        cur = db.execute("DELETE FROM travel WHERE id=?", (travel_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Travel entry not found")
        return {"ok": True}

@app.get("/api/holidays")
def holidays_get():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM holidays ORDER BY holiday_date").fetchall()]

@app.post("/api/holidays")
def holidays_post(item: HolidayIn):
    with connect() as db:
        db.execute("INSERT INTO holidays(holiday_date,name) VALUES(?,?) ON CONFLICT(holiday_date) DO UPDATE SET name=excluded.name",
                   (item.holiday_date,item.name))
        return {"ok": True}

@app.delete("/api/holidays/{holiday_id}")
def holidays_delete(holiday_id: int):
    with connect() as db:
        db.execute("DELETE FROM holidays WHERE id=?", (holiday_id,))
        return {"ok": True}

@app.post("/api/allowances")
def allowance_post(item: AllowanceIn):
    with connect() as db:
        cur = db.execute("INSERT INTO allowance_entries(entry_date,name,amount,notes) VALUES(?,?,?,?)",
                         (item.entry_date,item.name,item.amount,item.notes))
        return {"id": cur.lastrowid}

@app.get("/api/allowances")
def allowances_get():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM allowance_entries ORDER BY entry_date DESC").fetchall()]

def report_data(start=None, end=None):
    with connect() as db:
        settings = get_settings(db)
        if not start and not end:
            cycle = cycle_bounds(settings.get("pay_cycle_start_date", ""),
                                 settings.get("pay_cycle_type", "fortnightly"),
                                 settings.get("custom_cycle_days", 14), date.today())
            if cycle:
                start, end = cycle[0].isoformat(), cycle[1].isoformat()
        sql = "SELECT * FROM shifts"
        params = []
        if start and end:
            sql += " WHERE work_date BETWEEN ? AND ?"
            params = [start,end]
        shifts = [dict(r) for r in db.execute(sql + " ORDER BY work_date,start_time", params).fetchall()]
        travel_sql = "SELECT * FROM travel"
        travel_params = []
        if start and end:
            travel_sql += " WHERE travel_date BETWEEN ? AND ?"
            travel_params = [start, end]
        travel = [dict(r) for r in db.execute(travel_sql + " ORDER BY travel_date,start_time", travel_params).fetchall()]
        allowance_sql = "SELECT * FROM allowance_entries"
        allowance_params = []
        if start and end:
            allowance_sql += " WHERE entry_date BETWEEN ? AND ?"
            allowance_params = [start, end]
        allowances = [dict(r) for r in db.execute(allowance_sql + " ORDER BY entry_date", allowance_params).fetchall()]
        holidays = [r["holiday_date"] for r in db.execute("SELECT holiday_date FROM holidays").fetchall()]
        return calculate(shifts, travel, settings, holidays, allowances), settings, shifts, travel

@app.get("/api/report")
def report(start: str | None = None, end: str | None = None):
    result, settings, shifts, travel = report_data(start,end)
    result["base_rate"] = settings.get("base_rate")
    result["currency"] = settings.get("currency","AUD")
    result["pay_cycle_type"] = settings.get("pay_cycle_type")
    cycle = cycle_bounds(settings.get("pay_cycle_start_date", ""),
                         settings.get("pay_cycle_type", "fortnightly"),
                         settings.get("custom_cycle_days", 14), date.today())
    result["current_pay_period"] = ({"start": cycle[0].isoformat(), "end": cycle[1].isoformat()}
                                    if cycle else None)
    if start and end:
        result["period"] = {"start":start,"end":end}
    return result

@app.get("/api/export.csv")
def export_csv(start: str | None = None, end: str | None = None):
    result, settings, shifts, travel = report_data(start,end)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Record type","Date","Start","Finish","Break minutes","Paid hours","Category","Multiplier","Estimated earnings","Travelling","Overseas","Notes"])
    shift_map = {s["id"]:s for s in shifts}
    for item in result["shifts"]:
        s = shift_map[item["id"]]
        for seg in item["segments"]:
            writer.writerow(["Travel" if item["is_travelling"] else "Work",item["date"],s["start_time"],s["finish_time"],s["break_minutes"],
                             seg["hours"],seg["category"],seg["multiplier"],"" if item["estimated_earnings"] is None else item["estimated_earnings"],item["is_travelling"],item["is_overseas"],item["notes"]])
    for item in result["travel"]:
        t = next(x for x in travel if x["id"] == item["id"])
        writer.writerow(["Travel",item["date"],t["start_time"],t["finish_time"],t["break_minutes"],
                         item["hours"],item["category"],item["multiplier"],"" if item["estimated_earnings"] is None else item["estimated_earnings"],"", "",item["notes"]])
    for item in result.get("allowances", []):
        writer.writerow(["Allowance",item["basis"],"","","","",item["name"],"",item["amount"],"","",""])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition":"attachment; filename=timesheet.csv"})

@app.get("/api/export.xlsx")
def export_xlsx(start: str | None = None, end: str | None = None):
    result, settings, shifts, travel = report_data(start,end)
    wb = Workbook()
    ws = wb.active
    ws.title = "Timesheet"
    ws.append(["Type","Date","Start","Finish","Break (min)","Paid hours","Category","Multiplier","Estimated earnings","Travelling","Overseas","Notes"])
    shift_map = {s["id"]:s for s in shifts}
    for item in result["shifts"]:
        s = shift_map[item["id"]]
        for seg in item["segments"]:
            ws.append(["Travel" if item["is_travelling"] else "Work",item["date"],s["start_time"],s["finish_time"],s["break_minutes"],seg["hours"],
                       seg["category"],seg["multiplier"],item["estimated_earnings"],item["is_travelling"],item["is_overseas"],item["notes"]])
    for item in result["travel"]:
        t = next(x for x in travel if x["id"] == item["id"])
        ws.append(["Travel",item["date"],t["start_time"],t["finish_time"],t["break_minutes"],item["hours"],
                   item["category"],item["multiplier"],item["estimated_earnings"],item["notes"]])
    summary = wb.create_sheet("Summary")
    summary.append(["Metric","Value"])
    summary.append(["Work hours",result["total_work_hours"]])
    summary.append(["Travel hours",result["total_travel_hours"]])
    summary.append(["Base hourly rate",settings.get("base_rate")])
    summary.append(["Allowances",result.get("total_allowances", 0)])
    summary.append(["Estimated gross",result["estimated_gross"]])
    allowance_sheet = wb.create_sheet("Allowances")
    allowance_sheet.append(["Allowance","Frequency","Basis","Amount"])
    for item in result.get("allowances", []):
        allowance_sheet.append([item["name"],item["frequency"],item["basis"],item["amount"]])
    for sheet in wb.worksheets:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for col in sheet.columns:
            letter = col[0].column_letter
            sheet.column_dimensions[letter].width = min(42,max(12,max(len(str(c.value or "")) for c in col)+2))
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition":"attachment; filename=timesheet.xlsx"})

@app.get("/api/health")
def health():
    return {"status":"ok","application":"HATimeSheets","version":"0.1.1"}