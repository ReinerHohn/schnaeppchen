# 🏷️ Schnäppchen-Jäger

Durchsucht **echte, aktuelle Angebote** (Live von [mydealz.de](https://www.mydealz.de),
Deutschlands größter Schnäppchen-Community) nach **deinen Interessen** und hebt vier
Arten von Treffern hervor:

1. **🔥 Echte Schnäppchen** – gerade *viel billiger als üblich* (hoher Rabatt bzw.
   von der Community stark hochgevotet).
2. **💡 Sweet Spots** – *strukturell zu billig*. Nicht nur „günstig", sondern mit
   wirtschaftlichem Grund, warum der Preis unter dem Wert liegt:
   - **🦀 Invasive Delikatesse** – Königskrabbe, Blaukrabbe, Wollhandkrabbe, Signalkrebs,
     Nutria, Wels … sind eine Plage → Überangebot, Verzehr ökologisch erwünscht.
   - **📦 Bruchware / B-Ware** – nur optischer Mangel, voll funktionsfähig.
   - **🏷 Abverkauf / Restposten** – Lager/Auslauf muss raus.
   - **🌾 Saison-Schwemme** und **🧮 Sammeldeal / Menge**.
3. **🎯 Deine Interessen** – Genuss-Zugfahrten (Glacier Express …), günstiges
   Sterne-/Gourmet-Essen, Schlager-Konzerttickets, Delikatessen, Touri-Erlebnisse.
4. **📅 Wochentags-Schnäppchen** – Mo–Fr günstiger als am Wochenende
   *(nur mit eigener Preishistorie, siehe Demo-Modus)*.

Jeder Deal bekommt einen **Deal-Score** aus vier Signalen: Rabatt · Community-Hotness (°) ·
Interessen-Relevanz · Sweet-Spot-Boost.

## Schnellstart

```bash
python3 schnaeppchen.py                 # LIVE von mydealz -> Konsole + dashboard.html
python3 schnaeppchen.py --open          # Dashboard direkt im Browser
python3 schnaeppchen.py --feeds hot,lebensmittel,reisen,konzerte
python3 schnaeppchen.py --source demo   # Offline-Demo (mit Preisverlauf-Charts)
python3 schnaeppchen.py --json          # Ergebnis als JSON
```

Keine Abhängigkeiten – **reine Python-Standardbibliothek** (Python 3.9+).
Das Dashboard ist eine einzelne, self-contained `dashboard.html` (Karten-Grid mit
Bildern, °-Hotness, Filter-Buttons; Chart.js via CDN). Ohne Netz fällt das Tool
automatisch auf Demo-Daten zurück.

## Datenquellen, Feeds & aktive Suche

Zwei Pepper-Plattformen mit gleichem Parser — **mydealz.de** (DE) und
**preisjaeger.at** (AT, `pj_`-Präfix) — plus **preispirat.ch** (CH, WordPress,
CHF; relevant für Bergbahnen/Fondue/Swiss-Reisen).

**Feeds** (`config.json → settings.feeds`) — Presets in `mydealz.py → FEEDS`:

| Bereich | Presets |
|---------|---------|
| Global | `hot`, `new`, `trending`, `pj_hot`, `pj_new` |
| Essen & Trinken | `lebensmittel`, `restaurant`, `supermarkt`, `getraenke`, `wein`, `kochen`, `kaffee`, `pj_supermarkt`, `pj_getraenke` |
| Reisen | `reisen`, `urlaub`, `hotel`, `fluege`, `pj_reisen`, `pj_urlaub` |
| Events | `konzerte`, `freizeitpark`, `kino`, `musical` |
| Sonstiges | `elektronik` |

**Aktive Suche** (`config.json → settings.searches`) — für Nischen, die selten in
den Standard-Feeds stehen (Hummer, Königskrabbe, Bergbahn, Käsefondue). Das Tool
ruft die mydealz-Volltextsuche pro Begriff auf, filtert Fuzzy-Rauschen
(hummer → *nicht* hummel) und zieht Preis/Rabatt aus dem Titel. Alle Feeds und
Suchen laufen **parallel** (≈2–3 s für ~34 Quellen).

```bash
python3 schnaeppchen.py --search hummer,königskrabbe,raclette
python3 schnaeppchen.py --feeds hot,lebensmittel,restaurant,reisen
```

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

## Exklusiv-Modus (Kuratierung)

Standardmäßig zeigt das Tool **nur kuratierte Deals**: solche, die zu einem
Interesse **oder** Sweet-Spot passen **und nicht** auf der Müll-Blockliste stehen.
Kein Massenware-Firehose (kein Nordsee, Kaufland, vegane Fleisch-Alternativen,
Tropical Islands, Discounter, Handytarife, Elektronik-Kram …).

- `config.json → exclude` — Blockliste (Händler/Marken/Kategorien), beliebig erweiterbar.
- `config.json → settings.only_relevant` (default `true`) — Kuratierung an/aus.
- CLI `--all` — Kuratierung einmalig aus (kompletter Firehose).

Die Konsole meldet z. B. `kuratiert: 47 von 245 Deals (0 Müll geblockt)`.

Interessen sind auf **exklusiv/aspirational** ausgelegt: Genuss-Zugfahrten,
Schweizer Bergbahnen, Sterne & Fine Dining, Exklusiv & Luxus (Kaviar, Trüffel,
Wagyu, Suite, Spa …), Edel-Seafood (Hummer/Königskrabbe), Käsefondue & Raclette.

## Sweet Spots anpassen

`config.json → sweetspots` ist eine editierbare Liste von Heuristiken. Jede hat
`keywords`, eine `rationale` (Begründung, erscheint als Tooltip) und einen `boost`
auf den Score. Neue Sweet Spots (z. B. weitere invasive Arten oder „Mindesthaltbarkeit
bald") einfach ergänzen.

## Aufbau

| Datei | Zweck |
|-------|-------|
| `schnaeppchen.py` | CLI: Quelle → Analyse → Konsole + Dashboard |
| `mydealz.py` | Live-Quelle: mydealz-RSS holen & parsen (°-Hotness, Preis, Händler, Rabatt) |
| `sweetspots.py` | Heuristik-Engine: *warum* etwas strukturell zu billig ist |
| `analyze.py` | Rabatt, Hotness, Wochentags-Muster, Interessen-Match, Deal-Score |
| `sources.py` | Offline-Demo-Datengenerator (+ generischer JSON-Fetcher) |
| `dashboard.py` | Baut die self-contained `dashboard.html` (Karten-Grid) |
| `config.json` | Interessen · Sweet Spots · Feeds · Schwellen |
| `tests/` | `python3 -m unittest discover tests` (21 Tests, netzfrei) |

## Tests

```bash
python3 -m unittest discover -s tests -v
```
