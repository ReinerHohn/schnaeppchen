"""Tests für den Feinkost-/Seafood-Shop-Scraper (parse-only, kein Netz)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shop import parse_product, parse_sitemap  # noqa: E402

# Nachgebaut aus gourmetfleisch.de (Shopware, Preis mit &nbsp;EUR).
PRODUCT_HTML = """<html><head>
<meta property="og:image" content="https://img/hummer.jpg"/>
</head><body>
<h1>Hummerschwanzfleisch (sous-vide)</h1>
<div class="os_detail_pricetab">
  <span class="os_list_oldprice">59,90&nbsp;EUR</span>
  <span class="os_detail_price">47,70&nbsp;EUR</span>
</div>
<div class="crosssell"><span class="pricem">5,95&nbsp;EUR</span></div>
</body></html>"""

SITEMAP = """<?xml version="1.0"?><urlset>
<url><loc>https://www.gourmetfleisch.de/seafood/hummerschwanzfleisch-sous-vide.html</loc></url>
<url><loc>https://www.gourmetfleisch.de/seafood/langustenschwanz-mit-schale.html</loc></url>
<url><loc>https://www.gourmetfleisch.de/steaks/rumpsteak.html</loc></url>
<url><loc>https://www.gourmetfleisch.de/seafood/kabeljau-loins.html</loc></url>
</urlset>"""


class TestShopParse(unittest.TestCase):
    def test_parse_product_main_price(self):
        o = parse_product(PRODUCT_HTML, "https://x/hummer", "gourmetfleisch")
        self.assertEqual(o["title"], "Hummerschwanzfleisch (sous-vide)")
        self.assertEqual(o["price"], 47.70)          # Hauptpreis, NICHT 5,95 (Cross-Sell)
        self.assertEqual(o["image"], "https://img/hummer.jpg")
        self.assertEqual(o["category"], "Delikatessen")
        self.assertEqual(o["group"], "feinkost:gourmetfleisch")

    def test_parse_product_needs_price(self):
        self.assertIsNone(parse_product("<h1>Ohne Preis</h1>", "u", "s"))

    def test_sitemap_filters_seafood(self):
        urls = parse_sitemap(SITEMAP)
        self.assertIn("https://www.gourmetfleisch.de/seafood/hummerschwanzfleisch-sous-vide.html", urls)
        self.assertIn("https://www.gourmetfleisch.de/seafood/langustenschwanz-mit-schale.html", urls)
        self.assertNotIn("https://www.gourmetfleisch.de/steaks/rumpsteak.html", urls)  # kein Krustentier
        self.assertNotIn("https://www.gourmetfleisch.de/seafood/kabeljau-loins.html", urls)  # 08/15-Fisch


if __name__ == "__main__":
    unittest.main(verbosity=2)
