"""Rapport Recherche V4 (HTML autonome) construit à partir des fichiers de research/v4/out/."""
from __future__ import annotations

import html
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
DST = Path(__file__).resolve().parent / "rapport_v4.html"


def J(name):
    p = OUT / name
    return json.loads(p.read_text()) if p.exists() else None


def e(x):
    return html.escape(str(x))


def n(x, d=3, sign=True):
    if x is None or x != x:
        return "—"
    return f"{x:+.{d}f}".replace(".", ",") if sign else f"{x:.{d}f}".replace(".", ",")


def cls(x):
    return "" if x is None or x != x else ("pos" if x > 0 else "neg")


def chip(text, kind):
    return f'<span class="chip {kind}">{e(text)}</span>'


def placebo_chart(rows):
    W, H, pl, pr, pt, pb = 760, 260, 44, 10, 16, 46
    vals = [r["exp"] for r in rows]
    lo, hi = min(min(vals), -0.25), max(max(vals), 0.15)
    lo, hi = -0.25, 0.15
    bw = (W - pl - pr) / len(rows)
    y = lambda v: pt + (hi - v) / (hi - lo) * (H - pt - pb)
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Espérance du fade selon l\'heure, Train">']
    for g in (-0.2, -0.1, 0, 0.1):
        parts.append(f'<line x1="{pl}" x2="{W - pr}" y1="{y(g):.1f}" y2="{y(g):.1f}" class="{"axis0" if g == 0 else "grid"}"/>'
                     f'<text x="{pl - 6}" y="{y(g) + 4:.1f}" class="tick" text-anchor="end">{n(g, 1)}</text>')
    for i, r in enumerate(rows):
        v = r["exp"]
        x = pl + i * bw + 2
        top, bot = (y(v), y(0)) if v >= 0 else (y(0), y(v))
        fix = r["time"] == "16:00"
        c = "barfix" if fix else ("barpos" if v > 0 else "barneg")
        parts.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw - 4:.1f}" height="{max(bot - top, 1):.1f}" rx="2" class="{c}">'
                     f'<title>{r["time"]} Londres · {r["n"]} trades · espérance {n(v)} R · t {n(r["t"], 2)}</title></rect>')
        if i % 2 == 0 or fix:
            parts.append(f'<text x="{x + (bw - 4) / 2:.1f}" y="{H - pb + 16}" class="tick{" fixlab" if fix else ""}" '
                         f'text-anchor="middle">{r["time"]}</text>')
        if fix:
            parts.append(f'<text x="{x + (bw - 4) / 2:.1f}" y="{top - 6:.1f}" class="fixlab" text-anchor="middle">fix</text>')
    parts.append(f'<text x="{pl}" y="{H - 6}" class="tick">heure de Londres (entrée 1 min après)</text></svg>')
    return "".join(parts)


