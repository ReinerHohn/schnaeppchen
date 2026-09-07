"""Baut ein self-contained dashboard.html aus den analysierten Angeboten."""
from __future__ import annotations

import html
import json


def _badge(text, cls):
    return f'<span class="badge {cls}">{html.escape(text)}</span>'


def _card(title, value, sub=""):
    return (
        f'<div class="card"><div class="card-val">{html.escape(str(value))}</div>'
        f'<div class="card-title">{html.escape(title)}</div>'
        f'<div class="card-sub">{html.escape(sub)}</div></div>'
    )


def build_dashboard(analyzed, settings, generated_at):
    cur = settings.get("currency", "€")
    n_deals = sum(1 for a in analyzed if a["is_schnaeppchen"])
    n_weekday = sum(1 for a in analyzed if a["is_weekday_deal"])
    best = analyzed[0] if analyzed else None

    cards = "".join(
        [
            _card("Angebote geprüft", len(analyzed)),
            _card("Echte Schnäppchen", n_deals, "viel billiger als üblich"),
            _card("Wochentags-Schnäppchen", n_weekday, "unter der Woche günstiger"),
            _card(
                "Top-Deal",
                (best["title"][:22] if best else "–"),
                (f'{best["discount_pct"]:.0f}% Rabatt' if best else ""),
            ),
        ]
    )

    rows = []
    charts = []
    for i, a in enumerate(analyzed):
        badges = []
        if a["is_schnaeppchen"]:
            badges.append(_badge("SCHNÄPPCHEN", "hot"))
        if a["is_weekday_deal"]:
            s = a["weekday"]["weekday_saving_pct"]
            badges.append(_badge(f"WOCHENTAGS −{s:.0f}%", "week"))
        if a["interest"]:
            badges.append(_badge(a["interest"], "int"))

        typ = f'{a["typical_price"]:.2f}' if a["typical_price"] is not None else "–"
        title_link = (
            f'<a href="{html.escape(a.get("url",""))}" target="_blank" rel="noopener">'
            f'{html.escape(a["title"])}</a>'
            if a.get("url")
            else html.escape(a["title"])
        )
        disc = a["discount_pct"]
        disc_cls = "pos" if disc > 0 else "neg"
        rows.append(
            f"<tr>"
            f'<td class="rank">{i+1}</td>'
            f"<td>{title_link}<div class='brand'>{html.escape(a.get('brand',''))} · "
            f"{html.escape(a.get('category',''))}</div>"
            f"<div>{''.join(badges)}</div></td>"
            f'<td class="num">{a["price"]:.2f} {cur}</td>'
            f'<td class="num">{typ} {cur}</td>'
            f'<td class="num {disc_cls}">{disc:+.0f}%</td>'
            f'<td class="num">{a["deal_score"]:.2f}'
            f'<div class="bar"><span style="width:{min(a["deal_score"]*100,100):.0f}%"></span></div></td>'
            f"</tr>"
        )
        charts.append(
            {
                "title": a["title"],
                "labels": [p["date"][5:] for p in a["history"]],
                "prices": [p["price"] for p in a["history"]],
                "wd_mean": a["weekday"]["weekday_mean"],
                "we_mean": a["weekday"]["weekend_mean"],
            }
        )

    top_charts = json.dumps(charts[:4])

    return _TEMPLATE.format(
        generated_at=html.escape(generated_at),
        cards=cards,
        rows="".join(rows),
        charts_json=top_charts,
        cur=cur,
    )


