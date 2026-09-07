"""Angebots-Quellen.

- demo_source(): erzeugt deterministisch eine realistische Preishistorie + heutige
  Angebote (kein Netz nötig, ideal zum Ausprobieren & für Tests).
- rss_json_source(): optionaler generischer Fetcher für echte Quellen (RSS/JSON),
  konfigurierbar per URL + Feld-Mapping. Degradiert sauber ohne Netz.

Reine stdlib.
"""
from __future__ import annotations

import datetime
import json
import random
import urllib.request

from analyze import product_key


# --------------------------------------------------------------------------- #
# Demo-Katalog. weekday_disc = Anteil, um den der Artikel unter der Woche
# typischerweise günstiger ist (0.10 = ~10 % billiger Mo-Fr).
# --------------------------------------------------------------------------- #
_CATALOG = [
    # Genuss-Zugfahrten (Bahn: unter der Woche oft deutlich billiger)
    {"title": "Glacier Express Panoramafahrt", "brand": "RhB", "category": "Genuss-Bahn",
     "base": 349.0, "weekday_disc": 0.16, "url": "https://example.com/glacier"},
    {"title": "Bernina Express Tagesfahrt", "brand": "RhB", "category": "Genuss-Bahn",
     "base": 119.0, "weekday_disc": 0.13, "url": "https://example.com/bernina"},
    {"title": "Gourmetzug 4-Gang Dinner", "brand": "Dinnerzug", "category": "Genuss-Bahn",
     "base": 189.0, "weekday_disc": 0.11, "url": "https://example.com/gourmetzug"},
    # Sterne & Gourmet (Restaurants: Mo-Fr oft günstiger)
    {"title": "Sterne-Menü 5-Gang", "brand": "Guide-Restaurant", "category": "Fine Dining",
     "base": 145.0, "weekday_disc": 0.26, "url": "https://example.com/sternemenue"},
    {"title": "Chef's Table Tasting", "brand": "Gourmet-Küche", "category": "Fine Dining",
     "base": 219.0, "weekday_disc": 0.20, "url": "https://example.com/chefstable"},
    # Schlager-Konzerte
    {"title": "Schlager Open Air Ticket", "brand": "Festival", "category": "Konzert",
     "base": 79.0, "weekday_disc": 0.04, "url": "https://example.com/schlager"},
    {"title": "Helene Fischer Tribute Ticket", "brand": "Arena", "category": "Konzert",
     "base": 59.0, "weekday_disc": 0.07, "url": "https://example.com/tribute"},
    # Delikatessen (Hummer / Königskrabbe / Käsefondue)
    {"title": "Ganzer Hummer 500g", "brand": "Fischmarkt", "category": "Delikatessen",
     "base": 39.0, "weekday_disc": 0.10, "url": "https://example.com/hummer"},
    {"title": "Königskrabben-Beine 1kg", "brand": "Fischmarkt", "category": "Delikatessen",
     "base": 89.0, "weekday_disc": 0.12, "url": "https://example.com/koenigskrabbe"},
    {"title": "Käsefondue für 2 Personen", "brand": "Alpenkäserei", "category": "Delikatessen",
     "base": 45.0, "weekday_disc": 0.18, "url": "https://example.com/fondue"},
    # Touri-Erlebnisse
    {"title": "Therme Tagesticket", "brand": "Therme", "category": "Erlebnis",
     "base": 49.0, "weekday_disc": 0.24, "url": "https://example.com/therme"},
    {"title": "Städtetrip Bootstour", "brand": "Sightseeing", "category": "Erlebnis",
     "base": 35.0, "weekday_disc": 0.10, "url": "https://example.com/bootstour"},
    # Ausreißer ohne Interessen-Bezug (Rausch-Test)
    {"title": "Bürostuhl ErgoPlus", "brand": "OfficeCo", "category": "Büro",
     "base": 199.0, "weekday_disc": 0.02, "url": "https://example.com/buerostuhl"},
]

# Angebote, die HEUTE zusätzlich einen tiefen Aktionspreis bekommen (echtes Schnäppchen).
_TODAY_SALES = {
    "Sterne-Menü 5-Gang": 0.42,        # -42 % auf Basispreis
    "Königskrabben-Beine 1kg": 0.36,
    "Glacier Express Panoramafahrt": 0.32,
    "Therme Tagesticket": 0.35,
    "Ganzer Hummer 500g": 0.33,
}


def _price_for_day(item, day, rng):
    """Typischer Preis eines Artikels an einem Tag (mit Wochentags-Effekt + Rauschen)."""
    is_weekend = day.weekday() >= 5
    price = item["base"]
    if not is_weekend:
        price *= (1.0 - item["weekday_disc"])
    price *= (1.0 + rng.uniform(-0.03, 0.03))  # Marktrauschen
    return round(price, 2)


def demo_source(today=None, days=90, seed=42):
    """Erzeuge (offers, history) deterministisch.

    offers:  Liste heutiger Angebote (dicts mit title/brand/category/price/...).
    history: dict product_key -> Liste {"date","price"} der letzten `days` Tage.
    """
    if today is None:
        today = datetime.date.today()
    rng = random.Random(seed)

    history = {}
    for item in _CATALOG:
        key = product_key(item)
        points = []
        for d in range(days, 0, -1):
            day = today - datetime.timedelta(days=d)
            points.append({"date": day.isoformat(), "price": _price_for_day(item, day, rng)})
        history[key] = points

    offers = []
    for item in _CATALOG:
        price = _price_for_day(item, today, rng)
        sale = _TODAY_SALES.get(item["title"])
        if sale:
            price = round(item["base"] * (1.0 - sale), 2)
        offers.append(
            {
                "title": item["title"],
                "brand": item["brand"],
                "category": item["category"],
                "price": price,
                "currency": "€",
                "url": item["url"],
                "source": "demo",
                "observed_at": today.isoformat(),
            }
        )
    return offers, history


# --------------------------------------------------------------------------- #
# Optionale echte Quelle (generisch). Braucht Netz; degradiert sauber.
# --------------------------------------------------------------------------- #
def rss_json_source(url, mapping, timeout=10):
    """Hole Angebote aus einer JSON-Liste und mappe Felder.

    mapping z.B. {"title":"name","price":"amount","brand":"vendor",...}.
    Gibt (offers, {}) zurück; History muss extern gepflegt werden.
    Bei Netzwerkfehler: ([], {}).
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - bewusst tolerant
        print(f"[warn] Quelle nicht erreichbar ({url}): {exc}")
        return [], {}

    items = raw if isinstance(raw, list) else raw.get("items", [])
    offers = []
    for it in items:
        try:
            offers.append(
                {
                    "title": str(it[mapping["title"]]),
                    "brand": str(it.get(mapping.get("brand", ""), "")),
                    "category": str(it.get(mapping.get("category", ""), "")),
                    "price": float(it[mapping["price"]]),
                    "currency": str(it.get(mapping.get("currency", ""), "€")) or "€",
                    "url": str(it.get(mapping.get("url", ""), "")),
                    "source": url,
                    "observed_at": datetime.date.today().isoformat(),
                }
            )
        except (KeyError, ValueError, TypeError):
            continue
    return offers, {}
