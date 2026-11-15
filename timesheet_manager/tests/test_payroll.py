import unittest
from datetime import date
from app.payroll import minutes_between, weekly_bucket_start, calculate

class PayrollTests(unittest.TestCase):
    def test_normal_shift_minus_break(self):
        self.assertEqual(minutes_between("05:30", "16:00") - 30, 600)

    def test_overnight_time(self):
        self.assertEqual(minutes_between("22:00", "06:00"), 480)

    def test_week_start_monday(self):
        self.assertEqual(weekly_bucket_start(date(2026, 11, 18), 0), date(2026, 11, 16))

    def test_weekly_overtime_38_and_44_thresholds(self):
        settings = {"base_rate": 40, "week_start_day": 0,
                    "overtime_tiers": [
                        {"after_hours": 38, "multiplier": 1.5, "label": "OT1"},
                        {"after_hours": 44, "multiplier": 2.0, "label": "OT2"}],
                    "travel_rules": [], "penalty_rules": []}
        shifts = []
        for i, day in enumerate(["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"], 1):
            shifts.append({"id": i, "work_date": day, "start_time": "05:30",
                           "finish_time": "16:00", "break_minutes": 30, "notes": ""})
        result = calculate(shifts, [], settings)
        categories = {}
        for shift in result["shifts"]:
            for segment in shift["segments"]:
                categories[segment["category"]] = categories.get(segment["category"], 0) + segment["hours"]
        self.assertEqual(categories["Ordinary"], 38)
        self.assertEqual(categories["OT1"], 6)
        self.assertEqual(categories["OT2"], 6)

    def test_sunday_penalty_replaces_normal_rate(self):
        settings = {"base_rate": 40, "week_start_day": 0, "overtime_tiers": [],
                    "travel_rules": [], "penalty_rules": [
                        {"name": "Sunday", "enabled": True, "condition": "day_of_week",
                         "day": 6, "scope": "work", "multiplier": 2.0, "mode": "replace"}]}
        shift = {"id": 1, "work_date": "2026-11-22", "start_time": "05:30",
                 "finish_time": "16:00", "break_minutes": 30, "notes": ""}
        result = calculate([shift], [], settings)
        self.assertEqual(result["shifts"][0]["segments"][0]["category"], "Sunday")
        self.assertEqual(result["shifts"][0]["estimated_earnings"], 800)

    def test_base_rate_is_optional(self):
        settings = {"base_rate": None, "week_start_day": 0, "overtime_tiers": [], "travel_rules": [], "penalty_rules": []}
        shift = {"id":1,"work_date":"2026-11-16","start_time":"05:30","finish_time":"16:00","break_minutes":30,"notes":""}
        result = calculate([shift], [], settings)
        self.assertEqual(result["total_work_hours"], 10)
        self.assertIsNone(result["estimated_gross"])

if __name__ == "__main__":
    unittest.main()