# 🏷️ Schnäppchen-Jäger

Durchsucht Angebote nach **deinen Interessen** und hebt zwei Arten von Deals hervor:

1. **Echte Schnäppchen** – Artikel, die gerade *viel billiger als üblich* sind
   (Rabatt gegenüber dem typischen Preis der letzten Wochen).
2. **Wochentags-Schnäppchen** – Artikel, die *unter der Woche deutlich günstiger*
   sind als am Wochenende. Genau das, was du wolltest: „Highlights, die unter der
   Woche billiger sind".

Du gibst deine Interessen in `config.json` an (Stichwörter, Kategorie, Preisober­grenze,
Mindest­rabatt) – das Tool sucht, bewertet und baut ein Dashboard.

## Schnellstart

```bash
python3 schnaeppchen.py           # Demo-Daten: Konsolen-Report + dashboard.html
python3 schnaeppchen.py --open    # Dashboard direkt im Browser öffnen
python3 schnaeppchen.py --json    # Ergebnis als JSON (zum Weiterverarbeiten)
```

Keine Abhängigkeiten – **reine Python-Standardbibliothek** (Python 3.9+).
Das Dashboard ist eine einzelne, self-contained `dashboard.html` (Chart.js via CDN).

## Interessen anpassen

`config.json`:

```json
{
  "interests": [
    {
      "name": "Kaffee & Espresso",
      "keywords": ["espresso", "siebträger", "bohnen"],
      "category": "Küche",
      "max_price": 800,
      "min_discount_pct": 20,
      "weight": 1.5
    }
  ],
  "settings": { "weekday_flag_pct": 8.0, "min_deal_score": 0.30 }
}
```

- `keywords` / `category` – wonach gesucht wird
- `max_price` – teurer? kein Schnäppchen
- `min_discount_pct` – ab wann ein Preis als Schnäppchen zählt
- `weight` – wie wichtig dir dieses Interesse ist (Ranking)
- `weekday_flag_pct` – ab welcher Wochentags-Ersparnis das „📅 WOCHENTAGS"-Label gesetzt wird

## Wie „viel billiger als üblich" gemessen wird

Für jeden Artikel wird der **Median** der Preishistorie (Standard: 90 Tage) als
„üblicher Preis" genommen (robust gegen einzelne Ausreißer). Der Rabatt ist die
Abweichung des aktuellen Preises davon. Der **Deal-Score** kombiniert Rabatt +
Wochentags-Bonus, gewichtet mit der Wichtigkeit des Interesses.

## Echte Quellen anbinden

`sources.py` enthält neben der Demo einen generischen `rss_json_source(url, mapping)`,
der eine JSON-Angebotsliste holt und Felder mappt (z. B. `{"title":"name","price":"amount"}`).
Die Preishistorie kann dann fortlaufend in einer eigenen JSON-Datei gepflegt werden,
damit „billiger als üblich" und der Wochentags-Effekt über die Zeit erkannt werden.

## Aufbau

| Datei | Zweck |
|-------|-------|
| `schnaeppchen.py` | CLI: Quelle → Analyse → Konsole + Dashboard |
| `analyze.py` | Preis-Statistik, Rabatt, Wochentags-Muster, Interessen-Match, Score |
| `sources.py` | Demo-Datengenerator + optionaler echter Fetcher |
| `dashboard.py` | Baut die self-contained `dashboard.html` |
| `config.json` | Deine Interessen & Schwellen |
| `tests/` | `python3 -m unittest discover tests` |

## Tests

```bash
python3 -m unittest discover -s tests -v
```
