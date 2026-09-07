"""Baut ein self-contained dashboard.html (Karten-Grid) aus den Angeboten.

Funktioniert für Live-Deals (mydealz: Bild + Temperatur) und für Demo-Daten
(mit Preisverlauf-Charts, Wochentag-Muster). Reine stdlib.
"""
from __future__ import annotations

import html
import json


def _esc(s):
    return html.escape(str(s if s is not None else ""))


def _temp_class(t):
    if t is None:
        return ""
    if t >= 500:
        return "t-hot"
    if t >= 200:
        return "t-warm"
    return "t-cool"


def _card(a, cur):
    cur = a.get("currency") or cur
    temp = a.get("temperature")
    price = a.get("price")
    price_txt = f'{price:.2f} {cur}' if price is not None else "Preis im Deal"
    orig = a.get("original_price")
    disc = a.get("discount_pct") or 0

    sub = []
    if orig:
        sub.append(f'<span class="orig">statt {orig:.2f} {cur}</span>')
    if disc:
        sub.append(f'<span class="pct">-{disc:.0f}%</span>')
    if a.get("is_weekday_deal"):
        s = a["weekday"]["weekday_saving_pct"]
        sub.append(f'<span class="wk">\U0001F4C5 Mo-Fr -{s:.0f}%</span>')

    badges = []
    if a.get("interest"):
        badges.append(f'<span class="b int">\U0001F3AF {_esc(a["interest"])}</span>')
    if a.get("is_schnaeppchen"):
        badges.append('<span class="b hot">\U0001F525 SCHNÄPPCHEN</span>')
    for sw in a.get("sweetspots", []):
        badges.append(
            f'<span class="b sweet" title="{_esc(sw["rationale"])}">'
            f'{sw["icon"]} {_esc(sw["name"])}</span>'
        )
    if a.get("group") and a.get("group") not in ("custom", "hot", "new", "trending"):
        badges.append(f'<span class="b grp">{_esc(a["group"])}</span>')

    img = a.get("image")
    thumb = (
        f'<div class="thumb" style="background-image:url(\'{_esc(img)}\')">'
        if img
        else '<div class="thumb noimg">'
    )
    temp_badge = (
        f'<span class="temp {_temp_class(temp)}">{temp}°</span>' if temp is not None else ""
    )
    title = _esc(a["title"])
    url = _esc(a.get("url", ""))
    merchant = _esc(a.get("brand", ""))

    data = (
        f'data-interest="{1 if a.get("interest") else 0}" '
        f'data-hot="{1 if a.get("is_hot") else 0}" '
        f'data-weekday="{1 if a.get("is_weekday_deal") else 0}" '
        f'data-sweet="{1 if a.get("sweetspots") else 0}" '
        f'data-deal="{1 if a.get("is_schnaeppchen") else 0}"'
    )
    return (
        f'<a class="card" href="{url}" target="_blank" rel="noopener" {data}>'
        f'{thumb}{temp_badge}</div>'
        f'<div class="body">'
        f'<div class="badges">{"".join(badges)}</div>'
        f'<div class="title">{title}</div>'
        f'<div class="price">{price_txt}'
        + (f' <span class="merchant">@ {merchant}</span>' if merchant else "")
        + "</div>"
        f'<div class="sub">{" ".join(sub)}</div>'
        f'<div class="bar"><span style="width:{min(a["deal_score"]*100,100):.0f}%"></span></div>'
        f"</div></a>"
    )


def _summary(analyzed, settings):
    def card(val, title, sub=""):
        return (f'<div class="s-card"><div class="s-val">{_esc(val)}</div>'
                f'<div class="s-title">{_esc(title)}</div>'
                f'<div class="s-sub">{_esc(sub)}</div></div>')

    n_int = sum(1 for a in analyzed if a.get("interest"))
    n_hot = sum(1 for a in analyzed if a.get("is_hot"))
    n_sweet = sum(1 for a in analyzed if a.get("sweetspots"))
    return "".join([
        card(len(analyzed), "Deals gefunden"),
        card(n_int, "Zu deinen Interessen", "\U0001F3AF passend"),
        card(n_sweet, "Sweet Spots", "\U0001F4A1 strukturell zu billig"),
        card(n_hot, "Heiße Deals", "\U0001F525 stark hochgevotet"),
    ])


