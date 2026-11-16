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
            base, tier_label = tier_at(earlier)
            if payable_minutes:
                travel_kind = "OT" if "overtime" in str(tier_label).lower() or str(tier_label).lower().startswith("ot") else "Ordinary"
                segments = [{"category": "Travel", "pay_code": f"Travel-OTH {travel_kind} {base + loading:.1f}",
                             "hours": round(payable_minutes / 60, 4), "multiplier": base + loading}]
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
                if overseas:
                    travel_kind = "OT" if daily_overtime or "overtime" in str(label).lower() or str(label).lower().startswith("ot") else "Ordinary"
                    pay_code = f"Travel-OTH {travel_kind} {multiplier:.1f}"
                elif category == "Out-of-hours":
                    pay_code = "Ordinary 1.5"
                elif "public holiday" in str(label).lower():
                    pay_code = "Public Holiday"
                elif category == "Ordinary" and multiplier <= 1.0:
                    pay_code = "Ordinary 1.0"
                elif "ordinary" in str(label).lower() and multiplier <= 1.5:
                    pay_code = "Ordinary 1.5"
                elif multiplier >= 1.99:
                    pay_code = "Overtime 2.0"
                elif multiplier >= 1.49:
                    pay_code = "Overtime 1.5"
                else:
                    pay_code = str(label)
                if segments and segments[-1]["category"] == category and segments[-1].get("pay_code") == pay_code and abs(segments[-1]["multiplier"] - multiplier) < 1e-8:
                    segments[-1]["minutes"] += 1
                else:
                    segments.append({"category": category, "pay_code": pay_code, "minutes": 1, "multiplier": multiplier})
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
                code = "Public Holiday" if any(x.get("condition") == "public_holiday" for x in replacements) else str(chosen["name"])
                segments = [{"category": chosen["name"], "pay_code": code, "hours": round(mins / 60, 4),
                             "multiplier": float(chosen.get("multiplier", 1))}]
            for rule in additions:
                segments.append({"category": rule["name"] + " (additional)",
                                 "pay_code": str(rule["name"]),
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
        travel_kind = "OT" if "overtime" in str(label).lower() or str(label).lower().startswith("ot") else "Ordinary"
        pay_code = f"Travel-OTH {travel_kind} {multiplier:.1f}"
        earnings = None if rate in (None, "") else round((mins / 60) * float(rate) * multiplier, 2)
        travel_result.append({"id": t["id"], "date": d.isoformat(), "hours": round(mins / 60, 4),
                              "category": label, "pay_code": pay_code, "multiplier": multiplier,
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
            basis = f"{allowance_hours:.2f} Hours"
        elif frequency == "fixed":
            count = sum(1 for x in result if not x["is_travelling"] and x["hours"] > 0)
            value = count * amount
            basis = "Per Shift"
        else:
            count = len(work_weeks)
            value = count * amount
            basis = "Per Week"
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

    estimated_gross = round(work_pay + travel_pay + allowance_total, 2) if earnings_known else None
    weekly = {}
    def week_record(day_text):
        day = date.fromisoformat(day_text)
        start = weekly_bucket_start(day, week_start)
        return weekly.setdefault(start.isoformat(), {"start": start, "gross": 0.0})
    if earnings_known:
        for item in result:
            if item["estimated_earnings"] is not None:
                week_record(item["date"])["gross"] += item["estimated_earnings"]
        for item in travel_result:
            if item["estimated_earnings"] is not None:
                week_record(item["date"])["gross"] += item["estimated_earnings"]
        for rule in settings.get("allowances", []):
            amount = float(rule.get("amount", 0) or 0)
            if amount <= 0:
                continue
            frequency = rule.get("frequency", "weekly")
            if frequency == "hourly":
                hours_by_week = {}
                for item in result:
                    paid = float(item["payable_hours"] if item["is_travelling"] else item["hours"])
                    if paid:
                        start = weekly_bucket_start(date.fromisoformat(item["date"]), week_start)
                        hours_by_week[start.isoformat()] = hours_by_week.get(start.isoformat(), 0) + paid
                for item in travel_result:
                    start = weekly_bucket_start(date.fromisoformat(item["date"]), week_start)
                    hours_by_week[start.isoformat()] = hours_by_week.get(start.isoformat(), 0) + float(item["hours"])
                for key, hours_value in hours_by_week.items():
                    weekly.setdefault(key, {"start": date.fromisoformat(key), "gross": 0.0})["gross"] += hours_value * amount
            elif frequency == "fixed":
                counts = {}
                for item in result:
                    if not item["is_travelling"] and item["hours"] > 0:
                        start = weekly_bucket_start(date.fromisoformat(item["date"]), week_start)
                        counts[start.isoformat()] = counts.get(start.isoformat(), 0) + 1
                for key, count in counts.items():
                    weekly.setdefault(key, {"start": date.fromisoformat(key), "gross": 0.0})["gross"] += count * amount
            else:
                for key in work_weeks:
                    weekly.setdefault(key, {"start": date.fromisoformat(key), "gross": 0.0})["gross"] += amount
    for entry in allowance_entries:
        amount = float(entry.get("amount", 0) or 0)
        if amount:
            start = weekly_bucket_start(date.fromisoformat(entry["entry_date"]), week_start)
            weekly.setdefault(start.isoformat(), {"start": start, "gross": 0.0})["gross"] += amount
    payg_weeks = []
    for key, item in sorted(weekly.items()):
        week_end = item["start"] + timedelta(days=6)
        fy_start = week_end.year if week_end.month >= 7 else week_end.year - 1
        fy_label = f"{fy_start}-{str(fy_start + 1)[-2:]}"
        # Combine annual bracket editor data with the ATO weekly coefficient
        # table. Weekly coefficients take precedence because they include Medicare.
        year_settings = {}
        year_settings.update(settings.get("payg_annual_years", {}).get(fy_label) or {})
        year_settings.update(settings.get("payg_years", {}).get(fy_label) or {})
        withholding = calculate_weekly_payg(
            item["gross"], year_settings,
            bool(settings.get("payg_tax_free_threshold", True)),
            False,
            float(settings.get("payg_extra_withholding", 0) or 0)
        ) if earnings_known and year_settings else None
        payg_weeks.append({"week_start": key, "week_end": week_end.isoformat(),
            "financial_year": fy_label, "gross": round(item["gross"], 2),
            "payg": withholding["payg"] if withholding else None,
            "help": withholding["help"] if withholding else None,
            "extra": withholding["extra"] if withholding else None,
            "total_withheld": withholding["total_withheld"] if withholding else None,
            "net": withholding["net"] if withholding else None})
    withholding_known = bool(payg_weeks) and all(x["total_withheld"] is not None for x in payg_weeks)
    total_payg = round(sum(x["payg"] for x in payg_weeks), 2) if withholding_known else None
    total_help = round(sum(x["help"] for x in payg_weeks), 2) if withholding_known else None
    total_extra = round(sum(x["extra"] for x in payg_weeks), 2) if withholding_known else None
    total_withheld = round(sum(x["total_withheld"] for x in payg_weeks), 2) if withholding_known else None
    net_pay = round(estimated_gross - total_withheld, 2) if estimated_gross is not None and withholding_known else None
    return {"shifts": result, "travel": travel_result, "total_work_hours": total_hours,
            "total_travel_hours": total_travel, "base_rate_configured": earnings_known,
            "allowances": allowance_breakdown, "total_allowances": round(allowance_total, 2),
            "estimated_gross": estimated_gross, "payg_weeks": payg_weeks,
            "estimated_payg": total_payg, "estimated_help": total_help,
            "payg_extra_withholding": total_extra, "total_withheld": total_withheld,
            "estimated_net": net_pay, "payg_configured": bool(settings.get("payg_years"))}

def calculate_weekly_payg(gross, year_settings, claim_tax_free_threshold=True,
                          help_enabled=False, extra_withholding=0):
    """Calculate weekly PAYG using ATO weekly coefficients where available.

    The ATO Scale 1 and Scale 2 coefficients include the standard Medicare
    levy. Annual resident brackets are retained as a fallback for years where
    weekly coefficients have not been configured.
    """
    if not year_settings:
        return None
    earnings = max(0.0, float(gross))
    extra = _round_dollar(max(0, float(extra_withholding or 0)))
    # ATO weekly withholding uses earnings with cents ignored (represented as
    # the whole-dollar amount plus 0.99 in the published formula).
    scale = "scale2" if claim_tax_free_threshold else "scale1"
    weekly_brackets = year_settings.get(scale) or []
    if weekly_brackets:
        x = int(earnings) + 0.99
        payg = _round_dollar(_coefficient_withholding(x, weekly_brackets))
        help_amount = 0
        if help_enabled:
            help_scale = "help_scale2" if claim_tax_free_threshold else "help_scale1"
            help_amount = _round_dollar(_coefficient_withholding(x, year_settings.get(help_scale, [])))
        total = payg + help_amount + extra
        return {"payg": payg, "help": help_amount, "extra": extra,
                "total_withheld": total, "net": round(earnings - total, 2)}

    brackets = year_settings.get("resident_brackets") or year_settings.get("brackets")
    if brackets:
        annual_income = earnings * 52
        annual_tax = calculate_annual_resident_tax(annual_income, brackets)
        payg = _round_dollar(annual_tax / 52)
        total = payg + extra
        return {"payg": payg, "help": 0, "extra": extra,
                "total_withheld": total, "net": round(earnings - total, 2)}
    return None


def calculate_annual_resident_tax(annual_income, brackets):
    income = max(0.0, float(annual_income))
    ordered = sorted(brackets, key=lambda row: float(row.get("lower", 0)))
    applicable = None
    for bracket in ordered:
        if income >= float(bracket.get("lower", 0)):
            applicable = bracket
        else:
            break
    if applicable is None:
        return 0.0
    return max(0.0, float(applicable.get("base_tax", 0)) +
               (income - float(applicable.get("lower", 0))) * float(applicable.get("rate", 0)))



def _coefficient_withholding(x, brackets):
    for bracket in brackets:
        upper = bracket.get("upper")
        if upper is None or x < float(upper):
            a = float(bracket.get("a", 0))
            b = float(bracket.get("b", 0))
            return max(0.0, a * x - b)
    return 0.0


def _round_dollar(value):
    import math
    return int(math.floor(float(value) + 0.5))
