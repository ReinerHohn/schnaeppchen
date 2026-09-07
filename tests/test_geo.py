"""Tests für Ortsbezug & Entfernung (geo.py) – offline, deterministisch."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geo import geocode_home, haversine, locate, maps_route_url  # noqa: E402


class TestGeo(unittest.TestCase):
    def test_haversine_known_distance(self):
        # Köln -> München ~ 456 km Luftlinie.
        km = haversine(50.938, 6.960, 48.137, 11.575)
        self.assertTrue(450 <= km <= 460, km)

    def test_geocode_plz_and_city(self):
        lat, lon, label = geocode_home("50667 Köln")
        self.assertAlmostEqual(lat, 50.938, places=2)
        self.assertEqual(label, "Köln")

    def test_geocode_coords(self):
        self.assertEqual(geocode_home("47.377,8.540"), (47.377, 8.540, "47.377,8.540"))

    def test_geocode_plz_region_fallback(self):
        # Unbekannter Ort mit dt. PLZ -> grober Regions-Fallback (1xxxx = Berlin).
        lat, lon, _ = geocode_home("12345 Nirgendwo")
        self.assertAlmostEqual(lat, 52.5, places=1)

    def test_geocode_unknown_none(self):
        self.assertIsNone(geocode_home("Quatschstadt ohne PLZ"))

    def test_locate_city_in_title(self):
        self.assertEqual(locate("Dinner Hopping Augsburg für 2")[0], "Augsburg")
        self.assertEqual(locate("Glacier Express nach Zermatt")[0], "Zermatt")

    def test_locate_none_without_place(self):
        self.assertIsNone(locate("Hummerschwanzfleisch sous-vide"))

    def test_locate_prefers_longer_name(self):
        # 'Baden-Baden' (länger) soll 'Baden' nicht fälschlich verkürzen.
        self.assertEqual(locate("Wellness-Wochenende Baden-Baden")[0], "Baden-Baden")

    def test_maps_route_url(self):
        url = maps_route_url([50.94, 6.96], [48.14, 11.58])
        self.assertIn("origin=50.94,6.96", url)
        self.assertIn("destination=48.14,11.58", url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
