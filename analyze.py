"""Angebots-Analyse: echtes Schnäppchen (viel billiger als üblich) + Wochentags-Muster.

Reine stdlib. Alle Funktionen sind deterministisch und einzeln testbar.
"""
from __future__ import annotations

import datetime
import re
import unicodedata


# --------------------------------------------------------------------------- #
# Kleine Statistik-Helfer
# --------------------------------------------------------------------------- #
def median(values):
    """Median einer Zahlenliste (leere Liste -> None)."""
    xs = sorted(v for v in values if v is not None)
    n = len(xs)
    if n == 0:
        return None
    mid = n // 2
    if n % 2:
        return float(xs[mid])
    return (xs[mid - 1] + xs[mid]) / 2.0


def _mean(values):
    xs = [v for v in values if v is not None]
    return sum(xs) / len(xs) if xs else None


def normalize(text):
    """Klein, ohne Akzente, alnum+space -> für robusten Keyword-Match & Produkt-Key."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def product_key(offer):
    """Stabiler Schlüssel für die Preishistorie (Marke + Titel normalisiert)."""
    return normalize(f"{offer.get('brand', '')} {offer.get('title', '')}")


def keyword_matches(keyword, text):
    """Robuster Keyword-Treffer.

    * Mehrwort-Begriffe ('glacier express'): als Phrase (Teilstring) prüfen.
    * Lange Einzelwörter (>=5, 'krabbe', 'hummer'): Teilstring — fängt deutsche
      Komposita ('krabbe' in 'Königskrabben', 'hummer' in 'Hummersuppe').
    * Kurze Einzelwörter (<5, 'spa', 'rigi', 'wels'): nur als GANZES Wort, sonst
      Rauschen ('spa' in 'Spare', 'rigi' in 'Original', 'wels' in 'Edelweiss').
    """
    k = normalize(keyword)
    if not k:
        return False
    hay = normalize(text)
    if " " in k or len(k) >= 5:
        return k in hay
    return k in hay.split()  # kurz -> nur als ganzes Wort ('spa' != 'Spare')


# --------------------------------------------------------------------------- #
# Preis-Kennzahlen
# --------------------------------------------------------------------------- #
def typical_price(history_points):
    """'Üblicher' Preis = Median der Historie (robust gegen Ausreißer/Aktionen)."""
    return median([p["price"] for p in history_points])


def discount_pct(current, typical):
    """Rabatt gegenüber dem üblichen Preis in Prozent (0..100). Negativ = teurer."""
    if not typical or typical <= 0 or current is None:
        return 0.0
    return round((typical - current) / typical * 100.0, 1)


def _is_weekend(iso_date):
    return datetime.date.fromisoformat(iso_date).weekday() >= 5  # 5=Sa, 6=So


def weekday_stats(history_points):
    """Vergleicht Wochentags- vs. Wochenend-Preise.

    Rückgabe: dict mit weekday_mean, weekend_mean und weekday_saving_pct
    (positiv => unter der Woche billiger). None-Felder wenn zu wenig Daten.
    """
    wd = [p["price"] for p in history_points if not _is_weekend(p["date"])]
    we = [p["price"] for p in history_points if _is_weekend(p["date"])]
    wd_mean, we_mean = _mean(wd), _mean(we)
    saving = None
    if wd_mean is not None and we_mean and we_mean > 0:
        saving = round((we_mean - wd_mean) / we_mean * 100.0, 1)
    return {
        "weekday_mean": round(wd_mean, 2) if wd_mean is not None else None,
        "weekend_mean": round(we_mean, 2) if we_mean is not None else None,
        "weekday_saving_pct": saving,
        "n_weekday": len(wd),
        "n_weekend": len(we),
    }


# --------------------------------------------------------------------------- #
# Interessen-Zuordnung
# --------------------------------------------------------------------------- #
def match_interest(offer, interests):
    """Bestes passendes Interessen-Profil finden.

    Match über Keyword-Treffer im (normalisierten) Titel/Kategorie/Marke.
    Rückgabe: (interest|None, matched_keywords, hits).
    """
    text = f"{offer.get('title','')} {offer.get('brand','')} {offer.get('category','')}"
    best = (None, [], 0)
    for it in interests:
        matched = [kw for kw in it.get("keywords", []) if keyword_matches(kw, text)]
        # Kategorie zählt als zusätzlicher Treffer
        if it.get("category") and normalize(it["category"]) == normalize(offer.get("category", "")):
            hits = len(matched) + 1
        else:
            hits = len(matched)
        if hits > best[2]:
            best = (it, matched, hits)
    return best


# --------------------------------------------------------------------------- #
# Gesamt-Bewertung eines Angebots
# --------------------------------------------------------------------------- #
def analyze_offer(offer, history, interests, settings, sweetspots=None):
    """Ein Angebot komplett bewerten.

    Funktioniert für zwei Fälle:
    * Demo/eigene Historie -> `history[key]` liefert übliche Preise & Wochentag-Muster.
    * Live-Quelle (z.B. mydealz) -> das Angebot bringt selbst mit:
        - `temperature`   community-Hotness (°), Haupt-"geil"-Signal
        - `original_price` bzw. `discount_pct` falls "statt X€ / -Y%" bekannt.

    Rückgabe: angereichertes dict (Original + Kennzahlen + Flags + deal_score).
    """
    key = product_key(offer)
    hist = history.get(key, [])
    price = offer.get("price")

    # 'Üblicher' Preis: Median der Historie, sonst der mitgelieferte Originalpreis.
    typ = typical_price(hist)
    if typ is None and offer.get("original_price"):
        typ = float(offer["original_price"])

    # Rabatt: explizit mitgeliefert schlägt berechnet.
    if offer.get("discount_pct") is not None:
        disc = round(float(offer["discount_pct"]), 1)
    else:
        disc = discount_pct(price, typ)

    wstats = weekday_stats(hist)
    saving = wstats["weekday_saving_pct"] or 0.0
    is_weekday_deal = saving >= settings.get("weekday_flag_pct", 8.0)

    interest, matched, hits = match_interest(offer, interests)

    # Sweet-Spot-Heuristiken: strukturelle Gründe für einen zu niedrigen Preis.
    from sweetspots import match_sweetspots  # lokal, um Import-Zyklus zu vermeiden
    sweet = match_sweetspots(offer, sweetspots)
    sweet_boost = min(sum(s["boost"] for s in sweet), 0.5)

    # Kuratieren: Massenware-/Müll-Blockliste (Nordsee, Discounter, Mobilfunk ...).
    exclude = settings.get("exclude", [])
    ex_text = " ".join(
        str(offer.get(k, "")) for k in ("title", "brand", "category", "blurb")
    )
    hit_exclude = next((kw for kw in exclude if keyword_matches(kw, ex_text)), None)
    is_excluded = hit_exclude is not None
    # Produkte aus bewusst konfigurierten Shops (Feinkost ODER Genuss-Events)
    # gelten als relevant.
    is_shop = str(offer.get("group", "")).startswith(("feinkost:", "event:"))
    # Relevant = Interesse ODER Sweet-Spot ODER Feinkost-Shop, und nicht geblockt.
    is_relevant = (bool(interest) or bool(sweet) or is_shop) and not is_excluded

    # Community-Hotness -> 0..1 (500° gilt als "top").
    temp = offer.get("temperature")
    hot_threshold = settings.get("hot_temp_threshold", 200)
    hotness = max(0.0, min((temp or 0) / 500.0, 1.0)) if temp is not None else 0.0
    community_hot = temp is not None and temp >= hot_threshold

    # Schnäppchen: passt zu einem Interesse, Preis im Rahmen und entweder hoher
    # Rabatt ODER von der Community stark hochgevotet.
    min_disc = interest.get("min_discount_pct", 20) if interest else 20
    max_price = interest.get("max_price") if interest else None
    price_ok = (max_price is None) or (price is None) or (price <= max_price)
    # Schnäppchen, wenn Preis passt UND entweder (Interesse + hoher Rabatt/hot)
    # ODER ein struktureller Sweet-Spot (Bruchware, invasiv, Restposten ...) greift.
    is_schnaeppchen = price_ok and (
        (bool(interest) and (disc >= min_disc or community_hot)) or bool(sweet)
    )

    # Deal-Score aus vier Signalen, gewichtet mit der Wichtigkeit des Interesses:
    #   base       Rabatt (oft nur bei Global-/Aktions-Deals bekannt)
    #   hotness    Community-Temperatur (nur globale Feeds)
    #   relevance  wie gut es zu einem Interesse passt (Keyword-Treffer)
    #   weekday    Mo-Fr-Bonus (nur mit eigener Historie)
    base = max(0.0, min(disc / 100.0, 1.0))
    relevance = min(hits, 3) / 3.0 if interest else 0.0
    weekday_bonus = max(0.0, saving / 100.0) * 0.5
    weight = interest.get("weight", 1.0) if interest else 0.6
    score = round(
        min(
            (0.45 * base + 0.35 * hotness + 0.4 * relevance + weekday_bonus + sweet_boost)
            * weight,
            1.0,
        ),
        3,
    )
    if is_shop:  # kuratierte Feinkost bekommt einen soliden Sockel
        score = max(score, 0.35)

    result = dict(offer)
    result.update(
        {
            "product_key": key,
            "typical_price": round(typ, 2) if typ is not None else None,
            "discount_pct": disc,
            "temperature": temp,
            "is_hot": community_hot,
            "weekday": wstats,
            "is_weekday_deal": is_weekday_deal,
            "interest": interest["name"] if interest else None,
            "matched_keywords": matched,
            "sweetspots": sweet,
            "is_schnaeppchen": is_schnaeppchen,
            "is_excluded": is_excluded,
            "excluded_by": hit_exclude,
            "is_relevant": is_relevant,
            "deal_score": score,
            "history": hist,
        }
    )
    return result


def analyze_all(offers, history, interests, settings, sweetspots=None):
    """Alle Angebote bewerten und nach Deal-Score absteigend sortieren."""
    analyzed = [
        analyze_offer(o, history, interests, settings, sweetspots) for o in offers
    ]
    analyzed.sort(key=lambda r: r["deal_score"], reverse=True)
    return analyzed
