"""Rapport HTML du Parameter Lab (lab/rapport.html), généré depuis lab/results/*.json."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from ..config import ROOT
from .stats import ROBUSTNESS

RES = ROOT / "lab" / "results"

CRIT_LABEL = {
    "C1": "gain d'espérance IS ≥ 0,03 R et R total ≥ référence",
    "C2": "valeurs voisines aussi meilleures (plateau)",
    "C3": "au moins 50 % des trades conservés",
    "C4": "gain maintenu sans les 3 plus gros gagnants",
    "C5": "au moins 2 paires sur 3 non dégradées",
    "C6": "au moins 2 mois IS sur 3 non dégradés",
    "C7": "drawdown IS pas plus de 10 % pire",
    "C8": "validation (juin–juillet) non dégradée",
    "C9": "pas de coupe des gros gagnants (gain moyen −25 % max)",
    "C10": "au moins 10 trades IS modifiés (assez de preuves)",
    "C11": "gain positif sans les 2 changements les plus favorables",
    "C12": "au moins 5 trades modifiés en validation",
}

BLOCK_TITLE = {"A": "Bloc A — sorties, gestion du profit, durée", "B": "Bloc B — filtres de session, paire, régime",
               "C": "Bloc C — paramètres propres aux stratégies", "D": "Bloc D — Strategy Router"}

ROUTE_NOTE = {
    "A": "Mêmes entrées, sorties différentes : l'effet se lit trade par trade.",
    "B": "Filtres : on retire des trades. Un filtre n'est retenu que si les trades retirés perdaient vraiment, "
         "sur assez de cas, sur plusieurs mois et en validation.",
    "C": "Chaque stratégie concernée est recalculée entièrement avec la valeur testée.",
    "D": "Le régime est recalculé à chaque cycle avec la définition testée.",
}


def esc(x) -> str:
    return html.escape(str(x))


def fmt_val(v) -> str:
    if v is None:
        return "désactivé"
    if isinstance(v, bool):
        return "oui" if v else "non"
    if isinstance(v, list):
        if len(v) == 2 and all(isinstance(a, int) for a in v):
            return f"{v[0]:02d}h–{v[1]:02d}h"
        return ", ".join(map(str, v)) if v else "aucune"
    if isinstance(v, float):
        return f"{v:g}".replace(".", ",")
    return str(v)


def num(x, d=2, sign=False) -> str:
    if x is None:
        return "—"
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace(".", ",").replace("-", "−")


def delta_class(d: float | None, scale: float = 0.10) -> str:
    """Classe de couleur divergente (bleu = mieux, rouge = moins bien, gris = neutre)."""
    if d is None:
        return "d0"
    if abs(d) < 0.005:
        return "d0"
    k = min(3, int(abs(d) / scale * 3) + 1)
    return f"{'p' if d > 0 else 'n'}{k}"


def verdict(row) -> str:
    if row.get("is_base"):
        return '<span class="chip base">référence</span>'
    if row.get("accepted"):
        return '<span class="chip ok">✓ retenu</span>'
    fails = [k.split("_")[0] for k, v in (row.get("criteria") or {}).items() if v is False]
    title = "&#10;".join(f"{f} : {CRIT_LABEL.get(f, '')}" for f in fails)
    return f'<span class="chip no" title="{title}">✕ rejeté</span><span class="fails">{" ".join(fails)}</span>'


def param_table(p, base_is) -> str:
    rows = []
    for r in p["rows"]:
        s = r["summary"]
        i, v = s["IS"], s["VAL"]
        d = None if (i.get("exp") is None or base_is.get("exp") is None) else i["exp"] - base_is["exp"]
        width = 0 if d is None else min(50, abs(d) / 0.15 * 50)
        bar = (f'<span class="bar"><span class="{"pos" if (d or 0) > 0 else "neg"}" '
               f'style="width:{width:.1f}%;{"left:50%" if (d or 0) > 0 else f"left:{50 - width:.1f}%"}"></span></span>')
        rows.append(
            f'<tr class="{"isbase" if r.get("is_base") else ""}"><td class="v">{esc(fmt_val(r["value"]))}</td>'
            f'<td>{i["n"]}</td><td>{num(i.get("exp"), 3, True)}</td><td class="barcell">{bar}</td>'
            f'<td>{num(i.get("R"), 1, True)}</td><td>{num(i.get("dd"), 1)}</td>'
            f'<td>{v["n"]}</td><td>{num(v.get("R"), 1, True)}</td>'
            f'<td>{"" if r.get("is_base") else r.get("changed_IS", "—")}</td>'
            f'<td class="verdict">{verdict(r)}</td></tr>')
    return ('<div class="tablewrap"><table class="grid"><thead><tr><th>Valeur</th><th>Trades IS</th>'
            '<th>Espérance IS (R)</th><th class="barcell">vs référence</th><th>R total IS</th><th>DD IS (R)</th>'
            '<th>Trades VAL</th><th>R total VAL</th><th>Trades modifiés IS</th><th>Verdict</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def heatmap(title, cells, base_is, xlab, ylab) -> str:
    xs = sorted({c["x"] for c in cells}, key=lambda a: (a is None, a if a is not None else 0))
    ys = sorted({c["y"] for c in cells}, key=lambda a: (a is None, a if a is not None else 0))
    grid = {(c["x"], c["y"]): c for c in cells}
    head = "".join(f"<th>{esc(fmt_val(y))}</th>" for y in ys)
    body = []
    for x in xs:
        tds = []
        for y in ys:
            c = grid.get((x, y))
            if not c:
                tds.append("<td></td>")
                continue
            e = c["IS"].get("exp")
            d = None if e is None else e - base_is["exp"]
            val_r = c["VAL"].get("R")
            tds.append(f'<td class="hm {delta_class(d)}" title="IS : {c["IS"]["n"]} trades, espérance '
                       f'{num(e, 3, True)} R · VAL : {num(val_r, 1, True)} R"><b>{num(e, 3, True)}</b>'
                       f'<small>VAL {num(val_r, 1, True)}</small></td>')
        body.append(f"<tr><th>{esc(fmt_val(x))}</th>{''.join(tds)}</tr>")
    return (f'<figure class="heat"><figcaption>{esc(title)}</figcaption><div class="tablewrap">'
            f'<table class="hmt"><thead><tr><th class="corner">{esc(xlab)} ↓ · {esc(ylab)} →</th>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>'
            f'<p class="legend"><span class="sw p3"></span>mieux que la référence '
            f'<span class="sw d0"></span>≈ identique <span class="sw n3"></span>moins bien · '
            f'grand chiffre : espérance IS par trade ; petit : R total en validation</p></figure>')


def md_tables_to_html(md: str) -> str:
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("## "):
            out.append(f"<h3>{esc(ln[3:])}</h3>")
        elif ln.startswith("### "):
            out.append(f"<h4>{esc(ln[4:])}</h4>")
        elif ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[-| :]+\|$", lines[i + 1]):
            head = [c.strip() for c in ln.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            def cell(t):
                t = esc(t)
                t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
                return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
            out.append('<div class="tablewrap"><table class="inv"><thead><tr>' + "".join(f"<th>{cell(h)}</th>" for h in head)
                       + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{cell(c)}</td>" for c in r) + "</tr>"
                                                        for r in rows) + "</tbody></table></div>")
            continue
        i += 1
    return "\n".join(out)


def tiles(label, m) -> str:
    return (f'<div class="tile"><div class="tl">{esc(label)}</div>'
            f'<div class="tv">{num(m.get("R"), 1, True)} R</div>'
            f'<div class="ts">{m["n"]} trades · espérance {num(m.get("exp"), 3, True)} R · '
            f'gagnants {num((m.get("win") or 0) * 100, 0)} % · DD {num(m.get("dd"), 1)} R</div></div>')


def build(out_path: Path | None = None, extra: dict | None = None) -> Path:
    blocks = {b: json.loads((RES / f"block_{b}.json").read_text()) for b in "ABCD" if (RES / f"block_{b}.json").exists()}
    final = json.loads((RES / "final.json").read_text()) if (RES / "final.json").exists() else None
    inv = (ROOT / "lab" / "PARAMETRES.md").read_text(encoding="utf-8")
    ref = blocks["A"]["base"] if "A" in blocks else None
    n_var = sum(len(p["rows"]) - 1 for b in blocks.values() for p in b["params"]) + \
        sum(len(v) for b in blocks.values() for v in b.get("heatmaps", {}).values())
    kept_all = [(b, k) for b, r in blocks.items() for k in r.get("kept", [])]

    sec = []
    for b, r in blocks.items():
        base_is = r["base"]["IS"]
        parts = [f'<section id="bloc{b}"><h2>{esc(BLOCK_TITLE[b])}</h2><p class="lede">{esc(ROUTE_NOTE[b])}</p>']
        kept = r.get("kept", [])
        if kept:
            parts.append('<div class="callout ok"><b>Verrouillé :</b> ' +
                         ", ".join(f"{esc(k['param'])} = {esc(fmt_val(k['value']))}" for k in kept) + "</div>")
        else:
            parts.append('<div class="callout">Aucun réglage ne passe tous les critères : la valeur actuelle est conservée '
                         'pour chaque paramètre du bloc.</div>')
        parts.append(f'<p class="basebar">Référence du bloc : {base_is["n"]} trades IS, espérance '
                     f'{num(base_is["exp"], 3, True)} R, R total {num(base_is["R"], 1, True)}, DD {num(base_is["dd"], 1)} R · '
                     f'validation {num(r["base"]["VAL"]["R"], 1, True)} R sur {r["base"]["VAL"]["n"]} trades</p>')
        for title, cells in r.get("heatmaps", {}).items():
            xl, yl = [s.strip() for s in title.split("×")]
            parts.append(heatmap(title, cells, base_is, xl, yl))
        for p in r["params"]:
            if p["key"] == "new_trades_utc":
                cells = [{"x": row["value"][0], "y": row["value"][1], "IS": row["summary"]["IS"],
                          "VAL": row["summary"]["VAL"]} for row in p["rows"]]
                parts.append(heatmap("Horaires d'entrée : heure de début × heure de fin (UTC)", cells, base_is,
                                     "début", "fin"))
            parts.append(f'<details class="param"{" open" if any(x.get("accepted") for x in p["rows"]) else ""}>'
                         f'<summary><span class="pn">{esc(p["name"])}</span><span class="pk"><code>{esc(p["key"])}</code>'
                         f' · actuel : {esc(fmt_val(p["base"]))}</span></summary>{param_table(p, base_is)}</details>')
        parts.append("</section>")
        sec.append("".join(parts))

    fin_html = ""
    if final:
        rows = []
        for per, lab in (("IS", "In-sample (mars–mai)"), ("VAL", "Validation (juin–juillet)"),
                         ("OOS", "Hors-échantillon (août)"), ("OOS_B", "Hors-échantillon (sept. 2025–fév. 2026)")):
            if per not in final["reference"]:
                continue
            a, b = final["reference"][per], final["locked"][per]
            rows.append(f"<tr><th>{lab}</th><td>{a['n']}</td><td>{num(a.get('exp'), 3, True)}</td>"
                        f"<td>{num(a.get('R'), 1, True)}</td><td>{b['n']}</td><td>{num(b.get('exp'), 3, True)}</td>"
                        f"<td>{num(b.get('R'), 1, True)}</td></tr>")
        fin_html = ('<section id="final"><h2>Configuration verrouillée face à la V2</h2>'
                    + (extra or {}).get("final_note", "") +
                    '<div class="tablewrap"><table class="grid"><thead><tr><th>Période</th><th>V2 trades</th>'
                    '<th>V2 espérance</th><th>V2 R</th><th>Verrouillée trades</th><th>Verrouillée espérance</th>'
                    '<th>Verrouillée R</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div></section>")

    crit = "".join(f"<li><b>{k}</b> {esc(v)}</li>" for k, v in CRIT_LABEL.items())
    summary = (extra or {}).get("summary", "")
    doc = TEMPLATE.format(
        n_var=n_var, n_kept=len(kept_all), summary=summary,
        ref_tiles=(tiles("In-sample · mars → mai", ref["IS"]) + tiles("Validation · juin → juillet", ref["VAL"])) if ref else "",
        criteria=crit, blocks="".join(sec), final=fin_html, inventory=md_tables_to_html(inv),
        extra=(extra or {}).get("extra_html", ""))
    out = out_path or (ROOT / "lab" / "rapport.html")
    out.write_text(doc, encoding="utf-8")
    return out


TEMPLATE = """<title>Parameter Lab V2</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<style>
/* Carnet de laboratoire : colonne de lecture, tableaux de mesure, cartes de chaleur bleu/rouge autour de la référence */
:root {{
  --bg:#f7f8f9; --panel:#ffffff; --ink:#15191e; --ink2:#4c5561; --muted:#7c8591; --rule:#dfe3e8;
  --accent:#1c5cab; --ok:#0c7a0c; --okbg:#e6f3e6; --no:#8a2b2b; --nobg:#f7e9e9; --chip:#eef1f5;
  --p1:#cde2fb; --p2:#86b6ef; --p3:#2a78d6; --n1:#f6d4d3; --n2:#ec9a99; --n3:#d03b3b; --d0:#f0efec;
  --p3ink:#ffffff; --n3ink:#ffffff;
  --sans:"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono:"IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg:#101316; --panel:#171b20; --ink:#eef1f4; --ink2:#b4bcc6; --muted:#838c97; --rule:#2a3038;
  --accent:#6da7ec; --ok:#4cc24c; --okbg:#173017; --no:#e88; --nobg:#3a1d1d; --chip:#222830;
  --p1:#1c3656; --p2:#256abf; --p3:#5598e7; --n1:#4a2222; --n2:#9b3434; --n3:#e66767; --d0:#2a2d31;
  --p3ink:#0b0e12; --n3ink:#0b0e12; color-scheme:dark; }} }}
:root[data-theme="dark"] {{
  --bg:#101316; --panel:#171b20; --ink:#eef1f4; --ink2:#b4bcc6; --muted:#838c97; --rule:#2a3038;
  --accent:#6da7ec; --ok:#4cc24c; --okbg:#173017; --no:#e88; --nobg:#3a1d1d; --chip:#222830;
  --p1:#1c3656; --p2:#256abf; --p3:#5598e7; --n1:#4a2222; --n2:#9b3434; --n3:#e66767; --d0:#2a2d31;
  --p3ink:#0b0e12; --n3ink:#0b0e12; color-scheme:dark; }}
body {{ background:var(--bg); color:var(--ink); font:15px/1.55 var(--sans); }}
.wrap {{ max-width:1080px; margin:0 auto; padding-inline:16px; padding-block:28px 64px; }}
header h1 {{ font-size:clamp(26px,4vw,36px); line-height:1.15; margin:0 0 6px; letter-spacing:-0.01em; text-wrap:balance; }}
header .eyebrow {{ font:600 12px/1 var(--mono); letter-spacing:.08em; text-transform:uppercase; color:var(--accent); }}
header p {{ color:var(--ink2); max-width:68ch; margin:8px 0 0; }}
h2 {{ font-size:22px; margin:44px 0 6px; text-wrap:balance; }}
h3 {{ font-size:17px; margin:26px 0 8px; }} h4 {{ font-size:15px; margin:18px 0 6px; color:var(--ink2); }}
.lede {{ color:var(--ink2); max-width:70ch; margin:0 0 12px; }}
nav.toc {{ display:flex; flex-wrap:wrap; gap:8px; margin:18px 0 0; }}
nav.toc a {{ font:500 13px/1 var(--sans); color:var(--accent); background:var(--chip); padding:8px 10px; border-radius:6px; text-decoration:none; }}
nav.toc a:focus-visible, summary:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
.summary {{ background:var(--panel); border:1px solid var(--rule); border-radius:10px; padding:16px 18px; margin:20px 0 0; max-width:78ch; }}
.summary p {{ margin:0 0 8px; }} .summary p:last-child {{ margin:0; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; margin:14px 0; }}
.tile {{ background:var(--panel); border:1px solid var(--rule); border-radius:10px; padding:14px 16px; min-width:0; }}
.tl {{ font:600 12px/1.2 var(--mono); letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }}
.tv {{ font:600 28px/1.2 var(--mono); margin:6px 0 4px; }} .ts {{ color:var(--ink2); font-size:13px; }}
ol.crit {{ columns:2 320px; padding-left:18px; margin:8px 0; color:var(--ink2); font-size:14px; }}
ol.crit li {{ break-inside:avoid; margin:0 0 4px; }} ol.crit b {{ font-family:var(--mono); color:var(--ink); margin-right:4px; }}
.callout {{ background:var(--chip); border-radius:8px; padding:10px 14px; margin:8px 0 10px; }}
.callout.ok {{ background:var(--okbg); }}
.basebar {{ font:13px/1.5 var(--mono); color:var(--muted); margin:6px 0 14px; }}
.tablewrap {{ overflow-x:auto; -webkit-overflow-scrolling:touch; }}
table {{ border-collapse:collapse; font-variant-numeric:tabular-nums; }}
table.grid, table.inv {{ width:100%; font-size:13.5px; }}
table.grid th, table.grid td, table.inv th, table.inv td {{ padding:7px 10px; border-bottom:1px solid var(--rule); text-align:right; white-space:nowrap; }}
table.grid th:first-child, table.grid td:first-child {{ text-align:left; }}
table.grid thead th, table.inv thead th {{ font:600 11.5px/1.2 var(--mono); letter-spacing:.04em; text-transform:uppercase; color:var(--muted); vertical-align:bottom; }}
table.grid td {{ font-family:var(--mono); }}
table.inv td, table.inv th {{ text-align:left; white-space:normal; vertical-align:top; }}
table.inv td {{ min-width:90px; }}
tr.isbase td {{ background:var(--chip); font-weight:600; }}
td.v {{ font-weight:600; }}
.barcell {{ width:120px; }}
.bar {{ display:block; position:relative; height:10px; width:120px; background:linear-gradient(var(--rule),var(--rule)) center/1px 100% no-repeat; }}
.bar span {{ position:absolute; top:1px; height:8px; border-radius:2px; }}
.bar .pos {{ background:var(--p3); }} .bar .neg {{ background:var(--n3); }}
.verdict {{ text-align:left !important; font-family:var(--sans) !important; }}
.chip {{ display:inline-block; font:600 12px/1 var(--sans); padding:4px 7px; border-radius:5px; background:var(--chip); color:var(--ink2); }}
.chip.ok {{ background:var(--okbg); color:var(--ok); }} .chip.no {{ background:var(--nobg); color:var(--no); cursor:help; }}
.chip.base {{ background:var(--panel); border:1px solid var(--rule); }}
.fails {{ font:12px/1 var(--mono); color:var(--muted); margin-left:6px; }}
details.param {{ background:var(--panel); border:1px solid var(--rule); border-radius:10px; margin:10px 0; padding:0 12px; }}
details.param > summary {{ cursor:pointer; padding:12px 0; display:flex; flex-wrap:wrap; gap:4px 12px; align-items:baseline; list-style:none; }}
details.param > summary::before {{ content:"▸"; color:var(--muted); }}
details.param[open] > summary::before {{ content:"▾"; }}
.pn {{ font-weight:600; }} .pk {{ color:var(--muted); font-size:13px; }}
details.param .tablewrap {{ padding-bottom:10px; }}
code {{ font:12.5px var(--mono); color:var(--ink2); }}
figure.heat {{ margin:16px 0 20px; background:var(--panel); border:1px solid var(--rule); border-radius:10px; padding:14px; }}
figure.heat figcaption {{ font-weight:600; margin:0 0 10px; }}
table.hmt th {{ font:500 12px/1.2 var(--mono); color:var(--muted); padding:6px 8px; text-align:center; white-space:nowrap; }}
table.hmt th.corner {{ text-align:left; font-size:11px; }}
table.hmt tbody th {{ text-align:right; }}
td.hm {{ width:84px; min-width:72px; height:52px; text-align:center; border:2px solid var(--panel); border-radius:4px; font-family:var(--mono); }}
td.hm b {{ display:block; font-size:13px; font-weight:600; }} td.hm small {{ display:block; font-size:10.5px; opacity:.8; }}
.p1 {{ background:var(--p1); color:var(--ink); }} .p2 {{ background:var(--p2); color:var(--ink); }} .p3 {{ background:var(--p3); color:var(--p3ink); }}
.n1 {{ background:var(--n1); color:var(--ink); }} .n2 {{ background:var(--n2); color:var(--ink); }} .n3 {{ background:var(--n3); color:var(--n3ink); }}
.d0 {{ background:var(--d0); color:var(--ink); }}
.legend {{ font-size:12.5px; color:var(--muted); margin:10px 0 0; }}
.sw {{ display:inline-block; width:12px; height:12px; border-radius:3px; vertical-align:-2px; margin:0 4px 0 10px; }}
.sw:first-child {{ margin-left:0; }}
footer {{ margin-top:48px; color:var(--muted); font-size:13px; max-width:75ch; }}
@media (max-width:560px) {{ .barcell {{ display:none; }} }}
</style>
<div class="wrap">
<header>
  <div class="eyebrow">Agent Forex · Parameter Lab</div>
  <h1>Parameter Lab V2</h1>
  <p>{n_var} variantes testées sur les vraies données Dukascopy M1 (EURUSD, GBPUSD, USDJPY), bloc par bloc, chacune autour de la valeur actuelle.
  Réglages retenus : <b>{n_kept}</b>. Le risque monétaire, les 30 minutes et le capital de 50 € n'ont jamais changé.</p>
  <nav class="toc"><a href="#synthese">Synthèse</a><a href="#protocole">Protocole</a><a href="#blocA">Bloc A</a><a href="#blocB">Bloc B</a><a href="#blocC">Bloc C</a><a href="#blocD">Bloc D</a><a href="#final">Hors-échantillon</a><a href="#inventaire">Inventaire</a></nav>
</header>
<section id="synthese"><div class="summary">{summary}</div></section>
<section id="protocole">
<h2>Protocole, fixé avant les tests</h2>
<p class="lede">Découpage des données : <b>in-sample</b> mars → mai 2026 (seul à servir au choix), <b>validation</b> juin → juillet (doit confirmer),
<b>hors-échantillon</b> août 2026 et septembre 2025 → février 2026 (regardés une seule fois, à la fin). Un réglage n'est retenu que s'il passe les 12 critères ;
sinon la valeur actuelle reste. Les blocs sont faits dans l'ordre A → B → C → D, chacun sur la configuration verrouillée du précédent.</p>
<div class="tiles">{ref_tiles}</div>
<ol class="crit">{criteria}</ol>
</section>
{blocks}
{final}
{extra}
<section id="inventaire">
<h2>Inventaire complet des paramètres</h2>
<p class="lede">Chaque constante du code est maintenant dans la configuration, avec la même valeur (rejeu identique vérifié). Origine : PDF = règle donnée par une source ;
adaptation = règle des sources chiffrée par nous ; choix technique = sans appui dans les sources.</p>
{inventory}
</section>
<footer>Simulateur du lab vérifié : il reproduit exactement le backtest GitHub de référence (148 trades, −1,97 €, 0 centime d'écart par trade).
Les tests restent statistiquement limités : environ 80 trades en in-sample, 45 en validation. Un effet inférieur à ~0,1 R par trade ne se distingue pas du hasard sur un tel échantillon.</footer>
</div>
"""
