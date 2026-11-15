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

    def test_base_rate_is_optional(self):
        settings = {"base_rate": None, "week_start_day": 0, "overtime_tiers": [], "travel_rules": [], "penalty_rules": []}
        shift = {"id":1,"work_date":"2026-11-16","start_time":"05:30","finish_time":"16:00","break_minutes":30,"notes":""}
        result = calculate([shift], [], settings)
        self.assertEqual(result["total_work_hours"], 10)
        self.assertIsNone(result["estimated_gross"])

if __name__ == "__main__":
    unittest.main()