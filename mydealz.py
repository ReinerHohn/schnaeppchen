"""Echte Angebots-Quelle: mydealz.de (Community-Schnäppchen per RSS).

mydealz ist Deutschlands größte Schnäppchen-Community. Jeder Deal hat eine
"Temperatur" (°) = wie stark ihn die Community hochvotet -> ideales "geil"-Signal.
Preis + Händler stehen sauber in der Beschreibung (`<strong>3,84€ - Amazon</strong>`).

Feeds:
  hot/new/trending   globale Top- bzw. frische Deals
  gruppe/<slug>      thematisch (reisen, urlaub, lebensmittel, konzerte, ...)

Das Parsen ist von der Netzwerk-Schicht getrennt (parse_feed) -> testbar ohne Netz.
Reine stdlib.
"""
from __future__ import annotations

import datetime
import html
import re
import urllib.request

# Fertige Feed-Presets (Schlüssel -> URL). Erweiterbar in config.json.
FEEDS = {
    "hot": "https://www.mydealz.de/rss/hot",
    "new": "https://www.mydealz.de/rss/new",
    "trending": "https://www.mydealz.de/rss/trending",
    "reisen": "https://www.mydealz.de/rss/gruppe/reisen",
    "urlaub": "https://www.mydealz.de/rss/gruppe/urlaub",
    "lebensmittel": "https://www.mydealz.de/rss/gruppe/lebensmittel",
    "konzerte": "https://www.mydealz.de/rss/gruppe/konzerte",
}

_UA = {"User-Agent": "Mozilla/5.0 (SchnaeppchenJaeger/1.0)"}


# --------------------------------------------------------------------------- #
# Parser-Helfer (rein, ohne Netz)
# --------------------------------------------------------------------------- #
def _cdata(text):
    """CDATA-Hülle entfernen und HTML-Entities auflösen."""
    if text is None:
        return ""
    text = re.sub(r"^\s*<!\[CDATA\[(.*?)\]\]>\s*$", r"\1", text, flags=re.S)
    return html.unescape(text).strip()


def _euro(text):
    """Ersten Euro-Betrag aus Text ziehen. '1.299,00€' -> 1299.0, '3,84€' -> 3.84."""
    if not text:
        return None
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?\s*(?:€|EUR)", text)
    if not m:
        return None
    whole = m.group(1).replace(".", "")
    frac = m.group(2) or "0"
    try:
        return round(float(f"{whole}.{frac}"), 2)
    except ValueError:
        return None


def parse_title(raw):
    """'317° - Monitor iiyama ...' -> (317, 'Monitor iiyama ...')."""
    raw = _cdata(raw)
    m = re.match(r"^\s*(-?\d+)\s*°\s*-\s*(.*)$", raw, flags=re.S)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return None, raw


def parse_price_merchant(desc):
    """Aus '<strong>3,84€ - Amazon</strong>' -> (3.84, 'Amazon')."""
    m = re.search(r"<strong>(.*?)</strong>", desc, flags=re.S)
    if not m:
        return None, None
    head = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
    price = _euro(head)
    # Händler = Teil nach dem letzten ' - '
    merchant = head.split(" - ")[-1].strip() if " - " in head else None
    if merchant and _euro(merchant) is not None:  # war doch nur ein Preis
        merchant = None
    return price, merchant


def parse_discount(text):
    """Originalpreis ('statt X€'/'UVP X€') und/oder Prozent-Rabatt aus Text ziehen.

    Rückgabe (original_price|None, discount_pct|None).
    """
    original = None
    m = re.search(r"(?:statt|uvp|vgl\.?|regulär|regulaer|anstatt)\D{0,12}?"
                  r"(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s*(?:€|EUR)", text, flags=re.I)
    if m:
        original = _euro(m.group(1) + "€")
    pct = None
    mp = re.search(r"(-?\d{1,2})\s*%", text)
    if mp:
        val = abs(int(mp.group(1)))
        if 1 <= val <= 95:
            pct = float(val)
    return original, pct


def parse_feed(xml, group=None, today=None):
    """Ein RSS-XML in eine Liste von Angebots-dicts umwandeln (kein Netz)."""
    if today is None:
        today = datetime.date.today()
    offers = []
    for block in re.findall(r"<item>(.*?)</item>", xml, flags=re.S):
        def tag(name):
            m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, flags=re.S)
            return m.group(1) if m else ""

        temperature, title = parse_title(tag("title"))
        if not title:
            continue
        link = _cdata(tag("link")) or _cdata(tag("guid"))
        desc = tag("description")
        price, merchant = parse_price_merchant(desc)
        blurb = html.unescape(re.sub("<[^>]+>", " ", desc))
        blurb = re.sub(r"\s+", " ", blurb).strip()
        text_all = f"{title} {blurb}"
        original, pct = parse_discount(text_all)
        img = re.search(r'<img[^>]+src="([^"]+)"', desc)
        category = _cdata(tag("category"))

        offers.append(
            {
                "title": title,
                "brand": merchant or "",
                "category": category,
                "price": price,
                "currency": "€",
                "url": link,
                "source": "mydealz",
                "group": group,
                "temperature": temperature,
                "original_price": original,
                "discount_pct": pct,
                "image": img.group(1) if img else None,
                "blurb": blurb[:280],
                "observed_at": today.isoformat(),
            }
        )
    return offers


# --------------------------------------------------------------------------- #
# Netzwerk-Schicht
# --------------------------------------------------------------------------- #
def _fetch(url, timeout):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def fetch_offers(feeds=None, timeout=15, today=None):
    """Mehrere Feeds holen, parsen, nach URL deduplizieren.

    feeds: Liste von Preset-Schlüsseln (siehe FEEDS) oder vollen URLs.
    Rückgabe: (offers, meta) — meta zählt Erfolg/Fehler je Feed.
    """
    if feeds is None:
        feeds = ["hot", "new", "reisen", "urlaub", "lebensmittel", "konzerte"]
    seen = {}
    meta = {"ok": [], "failed": []}
    for f in feeds:
        url = FEEDS.get(f, f)
        label = f if f in FEEDS else "custom"
        try:
            xml = _fetch(url, timeout)
        except Exception as exc:  # noqa: BLE001 - tolerant, ein Feed darf ausfallen
            meta["failed"].append((f, str(exc)))
            continue
        got = parse_feed(xml, group=label, today=today)
        for o in got:
            if o["url"] and o["url"] not in seen:
                seen[o["url"]] = o
        meta["ok"].append((f, len(got)))
    return list(seen.values()), meta
