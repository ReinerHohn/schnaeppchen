"""Tests für den mydealz-RSS-Parser und die Sweet-Spot-Heuristiken (kein Netz)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyze import analyze_all  # noqa: E402
from mydealz import (  # noqa: E402
    _euro, parse_discount, parse_feed, parse_price_merchant, parse_search, parse_title,
)
from sweetspots import match_sweetspots  # noqa: E402

# Statischer RSS-Ausschnitt im mydealz-Format (nachgebaut aus echten Feeds).
SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss><channel>
<item>
  <title><![CDATA[334° - Königskrabben-Beine 1kg Bruchware statt 129€ | -40% Restposten]]></title>
  <link>https://www.mydealz.de/deals/koenigskrabbe-111</link>
  <description><![CDATA[<strong>77,40€ - Fischmarkt</strong><br /><img src="https://img/x.jpg" width="100"/><br />Frische Königskrabben-Beine als Bruchware, statt 129€.]]></description>
  <category><![CDATA[Lebensmittel]]></category>
  <pubDate>Mon, 07 Sep 2026 09:00:00 +0200</pubDate>
</item>
<item>
  <title><![CDATA[Nutella & Go 12er Pack - Prime]]></title>
  <link>https://www.mydealz.de/deals/nutella-222</link>
  <description><![CDATA[<strong>5,99€ - Amazon</strong><br />Nur mit Prime.]]></description>
  <category><![CDATA[Lebensmittel]]></category>
  <pubDate>Mon, 07 Sep 2026 09:10:00 +0200</pubDate>
</item>
</channel></rss>"""


class TestParsers(unittest.TestCase):
    def test_euro(self):
        self.assertEqual(_euro("3,84€"), 3.84)
        self.assertEqual(_euro("1.299,00€"), 1299.0)
        self.assertEqual(_euro("29 €"), 29.0)
        self.assertIsNone(_euro("kostenlos"))

    def test_parse_title_temperature(self):
        self.assertEqual(parse_title("<![CDATA[317° - Monitor XYZ]]>"), (317, "Monitor XYZ"))
        # ohne Grad-Prefix (Gruppen-Feeds)
        self.assertEqual(parse_title("<![CDATA[Milka Pralinés 0,74€]]>"), (None, "Milka Pralinés 0,74€"))

    def test_parse_price_merchant(self):
        p, m = parse_price_merchant("<strong>77,40€ - Fischmarkt</strong>")
        self.assertEqual(p, 77.40)
        self.assertEqual(m, "Fischmarkt")

    def test_parse_discount(self):
        orig, pct = parse_discount("Bruchware statt 129€ | -40% Restposten")
        self.assertEqual(orig, 129.0)
        self.assertEqual(pct, 40.0)


class TestFeed(unittest.TestCase):
    def test_parse_feed_fields(self):
        offers = parse_feed(SAMPLE, group="lebensmittel")
        self.assertEqual(len(offers), 2)
        krabbe = offers[0]
        self.assertEqual(krabbe["temperature"], 334)
        self.assertEqual(krabbe["price"], 77.40)
        self.assertEqual(krabbe["brand"], "Fischmarkt")
        self.assertEqual(krabbe["original_price"], 129.0)
        self.assertEqual(krabbe["discount_pct"], 40.0)
        self.assertEqual(krabbe["group"], "lebensmittel")
        self.assertTrue(krabbe["url"].endswith("koenigskrabbe-111"))


SEARCH_HTML = """
<div class="thread-title thread-title--list"><a href="/deals/hummer-frisch-999" class="cept-tt thread-link">
  Ganzer Hummer 500g für 19,99€ statt 34,99€</a></div>
<div class="thread-title"><a href="https://www.mydealz.de/deals/hummel-tights-111" class="thread-link">
  hummel hmlMOVER Tights Damen für 3,17€</a></div>
"""


class TestSearch(unittest.TestCase):
    def test_parse_search_extracts_and_filters(self):
        offers = parse_search(SEARCH_HTML, "hummer")
        # 'hummel' muss rausgefiltert werden (Fuzzy-Rauschen), nur echter Hummer bleibt
        self.assertEqual(len(offers), 1)
        o = offers[0]
        self.assertTrue(o["title"].startswith("Ganzer Hummer"))
        self.assertEqual(o["price"], 19.99)
        self.assertEqual(o["original_price"], 34.99)
        self.assertEqual(o["group"], "suche:hummer")
        self.assertTrue(o["url"].startswith("https://www.mydealz.de/deals/hummer"))


class TestSweetspots(unittest.TestCase):
    def test_matches_invasive_and_bruchware(self):
        offer = {"title": "Königskrabben-Beine 1kg Bruchware", "blurb": "Restposten Abverkauf"}
        found = {s["name"] for s in match_sweetspots(offer)}
        self.assertIn("Invasive Delikatesse", found)
        self.assertIn("Bruchware / B-Ware", found)
        self.assertIn("Abverkauf / Restposten", found)

    def test_no_false_positive(self):
        offer = {"title": "Nutella & Go 12er Pack", "blurb": "Nur mit Prime"}
        self.assertEqual(match_sweetspots(offer), [])


class TestEndToEndLive(unittest.TestCase):
    def test_krabbe_ranks_above_nutella(self):
        interests = [{"name": "Delikatessen", "keywords": ["königskrabbe", "krabbe"],
                      "category": "Delikatessen", "max_price": 150, "min_discount_pct": 15,
                      "weight": 1.4}]
        offers = parse_feed(SAMPLE, group="lebensmittel")
        analyzed = analyze_all(offers, {}, interests, {"hot_temp_threshold": 200})
        # Krabbe: Interesse + Rabatt 40% + hot 334° + Sweet Spots -> muss vorne sein
        self.assertEqual(analyzed[0]["title"].split()[0], "Königskrabben-Beine")
        self.assertTrue(analyzed[0]["is_schnaeppchen"])
        self.assertGreater(len(analyzed[0]["sweetspots"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
