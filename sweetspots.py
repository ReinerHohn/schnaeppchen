"""Sweet-Spot-Heuristiken: *warum* etwas strukturell zu billig ist.

Kernidee des Users: nicht nur "billiger als üblich", sondern wirtschaftlich
sinnvolle Sweet Spots erkennen — Gründe, aus denen ein Preis unter dem echten
Wert liegen SOLLTE:

  * Invasive Art / Plage (Königskrabbe, Blaukrabbe, Wollhandkrabbe, Nutria,
    Signalkrebs, Rotfeuerfisch ...): Überangebot, Verzehr ist ökologisch
    erwünscht -> sollte billig sein.
  * Bruchware / B-Ware / Retoure: optischer Mangel, voll funktionsfähig.
  * Abverkauf / Restposten / Überbestand: Lager muss geräumt werden.
  * Saison-Schwemme: zu viel Angebot zur Erntezeit.
  * Sammeldeal / Mengenrabatt: Stückpreis kippt.

Jede getroffene Heuristik liefert einen Boost auf den Deal-Score und eine
Begründung fürs Dashboard. Reine stdlib.
"""
from __future__ import annotations

from analyze import normalize

# Standard-Heuristiken. In config.json unter "sweetspots" überschreibbar/erweiterbar.
DEFAULT_SWEETSPOTS = [
    {
        "name": "Invasive Delikatesse",
        "icon": "\U0001F980",  # 🦀
        "keywords": [
            "königskrabbe", "koenigskrabbe", "king crab", "blaukrabbe", "blue crab",
            "wollhandkrabbe", "signalkrebs", "sumpfkrebs", "nutria", "rotfeuerfisch",
            "lionfish", "wels", "waschbär", "wildschwein", "amerikanischer flusskrebs",
        ],
        "rationale": "Invasive Art / Plage: Überangebot, Verzehr ökologisch erwünscht → sollte günstig sein.",
        "boost": 0.30,
    },
    {
        "name": "Bruchware / B-Ware",
        "icon": "\U0001F4E6",  # 📦
        "keywords": [
            "bruch", "bruchware", "b-ware", "b ware", "zweite wahl", "2. wahl",
            "retoure", "open box", "geöffnet", "aussteller", "vorführ", "mängelexemplar",
            "kosmetisch", "kratzer", "generalüberholt", "refurbished", "gebraucht",
        ],
        "rationale": "Nur optischer Mangel, voll funktionsfähig → deutlich unter Neupreis.",
        "boost": 0.22,
    },
    {
        "name": "Abverkauf / Restposten",
        "icon": "\U0001F3F7",  # 🏷
        "keywords": [
            "abverkauf", "ausverkauf", "räumung", "raeumung", "restposten", "überbestand",
            "ueberbestand", "lagerräumung", "auslauf", "auslaufmodell", "sonderposten",
            "letzte chance", "clearance", "sale bis",
        ],
        "rationale": "Lager/Auslauf muss raus → Preis fällt unter Marktwert.",
        "boost": 0.18,
    },
    {
        "name": "Saison-Schwemme",
        "icon": "\U0001F33E",  # 🌾
        "keywords": [
            "schwemme", "überschuss", "ueberschuss", "erntefrisch", "hauptsaison",
            "glut", "überproduktion",
        ],
        "rationale": "Saisonales Überangebot drückt den Preis.",
        "boost": 0.14,
    },
    {
        "name": "Sammeldeal / Menge",
        "icon": "\U0001F9EE",  # 🧮
        "keywords": [
            "sammeldeal", "mengenrabatt", "staffelpreis", "großpack", "grosspack",
            "palette", "vorratspack", "multipack", "bundle",
        ],
        "rationale": "Stückpreis kippt durch Menge/Bündel.",
        "boost": 0.10,
    },
]


def match_sweetspots(offer, sweetspots=None):
    """Alle zutreffenden Sweet-Spot-Heuristiken für ein Angebot finden.

    Sucht in Titel + Händler + Kategorie + Beschreibungs-Blurb.
    Rückgabe: Liste von dicts (name, icon, rationale, boost, matched).
    """
    if sweetspots is None:
        sweetspots = DEFAULT_SWEETSPOTS
    hay = normalize(
        " ".join(str(offer.get(k, "")) for k in ("title", "brand", "category", "blurb"))
    )
    found = []
    for s in sweetspots:
        matched = [kw for kw in s.get("keywords", []) if normalize(kw) in hay]
        if matched:
            found.append(
                {
                    "name": s["name"],
                    "icon": s.get("icon", "\U0001F4A1"),
                    "rationale": s.get("rationale", ""),
                    "boost": float(s.get("boost", 0.1)),
                    "matched": matched,
                }
            )
    return found
