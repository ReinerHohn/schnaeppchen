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

import concurrent.futures as _cf
import datetime
import html
import re
import urllib.parse
import urllib.request

from analyze import normalize

_MD = "https://www.mydealz.de"
_PJ = "https://www.preisjaeger.at"

# Fertige Feed-Presets (Schlüssel -> URL). Erweiterbar in config.json / via --feeds.
# mydealz (DE) und preisjaeger (AT, "pj_") laufen auf derselben Plattform -> selber Parser.
_MD_GROUPS = ["lebensmittel", "restaurant", "supermarkt", "getraenke", "wein", "kochen",
              "kaffee", "reisen", "urlaub", "hotel", "fluege", "konzerte", "freizeitpark",
              "kino", "musical", "elektronik"]
_PJ_GROUPS = ["supermarkt", "getraenke", "reisen", "urlaub"]

FEEDS = {
    "hot": f"{_MD}/rss/hot",
    "new": f"{_MD}/rss/new",
    "trending": f"{_MD}/rss/trending",
    "pj_hot": f"{_PJ}/rss/hot",
    "pj_new": f"{_PJ}/rss/new",
}
FEEDS.update({g: f"{_MD}/rss/gruppe/{g}" for g in _MD_GROUPS})
FEEDS.update({f"pj_{g}": f"{_PJ}/rss/gruppe/{g}" for g in _PJ_GROUPS})

# Generische WordPress-Deal-Feeds (anderer Parser). preispirat.ch = Schweiz
# (relevant für Bergbahnen/Fondue/Swiss-Reisen), CHF.
WP_FEEDS = {
    "preispirat_ch": {"url": "https://www.preispirat.ch/feed/", "currency": "CHF"},
    "urlaubspiraten": {"url": "https://www.urlaubspiraten.de/feed", "currency": "€"},
    "reisetiger": {"url": "https://www.reisetiger.net/feed", "currency": "€"},
    "traveldealz": {"url": "https://travel-dealz.de/feed/", "currency": "€"},
}

# Suche aktiv nach diesen Begriffen (mydealz-Volltextsuche, HTML). Für Nischen
# wie Hummer/Königskrabbe, die selten in den Standard-Feeds auftauchen.
_SEARCH_URL = _MD + "/search?q={}"

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


_CUR = r"(?:€|EUR|CHF|SFr\.?|Fr\.?)"  # Euro + Schweizer Franken (preispirat.ch)


def _euro(text):
    """Ersten Geldbetrag ziehen. '1.299,00€'->1299.0, '3,84€'->3.84, '99 CHF'->99.0."""
    if not text:
        return None
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?\s*" + _CUR, text)
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
                  r"(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s*" + _CUR, text, flags=re.I)
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
        if price is None:  # Fallback: Preis steckt im Titel ('... für 19,99€')
            price = _euro(title)
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


def parse_search(html_doc, query, base=_MD, today=None):
    """Deals aus einer mydealz/preisjaeger-Suchergebnisseite (HTML) ziehen.

    Titel-Anker liefern Titel + Link; Preis/Rabatt stecken im Titeltext
    ('... für 3,17€ statt 19,95€'). Nur Treffer, die den Suchbegriff wirklich
    enthalten (gegen Fuzzy-Rauschen wie hummer->hummel).
    """
    if today is None:
        today = datetime.date.today()
    q = normalize(query).replace(" ", "")
    offers = []
    anchors = re.findall(
        r'class="thread-title[^"]*"[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        html_doc, re.S,
    )
    for href, raw in anchors:
        title = html.unescape(re.sub("<[^>]+>", "", raw)).strip()
        if q and q not in normalize(title).replace(" ", ""):
            continue  # Fuzzy-Rauschen raus
        link = href if href.startswith("http") else base + href
        original, pct = parse_discount(title)
        offers.append(
            {
                "title": title,
                "brand": "",
                "category": "",
                "price": _euro(title),
                "currency": "€",
                "url": link,
                "source": "mydealz-suche",
                "group": f"suche:{query}",
                "temperature": None,
                "original_price": original,
                "discount_pct": pct,
                "image": None,
                "blurb": "",
                "observed_at": today.isoformat(),
            }
        )
    return offers