def main():
    train, val, oos = J("train.json"), J("validation.json"), J("oos.json")
    crit, plac, router = J("critic_h3.json"), J("placebo.json"), J("router.json")
    sel = J("selection.json")

    # ---------- E : tableau Train / Validation / OOS
    rows = []
    for hyp, evs in train.items():
        s = sel[hyp]
        ev = next((x for x in evs if x["variant"] == s.get("variant")), None) or max(evs, key=lambda x: x["stats"]["exp"])
        st = ev["stats"]
        v = (val or {}).get(hyp)
        o = (oos or {}).get(hyp)
        dec = s["decision"]
        if v:
            dec = "CANDIDATE" if v["candidate"] else "REJECT (validation)"
        if o:
            dec = "RETENUE" if o["retained"] else "REJECT (hors-échantillon)"
        kind = "ok" if dec in ("RETENUE", "CANDIDATE", "KEEP FOR VALIDATION") else "no"
        label = "meilleure variante Train" if s.get("variant") is None else "variante figée"
        oos_cell = (f'<td class="{cls(o["OOS"]["exp"])}">{n(o["OOS"]["exp"])}</td><td>{o["OOS"]["n"]}</td><td>{n(o["OOS"]["pf"], 2, False)}</td>'
                    if o else ('<td colspan="3" class="muted">en attente des données 2024-2025</td>' if v and v["candidate"]
                               else '<td colspan="3" class="muted">non testée (rejetée avant)</td>'))
        val_cell = (f'<td class="{cls(v["VAL"]["exp"])}">{n(v["VAL"]["exp"])}</td><td>{v["VAL"]["n"]}</td><td>{n(v["VAL"]["pf"], 2, False)}</td>'
                    if v else '<td colspan="3" class="muted">non testée</td>')
        rows.append(f'<tr><th>{hyp}<small>{e(ev["variant"])} · {label}</small></th>'
                    f'<td class="{cls(st["exp"])}">{n(st["exp"])}</td><td>{st["n"]}</td><td>{n(st["t"], 2)}</td>'
                    f'{val_cell}{oos_cell}<td>{chip(dec, kind)}</td></tr>')
    table_e = "".join(rows)

    # ---------- détail H3
    crow = {r["name"]: r for r in crit["rows"]}
    def crow_html(names):
        out = []
        for k in names:
            r = crow[k]
            out.append(f'<tr><th>{e(k)}</th><td>{r["n"]}</td><td class="{cls(r["exp"])}">{n(r["exp"])}</td><td>{n(r["t"], 2)}</td>'
                       f'<td>{n(r["pf"], 2, False)}</td>' + "".join(f'<td class="{cls(r[p])}">{n(r[p])}</td>' for p in ("T1", "T2", "V1", "V2")) + "</tr>")
        return "".join(out)
    stress = crow_html(["RÉFÉRENCE k=0,5 stop 1,5 ATR 30 min", "k=0.25", "k=1.0", "stop 1.0 ATR", "stop 3.0 ATR",
                        "durée 15 min", "durée 20 min", "cible 1 R", "entrée retardée +2 min", "entrée retardée +5 min",
                        "sans fin de mois", "fin de mois seulement", "achats", "ventes", "EURUSD", "GBPUSD", "USDJPY",
                        "coût extra 0.2 pip par côté", "coût extra 0.5 pip par côté", "coût extra 1.0 pip par côté"])

    # ---------- router
    def pers(name):
        out = []
        for p in router[name]["persistence"]:
            if p["cells"] < 3:
                continue
            ss = "—" if p["same_sign"] is None else f'{p["same_sign"]:.0%}'
            out.append(f'<tr><th>{e(p["dims"])}</th><td>{p["cells"]}</td>'
                       f'<td class="{cls(p["rank_corr"])}">{n(p["rank_corr"], 2)}</td><td>{ss}</td></tr>')
        return "".join(out)
    v2full, h3full = router["V2"]["full"], router["H3"]["full"]

    oos_note = ""
    if oos and "H3" in oos:
        o = oos["H3"]
        q = "".join(f'<tr><th>{e(k)}</th><td>{x["n"]}</td><td class="{cls(x["exp"])}">{n(x["exp"])}</td><td>{n(x["pf"], 2, False)}</td></tr>'
                    for k, x in o["quarters"].items())
        p = "".join(f'<tr><th>{e(k)}</th><td>{x["n"]}</td><td class="{cls(x["exp"])}">{n(x["exp"])}</td><td>{n(x["pf"], 2, False)}</td></tr>'
                    for k, x in o["pairs"].items())
        oos_note = (f'<h3>Hors-échantillon verrouillé ({e(o["first"][:10])} → {e(o["last"][:10])})</h3>'
                    f'<p class="lede">Lu une seule fois, variante figée. {o["OOS"]["n"]} trades, espérance {n(o["OOS"]["exp"])} R, '
                    f'profit factor {n(o["OOS"]["pf"], 2, False)}, t {n(o["OOS"]["t"], 2)}.</p>'
                    f'<div class="two"><div class="tablewrap"><table class="grid"><thead><tr><th>Trimestre</th><th>n</th><th>Esp.</th><th>PF</th></tr></thead><tbody>{q}</tbody></table></div>'
                    f'<div class="tablewrap"><table class="grid"><thead><tr><th>Paire</th><th>n</th><th>Esp.</th><th>PF</th></tr></thead><tbody>{p}</tbody></table></div></div>')

    sm = J("summary.json") or {}
    summary = sm.get("html", "")
    doc = TEMPLATE.format(summary=summary, table_e=table_e, stress=stress, chart=placebo_chart(plac),
                          boot=f"[{n(crit['boot'][0])} ; {n(crit['boot'][1])}]",
                          pers_v2=pers("V2"), pers_h3=pers("H3"), v2cells=v2full["cells"],
                          v2med=n(v2full["median_n"], 0, False), h3cells=h3full["cells"], oos_note=oos_note,
                          drop=chip("DROP", "no"), insuf=chip("INSUFFICIENT DATA", ""), modify=chip("MODIFY", "")).replace(
                          "{RECO}", sm.get("reco", ""))
    DST.write_text(doc, encoding="utf-8")
    return DST


