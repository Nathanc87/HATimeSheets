import unittest
from app.ha_presence import _round, _zone
from datetime import datetime

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