def parse_wp_feed(xml, source, currency="€", today=None):
    """Generisches WordPress-RSS (z.B. preispirat.ch) parsen.

    Kein °-System; Preis/Rabatt stecken in Titel oder Beschreibung.
    """
    if today is None:
        today = datetime.date.today()
    offers = []
    for block in re.findall(r"<item>(.*?)</item>", xml, flags=re.S):
        def tag(name):
            m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, flags=re.S)
            return m.group(1) if m else ""

        title = _cdata(tag("title"))
        if not title:
            continue
        link = _cdata(tag("link")) or _cdata(tag("guid"))
        body = tag("encoded") or tag("description")
        blurb = re.sub(r"\s+", " ", _cdata(re.sub("<[^>]+>", " ", body))).strip()
        text = f"{title} {blurb}"
        original, pct = parse_discount(text)
        img = re.search(r'<(?:media:content|enclosure)[^>]+url="([^"]+)"', block) \
            or re.search(r'<img[^>]+src="([^"]+)"', body)
        offers.append(
            {
                "title": title,
                "brand": "",
                "category": _cdata(tag("category")),
                "price": _euro(title) or _euro(blurb),
                "currency": currency,
                "url": link,
                "source": source,
                "group": source,
                "temperature": None,
                "original_price": original,
                "discount_pct": pct,
                "image": img.group(1) if img else None,
                "blurb": blurb[:280],
                "observed_at": today.isoformat(),
            }
        )
    return offers


def _fetch_feed_job(f, timeout, today):
    if f in WP_FEEDS:
        cfg = WP_FEEDS[f]
        try:
            xml = _fetch(cfg["url"], timeout)
        except Exception as exc:  # noqa: BLE001
            return ("feed", f, None, str(exc))
        return ("feed", f, parse_wp_feed(xml, f, cfg.get("currency", "€"), today), None)
    url = FEEDS.get(f, f)
    label = f if f in FEEDS else "custom"
    try:
        xml = _fetch(url, timeout)
    except Exception as exc:  # noqa: BLE001 - ein Feed darf ausfallen
        return ("feed", f, None, str(exc))
    return ("feed", f, parse_feed(xml, group=label, today=today), None)


def _search_job(query, timeout, today):
    try:
        doc = _fetch(_SEARCH_URL.format(urllib.parse.quote(query)), timeout)
    except Exception as exc:  # noqa: BLE001
        return ("search", query, None, str(exc))
    return ("search", query, parse_search(doc, query, today=today), None)


def collect(feeds=None, searches=None, timeout=15, today=None, workers=10):
    """Feeds + aktive Suchen parallel holen, parsen, nach URL deduplizieren.

    feeds:    Preset-Schlüssel (siehe FEEDS) oder volle URLs.
    searches: Suchbegriffe für die mydealz-Volltextsuche (z.B. 'hummer').
    Rückgabe: (offers, meta) — meta zählt Treffer/Fehler je Quelle.
    """
    if feeds is None:
        feeds = ["hot", "new", "lebensmittel", "reisen", "urlaub", "konzerte"]
    searches = searches or []
    jobs = [(_fetch_feed_job, f) for f in feeds] + [(_search_job, s) for s in searches]

    seen, meta = {}, {"ok": [], "failed": []}
    with _cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(fn, arg, timeout, today) for fn, arg in jobs]
        for fut in _cf.as_completed(futures):
            kind, name, got, err = fut.result()
            tag = name if kind == "feed" else f"🔎{name}"
            if err is not None:
                meta["failed"].append((tag, err))
                continue
            for o in got:
                if o["url"] and o["url"] not in seen:
                    seen[o["url"]] = o
            meta["ok"].append((tag, len(got)))
    return list(seen.values()), meta


def fetch_offers(feeds=None, timeout=15, today=None):
    """Rückwärtskompatibel: nur Feeds (ohne aktive Suche)."""
    return collect(feeds=feeds, searches=None, timeout=timeout, today=today)
