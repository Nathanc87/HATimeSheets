import unittest
from datetime import date
from app.payroll import minutes_between, weekly_bucket_start, calculate, calculate_weekly_payg

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

    def test_weekly_bands_include_ordinary_and_overtime_15(self):
        settings = {"base_rate": 40, "week_start_day": 0, "overtime_tiers": [
                        {"after_hours": 0, "multiplier": 1.0, "label": "Ordinary"},
                        {"after_hours": 38, "multiplier": 1.5, "label": "Ordinary 1.5x"},
                        {"after_hours": 40, "multiplier": 1.5, "label": "Overtime 1.5x"},
                        {"after_hours": 44, "multiplier": 2.0, "label": "Overtime 2.0x"}],
                    "travel_loading": 0.3, "penalty_rules": []}
        shifts = [{"id": i, "work_date": "2026-11-"+str(16+i), "start_time": "00:00",
                   "finish_time": "10:00", "break_minutes": 0} for i in range(1, 6)]
        result = calculate(shifts, [], settings)
        totals = {}
        for shift in result["shifts"]:
            for seg in shift["segments"]:
                totals[seg["category"]] = totals.get(seg["category"], 0) + seg["hours"]
        self.assertEqual(totals["Ordinary"], 38)
        self.assertEqual(totals["Ordinary 1.5x"], 2)
        self.assertEqual(totals["Overtime 1.5x"], 4)
        self.assertEqual(totals["Overtime 2.0x"], 6)

    def test_work_outside_roster_gets_minimum_15(self):
        settings = {"base_rate": 40, "week_start_day": 0,
                    "normal_hours_schedule": [{"day": 0, "enabled": True, "start_time": "05:30", "finish_time": "16:00"}],
                    "overtime_tiers": [{"after_hours": 0, "multiplier": 1.0, "label": "Ordinary"}],
                    "travel_loading": 0.3, "penalty_rules": []}
        shift = {"id": 1, "work_date": "2026-11-16", "start_time": "04:30",
                 "finish_time": "07:30", "break_minutes": 0}
        result = calculate([shift], [], settings)
        self.assertEqual([(x["category"], x["hours"], x["multiplier"]) for x in result["shifts"][0]["segments"]],
                         [("Out-of-hours", 1.0, 1.5), ("Ordinary", 2.0, 1.0)])

    def test_overseas_loading_adds_point_three(self):
        settings = {"base_rate": 40, "week_start_day": 0, "normal_hours_schedule": [],
                    "overtime_tiers": [{"after_hours": 0, "multiplier": 1.5, "label": "OT"}],
                    "travel_loading": 0.3, "penalty_rules": []}
        shift = {"id": 1, "work_date": "2026-11-16", "start_time": "00:00",
                 "finish_time": "02:00", "break_minutes": 0, "is_overseas": True}
        result = calculate([shift], [], settings)
        self.assertEqual(result["shifts"][0]["segments"][0]["category"], "Overseas")
        self.assertEqual(result["shifts"][0]["segments"][0]["multiplier"], 1.8)
        self.assertEqual(result["shifts"][0]["estimated_earnings"], 144)

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
        self.assertEqual(entry["segments"], [{"category": "Travel", "pay_code": "Travel-OTH Ordinary 1.3", "hours": 10.0, "multiplier": 1.3}])
        self.assertEqual(entry["estimated_earnings"], 520)
        self.assertTrue(entry["is_overseas"])
        self.assertEqual(result["total_work_hours"], 0)
        self.assertEqual(result["total_travel_hours"], 10)

    def test_overseas_ignores_roster_and_pays_first_10_hours_at_1_3(self):
        settings = {"base_rate": 40, "week_start_day": 0,
                    "normal_hours_schedule": [{"day": 0, "enabled": True, "start_time": "05:30", "finish_time": "16:00"}],
                    "overtime_tiers": [{"after_hours": 38, "multiplier": 1.5, "label": "OT1"},
                                       {"after_hours": 44, "multiplier": 2.0, "label": "OT2"}],
                    "travel_loading": 0.3, "travel_rules": [], "penalty_rules": []}
        shift = {"id": 1, "work_date": "2026-11-16", "start_time": "20:00",
                 "finish_time": "06:30", "break_minutes": 30, "is_overseas": True, "notes": ""}
        result = calculate([shift], [], settings)
        self.assertEqual(result["total_work_hours"], 10)
        self.assertEqual(result["shifts"][0]["segments"], [
            {"category": "Overseas", "pay_code": "Travel-OTH Ordinary 1.3", "hours": 10.0, "multiplier": 1.3}])
        self.assertEqual(result["shifts"][0]["estimated_earnings"], 520)

    def test_overseas_daily_overtime_after_10_hours(self):
        settings = {"base_rate": 40, "week_start_day": 0,
                    "normal_hours_schedule": [{"day": 0, "enabled": True, "start_time": "05:30", "finish_time": "16:00"}],
                    "overtime_tiers": [{"after_hours": 38, "multiplier": 1.5, "label": "OT1"},
                                       {"after_hours": 44, "multiplier": 2.0, "label": "OT2"}],
                    "travel_loading": 0.3, "travel_rules": [], "penalty_rules": []}
        shift = {"id": 1, "work_date": "2026-11-16", "start_time": "20:00",
                 "finish_time": "07:00", "break_minutes": 0, "is_overseas": True, "notes": ""}
        result = calculate([shift], [], settings)
        self.assertEqual([(x["hours"], x["multiplier"]) for x in result["shifts"][0]["segments"]],
                         [(10.0, 1.3), (1.0, 1.8)])

    def test_overseas_weekly_overtime_starts_after_38_hours(self):
        settings = {"base_rate": 40, "week_start_day": 0, "overtime_tiers": [
                        {"after_hours": 38, "multiplier": 1.5, "label": "OT1"},
                        {"after_hours": 44, "multiplier": 2.0, "label": "OT2"}],
                    "travel_loading": 0.3, "travel_rules": [], "penalty_rules": []}
        shifts = [{"id": i, "work_date": f"2026-11-{15+i:02d}", "start_time": "20:00",
                   "finish_time": "06:00", "break_minutes": 0, "is_overseas": True}
                  for i in range(1, 5)]
        result = calculate(shifts, [], settings)
        totals = {}
        for shift in result["shifts"]:
            for seg in shift["segments"]:
                totals[seg["multiplier"]] = totals.get(seg["multiplier"], 0) + seg["hours"]
        self.assertEqual(totals[1.3], 38)
        self.assertEqual(totals[1.8], 2)

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
        self.assertEqual(result["total_allowances"], 165)
        self.assertEqual(result["estimated_gross"], 1485)
        self.assertEqual(result["allowances"][0]["basis"], "30.00 Hours")
        self.assertEqual(len(result["allowances"]), 4)

    def test_hourly_allowance_includes_separate_travel_hours(self):
        settings = {"base_rate": 40, "week_start_day": 0, "overtime_tiers": [],
                    "travel_rules": [], "penalty_rules": [],
                    "allowances": [{"name": "Site", "amount": 2, "frequency": "hourly"}]}
        shifts = [{"id": i, "work_date": f"2026-11-{15+i:02d}", "start_time": "05:30",
                   "finish_time": "16:00", "break_minutes": 30}
                  for i in range(1, 6)]
        travel = [{"id": 1, "travel_date": "2026-11-20", "start_time": "06:00",
                   "finish_time": "16:00", "break_minutes": 0}]
        result = calculate(shifts, travel, settings)
        self.assertEqual(result["total_work_hours"], 50)
        self.assertEqual(result["total_travel_hours"], 10)
        self.assertEqual(result["allowances"][0]["basis"], "60.00 Hours")
        self.assertEqual(result["total_allowances"], 120)

    def test_allowances_are_reported_without_base_rate_but_gross_is_unknown(self):
        settings = {"base_rate": None, "week_start_day": 0, "overtime_tiers": [],
                    "travel_rules": [], "penalty_rules": [],
                    "allowances": [{"name":"Weekly","amount":30,"frequency":"weekly"}]}
        shift = {"id":1,"work_date":"2026-11-16","start_time":"05:30","finish_time":"16:00","break_minutes":30}
        result = calculate([shift], [], settings)
        self.assertEqual(result["total_allowances"], 30)
        self.assertIsNone(result["estimated_gross"])


    def test_allowance_basis_labels_are_compact(self):
        settings = {"base_rate": 40, "week_start_day": 0, "overtime_tiers": [],
                    "travel_rules": [], "penalty_rules": [],
                    "allowances": [
                        {"name": "Hourly", "amount": 2, "frequency": "hourly"},
                        {"name": "Weekly", "amount": 20, "frequency": "weekly"},
                        {"name": "Shift", "amount": 10, "frequency": "fixed"}]}
        shift = {"id": 1, "work_date": "2026-11-16", "start_time": "05:30",
                 "finish_time": "16:00", "break_minutes": 30}
        result = calculate([shift], [], settings)
        self.assertEqual([x["basis"] for x in result["allowances"]],
                         ["10.00 Hours", "Per Week", "Per Shift"])

    def test_ato_weekly_payg_with_tax_free_threshold_and_help(self):
        rates = {"scale2": [
            {"upper": 362, "a": 0, "b": 0},
            {"upper": 538, "a": 0.15, "b": 54.3462},
            {"upper": 673, "a": 0.25, "b": 108.2135},
            {"upper": 721, "a": 0.17, "b": 54.3473},
            {"upper": 865, "a": 0.179, "b": 60.8377},
            {"upper": 1282, "a": 0.3227, "b": 185.1935},
            {"upper": 2596, "a": 0.32, "b": 181.7319},
            {"upper": 3653, "a": 0.39, "b": 363.4627},
            {"upper": None, "a": 0.47, "b": 655.7704}],
            "help_scale2": [
            {"upper": 1337, "a": 0, "b": 0},
            {"upper": 2494, "a": 0.15, "b": 200.5615},
            {"upper": 3577, "a": 0.17, "b": 250.4527},
            {"upper": None, "a": 0.10, "b": 0}]}
        result = calculate_weekly_payg(2000, rates, True, True, 10)
        self.assertEqual(result, {"payg": 459, "help": 100, "extra": 10,
                                  "total_withheld": 569, "net": 1431.0})

    def test_payg_is_calculated_per_week_and_summed_for_report(self):
        rates = {"2026-27": {
            "scale2": [{"upper": 362, "a": 0, "b": 0},
                       {"upper": None, "a": 0.32, "b": 181.7319}],
            "scale1": [{"upper": None, "a": 0.47, "b": 493.1893}],
            "help_scale1": [], "help_scale2": []}}
        settings = {"base_rate": 40, "week_start_day": 0, "overtime_tiers": [],
                    "travel_rules": [], "penalty_rules": [], "allowances": [],
                    "payg_years": rates, "payg_tax_free_threshold": True}
        shifts = [
            {"id": 1, "work_date": "2026-11-16", "start_time": "00:00", "finish_time": "20:00", "break_minutes": 0},
            {"id": 2, "work_date": "2026-11-23", "start_time": "00:00", "finish_time": "20:00", "break_minutes": 0}]
        result = calculate(shifts, [], settings)
        self.assertEqual(len(result["payg_weeks"]), 2)
        self.assertEqual([w["gross"] for w in result["payg_weeks"]], [800, 800])
        self.assertEqual(result["estimated_payg"], 150)
        self.assertEqual(result["estimated_net"], 1450)

    def test_travel_pay_codes_distinguish_ordinary_and_overtime(self):
        settings = {"base_rate": 40, "week_start_day": 0,
                    "overtime_tiers": [
                        {"after_hours": 0, "multiplier": 1.0, "label": "Ordinary"},
                        {"after_hours": 38, "multiplier": 1.5, "label": "Overtime 1.5x"}],
                    "travel_loading": 0.3, "travel_rules": [], "penalty_rules": []}
        shifts = [
            {"id": 1, "work_date": "2026-11-16", "start_time": "00:00",
             "finish_time": "01:00", "break_minutes": 0, "is_overseas": True},
        ]
        result = calculate(shifts, [], settings)
        segment = result["shifts"][0]["segments"][0]
        self.assertEqual(segment["pay_code"], "Travel-OTH Ordinary 1.3")
        self.assertEqual(segment["multiplier"], 1.3)
        self.assertEqual(result["shifts"][0]["estimated_earnings"], 52)

if __name__ == "__main__":
    unittest.main()