_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Schnäppchen-Jäger</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  :root {{ --bg:#0f1419; --card:#1a2029; --accent:#ffb020; --hot:#ff4d4f;
          --week:#36cfc9; --int:#597ef7; --pos:#52c41a; --neg:#8c8c8c; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:#e6e6e6; }}
  header {{ padding:24px 20px 8px; }}
  h1 {{ margin:0; font-size:26px; }}
  h1 span {{ color:var(--accent); }}
  .sub {{ color:#8a94a6; font-size:13px; margin-top:4px; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:0 20px 60px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
           gap:14px; margin:20px 0; }}
  .card {{ background:var(--card); border-radius:12px; padding:16px; }}
  .card-val {{ font-size:30px; font-weight:700; color:var(--accent); }}
  .card-title {{ font-size:14px; margin-top:2px; }}
  .card-sub {{ font-size:12px; color:#8a94a6; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card);
          border-radius:12px; overflow:hidden; }}
  th,td {{ padding:12px 12px; text-align:left; border-bottom:1px solid #232b36; }}
  th {{ font-size:12px; text-transform:uppercase; color:#8a94a6; letter-spacing:.04em; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  td.rank {{ color:#8a94a6; width:32px; }}
  a {{ color:#e6e6e6; text-decoration:none; }}
  a:hover {{ color:var(--accent); }}
  .brand {{ font-size:12px; color:#8a94a6; margin:2px 0 6px; }}
  .badge {{ display:inline-block; font-size:11px; font-weight:600; padding:2px 8px;
           border-radius:20px; margin-right:5px; margin-bottom:3px; }}
  .badge.hot {{ background:var(--hot); color:#fff; }}
  .badge.week {{ background:var(--week); color:#04302e; }}
  .badge.int {{ background:#20293a; color:var(--int); }}
  .pos {{ color:var(--pos); }} .neg {{ color:var(--neg); }}
  .bar {{ height:5px; background:#232b36; border-radius:3px; margin-top:4px; }}
  .bar span {{ display:block; height:100%; background:var(--accent); border-radius:3px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
          gap:16px; margin:22px 0; }}
  .chartbox {{ background:var(--card); border-radius:12px; padding:14px; }}
  .chartbox h3 {{ margin:0 0 4px; font-size:13px; font-weight:600; }}
  .chartbox .meta {{ font-size:11px; color:#8a94a6; margin-bottom:8px; }}
  h2 {{ font-size:16px; margin:26px 0 10px; }}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <h1><span>🏷️ Schnäppchen</span>-Jäger</h1>
    <div class="sub">Automatisch nach deinen Interessen · Stand {generated_at}</div>
  </div>
</header>
<div class="wrap">
  <div class="cards">{cards}</div>

  <h2>Preisverlauf der Top-Deals (Wochentag ⟷ Wochenende)</h2>
  <div class="grid" id="charts"></div>

  <h2>Alle Treffer nach Deal-Score</h2>
  <table>
    <thead><tr>
      <th>#</th><th>Artikel</th><th>Preis</th><th>üblich</th><th>Rabatt</th><th>Score</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
<script>
const CHARTS = {charts_json};
const CUR = {cur!r};
const box = document.getElementById('charts');
CHARTS.forEach((c, i) => {{
  const div = document.createElement('div');
  div.className = 'chartbox';
  const meta = (c.wd_mean!=null && c.we_mean!=null)
    ? `Ø Mo–Fr ${{c.wd_mean}} ${{CUR}} · Ø Sa/So ${{c.we_mean}} ${{CUR}}` : '';
  div.innerHTML = `<h3>${{c.title}}</h3><div class="meta">${{meta}}</div><canvas></canvas>`;
  box.appendChild(div);
  new Chart(div.querySelector('canvas'), {{
    type: 'line',
    data: {{ labels: c.labels, datasets: [{{
      data: c.prices, borderColor: '#ffb020', borderWidth: 1.5,
      pointRadius: 0, tension: 0.25, fill: false }}]}},
    options: {{ plugins:{{legend:{{display:false}}}},
      scales:{{ x:{{ ticks:{{maxTicksLimit:6, color:'#8a94a6'}}, grid:{{display:false}} }},
               y:{{ ticks:{{color:'#8a94a6'}}, grid:{{color:'#232b36'}} }} }} }}
  }});
}});
</script>
</body>
</html>
"""
