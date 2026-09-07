"""Feinkost-/Seafood-Shops scrapen (echte Hummer/Krabbe/Langusten-Produkte).

Deal-Communities posten Hummer & Co. nur selten. Dieser Scraper holt echte
Produkte direkt aus Gourmet-Shops: Sitemap -> Seafood-Produkt-URLs filtern ->
Produktseiten parsen (Name + Preis + Bild). Server-gerendert, robust.

Getestet gegen gourmetfleisch.de (Shopware, iso-8859-1, Preis in
`<span class="os_detail_price">47,70&nbsp;EUR`). Weitere Shops via config.shops.

Das Parsen ist von der Netzwerk-Schicht getrennt -> testbar ohne Netz. stdlib.
"""
from __future__ import annotations

import concurrent.futures as _cf
import datetime
import gzip
import html
import re
import urllib.request

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/120 Safari/537.36"}

# Währungssymbol (Suffix wie '47,70 EUR' ODER Präfix wie '€ 26,97').
_CUR = r"€|EUR|CHF"
# Betrag im Anzeige-Format ('47,70&nbsp;EUR', '1.299,00 €', '€ 26,97*').
_AMOUNT = re.compile(r"(\d{1,3}(?:\.\d{3})*),(\d{2})")
_HAS_CUR = re.compile(_CUR)

# Hauptpreis-Selektoren (in Reihenfolge). display=Anzeige-Text, content=Attribut.
_PRICE_SELECTORS = [
    ("display", r'class="os_detail_price"[^>]*>\s*([^<]+)'),
    ("content", r'itemprop="price"[^>]*content="([\d.,]+)"'),
    ("content", r'property="product:price:amount"[^>]*content="([\d.,]+)"'),
    ("content", r'"price"\s*:\s*"?([\d]+(?:[.,]\d{1,2})?)"?'),  # JSON-LD (Shopify/eataly)
    ("display", r'class="[^"]*product--price[^"]*"[^>]*>\s*([^<]+)'),
    ("display", r'class="[^"]*price--default[^"]*"[^>]*>\s*([^<]+)'),
    ("display", r'class="price_pcs"[^>]*>\s*([^<]+)'),  # JTL-Shop (bosfood)
]

# Standard-Filter: nur Edel-Krustentiere/Delikatessen (kein 08/15-Lachs/Kabeljau).
DEFAULT_MATCH = ["hummer", "krabbe", "krebs", "kaviar", "languste", "austern",
                 "jakobs", "scampi", "gambas", "garnele", "krustentier",
                 "king-crab", "koenigskrabbe", "kaisergranat", "seeigel"]


def _display_price(text):
    """Betrag aus Anzeige-Text. Verlangt eine Währung (sonst wäre '2,00' aus einem
    Fußzeilen-Hinweis ein Fehlpreis) und akzeptiert sie vor ODER nach der Zahl."""
    text = html.unescape(text)
    if not _HAS_CUR.search(text):
        return None
    m = _AMOUNT.search(text)
    if not m:
        return None
    return round(float(m.group(1).replace(".", "") + "." + m.group(2)), 2)


def _content_price(text):
    try:
        return round(float(text.replace(",", ".")), 2)
    except (ValueError, AttributeError):
        return None


def parse_product(html_doc, url, source, currency="€", today=None,
                  category="Delikatessen", kind="feinkost"):
    """Eine Produktseite -> Angebots-dict (oder None, wenn kein Preis/Name).

    category/kind steuern die Einordnung: Feinkost-Produkt (Standard) ODER
    Genuss-Event (category='Event', kind='event') -> group 'event:<source>'.
    """
    if today is None:
        today = datetime.date.today()
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html_doc, re.S)
    name = html.unescape(re.sub("<[^>]+>", "", h1.group(1))).strip() if h1 else None
    if name:
        name = re.sub(r"\s+", " ", name)  # Zeilenumbrüche/Tabs aus mehrzeiligem H1 glätten
    if not name:
        return None

    price = None
    for sel_kind, pat in _PRICE_SELECTORS:
        m = re.search(pat, html_doc)
        if not m:
            continue
        price = _display_price(m.group(1)) if sel_kind == "display" else _content_price(m.group(1))
        if price:  # >0 und nicht None
            break
        price = None
    if not price:  # ohne (echten) Preis kein Deal
        return None

    img = (re.search(r'property="og:image"\s+content="([^"]+)"', html_doc)
           or re.search(r'name="twitter:image"\s+content="([^"]+)"', html_doc)
           or re.search(r'<img[^>]+src="([^"]+\.(?:jpg|jpeg|png|webp))"', html_doc))
    return {
        "title": name,
        "brand": source,
        "category": category,
        "price": price,
        "currency": currency,
        "url": url,
        "source": source,
        "group": f"{kind}:{source}",
        "temperature": None,
        "original_price": None,
        "discount_pct": None,
        "image": img.group(1) if img else None,
        "blurb": name,
        "observed_at": today.isoformat(),
    }