TEMPLATE = """<title>Recherche Forex V4</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<style>
/* Carnet de recherche : colonne de lecture, tableaux de mesure, un seul graphique (placebo horaire) */
:root {{
  --bg:#f7f8f9; --panel:#ffffff; --ink:#15191e; --ink2:#4c5561; --muted:#7c8591; --rule:#dfe3e8; --chip:#eef1f5;
  --accent:#1c5cab; --pos:#1c5cab; --neg:#b03a3a; --ok:#0c7a0c; --okbg:#e6f3e6; --no:#8a2b2b; --nobg:#f7e9e9;
  --barpos:#86b6ef; --barneg:#ec9a99; --barfix:#1c5cab;
  --sans:"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono:"IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg:#101316; --panel:#171b20; --ink:#eef1f4; --ink2:#b4bcc6; --muted:#838c97; --rule:#2a3038; --chip:#222830;
  --accent:#6da7ec; --pos:#7fb2f0; --neg:#ee8a8a; --ok:#4cc24c; --okbg:#173017; --no:#e88; --nobg:#3a1d1d;
  --barpos:#256abf; --barneg:#9b3434; --barfix:#8fc0ff; color-scheme:dark; }} }}
:root[data-theme="dark"] {{
  --bg:#101316; --panel:#171b20; --ink:#eef1f4; --ink2:#b4bcc6; --muted:#838c97; --rule:#2a3038; --chip:#222830;
  --accent:#6da7ec; --pos:#7fb2f0; --neg:#ee8a8a; --ok:#4cc24c; --okbg:#173017; --no:#e88; --nobg:#3a1d1d;
  --barpos:#256abf; --barneg:#9b3434; --barfix:#8fc0ff; color-scheme:dark; }}
body {{ background:var(--bg); color:var(--ink); font:15px/1.55 var(--sans); }}
.wrap {{ max-width:1040px; margin:0 auto; padding-inline:16px; padding-block:28px 64px; }}
.eyebrow {{ font:600 12px/1 var(--mono); letter-spacing:.08em; text-transform:uppercase; color:var(--accent); }}
h1 {{ font-size:clamp(26px,4vw,36px); line-height:1.15; margin:6px 0 6px; text-wrap:balance; }}
h2 {{ font-size:22px; margin:44px 0 8px; text-wrap:balance; }} h3 {{ font-size:17px; margin:24px 0 8px; }}
p {{ max-width:72ch; }} .lede {{ color:var(--ink2); margin:0 0 12px; }}
.summary {{ background:var(--panel); border:1px solid var(--rule); border-radius:10px; padding:16px 18px; margin:18px 0 0; max-width:80ch; }}
.summary p {{ margin:0 0 8px; }} .summary p:last-child {{ margin:0; }}
ul.f {{ padding-left:18px; max-width:76ch; }} ul.f li {{ margin:0 0 8px; }}
nav.toc {{ display:flex; flex-wrap:wrap; gap:8px; margin:16px 0 0; }}
nav.toc a {{ font:500 13px/1 var(--sans); color:var(--accent); background:var(--chip); padding:8px 10px; border-radius:6px; text-decoration:none; }}
nav.toc a:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
.tablewrap {{ overflow-x:auto; -webkit-overflow-scrolling:touch; min-width:0; }}
table {{ border-collapse:collapse; font-variant-numeric:tabular-nums; width:100%; font-size:13.5px; }}
th, td {{ padding:7px 10px; border-bottom:1px solid var(--rule); text-align:right; white-space:nowrap; }}
th:first-child, td:first-child {{ text-align:left; }}
thead th {{ font:600 11.5px/1.2 var(--mono); letter-spacing:.04em; text-transform:uppercase; color:var(--muted); vertical-align:bottom; }}
tbody th small {{ display:block; font:12px var(--mono); color:var(--muted); white-space:normal; }}
td {{ font-family:var(--mono); }} td.pos {{ color:var(--pos); font-weight:600; }} td.neg {{ color:var(--neg); }}
td.muted {{ color:var(--muted); font-family:var(--sans); text-align:center; }}
table.txt td, table.txt th {{ white-space:normal; text-align:left; vertical-align:top; font-family:var(--sans); }}
.chip {{ display:inline-block; font:600 12px/1 var(--sans); padding:4px 7px; border-radius:5px; background:var(--chip); color:var(--ink2); white-space:nowrap; }}
.chip.ok {{ background:var(--okbg); color:var(--ok); }} .chip.no {{ background:var(--nobg); color:var(--no); }}
figure {{ margin:14px 0 18px; background:var(--panel); border:1px solid var(--rule); border-radius:10px; padding:14px; }}
figcaption {{ font-weight:600; margin:0 0 8px; }} figure p {{ color:var(--ink2); font-size:13.5px; margin:8px 0 0; }}
svg {{ width:100%; height:auto; display:block; }}
.grid {{ stroke:var(--rule); stroke-width:1; }} .axis0 {{ stroke:var(--muted); stroke-width:1; }}
.tick {{ fill:var(--muted); font:11px var(--mono); }} .fixlab {{ fill:var(--ink); font:600 11px var(--mono); }}
.barpos {{ fill:var(--barpos); }} .barneg {{ fill:var(--barneg); }} .barfix {{ fill:var(--barfix); }}
.two {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:16px; }}
footer {{ margin-top:48px; color:var(--muted); font-size:13px; max-width:76ch; }}
</style>
<div class="wrap">
<div class="eyebrow">Agent Forex · branche research-v4</div>
<h1>Recherche Forex V4</h1>
<p class="lede">Trades de 5 à 30 minutes, EURUSD · GBPUSD · USDJPY, données Dukascopy M1 bid/ask réelles. Risque inchangé, baseline V2 non modifiée.</p>
<nav class="toc"><a href="#a">A · Échecs V2</a><a href="#b">B · Stratégies</a><a href="#pdf">Concepts PDF</a><a href="#c">C · Hypothèses</a><a href="#e">E · Résultats</a><a href="#h3">Fix de Londres</a><a href="#router">Router</a><a href="#f">F · Auto-critique</a><a href="#g">G · Suite</a></nav>
<div class="summary">{summary}</div>

<section id="a"><h2>A · Pourquoi V2 / V3 n'ont pas généralisé</h2>
<ul class="f">
<li><b>Les signaux ne disent rien du sens à 30 minutes.</b> Test du miroir sur 305 trades V2 (12 mois) : même instant, même stop, même cible, sens inverse. Signal −0,022 R, sens opposé −0,068 R, sans cible −0,009 R. L'écart ne se distingue pas du hasard. Par stratégie, DoubleTopBottom ferait mieux en sens inverse (−0,001 contre −0,111).</li>
<li><b>Les cibles sont celles d'un swing, pas d'un trade de 30 min.</b> Cible médiane = 1,5 à 2,9 fois le mouvement typique de 30 minutes à cette heure ; seuls 4 à 12 % des trades l'atteignent. 58 % des trades finissent au temps : leur résultat, c'est simplement « où est le prix 30 min plus tard ».</li>
<li><b>Le coût n'est pas le tueur principal</b> (spread ≈ 3 à 6 % du R avec les stops V2), mais il suffit à rendre négatif un système sans avantage : V2 ≈ entrées au hasard moins le spread.</li>
<li><b>Rien n'est stable d'une période à l'autre.</b> Les cellules stratégie × régime, × séance, × paire de sept.–fév. ont une corrélation de rang de −0,36 à +0,03 avec celles de mars–août, et ne gardent leur signe qu'une fois sur trois. BreakRetest : +0,13 R puis −0,20 R. C'est ce qui a piégé le Parameter Lab.</li>
<li><b>Les confirmations optionnelles n'aident pas.</b> « Tendance fraîche » est négative dans les deux périodes ; « killzone » change de signe.</li>
</ul></section>

<section id="b"><h2>B · Stratégies actuelles</h2>
<div class="tablewrap"><table class="txt"><thead><tr><th>Stratégie</th><th>Verdict</th><th>Pourquoi</th></tr></thead><tbody>
<tr><th>BreakRetest_v2</th><td>{drop}</td><td>84 trades ; +0,13 R puis −0,20 R ; aucune information de sens (miroir).</td></tr>
<tr><th>DoubleTopBottom_v1</th><td>{drop}</td><td>83 trades, négatif dans les deux périodes (−0,11 / −0,16) ; cellules NO_EDGE en tendance baissière et en forte volatilité.</td></tr>
<tr><th>FlagBreakout_v1</th><td>{drop}</td><td>102 trades, ≈ 0 R dans les deux périodes (t 0,4) : pas d'avantage à 30 min.</td></tr>
<tr><th>TrendPullback_v2</th><td>{insuf}</td><td>16 trades en 12 mois.</td></tr>
<tr><th>RangeFade_v2</th><td>{modify}</td><td>20 trades seulement, mais c'est la seule où le sens compte (miroir +0,42 contre −0,54). Même famille que H3 (retour à la moyenne) : à reformuler pour produire assez de trades.</td></tr>
<tr><th>SweepMSS_v2</th><td>{insuf}</td><td>≈ 0 trade en 12 mois : trop de conditions empilées pour 30 min.</td></tr>
</tbody></table></div></section>

<section id="pdf"><h2>Concepts des PDF face à l'horizon 5–30 min</h2>
<div class="tablewrap"><table class="txt"><thead><tr><th>Catégorie</th><th>Concepts</th><th>Ce que les données disent</th></tr></thead><tbody>
<tr><th>Compatible scalping</th><td>Le temps comme composante du setup (ICT : heures précises, killzones) · NO TRADE binaire (NNFX) · stops en ATR · coût du spread</td><td>Le seul avantage trouvé est purement horaire (fix de 16:00 Londres).</td></tr>
<tr><th>Adaptable (contexte, pas signal)</th><td>Liquidité nommée (Asie, PDH/PDL) · régime de volatilité</td><td>Le sweep-and-reclaim en signal d'entrée perd (H1, 8 variantes). Utile comme repère seulement.</td></tr>
<tr><th>Mal adapté à 30 min</th><td>Cibles sur structure / liquidité opposée avec R:R ≥ 1,5 · figures de tendance Daily/H4 (flag, double top, cassure-retest, pullback) · « tendance fraîche »</td><td>Cibles hors de portée ; pas d'information de sens ; « fraîche » négative.</td></tr>
<tr><th>À abandonner pour V4</th><td>Displacement ICT comme déclencheur de continuation · opening range breakout · indicateurs Trading Rush en signal (RSI, MACD, croisements) · chaîne complète SweepMSS / FVG / OTE</td><td>Continuation après displacement : −0,14 à −0,19 R (t −4 à −6) ; ORB : −0,15 à 0 R ; SweepMSS : ≈ 0 trade.</td></tr>
</tbody></table></div></section>

<section id="c"><h2>C · Hypothèses V4 (pré-enregistrées avant tout test)</h2>
<div class="tablewrap"><table class="txt"><thead><tr><th>Hypothèse</th><th>Idée et pourquoi 5–30 min</th><th>Où elle devrait marcher</th><th>Pourquoi elle pourrait échouer</th></tr></thead><tbody>
<tr><th>H1 Sweep &amp; reclaim</th><td>Les stops au-delà du haut/bas d'Asie ou du PDH/PDL sont chassés, puis le prix revient (Judas swing ICT). Mouvement rapide, donc court.</td><td>Ouvertures Londres / New York, range</td><td>Le dépassement peut être une vraie cassure ; signal trop fréquent pour porter de l'information.</td></tr>
<tr><th>H2 Opening range</th><td>Le sens de la cassure des 30 premières minutes d'une séance se prolonge.</td><td>Jours de tendance</td><td>Faux départs fréquents en FX, spread à l'ouverture.</td></tr>
<tr><th>H3 Fix de Londres</th><td>Le fix WM/Reuters de 16:00 Londres concentre des ordres de gestionnaires d'actifs ; le prix est poussé avant et se détend après. Effet documenté, durée de quelques minutes à une heure.</td><td>Tous régimes ; plus fort en fin de mois</td><td>Effet arbitré depuis la réforme du fix (fenêtre de 5 min) ; avantage minuscule en pips, sensible au coût d'exécution.</td></tr>
<tr><th>H4 Fix de Tokyo</th><td>Demande d'USD des importateurs japonais avant le fix de 9:55 (00:55 UTC), surtout les jours gotobi.</td><td>USDJPY, heure asiatique</td><td>Une seule paire, ~1 trade/jour : peu de données.</td></tr>
<tr><th>H5 Displacement M5</th><td>Test direct du concept ICT : une grosse bougie M5 se prolonge-t-elle ou s'essouffle-t-elle sur 30 min ?</td><td>Séances actives</td><td>Bruit pur à cette échelle.</td></tr>
</tbody></table></div></section>

<section id="e"><h2>E · Résultats Train / Validation / Hors-échantillon</h2>
<p class="lede">Espérance en R par trade, spread bid/ask inclus. Train = sept. 2025 → fév. 2026 ; validation = mars → août 2026 ; hors-échantillon verrouillé = sept. 2024 → août 2025, téléchargé exprès et jamais ouvert avant la fin.</p>
<div class="tablewrap"><table><thead><tr><th>Hypothèse</th><th>Train esp.</th><th>n</th><th>t</th><th>Valid. esp.</th><th>n</th><th>PF</th><th>OOS esp.</th><th>n</th><th>PF</th><th>Décision</th></tr></thead><tbody>{table_e}</tbody></table></div>
</section>

<section id="h3"><h2>H3 · Fix de Londres : la seule hypothèse qui tient</h2>
<p class="lede">Règle : à 16:00 Londres (heure d'été prise en compte), si le prix a bougé d'au moins 0,5 ATR(M5) dans les 30 minutes précédentes, prendre la position opposée à 16:01 ; stop 1,5 ATR ; sortie au bout de 30 minutes. Au plus un trade par paire et par jour.</p>
<figure><figcaption>Test placebo (Train) : la même règle à toutes les demi-heures</figcaption>{chart}
<p>Si c'était un simple retour à la moyenne valable à toute heure, toutes les barres seraient positives. Sur les 26 horaires, 16:00 est le seul positif dans les deux moitiés du Train avec t ≥ 2. L'effet est spécifique au fix. 19:30 (+0,10) montre qu'un horaire au hasard peut aussi sortir positif : la preuve tient à la validation et au hors-échantillon, pas à ce graphique seul.</p></figure>
<h3>Tests de robustesse (12 mois, aucune sélection)</h3>
<div class="tablewrap"><table><thead><tr><th>Variante</th><th>n</th><th>Esp.</th><th>t</th><th>PF</th><th>T1</th><th>T2</th><th>V1</th><th>V2</th></tr></thead><tbody>{stress}</tbody></table></div>
<p class="lede">Bootstrap de l'espérance sur 12 mois : IC 90 % {boot} R. Le gain moyen ne fait qu'environ 1,3 pip par trade : <b>un coût supplémentaire de 0,5 pip par côté l'annule</b>. Spread Dukascopy médian à 16:01 : 0,3 pip EURUSD, 0,6 GBPUSD, 0,3 USDJPY.</p>
{oos_note}
</section>

<section id="router"><h2>Router V4 : contexte d'abord, abstention par défaut</h2>
<p class="lede">Règle : une cellule stratégie × régime × séance × volatilité × paire n'est « EDGE » qu'avec au moins 30 trades et un intervalle de confiance entièrement positif ; « NO EDGE » s'il est entièrement négatif ; sinon UNKNOWN, donc NO TRADE. La matrice ne sert à filtrer que si les cellules sont persistantes d'une période à l'autre.</p>
<div class="two">
<div><h3>Stratégies V2</h3><p class="lede">Matrice complète : {v2cells} cellules, toutes UNKNOWN (médiane {v2med} trades par cellule). Persistance P1 → P2 :</p>
<div class="tablewrap"><table><thead><tr><th>Découpage</th><th>Cellules</th><th>Corr. rang</th><th>Même signe</th></tr></thead><tbody>{pers_v2}</tbody></table></div></div>
<div><h3>H3 fix de Londres</h3><p class="lede">Matrice complète : {h3cells} cellules, presque toutes UNKNOWN. Persistance Train → Validation :</p>
<div class="tablewrap"><table><thead><tr><th>Découpage</th><th>Cellules</th><th>Corr. rang</th><th>Même signe</th></tr></thead><tbody>{pers_h3}</tbody></table></div></div>
</div>
<p>Conclusion : avec un an de données, découper par régime ou volatilité apprend du bruit (corrélations négatives). Le Router V4 utilise donc le niveau le plus fin dont la persistance est démontrée. Pour H3, c'est la stratégie entière, sur les 3 paires, sans filtre de régime. Le contexte qui compte, c'est l'heure. Tout le reste est NO TRADE.</p>
</section>

<section id="f"><h2>F · Auto-critique</h2>
<ul class="f">
<li><b>Faux positif possible.</b> 40 variantes testées : au seuil t ≥ 2, environ un faux positif est attendu par hasard. H3 a survécu à la validation, mais c'est l'hors-échantillon qui tranche.</li>
<li><b>L'avantage est minuscule en pips</b> (≈ 1,3 pip). Il n'existe qu'avec un spread type ECN (0,3 à 0,6 pip) et une exécution rapide. Chez un courtier « standard » à 1 pip de spread, il disparaît.</li>
<li><b>Le spread réel au moment du fix</b> peut être plus large que la médiane Dukascopy, et le glissement n'est modélisé qu'à la minute.</li>
<li><b>Fréquence faible :</b> environ 2 trades par jour ouvré sur les 3 paires. Les 3 paires réagissent au même fix (USD), donc leurs résultats sont corrélés : 590 trades valent moins que 590 tirages indépendants.</li>
<li><b>Le fix de fin de mois pèse lourd</b> (30 trades, +0,45 R), mais l'effet reste positif sans eux (+0,11 R).</li>
<li><b>Analyse des échecs V2 faite sur les 12 mois</b> utilisés ensuite pour Train / Validation. Les hypothèses V4 n'en ont pas été tirées (elles viennent de la littérature et des PDF), mais c'est une fuite possible. D'où l'hors-échantillon 2024-2025.</li>
<li><b>Rejeté sans regret :</b> H1, H2, H5 (toutes négatives dans les deux moitiés du Train). H4 (Tokyo) est positive dans les deux moitiés, mais t &lt; 1 : pas de preuve. Je la garde en observation, sans la retenir.</li>
</ul></section>

<section id="g"><h2>G · Recommandation</h2><div id="reco">{{RECO}}</div></section>
<footer>Code et protocole : branche research-v4, dossier research/v4/ (PROTOCOLE.md commité avant les tests). Simulation M1 bid/ask, stop compté en premier si stop et cible tombent dans la même minute, glissement si l'ouverture saute le stop.</footer>
</div>
"""

if __name__ == "__main__":
    print(main())
