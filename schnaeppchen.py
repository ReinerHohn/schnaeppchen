#!/usr/bin/env python3
"""Schnäppchen-Jäger — durchsucht echte Angebote nach deinen Interessen.

Findet:
  * echte Schnäppchen (viel billiger als üblich)
  * Wochentags-Schnäppchen (Mo-Fr günstiger; nur mit eigener Historie)
  * Sweet Spots (strukturell zu billig: invasive Arten/Plage, Bruchware/B-Ware,
    Restposten/Abverkauf, Saison-Schwemme, Sammeldeals)

Quelle: mydealz.de (Community-Schnäppchen per RSS). Ohne Netz -> Demo-Daten.

Nutzung:
    python3 schnaeppchen.py                 # Live von mydealz -> Konsole + dashboard.html
    python3 schnaeppchen.py --source demo   # Demo-Daten (offline)
    python3 schnaeppchen.py --feeds hot,lebensmittel,reisen
    python3 schnaeppchen.py --json          # Ergebnis als JSON
    python3 schnaeppchen.py --open          # Dashboard im Browser
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import webbrowser

from analyze import analyze_all
from dashboard import build_dashboard


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def get_offers(source, feeds, settings):
    """(offers, history, meta) für die gewählte Quelle liefern."""
    if source == "demo":
        from sources import demo_source
        offers, history = demo_source(days=settings.get("history_days", 90))
        return offers, history, {"ok": [("demo", len(offers))], "failed": []}

    from mydealz import fetch_offers
    offers, meta = fetch_offers(feeds=feeds)
    if not offers:  # Netzproblem -> sauberer Fallback auf Demo
        print("[warn] Keine Live-Deals erreichbar – nutze Demo-Daten.")
        from sources import demo_source
        offers, history = demo_source(days=settings.get("history_days", 90))
        return offers, history, {"ok": [("demo (fallback)", len(offers))], "failed": meta["failed"]}
    return offers, {}, meta


def print_console(analyzed, settings, meta):
    cur = settings.get("currency", "€")
    ok = ", ".join(f"{k}:{n}" for k, n in meta.get("ok", []))
    print(f"\n🏷️  SCHNÄPPCHEN-JÄGER  ({ok})\n" + "=" * 64)
    shown = 0
    for a in analyzed[: settings.get("top_n", 60)]:
        if not a["is_schnaeppchen"] and a["deal_score"] < settings.get("min_deal_score", 0.0):
            continue
        flags = []
        if a["is_schnaeppchen"]:
            flags.append("🔥 SCHNÄPPCHEN")
        for sw in a.get("sweetspots", []):
            flags.append(f"{sw['icon']} {sw['name']}")
        if a["is_weekday_deal"]:
            flags.append(f"📅 Mo-Fr −{a['weekday']['weekday_saving_pct']:.0f}%")
        temp = f"{a['temperature']}° " if a.get("temperature") is not None else ""
        price = f"{a['price']:.2f} {cur}" if a.get("price") is not None else "Preis im Deal"
        interest = f"  · {a['interest']}" if a["interest"] else ""
        print(f"\n[{a['deal_score']:.2f}] {temp}{a['title'][:70]}{interest}")
        print(f"    {price}" + (f"  @ {a['brand']}" if a.get("brand") else "")
              + (f"  (statt {a['original_price']:.2f} {cur})" if a.get("original_price") else ""))
        if flags:
            print("    " + "   ".join(flags))
        shown += 1
    if not shown:
        print("\nKeine Treffer über der Schwelle. config.json anpassen.")
    print("\n" + "=" * 64)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Schnäppchen-Jäger")
    here = os.path.dirname(__file__)
    ap.add_argument("--config", default=os.path.join(here, "config.json"))
    ap.add_argument("--out", default=os.path.join(here, "dashboard.html"))
    ap.add_argument("--source", choices=["mydealz", "demo"], default=None)
    ap.add_argument("--feeds", default=None, help="Komma-Liste, z.B. hot,lebensmittel,reisen")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args(argv)

    config = load_config(args.config)
    interests = config["interests"]
    settings = config.get("settings", {})
    sweetspots = config.get("sweetspots")  # None -> Defaults in sweetspots.py

    source = args.source or settings.get("source", "mydealz")
    feeds = args.feeds.split(",") if args.feeds else settings.get("feeds")

    offers, history, meta = get_offers(source, feeds, settings)
    analyzed = analyze_all(offers, history, interests, settings, sweetspots)

    if args.json:
        for a in analyzed:
            a.pop("history", None)
        print(json.dumps(analyzed, ensure_ascii=False, indent=2))
        return 0

    generated_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    html = build_dashboard(analyzed, settings, generated_at, meta)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)

    print_console(analyzed, settings, meta)
    print(f"Dashboard: {args.out}  ({len(analyzed)} Deals)")
    if args.open and not os.environ.get("NO_OPEN"):
        webbrowser.open("file://" + os.path.abspath(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
