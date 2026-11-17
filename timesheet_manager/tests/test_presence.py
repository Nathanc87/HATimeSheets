import unittest
from app.ha_presence import _round, _zone
from app.db import DEFAULT_SETTINGS
from datetime import datetime

class SettingsDefaultTests(unittest.TestCase):
    def test_default_overtime_tiers_match_requested_values(self):
        tiers = DEFAULT_SETTINGS["overtime_tiers"]
        self.assertEqual([(x["after_hours"], x["multiplier"], x["label"], x["cost_code"]) for x in tiers[1:]],
                         [(38, 1.5, "Ord 1.5", "Ordinary 1.5"), (40, 1.5, "OT 1.5", "Overtime 1.5"), (44, 2.0, "OT 2.0", "Overtime 2.0")])

    def test_default_travel_tiers_match_requested_values(self):
        self.assertEqual([(x["after_hours"], x["multiplier"], x["label"], x["cost_code"]) for x in DEFAULT_SETTINGS["travel_rules"]],
                         [(0, 1.3, "Travel ordinary", "Travel-OTH Ordinary"), (38, 1.8, "Travel overtime 1.5", "Travel-OTH OT 1.8"), (44, 2.3, "Travel overtime 2.0", "Travel-OTH OT 2.3")])

    def test_default_2026_27_resident_tax_brackets_match(self):
        self.assertEqual([(x["lower"], x["upper"], x["base_tax"], x["rate"]) for x in DEFAULT_SETTINGS["payg_annual_years"]["2026-27"]["resident_brackets"]],
                         [(0, 18200, 0, 0), (18200, 45000, 0, 0.15), (45000, 135000, 4020, 0.30), (135000, 190000, 31020, 0.37), (190000, None, 51370, 0.45)])

class PresenceHelpersTests(unittest.TestCase):
    def test_finish_rounds_to_nearest_quarter_hour(self):
        self.assertEqual(_round(datetime(2026, 11, 16, 15, 7), 15), "15:00")
        self.assertEqual(_round(datetime(2026, 11, 16, 15, 8), 15), "15:15")
        self.assertEqual(_round(datetime(2026, 11, 16, 15, 53), 15), "16:00")

    def test_zone_matches_friendly_name_or_entity_id(self):
        zones = {"zone.workshop": "Workshop"}
        self.assertEqual(_zone("Workshop", zones), "zone.workshop")
        self.assertEqual(_zone("zone.workshop", zones), "zone.workshop")
        self.assertIsNone(_zone("not_home", zones))
        self.assertIsNone(_zone("unavailable", zones))

if __name__ == "__main__":
    unittest.main()
