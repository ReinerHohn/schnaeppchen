"""Unittests für die Analyse-Logik (stdlib unittest, kein Netz)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyze import (  # noqa: E402
    analyze_all,
    discount_pct,
    keyword_matches,
    match_interest,
    median,
    normalize,
    product_key,
    typical_price,
    weekday_stats,
)
from sources import demo_source  # noqa: E402


class TestStats(unittest.TestCase):
    def test_median_odd_even_empty(self):
        self.assertEqual(median([3, 1, 2]), 2)
        self.assertEqual(median([1, 2, 3, 4]), 2.5)
        self.assertIsNone(median([]))

    def test_discount_pct(self):
        self.assertEqual(discount_pct(80, 100), 20.0)
        self.assertEqual(discount_pct(120, 100), -20.0)  # teurer -> negativ
        self.assertEqual(discount_pct(80, 0), 0.0)       # kein üblicher Preis
        self.assertEqual(discount_pct(80, None), 0.0)

    def test_typical_price_uses_median(self):
        hist = [{"date": "2026-01-01", "price": 10},
                {"date": "2026-01-02", "price": 100},
                {"date": "2026-01-03", "price": 12}]
        self.assertEqual(typical_price(hist), 12)  # robust gg. Ausreißer 100


class TestNormalizeMatch(unittest.TestCase):
    def test_normalize_strips_accents_and_symbols(self):
        self.assertEqual(normalize("De'Longhi Siebträger!"), "de longhi siebtrager")

    def test_product_key_stable(self):
        a = {"brand": "Sony", "title": "WH-1000XM5 Kopfhörer"}
        b = {"brand": "sony", "title": "wh 1000xm5   kopfhörer"}
        self.assertEqual(product_key(a), product_key(b))

    def test_keyword_matches_wordstart_not_midword(self):
        # Komposita treffen (Wortanfang), Mittendrin-Rauschen nicht
        self.assertTrue(keyword_matches("hummer", "Frische Hummersuppe im Angebot"))
        self.assertTrue(keyword_matches("krabbe", "Königskrabben-Beine 1kg"))
        self.assertFalse(keyword_matches("rigi", "DAZN Gamepass im Original"))
        self.assertFalse(keyword_matches("wels", "Edelweiss Pullover"))
        self.assertFalse(keyword_matches("spa", "Spare bis zu 50% auf Technik"))
        self.assertTrue(keyword_matches("spa", "Wellness Spa Hotel Tirol"))
        # Mehrwort-Begriff als Phrase
        self.assertTrue(keyword_matches("glacier express", "Ticket Glacier Express Panorama"))
        self.assertFalse(keyword_matches("glacier express", "Glacier Bier Express Versand"))

    def test_match_interest_picks_best(self):
        interests = [
            {"name": "Kaffee", "keywords": ["espresso", "siebträger"], "category": "Küche"},
            {"name": "Audio", "keywords": ["kopfhörer"], "category": "Elektronik"},
        ]
        offer = {"title": "WH-1000XM5 Kopfhörer", "brand": "Sony", "category": "Elektronik"}
        it, matched, hits = match_interest(offer, interests)
        self.assertEqual(it["name"], "Audio")
        self.assertIn("kopfhörer", matched)

    def test_match_interest_none_when_unrelated(self):
        interests = [{"name": "Kaffee", "keywords": ["espresso"], "category": "Küche"}]
        offer = {"title": "Gartenschlauch", "brand": "Gardena", "category": "Garten"}
        it, _, hits = match_interest(offer, interests)
        self.assertIsNone(it)
        self.assertEqual(hits, 0)


class TestWeekday(unittest.TestCase):
    def test_weekday_saving_detected(self):
        # 2026-06-01 ist Montag. Mo-Fr = 90, Sa/So = 100 -> 10% Ersparnis unter der Woche.
        hist = []
        import datetime
        for d in range(14):
            day = datetime.date(2026, 6, 1) + datetime.timedelta(days=d)
            price = 100 if day.weekday() >= 5 else 90
            hist.append({"date": day.isoformat(), "price": price})
        st = weekday_stats(hist)
        self.assertEqual(st["weekday_mean"], 90)
        self.assertEqual(st["weekend_mean"], 100)
        self.assertEqual(st["weekday_saving_pct"], 10.0)


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.interests = [
            {"name": "Sterne & Gourmet günstig",
             "keywords": ["sterne", "menü", "tasting", "chef", "gourmet"],
             "category": "Fine Dining", "max_price": 250, "min_discount_pct": 20, "weight": 1.6},
            {"name": "Delikatessen",
             "keywords": ["hummer", "königskrabbe", "krabbe", "käsefondue", "fondue"],
             "category": "Delikatessen", "max_price": 150, "min_discount_pct": 15, "weight": 1.4},
        ]
        self.settings = {"weekday_flag_pct": 8.0, "min_deal_score": 0.25}

    def test_demo_deterministic(self):
        o1, h1 = demo_source(days=60, seed=42)
        o2, h2 = demo_source(days=60, seed=42)
        self.assertEqual([o["price"] for o in o1], [o["price"] for o in o2])

    def test_today_sale_is_flagged_schnaeppchen(self):
        offers, history = demo_source(days=90, seed=42)
        analyzed = analyze_all(offers, history, self.interests, self.settings)
        by_title = {a["title"]: a for a in analyzed}
        deal = by_title["Sterne-Menü 5-Gang"]  # -42% Aktion heute
        self.assertTrue(deal["is_schnaeppchen"])
        self.assertGreater(deal["discount_pct"], 20)
        self.assertEqual(deal["interest"], "Sterne & Gourmet günstig")

    def test_unrelated_item_not_schnaeppchen(self):
        offers, history = demo_source(days=90, seed=42)
        analyzed = analyze_all(offers, history, self.interests, self.settings)
        stuhl = next(a for a in analyzed if a["title"].startswith("Bürostuhl"))
        self.assertFalse(stuhl["is_schnaeppchen"])
        self.assertIsNone(stuhl["interest"])

    def test_sorted_by_score_desc(self):
        offers, history = demo_source(days=90, seed=42)
        analyzed = analyze_all(offers, history, self.interests, self.settings)
        scores = [a["deal_score"] for a in analyzed]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_weekday_deal_flagged(self):
        offers, history = demo_source(days=90, seed=42)
        analyzed = analyze_all(offers, history, self.interests, self.settings)
        # Sterne-Menü hat weekday_disc 0.26 -> deutlich unter der Woche billiger
        deal = next(a for a in analyzed if a["title"] == "Sterne-Menü 5-Gang")
        self.assertTrue(deal["is_weekday_deal"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
