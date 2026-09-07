#!/usr/bin/env python3
"""Schnäppchen-Jäger — durchsucht Angebote nach deinen Interessen.

Findet echte Schnäppchen (viel billiger als üblich) und Wochentags-Schnäppchen
(unter der Woche deutlich günstiger als am Wochenende) und baut ein Dashboard.

Nutzung:
    python3 schnaeppchen.py                 # Demo-Daten, Konsole + dashboard.html
    python3 schnaeppchen.py --config x.json # eigene Interessen
    python3 schnaeppchen.py --json          # Ergebnis als JSON auf stdout
    python3 schnaeppchen.py --open          # dashboard.html im Browser öffnen

Reine stdlib.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import webbrowser

from analyze import analyze_all
from dashboard import build_dashboard
from sources import demo_source


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def print_console(analyzed, settings):
    cur = settings.get("currency", "€")
    top_n = settings.get("top_n", 25)
    print("\n🏷️  SCHNÄPPCHEN-JÄGER — Treffer nach Deal-Score\n" + "=" * 60)
    shown = 0
    for a in analyzed[: settings.get("top_n", 25)]:
        if a["deal_score"] < settings.get("min_deal_score", 0.0) and not a["is_schnaeppchen"]:
            continue
        flags = []
        if a["is_schnaeppchen"]:
            flags.append("🔥 SCHNÄPPCHEN")
        if a["is_weekday_deal"]:
            flags.append(f"📅 unter der Woche −{a['weekday']['weekday_saving_pct']:.0f}%")
        typ = f"{a['typical_price']:.2f}" if a["typical_price"] is not None else "?"
        print(
            f"\n[{a['deal_score']:.2f}] {a['title']}  ({a.get('brand','')})\n"
            f"    {a['price']:.2f} {cur}  (üblich {typ} {cur}, {a['discount_pct']:+.0f}%)"
            + (f"  · {a['interest']}" if a["interest"] else "")
        )
        if flags:
            print("    " + "   ".join(flags))
        shown += 1
    if not shown:
        print("\nKeine Treffer über der Schwelle. Interessen/Schwellen in config.json anpassen.")
    print("\n" + "=" * 60)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Schnäppchen-Jäger")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "config.json"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "dashboard.html"))
    ap.add_argument("--json", action="store_true", help="Ergebnis als JSON auf stdout")
    ap.add_argument("--open", action="store_true", help="Dashboard im Browser öffnen")
    ap.add_argument("--days", type=int, default=None, help="Länge der Preishistorie")
    args = ap.parse_args(argv)

    config = load_config(args.config)
    interests = config["interests"]
    settings = config.get("settings", {})
    days = args.days or settings.get("history_days", 90)

    offers, history = demo_source(days=days)
    analyzed = analyze_all(offers, history, interests, settings)

    if args.json:
        for a in analyzed:
            a.pop("history", None)  # kompakter
        print(json.dumps(analyzed, ensure_ascii=False, indent=2))
        return 0

    generated_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    html = build_dashboard(analyzed, settings, generated_at)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)

    print_console(analyzed, settings)
    print(f"Dashboard geschrieben: {args.out}")
    if args.open and not os.environ.get("NO_OPEN"):
        webbrowser.open("file://" + os.path.abspath(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
