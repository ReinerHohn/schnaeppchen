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
   Sterne-/Gourmet-Essen, exklusive Genuss-Events (Degustationsdinner, Wein-/
   Champagner-Verkostungen, Kochkurse, Menü-/Winzerabende), Schlager-Konzerttickets,
   Delikatessen (Hummer/Krabbe/Kaviar/Trüffel), Touri-Erlebnisse.
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
python3 schnaeppchen.py --home "50667 Köln"   # Entfernungsfilter ab deinem Ort
```

## Entfernungsfilter & Route (offline)

Events/Erlebnisse und Bergbahn-/Reise-Deals haben einen **Ort** im Titel
(„Dinner Hopping Augsburg", „Glacier Express nach Zermatt"). Mit einem
**Startort** (`settings.home` in `config.json` oder `--home`) rechnet das Tool die
**Luftlinie** (Haversine) und blendet im Dashboard **Distanz-Filter** (≤50/100/200/
400 km) plus je Karte einen **🚗 Route-Link** (Google-Maps-Navigation) ein.

- Startort als `PLZ Ort` (`50667 Köln`), nur `Ort` oder `lat,lon`.
- Orte kommen aus einer eingebauten Tabelle (230 Einträge: DE/AT/CH-Städte,
  Bergbahnen sowie Ferien-Regionen wie Tirol, Allgäu, Salzburger Land, Schwarzwald
  – viele Hotel-/Reise-Deals nennen die Region statt der Stadt); unbekannte dt.
  PLZ nutzen einen groben Regions-Fallback. Kein Netz/API nötig.
- Versandfähige Feinkost-Shop-Produkte bekommen bewusst **keine** Entfernung.

Keine Abhängigkeiten – **reine Python-Standardbibliothek** (Python 3.9+).
Das Dashboard ist eine einzelne, self-contained `dashboard.html` (Karten-Grid mit
Bildern, °-Hotness, Filter-Buttons; Chart.js via CDN). Ohne Netz fällt das Tool
automatisch auf Demo-Daten zurück.

## Datenquellen, Feeds & aktive Suche

Drei Arten von Quellen:

- **Deal-Communities** (Pepper, gleicher Parser): mydealz.de (DE) + preisjaeger.at
  (AT, `pj_`) — plus WordPress-Blogs preispirat.ch (CH, CHF), urlaubspiraten.de,
  reisetiger.de, travel-dealz.de (Reise-Deals).
- **Aktive Suche** über die mydealz-Volltextsuche (Nischen).
- **Feinkost-/Seafood-Shops** (`config.json → settings.shops`): echte Hummer/
  Krabbe/Langusten-/Kaviar-/Trüffel-Produkte direkt aus Gourmet-Shops. Der Scraper
  liest die Shop-Sitemap, filtert Delikatessen-URLs und parst je Produktseite
  Name + Preis + Bild (server-gerendert). Erkennt Preise mit Währung vor *oder*
  nach der Zahl (`47,70 EUR`, `€ 26,97`) und Sitemap-Indizes (inkl. `.gz`).
  Mit dabei: **gourmetfleisch.de** (Shopware), **viani.de**, **bosfood.de** (JTL,
  Kaviar/Trüffel), **gustini.de** & **eataly.net** (ital. Delikatessen),
  **otto-gourmet.de** (Wagyu/Kobe/Dry-Aged/Kaviar), **gute-weine.de** (Premium-
  Weine/Champagner, `require:"/produkt/"`). Sitemap-Indizes werden am
  `<sitemapindex>`-Wurzelelement erkannt (auch Sub-Sitemaps ohne `.xml`-Endung).
  Weitere
  Shops per Eintrag `{name, sitemap, currency, encoding, match, exclude, require,
  kind, category}` – kein Code nötig:
  - `match` — URL muss einen dieser Substrings enthalten (Delikatessen-Filter).
  - `exclude` — URL darf keinen enthalten (Bücher, Blog, Non-Food …).
  - `require` — URL *muss* diesen Substring enthalten (z.B. `/produkt/`, um
    Kategorie-/Landing-Seiten mit Fehlpreisen auszublenden).
  - `kind`/`category` — `event`/`Event` macht aus dem Shop eine **Genuss-Event**-
    Quelle (Gruppe `event:<name>` statt `feinkost:<name>`).
- **Genuss-Event-Shops** (gleicher Scraper, `kind:"event"`): buchbare Erlebnisse –
  Kochkurse, Wein-/Whisky-/Gin-Verkostungen, Menü-/Dinner-Abende. Standardmäßig
  **mydays.de** & **jochen-schweizer.de** (`require` grenzt via `/p/`+`/l/` auf
  echte Event-Seiten ein). Im Dashboard eigener Filter **🍽️ Genuss-Events**.

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
| `schnaeppchen.py` | CLI: Quellen → Analyse → Kuratierung → Konsole + Dashboard |
| `mydealz.py` | Deal-Communities (RSS + Volltextsuche), Pepper + WordPress-Feeds |
| `shop.py` | Feinkost-/Seafood-Shop-Scraper (Sitemap → Produktseiten, Name+Preis) |
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
