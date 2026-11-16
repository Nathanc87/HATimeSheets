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

    def test_travelling_entry_is_capped_at_10_hours_and_1_3x(self):
        settings = {"base_rate": 40, "week_start_day": 0, "overtime_tiers": [
            {"after_hours": 0, "multiplier": 1.0, "label": "Ordinary"},
            {"after_hours": 38, "multiplier": 2.0, "label": "OT"}],
            "travel_rules": [], "penalty_rules": [
                {"name": "Sunday", "enabled": True, "condition": "day_of_week",
                 "day": 6, "scope": "work", "multiplier": 3.0, "mode": "replace"}]}
        shift = {"id": 1, "work_date": "2026-11-22", "start_time": "05:00",
                 "finish_time": "18:00", "break_minutes": 0, "is_travelling": True,
                 "is_overseas": True, "notes": ""}
        result = calculate([shift], [], settings)
        entry = result["shifts"][0]
        self.assertEqual(entry["hours"], 13)
        self.assertEqual(entry["payable_hours"], 10)
        self.assertEqual(entry["segments"], [{"category": "Travel", "hours": 10.0, "multiplier": 1.3}])
        self.assertEqual(entry["estimated_earnings"], 520)
        self.assertTrue(entry["is_overseas"])
        self.assertEqual(result["total_work_hours"], 0)
        self.assertEqual(result["total_travel_hours"], 10)

    def test_overseas_flag_does_not_change_normal_pay(self):
        settings = {"base_rate": 40, "week_start_day": 0, "overtime_tiers": [],
                    "travel_rules": [], "penalty_rules": []}
        shift = {"id": 1, "work_date": "2026-11-16", "start_time": "05:30",
                 "finish_time": "16:00", "break_minutes": 30, "is_overseas": True, "notes": ""}
        result = calculate([shift], [], settings)
        self.assertEqual(result["total_work_hours"], 10)
        self.assertEqual(result["shifts"][0]["estimated_earnings"], 400)

    def test_configured_allowances_are_included_in_gross(self):
        settings = {"base_rate": 40, "week_start_day": 0, "overtime_tiers": [],
                    "travel_rules": [], "penalty_rules": [],
                    "allowances": [
                        {"name": "Site", "amount": 2, "frequency": "hourly"},
                        {"name": "Weekly tool", "amount": 50, "frequency": "weekly"},
                        {"name": "Meal", "amount": 15, "frequency": "fixed"}]}
        shifts = [
            {"id": 1, "work_date": "2026-11-16", "start_time": "05:30", "finish_time": "16:00", "break_minutes": 30},
            {"id": 2, "work_date": "2026-11-17", "start_time": "05:30", "finish_time": "16:00", "break_minutes": 30},
            {"id": 3, "work_date": "2026-11-18", "start_time": "05:30", "finish_time": "16:00", "break_minutes": 30, "is_travelling": True}
        ]
        result = calculate(shifts, [], settings, [], [{"entry_date":"2026-11-16","name":"Reimbursement","amount":25}])
        self.assertEqual(result["total_allowances"], 130)
        self.assertEqual(result["estimated_gross"], 930)
        self.assertEqual(len(result["allowances"]), 4)

    def test_allowances_are_reported_without_base_rate_but_gross_is_unknown(self):
        settings = {"base_rate": None, "week_start_day": 0, "overtime_tiers": [],
                    "travel_rules": [], "penalty_rules": [],
                    "allowances": [{"name":"Weekly","amount":30,"frequency":"weekly"}]}
        shift = {"id":1,"work_date":"2026-11-16","start_time":"05:30","finish_time":"16:00","break_minutes":30}
        result = calculate([shift], [], settings)
        self.assertEqual(result["total_allowances"], 30)
        self.assertIsNone(result["estimated_gross"])

if __name__ == "__main__":
    unittest.main()