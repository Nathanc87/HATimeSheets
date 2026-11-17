import csv
import asyncio
import io
import json
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

from .db import connect, init_db, get_settings, save_settings, now_iso
from .payroll import calculate, cycle_bounds
from .ha_presence import get_ha_entities, presence_poll

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
    leave_type: str = "work"
    project: str = ""

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
async def startup():
    init_db()
    app.state.presence_task = asyncio.create_task(presence_poll())

@app.on_event("shutdown")
async def shutdown():
    task = getattr(app.state, "presence_task", None)
    if task:
        task.cancel()

@app.get("/api/ha/entities")
def ha_entities():
    try:
        return get_ha_entities()
    except Exception as exc:
        raise HTTPException(503, f"Home Assistant entities unavailable: {exc}")

@app.get("/api/presence/status")
def presence_status():
    with connect() as db:
        settings = get_settings(db)
        return {"enabled": bool(settings.get("presence_entity") and settings.get("work_zone_entities")),
                "entity": settings.get("presence_entity", ""),
                "zones": settings.get("work_zone_entities", []),
                "session": settings.get("presence_session")}

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
        normalized = []
        seen_dates = set()
        for item in current.get("pay_rate_history", []):
            effective_from = str(item.get("effective_from", "")).strip()
            value = item.get("rate")
            if not effective_from:
                raise HTTPException(400, "Every pay rate needs an effective date")
            try:
                date.fromisoformat(effective_from)
            except ValueError:
                raise HTTPException(400, "Pay rate effective dates must be valid dates")
            if effective_from in seen_dates:
                raise HTTPException(400, "Pay rate effective dates must be unique")
            seen_dates.add(effective_from)
            rate_value = None if value in ("", None) else float(value)
            if rate_value is not None and rate_value < 0:
                raise HTTPException(400, "Pay rate cannot be negative")
            normalized.append({"effective_from": effective_from, "rate": rate_value})
        normalized.sort(key=lambda x: x["effective_from"])
        current["pay_rate_history"] = normalized
        current["base_rate"] = next((x["rate"] for x in reversed(normalized) if x["effective_from"] <= date.today().isoformat()), None)
        save_settings(db, current)
        return current

@app.post("/api/projects/rename")
def project_rename(payload: dict):
    old_name = str(payload.get("old_name", "")).strip()
    new_name = str(payload.get("new_name", "")).strip()
    if not old_name or not new_name:
        raise HTTPException(400, "Project names are required")
    with connect() as db:
        db.execute("UPDATE shifts SET project=? WHERE project=?", (new_name, old_name))
        return {"ok": True}

@app.post("/api/projects/remove")
def project_remove(payload: dict):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(400, "Project name is required")
    with connect() as db:
        db.execute("UPDATE shifts SET project='' WHERE project=?", (name,))
        return {"ok": True}

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

