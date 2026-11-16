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

def calculate(shifts, travel, settings, holidays=None, allowance_entries=None):
    """Calculate pay categories using weekly thresholds and an optional daily roster."""
    holidays = set(holidays or [])
    allowance_entries = allowance_entries or []
    week_start = int(settings.get("week_start_day", 0))
    tiers = sorted(settings.get("overtime_tiers", []), key=lambda x: float(x.get("after_hours", 0)))
    travel_tiers = sorted(settings.get("travel_rules", []), key=lambda x: float(x.get("after_hours", 0)))
    penalties = [p for p in settings.get("penalty_rules", []) if p.get("enabled", True)]
    rate = settings.get("base_rate")
    schedule = settings.get("normal_hours_schedule")
    loading = float(settings.get("travel_loading", 0.3))
    result, normalized, by_week = [], [], {}

    for s in shifts:
        d = date.fromisoformat(s["work_date"])
        mins = max(0, minutes_between(s["start_time"], s["finish_time"]) - int(s.get("break_minutes", 0)))
        key = weekly_bucket_start(d, week_start).isoformat()
        travelling = bool(s.get("is_travelling", False))
        normalized.append((s, d, mins, key, travelling))
        if not travelling:
            by_week[key] = by_week.get(key, 0) + mins

    def tier_at(absolute_minutes):
        multiplier, label = 1.0, "Ordinary"
        for tier in tiers:
            if absolute_minutes >= float(tier.get("after_hours", 0)) * 60:
                multiplier = float(tier.get("multiplier", 1))
                label = tier.get("label", "Overtime")
        return multiplier, label

    def in_roster(moment):
        if schedule is None:
            return True
        rule = next((x for x in schedule if int(x.get("day", -1)) == moment.weekday()), None)
        if not rule or not rule.get("enabled", False):
            return False
        begin = datetime.strptime(rule.get("start_time", "00:00"), "%H:%M").time()
        finish = datetime.strptime(rule.get("finish_time", "00:00"), "%H:%M").time()
        clock = moment.time()
        return begin <= clock < finish if finish > begin else (clock >= begin or clock < finish)

    for s, d, mins, key, travelling in normalized:
        earlier = sum(m for other, od, m, wk, is_travel in normalized
                      if wk == key and not is_travel and
                      (od < d or (od == d and other["id"] < s["id"])))
        earlier_today = sum(m for other, od, m, wk, is_travel in normalized
                            if od == d and not is_travel and other["id"] < s["id"])
        segments = []
        payable_minutes = min(mins, 600) if travelling else mins
        if travelling:
            base, _ = tier_at(earlier)
            if payable_minutes:
                segments = [{"category": "Travel", "hours": round(payable_minutes / 60, 4),
                             "multiplier": base + loading}]
        else:
            # The entry model stores break duration, not its timestamp; deduct it at shift end.
            start_dt = datetime.combine(d, datetime.strptime(s["start_time"], "%H:%M").time())
            for cursor in range(mins):
                moment = start_dt + timedelta(minutes=cursor)
                base, label = tier_at(earlier + cursor)
                overseas = bool(s.get("is_overseas"))
                outside = schedule is not None and not in_roster(moment)
                if overseas:
                    # Overseas ordinary time is based on a 10 paid-hour day,
                    # not the configured local start/finish roster. Daily OT
                    # uses at least 1.5x; weekly tiers can increase that rate.
                    daily_overtime = earlier_today + cursor >= 600
                    multiplier = max(base, 1.5 if daily_overtime else 1.0)
                else:
                    multiplier = max(base, 1.5) if outside else base
                category = ("Overseas" if overseas else
                            "Travel" if s.get("is_travelling") else
                            "Out-of-hours" if outside and base < 1.5 else label)
                if s.get("is_travelling") or s.get("is_overseas"):
                    multiplier += loading
                if segments and segments[-1]["category"] == category and abs(segments[-1]["multiplier"] - multiplier) < 1e-8:
                    segments[-1]["minutes"] += 1
                else:
                    segments.append({"category": category, "minutes": 1, "multiplier": multiplier})
            for seg in segments:
                seg["hours"] = round(seg.pop("minutes") / 60, 4)

        applicable = []
        is_holiday = bool(s.get("is_public_holiday")) or d.isoformat() in holidays
        for rule in ([] if travelling else penalties):
            cond = rule.get("condition")
            match = ((cond == "day_of_week" and d.weekday() == int(rule.get("day", -1))) or
                     (cond == "public_holiday" and is_holiday))
            if match and rule.get("scope", "work") in ("work", "both"):
                applicable.append(rule)
        if applicable:
            replacements = [x for x in applicable if x.get("mode", "replace") == "replace"]
            additions = [x for x in applicable if x.get("mode") == "add"]
            if replacements:
                chosen = max(replacements, key=lambda x: float(x.get("multiplier", 1)))
                segments = [{"category": chosen["name"], "hours": round(mins / 60, 4),
                             "multiplier": float(chosen.get("multiplier", 1))}]
            for rule in additions:
                segments.append({"category": rule["name"] + " (additional)",
                                 "hours": round(mins / 60, 4),
                                 "multiplier": float(rule.get("multiplier", 0))})

        earnings = None if rate in (None, "") else round(sum(x["hours"] * float(rate) * x["multiplier"] for x in segments), 2)
        result.append({"id": s["id"], "date": d.isoformat(), "hours": round(mins / 60, 4),
                       "payable_hours": round(payable_minutes / 60, 4),
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
        multiplier, label = 1.0 + loading, "Travel ordinary"
        for tier in travel_tiers:
            if position >= float(tier.get("after_hours", 0)) * 60:
                multiplier, label = float(tier.get("multiplier", 1)) + loading, tier.get("label", "Travel")
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

    # Hourly allowances apply to paid work and paid travel hours. Weekly
    # allowances apply once per work week; fixed allowances apply per work shift.
    allowance_breakdown = []
    allowance_total = 0.0
    work_weeks = {key for s, d, mins, key, travelling in normalized if not travelling and mins > 0}
    ordinary_work_hours = sum(x["hours"] for x in result if not x["is_travelling"])
    allowance_hours = ordinary_work_hours + total_travel
    for rule in settings.get("allowances", []):
        amount = float(rule.get("amount", 0) or 0)
        frequency = rule.get("frequency", "weekly")
        if amount <= 0:
            continue
        if frequency == "hourly":
            value = allowance_hours * amount
            basis = f"{allowance_hours:.2f} work and travel hours"
        elif frequency == "fixed":
            count = sum(1 for x in result if not x["is_travelling"] and x["hours"] > 0)
            value = count * amount
            basis = f"{count} work shifts"
        else:
            count = len(work_weeks)
            value = count * amount
            basis = f"{count} work weeks"
        if value:
            allowance_breakdown.append({"name": rule.get("name", "Allowance"),
                                        "frequency": frequency, "basis": basis,
                                        "amount": round(value, 2)})
            allowance_total += value

    for entry in allowance_entries:
        value = float(entry.get("amount", 0) or 0)
        if value:
            allowance_breakdown.append({"name": entry.get("name", "Allowance entry"),
                                        "frequency": "entry", "basis": entry.get("entry_date", ""),
                                        "amount": round(value, 2)})
            allowance_total += value

    return {"shifts": result, "travel": travel_result, "total_work_hours": total_hours,
            "total_travel_hours": total_travel, "base_rate_configured": earnings_known,
            "allowances": allowance_breakdown, "total_allowances": round(allowance_total, 2),
            "estimated_gross": round(work_pay + travel_pay + allowance_total, 2) if earnings_known else None}