def parse_sitemap(xml, match=None, exclude=None, require=None):
    """Seafood-Produkt-URLs aus einer Sitemap ziehen.

    match:   URL muss einen dieser Substrings enthalten (Positiv-Filter).
    exclude: URL darf keinen dieser Substrings enthalten – blendet Landing-,
             Blog- und Non-Food-Seiten aus (z.B. 'buecher', 'magazin').
    require: URL MUSS diesen Substring (oder EINEN aus einer Liste) enthalten –
             grenzt auf echte Produkt-/Detailseiten ein (z.B. '/produkt/', oder
             ['/p/', '/l/'] bei Event-Shops), deren Übersichtsseiten sonst als
             Fehlpreis durchrutschen.
    """
    match = match or DEFAULT_MATCH
    urls = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", xml)
    rx = re.compile("|".join(re.escape(m) for m in match), re.I)
    ex = re.compile("|".join(re.escape(x) for x in exclude), re.I) if exclude else None
    req = [require] if isinstance(require, str) else require  # str oder Liste (any-of)
    return [
        u for u in urls
        if rx.search(u)
        and (not req or any(r in u for r in req))
        and not (ex and ex.search(u))
    ]


# --------------------------------------------------------------------------- #
# Netzwerk
# --------------------------------------------------------------------------- #
def _fetch(url, timeout, encoding=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=timeout) as r:
        raw = r.read()
        enc = encoding or r.headers.get_content_charset() or "utf-8"
    if url.endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw.decode(enc, "replace")


def _sitemap_urls(sitemap_url, timeout):
    """Sitemap holen; ist es ein Index, eine Ebene in die Sub-Sitemaps absteigen."""
    xml = _fetch(sitemap_url, timeout)
    locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", xml)
    subs = [l for l in locs if l.endswith((".xml", ".xml.gz"))]
    if subs:
        parts = [xml]
        for s in subs[:25]:
            try:
                parts.append(_fetch(s, timeout))
            except Exception:  # noqa: BLE001 - einzelne Sub-Sitemap darf fehlen
                pass
        xml = "\n".join(parts)
    return xml


def fetch_shop(cfg, timeout=20, today=None, max_products=30):
    """Einen Shop scrapen: Sitemap -> Seafood-URLs -> Produktseiten parsen.

    cfg: {name, sitemap, currency?, match?, exclude?, require?, encoding?,
          category?, kind?}. category/kind='Event'/'event' -> Genuss-Event-Shop.
    Rückgabe: (offers, count).
    """
    name = cfg["name"]
    currency = cfg.get("currency", "€")
    cap = cfg.get("max_products", max_products)
    category = cfg.get("category", "Delikatessen")
    kind = cfg.get("kind", "feinkost")
    try:
        xml = _sitemap_urls(cfg["sitemap"], timeout)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"sitemap: {exc}") from exc
    urls = parse_sitemap(xml, cfg.get("match"), cfg.get("exclude"), cfg.get("require"))[:cap]

    def one(u):
        try:
            doc = _fetch(u, timeout, cfg.get("encoding"))
        except Exception:  # noqa: BLE001 - einzelne Produktseite darf ausfallen
            return None
        return parse_product(doc, u, name, currency, today, category, kind)

    offers = []
    with _cf.ThreadPoolExecutor(max_workers=8) as ex:
        for o in ex.map(one, urls):
            if o and o["price"] is not None:
                offers.append(o)
    return offers, len(offers)


def fetch_shops(shops, timeout=20, today=None, workers=6):
    """Mehrere Shops parallel scrapen. Rückgabe (offers, meta)."""
    offers, meta = [], {"ok": [], "failed": []}
    if not shops:
        return offers, meta
    with _cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_shop, s, timeout, today): s["name"] for s in shops}
        for fut in _cf.as_completed(futs):
            name = futs[fut]
            try:
                got, n = fut.result()
            except Exception as exc:  # noqa: BLE001
                meta["failed"].append((f"🐟{name}", str(exc)))
                continue
            offers.extend(got)
            meta["ok"].append((f"🐟{name}", n))
    return offers, meta