def round_shift_times(start_time: str, finish_time: str):
    """Round clock-in up and clock-out down to 15-minute boundaries."""
    start = datetime.strptime(start_time, "%H:%M")
    finish = datetime.strptime(finish_time, "%H:%M")
    start_minutes = start.hour * 60 + start.minute
    finish_minutes = finish.hour * 60 + finish.minute
    rounded_start = min(((start_minutes + 14) // 15) * 15, 23 * 60 + 45)
    rounded_finish = (finish_minutes // 15) * 15
    return f"{rounded_start // 60:02d}:{rounded_start % 60:02d}", f"{rounded_finish // 60:02d}:{rounded_finish % 60:02d}"


@app.post("/api/shifts")
def shifts_post(item: ShiftIn):
    try:
        date.fromisoformat(item.work_date)
    except ValueError:
        raise HTTPException(400, "Invalid date")
    rounded_start, rounded_finish = round_shift_times(item.start_time, item.finish_time)
    now = now_iso()
    with connect() as db:
        cur = db.execute("""INSERT INTO shifts
          (work_date,start_time,finish_time,break_minutes,notes,is_public_holiday,is_travelling,is_overseas,leave_type,project,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
          (item.work_date,rounded_start,rounded_finish,item.break_minutes,item.notes,
           int(item.is_public_holiday),int(item.is_travelling),int(item.is_overseas),item.leave_type,item.project,now,now))
        return {"id": cur.lastrowid}

@app.put("/api/shifts/{shift_id}")
def shifts_put(shift_id: int, item: ShiftIn):
    rounded_start, rounded_finish = round_shift_times(item.start_time, item.finish_time)
    with connect() as db:
        cur = db.execute("""UPDATE shifts SET work_date=?,start_time=?,finish_time=?,
          break_minutes=?,notes=?,is_public_holiday=?,is_travelling=?,is_overseas=?,leave_type=?,project=?,updated_at=? WHERE id=?""",
          (item.work_date,rounded_start,rounded_finish,item.break_minutes,item.notes,
           int(item.is_public_holiday),int(item.is_travelling),int(item.is_overseas),item.leave_type,item.project,now_iso(),shift_id))
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
def report(start: str | None = None, end: str | None = None, project: str | None = None):
    result, settings, shifts, travel = report_data(start, end)
    if project is not None:
        shifts = [s for s in shifts if (s.get("project") or "") == project]
        shift_ids = {s["id"] for s in shifts}
        travel = [t for t in travel if t.get("shift_id") in shift_ids]
        with connect() as db:
            holidays = [r["holiday_date"] for r in db.execute("SELECT holiday_date FROM holidays").fetchall()]
        result = calculate(shifts, travel, settings, holidays, [])
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
    from .payroll import minutes_between
    result, settings, shifts, travel = report_data(start, end)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["TIMESHEET"])
    writer.writerow(["Date", "Time in", "Time out", "Unpaid break (minutes)", "Total paid hours", "Rate breakdown", "Entry type", "Overseas", "Notes"])
    shift_map = {s["id"]: s for s in shifts}
    total_hours = 0.0
    rate_totals = {}
    for item in result["shifts"]:
        s = shift_map[item["id"]]
        paid_minutes = max(0, minutes_between(s["start_time"], s["finish_time"]) - int(s.get("break_minutes", 0)))
        payable_minutes = min(paid_minutes, 600) if item["is_travelling"] else paid_minutes
        total_hours += payable_minutes / 60
        breakdown = "; ".join("{}: {:.2f}h @ {:.2f}x".format(seg["category"], seg["hours"], seg["multiplier"]) for seg in item.get("segments", []))
        for seg in item.get("segments", []):
            key = "{} ({:.2f}x)".format(seg["category"], seg["multiplier"])
            rate_totals[key] = rate_totals.get(key, 0) + float(seg["hours"])
        kind = "Travel" if item["is_travelling"] else ("Work - Overseas" if item["is_overseas"] else ("Public holiday" if s.get("is_public_holiday") else "Work"))
        writer.writerow([item["date"], s["start_time"], s["finish_time"], s["break_minutes"],
                         round(payable_minutes / 60, 2), breakdown, kind, "Yes" if item["is_overseas"] else "No", item["notes"]])
    writer.writerow([])
    writer.writerow(["ALLOWANCES"])
    writer.writerow(["Allowance", "Allowance amount", "Frequency", "Basis", "Period amount"])
    for item in result.get("allowances", []):
        writer.writerow([item["name"], item.get("unit_amount", item["amount"]), item["frequency"], item["basis"], item["amount"]])
    writer.writerow([])
    writer.writerow(["PERIOD TOTALS"])
    writer.writerow(["Rate category", "Hours"])
    for category, hours_value in rate_totals.items():
        writer.writerow([category, round(hours_value, 2)])
    writer.writerow(["Total paid hours", round(total_hours, 2)])
    writer.writerow(["Total allowances", result.get("total_allowances", 0)])
    writer.writerow(["Estimated gross", result["estimated_gross"] if result["estimated_gross"] is not None else "Not configured"])
    writer.writerow(["Estimated PAYG", result.get("estimated_payg") if result.get("estimated_payg") is not None else "Not configured"])
    writer.writerow(["Total withheld", result.get("total_withheld") if result.get("total_withheld") is not None else "Not configured"])
    writer.writerow(["Estimated take-home", result.get("estimated_net") if result.get("estimated_net") is not None else "Not configured"])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=timesheet.csv"})

@app.get("/api/export.xlsx")
def export_xlsx(start: str | None = None, end: str | None = None):
    from .payroll import minutes_between

    period_result, settings, shifts, travel = report_data(start, end)
    today = date.today()
    cycle = cycle_bounds(settings.get("pay_cycle_start_date", ""),
                         settings.get("pay_cycle_type", "fortnightly"),
                         settings.get("custom_cycle_days", 14), today)
    if start and end:
        period_start, period_end = date.fromisoformat(start), date.fromisoformat(end)
    elif cycle:
        period_start, period_end = cycle
    else:
        period_start = period_end = today

    # Financial-year-to-date is measured from 1 July through the selected
    # period end, matching the Australian financial year.
    fy_start = date(period_end.year if period_end.month >= 7 else period_end.year - 1, 7, 1)
    ytd_result, _, _, _ = report_data(fy_start.isoformat(), period_end.isoformat())

    def earnings_summary(data, from_date=None, to_date=None):
        rows = {}
        def add(description, hours, base_rate, multiplier):
            if from_date and to_date:
                # The caller filters the dated item before adding it.
                pass
            hours = float(hours or 0)
            if hours <= 0:
                return
            rate = None if base_rate in (None, "") else round(float(base_rate) * float(multiplier or 1), 4)
            key = (str(description or "Other"), rate)
            row = rows.setdefault(key, {"description": key[0], "rate": rate, "hours": 0.0, "amount": 0.0, "amount_known": rate is not None})
            row["hours"] += hours
            if rate is None:
                row["amount_known"] = False
            else:
                row["amount"] += hours * rate
        for item in data.get("shifts", []):
            day = date.fromisoformat(item["date"])
            if from_date and day < from_date or to_date and day > to_date:
                continue
            for segment in item.get("segments", []):
                add(segment.get("pay_code") or segment.get("category"), segment.get("hours"),
                    item.get("base_rate"), segment.get("multiplier", 1))
        for item in data.get("travel", []):
            day = date.fromisoformat(item["date"])
            if from_date and day < from_date or to_date and day > to_date:
                continue
            add(item.get("pay_code") or item.get("category"), item.get("hours"),
                item.get("base_rate"), item.get("multiplier", 1))
        for row in rows.values():
            row["hours"] = round(row["hours"], 4)
            row["amount"] = round(row["amount"], 2) if row["amount_known"] else None
        return rows

    def allowance_summary(data):
        rows = {}
        for item in data.get("allowances", []):
            amount = float(item.get("amount", 0) or 0)
            unit_rate = item.get("unit_amount")
            rate = None if unit_rate in (None, "") else float(unit_rate)
            frequency = item.get("frequency", "")
            key = (str(item.get("name", "Allowance")), rate, frequency)
            units = (amount / rate) if rate not in (None, 0) else 1.0
            row = rows.setdefault(key, {"description": key[0], "rate": rate, "hours": 0.0, "amount": 0.0})
            row["hours"] += units
            row["amount"] += amount
        for row in rows.values():
            row["hours"] = round(row["hours"], 4)
            row["amount"] = round(row["amount"], 2)
        return rows

    period_earnings = earnings_summary(ytd_result, period_start, period_end)
    ytd_earnings = earnings_summary(ytd_result, fy_start, period_end)
    period_allowances = allowance_summary(period_result)
    ytd_allowances = allowance_summary(ytd_result)

    wb = Workbook()
    ws = wb.active
    ws.title = "Pay Summary"
    headers = ["Description", "Dates", "Hours/Units", "Rate", "Amount", "YTD Hours", "YTD Amount"]
    title_font = Font(bold=True, italic=True, size=11)
    header_font = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="E8EDF3")
    ytd_fill = PatternFill("solid", fgColor="B7E1CD")
    total_font = Font(bold=True)
    thin_grey = Side(style="thin", color="D9E0E8")
    date_label = f"{period_start:%d/%m/%Y} - {period_end:%d/%m/%Y}"

    def write_section(title, period_rows, ytd_rows):
        ws.append([title])
        title_row = ws.max_row
        ws.cell(title_row, 1).font = title_font
        ws.append(headers)
        header_row = ws.max_row
        for cell in ws[header_row]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = Border(bottom=thin_grey)
        for key in sorted(set(period_rows) | set(ytd_rows), key=lambda x: (x[0].casefold(), x[1] if x[1] is not None else -1)):
            current = period_rows.get(key, {})
            year = ytd_rows.get(key, {})
            has_period = bool(current)
            rate = current.get("rate", year.get("rate"))
            ws.append([
                key[0],
                date_label if has_period else "",
                current.get("hours", "") if has_period else "",
                rate if has_period and rate is not None else "",
                current.get("amount") if has_period else "",
                year.get("hours", ""),
                year.get("amount") if year else ""
            ])
        total_row = ws.max_row + 1
        ws.append([
            f"Total {title.lower()}",
            "",
            round(sum(x.get("hours", 0) for x in period_rows.values()), 2),
            "",
            round(sum(x.get("amount", 0) for x in period_rows.values() if x.get("amount") is not None), 2),
            round(sum(x.get("hours", 0) for x in ytd_rows.values()), 2),
            round(sum(x.get("amount", 0) for x in ytd_rows.values()), 2)
        ])
        for cell in ws[total_row]:
            cell.font = total_font
            cell.border = Border(top=thin_grey)
        return total_row

    earnings_total_row = write_section("Earnings", period_earnings, ytd_earnings)
    ws.append([])
    allowance_total_row = write_section("Allowances", period_allowances, ytd_allowances)

    ws.freeze_panes = "A3"
    widths = {"A": 32, "B": 25, "C": 15, "D": 14, "E": 16, "F": 15, "G": 17}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows(min_row=1, max_col=7):
        for cell in row:
            if cell.column == 6:
                cell.fill = ytd_fill
            if cell.column in (3, 6) and isinstance(cell.value, (int, float)):
                cell.number_format = "0.00"
            elif cell.column in (4,) and isinstance(cell.value, (int, float)):
                cell.number_format = '$0.0000'
            elif cell.column in (5, 7) and isinstance(cell.value, (int, float)):
                cell.number_format = '$#,##0.00'
            if cell.row not in (1, 2) and cell.value is not None:
                cell.alignment = Alignment(vertical="center")
    for row in (earnings_total_row, allowance_total_row):
        for cell in ws[row]:
            cell.fill = PatternFill("solid", fgColor="E8EDF3")
    for row in ws.iter_rows():
        ws.row_dimensions[row[0].row].height = 20

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=timesheet.xlsx"})

@app.get("/api/health")
def health():
    return {"status":"ok","application":"HATimeSheets","version":"0.1.53"}