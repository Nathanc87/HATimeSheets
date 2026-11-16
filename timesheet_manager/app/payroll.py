from datetime import date, datetime, time, timedelta

def minutes_between(start, finish):
    a = datetime.strptime(start, "%H:%M")
    b = datetime.strptime(finish, "%H:%M")
    if b <= a:
        b += timedelta(days=1)
    return int((b - a).total_seconds() // 60)

def cycle_bounds(anchor_text, cycle_type, custom_days, target):
    if not anchor_text:
        return None
    anchor = date.fromisoformat(anchor_text)
    if cycle_type == "weekly":
        days = 7
    elif cycle_type == "fortnightly":
        days = 14
    elif cycle_type == "monthly":
        # Calendar month cycle anchored on the configured day.
        from calendar import monthrange
        months = (target.year - anchor.year) * 12 + target.month - anchor.month
        start_month = anchor.month + months
        year = anchor.year + (start_month - 1) // 12
        month = (start_month - 1) % 12 + 1
        day = min(anchor.day, monthrange(year, month)[1])
        start = date(year, month, day)
        if target < start:
            months -= 1
            start_month = anchor.month + months
            year = anchor.year + (start_month - 1) // 12
            month = (start_month - 1) % 12 + 1
            start = date(year, month, min(anchor.day, monthrange(year, month)[1]))
        next_month = start.month + 1
        next_year = start.year + (next_month - 1) // 12
        next_month = (next_month - 1) % 12 + 1
        end = date(next_year, next_month, min(anchor.day, monthrange(next_year, next_month)[1])) - timedelta(days=1)
        return start, end
    else:
        days = max(1, int(custom_days or 14))
    delta = (target - anchor).days
    offset = delta % days
    start = target - timedelta(days=offset)
    return start, start + timedelta(days=days - 1)

def weekly_bucket_start(day, week_start):
    return day - timedelta(days=(day.weekday() - int(week_start)) % 7)

def calculate(shifts, travel, settings, holidays=None):
    """Calculate transparent estimated categories.

    Work overtime thresholds are applied to paid work minutes in each configured
    overtime week. Travel is classified against the same weekly work-hour
    progression by default. Special day/public holiday rules replace the base
    multiplier when configured to do so.
    """
    holidays = set(holidays or [])
    week_start = int(settings.get("week_start_day", 0))
    tiers = sorted(settings.get("overtime_tiers", []), key=lambda x: float(x.get("after_hours", 0)))
    travel_tiers = sorted(settings.get("travel_rules", []), key=lambda x: float(x.get("after_hours", 0)))
    penalties = [p for p in settings.get("penalty_rules", []) if p.get("enabled", True)]
    rate = settings.get("base_rate")
    result = []
    by_week = {}

    normalized = []
    for s in shifts:
        d = date.fromisoformat(s["work_date"])
        mins = max(0, minutes_between(s["start_time"], s["finish_time"]) - int(s.get("break_minutes", 0)))
        key = weekly_bucket_start(d, week_start).isoformat()
        travelling = bool(s.get("is_travelling", False))
        normalized.append((s, d, mins, key, travelling))
        # Travel-only entries use the fixed travel rule and do not consume overtime thresholds.
        if not travelling:
            by_week[key] = by_week.get(key, 0) + mins

    for s, d, mins, key, travelling in normalized:
        # Travel-only entries are excluded from weekly work/overtime progression.
        earlier = sum(m for other, od, m, wk, is_travel in normalized
                      if wk == key and not is_travel and
                      (od < d or (od == d and other["id"] < s["id"])))
        segments = []
        if travelling:
            payable_minutes = min(mins, 600)
            segments = ([{"category": "Travel", "hours": round(payable_minutes / 60, 4),
                          "multiplier": 1.3}] if payable_minutes else [])
        cursor = 0
        remaining = 0 if travelling else mins
        while remaining > 0:
            absolute = earlier + cursor
            multiplier = 1.0
            label = "Ordinary"
            for tier in tiers:
                threshold = float(tier.get("after_hours", 0)) * 60
                if absolute >= threshold:
                    multiplier = float(tier.get("multiplier", 1))
                    label = tier.get("label", "Overtime")
            next_thresholds = [float(t.get("after_hours", 0)) * 60 for t in tiers
                               if float(t.get("after_hours", 0)) * 60 > absolute]
            chunk = min(remaining, (min(next_thresholds) - absolute) if next_thresholds else remaining)
            if chunk <= 0:
                chunk = remaining
            segments.append({"category": label, "hours": round(chunk / 60, 4),
                             "multiplier": multiplier})
            cursor += chunk
            remaining -= chunk

        applicable = []
        is_holiday = bool(s.get("is_public_holiday")) or d.isoformat() in holidays
        for p in ([] if travelling else penalties):
            cond = p.get("condition")
            match = ((cond == "day_of_week" and d.weekday() == int(p.get("day", -1))) or
                     (cond == "public_holiday" and is_holiday))
            if match and p.get("scope", "work") in ("work", "both"):
                applicable.append(p)
        if applicable:
            # Multiple replacement penalties use the highest multiplier; additive
            # rules are separately shown as additions.
            replacements = [p for p in applicable if p.get("mode", "replace") == "replace"]
            additions = [p for p in applicable if p.get("mode") == "add"]
            if replacements:
                chosen = max(replacements, key=lambda p: float(p.get("multiplier", 1)))
                segments = [{"category": chosen["name"], "hours": round(mins / 60, 4),
                             "multiplier": float(chosen.get("multiplier", 1))}]
            for p in additions:
                segments.append({"category": p["name"] + " (additional)",
                                 "hours": round(mins / 60, 4),
                                 "multiplier": float(p.get("multiplier", 0))})

        hours = round(mins / 60, 4)
        payable_hours = round(min(mins, 600) / 60, 4) if travelling else hours
        earnings = None if rate in (None, "") else round(sum(x["hours"] * float(rate) * x["multiplier"] for x in segments), 2)
        result.append({"id": s["id"], "date": d.isoformat(), "hours": hours,
                       "payable_hours": payable_hours,
                       "is_travelling": travelling, "is_overseas": bool(s.get("is_overseas", False)),
                       "weekly_hours_including_shift": round((earlier + (0 if travelling else mins)) / 60, 4),
                       "segments": segments, "estimated_earnings": earnings,
                       "notes": s.get("notes", "")})

    travel_result = []
    for t in travel:
        d = date.fromisoformat(t["travel_date"])
        mins = max(0, minutes_between(t["start_time"], t["finish_time"]) - int(t.get("break_minutes", 0)))
        key = weekly_bucket_start(d, week_start).isoformat()
        work_before = sum(m for s, sd, m, wk, is_travel in normalized if wk == key and sd <= d and not is_travel)
        earlier_travel = sum(minutes_between(x["start_time"], x["finish_time"]) - int(x.get("break_minutes", 0))
                             for x in travel if x["travel_date"] < t["travel_date"] and
                             weekly_bucket_start(date.fromisoformat(x["travel_date"]), week_start).isoformat() == key)
        position = max(0, work_before - mins + earlier_travel)
        multiplier, label = 1.3, "Travel ordinary"
        for tier in travel_tiers:
            if position >= float(tier.get("after_hours", 0)) * 60:
                multiplier, label = float(tier.get("multiplier", 1)), tier.get("label", "Travel")
        earnings = None if rate in (None, "") else round((mins / 60) * float(rate) * multiplier, 2)
        travel_result.append({"id": t["id"], "date": d.isoformat(), "hours": round(mins / 60, 4),
                              "category": label, "multiplier": multiplier,
                              "estimated_earnings": earnings, "notes": t.get("notes", "")})

    total_hours = round(sum(x["hours"] for x in result if not x["is_travelling"]), 2)
    total_travel = round(sum(x["payable_hours"] for x in result if x["is_travelling"]) +
                         sum(x["hours"] for x in travel_result), 2)
    earnings_known = rate not in (None, "")
    work_pay = sum(x["estimated_earnings"] or 0 for x in result)
    travel_pay = sum(x["estimated_earnings"] or 0 for x in travel_result)
    return {"shifts": result, "travel": travel_result, "total_work_hours": total_hours,
            "total_travel_hours": total_travel, "base_rate_configured": earnings_known,
            "estimated_gross": round(work_pay + travel_pay, 2) if earnings_known else None}