def build_dashboard(analyzed, settings, generated_at, meta=None):
    cur = settings.get("currency", "€")
    cards = "".join(_card(a, cur) for a in analyzed)

    # Preisverlauf-Charts nur wenn eigene Historie da ist (Demo-Modus).
    charts = [
        {
            "title": a["title"],
            "labels": [p["date"][5:] for p in a["history"]],
            "prices": [p["price"] for p in a["history"]],
            "wd_mean": a["weekday"]["weekday_mean"],
            "we_mean": a["weekday"]["weekend_mean"],
        }
        for a in analyzed if a.get("history")
    ][:4]
    charts_section = ""
    if charts:
        charts_section = (
            '<h2>Preisverlauf der Top-Deals (Wochentag ⟷ Wochenende)</h2>'
            '<div class="grid" id="charts"></div>'
        )

    src = ""
    if meta and meta.get("ok"):
        feeds = ", ".join(f"{k} ({n})" for k, n in meta["ok"])
        src = f"Quelle: mydealz · Feeds: {_esc(feeds)}"

    return _TEMPLATE.format(
        generated_at=_esc(generated_at),
        summary=_summary(analyzed, settings),
        cards=cards,
        charts_section=charts_section,
        charts_json=json.dumps(charts),
        cur=cur,
        src=src,
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
          --week:#36cfc9; --int:#597ef7; --muted:#8a94a6; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:#e6e6e6; }}
  header {{ padding:22px 20px 6px; }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:0 20px 60px; }}
  h1 {{ margin:0; font-size:26px; }} h1 span {{ color:var(--accent); }}
  .sub {{ color:var(--muted); font-size:13px; margin-top:4px; }}
  .summary {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
             gap:14px; margin:20px 0; }}
  .s-card {{ background:var(--card); border-radius:12px; padding:16px; }}
  .s-val {{ font-size:30px; font-weight:700; color:var(--accent); }}
  .s-title {{ font-size:14px; margin-top:2px; }}
  .s-sub {{ font-size:12px; color:var(--muted); }}
  .filters {{ display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 20px; }}
  .filters button {{ background:var(--card); color:#e6e6e6; border:1px solid #2a3340;
    border-radius:20px; padding:7px 14px; font-size:13px; cursor:pointer; }}
  .filters button.active {{ background:var(--accent); color:#12161c; border-color:var(--accent);
    font-weight:600; }}
  h2 {{ font-size:16px; margin:26px 0 12px; }}
  .deals {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:16px; }}
  .card {{ background:var(--card); border-radius:14px; overflow:hidden; text-decoration:none;
    color:inherit; display:flex; flex-direction:column; transition:transform .12s; }}
  .card:hover {{ transform:translateY(-3px); }}
  .thumb {{ position:relative; height:150px; background-size:cover; background-position:center;
    background-color:#222b36; }}
  .thumb.noimg {{ background:linear-gradient(135deg,#232b36,#141a22); }}
  .temp {{ position:absolute; top:8px; left:8px; font-weight:700; font-size:13px;
    padding:3px 9px; border-radius:20px; background:#000a; }}
  .temp.t-hot {{ color:#fff; background:var(--hot); }}
  .temp.t-warm {{ color:#12161c; background:var(--accent); }}
  .temp.t-cool {{ color:#cfd6e0; }}
  .body {{ padding:12px 13px 13px; display:flex; flex-direction:column; gap:6px; flex:1; }}
  .badges {{ display:flex; flex-wrap:wrap; gap:5px; }}
  .b {{ font-size:10.5px; font-weight:600; padding:2px 7px; border-radius:20px; }}
  .b.int {{ background:#20293a; color:var(--int); }}
  .b.hot {{ background:var(--hot); color:#fff; }}
  .b.grp {{ background:#212a24; color:#7bd88f; }}
  .b.sweet {{ background:#2a2140; color:#b37feb; cursor:help; }}
  .title {{ font-size:14px; line-height:1.3; font-weight:600; }}
  .price {{ font-size:19px; font-weight:700; color:var(--accent); margin-top:auto; }}
  .merchant {{ font-size:12px; font-weight:400; color:var(--muted); }}
  .sub {{ font-size:12px; color:var(--muted); display:flex; gap:8px; flex-wrap:wrap; }}
  .orig {{ text-decoration:line-through; }} .pct {{ color:#ff7875; font-weight:600; }}
  .wk {{ color:var(--week); }}
  .bar {{ height:5px; background:#232b36; border-radius:3px; }}
  .bar span {{ display:block; height:100%; background:var(--accent); border-radius:3px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px; }}
  .chartbox {{ background:var(--card); border-radius:12px; padding:14px; }}
  .chartbox h3 {{ margin:0 0 4px; font-size:13px; }}
  .chartbox .meta {{ font-size:11px; color:var(--muted); margin-bottom:8px; }}
  footer {{ color:var(--muted); font-size:12px; margin-top:30px; }}
</style>
</head>
<body>
<header><div class="wrap">
  <h1><span>\U0001F3F7️ Schnäppchen</span>-Jäger</h1>
  <div class="sub">Live nach deinen Interessen · Stand {generated_at}</div>
</div></header>
<div class="wrap">
  <div class="summary">{summary}</div>
  <div class="filters">
    <button data-f="all" class="active">Alle</button>
    <button data-f="interest">\U0001F3AF Meine Interessen</button>
    <button data-f="sweet">\U0001F4A1 Sweet Spots</button>
    <button data-f="deal">\U0001F525 Nur Schnäppchen</button>
    <button data-f="weekday">\U0001F4C5 Wochentags billiger</button>
  </div>

  {charts_section}

  <h2>Deals nach Score</h2>
  <div class="deals" id="deals">{cards}</div>

  <footer>{src}</footer>
</div>
<script>
// Filter
const btns = document.querySelectorAll('.filters button');
const cards = [...document.querySelectorAll('#deals .card')];
btns.forEach(b => b.addEventListener('click', () => {{
  btns.forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  const f = b.dataset.f;
  cards.forEach(c => {{
    const show = f === 'all' || c.dataset[f] === '1';
    c.style.display = show ? '' : 'none';
  }});
}}));

// Optionale Preisverlauf-Charts (Demo)
const CHARTS = {charts_json};
const CUR = {cur!r};
const box = document.getElementById('charts');
if (box) CHARTS.forEach(c => {{
  const div = document.createElement('div');
  div.className = 'chartbox';
  const meta = (c.wd_mean!=null && c.we_mean!=null)
    ? `Ø Mo-Fr ${{c.wd_mean}} ${{CUR}} · Ø Sa/So ${{c.we_mean}} ${{CUR}}` : '';
  div.innerHTML = `<h3>${{c.title}}</h3><div class="meta">${{meta}}</div><canvas></canvas>`;
  box.appendChild(div);
  new Chart(div.querySelector('canvas'), {{
    type:'line',
    data:{{ labels:c.labels, datasets:[{{ data:c.prices, borderColor:'#ffb020',
      borderWidth:1.5, pointRadius:0, tension:.25 }}]}},
    options:{{ plugins:{{legend:{{display:false}}}},
      scales:{{ x:{{ ticks:{{maxTicksLimit:6,color:'#8a94a6'}}, grid:{{display:false}} }},
               y:{{ ticks:{{color:'#8a94a6'}}, grid:{{color:'#232b36'}} }} }} }}
  }});
}});
</script>
</body>
</html>
"""
