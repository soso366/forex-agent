"""Phase V3 : trois hypothèses documentées (PROTOCOLE_V3.md). Optimisation sur IS uniquement, validation unique sur VAL.

Usage : python -m forex_lab.v3 --data <dossier forex-data> [--only H1 H2 H3]
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .engine import REALISTIC, Event, Rules, Simulator, load_m1, pip_value_usd_per_lot, resample, run_portfolio

LAB = Path(__file__).resolve().parent
IS = (pd.Timestamp("2024-09-01", tz="UTC"), pd.Timestamp("2025-09-01", tz="UTC"))
VAL = (pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
VAL_HALVES = [(VAL[0], pd.Timestamp("2026-03-01", tz="UTC")), (pd.Timestamp("2026-03-01", tz="UTC"), VAL[1])]
PAIRS = ["EURUSD", "GBPUSD", "USDJPY"]
PROJ = Rules(cap_min=240, flat_utc_hour=21)


# ------------------------------------------------------------------ outils
def weekdays(start, end, tz):
    d = pd.date_range(start.tz_convert(tz).normalize(), end.tz_convert(tz).normalize(), freq="D")
    return [x for x in d if x.weekday() < 5]


def gotobi_dates(start, end) -> set:
    """Jours 5, 10, 15, 20, 25, 30 et dernier jour ouvré du mois ; si week-end → jour ouvré précédent (Tokyo)."""
    out = set()
    for y, m in sorted({(d.year, d.month) for d in pd.date_range(start.tz_convert(None), end.tz_convert(None), freq="D")}):
        for dd in (5, 10, 15, 20, 25, 30):
            try:
                t = pd.Timestamp(y, m, dd)
            except ValueError:
                continue
            while t.weekday() >= 5:
                t -= pd.Timedelta(days=1)
            out.add(t.date())
        out.add((pd.Timestamp(y, m, 1) + pd.offsets.BMonthEnd(0)).date())
    return out


def tstat(x):
    x = np.asarray(x, float)
    if len(x) < 2 or x.std(ddof=1) == 0:
        return None
    return round(float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))), 2)


def net_pips(tr, commission=3.0, slippage=0.1, extra=0.0):
    """Recalcule le net d'un trade sous d'autres hypothèses de coûts (sensibilité)."""
    comm = 2 * commission / pip_value_usd_per_lot(tr.pair, tr.entry) if commission else 0.0
    slip = slippage * (1 if tr.reason == "objectif" else 2)
    return tr.gross_pips - comm - slip - extra


def summarize(trades, **cost):
    if not trades:
        return {"trades": 0}
    x = np.array([net_pips(t, **cost) for t in trades])
    g, l = x[x > 0].sum(), -x[x < 0].sum()
    days = pd.Series(x, index=[t.entry_time.date() for t in trades]).groupby(level=0).sum()
    return {"trades": int(len(x)), "pips_moyen": round(float(x.mean()), 3), "pips_total": round(float(x.sum()), 1),
            "taux_gain_pct": round(100 * float((x > 0).mean()), 1), "profit_factor": round(float(g / l), 2) if l else None,
            "t_trades": tstat(x), "t_jours": tstat(days.to_numpy()), "jours": int(len(days)),
            "brut_moyen": round(float(np.mean([t.gross_pips for t in trades])), 3),
            "cout_moyen": round(float(np.mean([t.gross_pips - v for t, v in zip(trades, x)])), 3),
            "duree_moy_min": round(float(np.mean([(t.exit_time - t.entry_time).total_seconds() / 60 for t in trades])), 1),
            "ambigus": int(sum(t.ambiguous for t in trades)),
            "par_paire": {p: round(float(sum(v for t, v in zip(trades, x) if t.pair == p)), 1) for p in sorted({t.pair for t in trades})},
            "drawdown_max_pips": round(float(np.max(np.maximum.accumulate(np.cumsum(x)) - np.cumsum(x))), 1)}


def window(trades, a, b):
    return [t for t in trades if a <= t.entry_time < b]


# ------------------------------------------------------------------ H1 Tokyo fix
def h1_events(start, end, d, h, days, sims=None):
    gob = gotobi_dates(start, end)
    ev = []
    for day in weekdays(start, end, "Asia/Tokyo"):
        if days == "gotobi" and day.date() not in gob:
            continue
        fix = (day + pd.Timedelta(hours=9, minutes=55)).tz_convert("UTC")
        t0 = fix + pd.Timedelta(minutes=d)
        if not (start <= t0 < end):
            continue
        ev.append(Event(t0, "USDJPY", -1, Rules(cap_min=int(h * 60), flat_utc_hour=21), tag="H1"))
    return ev


def h1_exact_events(start, end):
    ev = []
    for day in weekdays(start, end, "Asia/Tokyo"):
        fix = (day + pd.Timedelta(hours=9, minutes=55)).tz_convert("UTC")
        # le fix (00:55 UTC) tombe vers 20:55 New York la veille : début 17:00 New York ce même soir, fin 02:00 New York la nuit suivante
        fix_ny = fix.tz_convert("America/New_York")
        prev_ny = fix_ny.normalize() + pd.Timedelta(hours=17)
        end_ny = fix_ny.normalize() + pd.Timedelta(days=1, hours=2)
        if prev_ny.tz_convert("UTC") < start or end_ny.tz_convert("UTC") > end:
            continue
        ev.append(Event(prev_ny.tz_convert("UTC"), "USDJPY", +1, Rules(), hard_exit=fix, tag="H1x", chain=True))
        ev.append(Event(fix, "USDJPY", -1, Rules(), hard_exit=end_ny.tz_convert("UTC"), tag="H1x", chain=True))
    return ev


H1_GRID = [dict(d=d, h=h, days=g) for d, h, g in itertools.product([1, 5, 15], [2, 3, 4], ["tous", "gotobi"])]


# ------------------------------------------------------------------ H2 momentum filtré par la volatilité
def _price_at(m1, ts):
    i = m1.index.searchsorted(ts)
    if i >= len(m1) or (m1.index[i] - ts) > pd.Timedelta(minutes=10):
        return np.nan
    r = m1.iloc[i]
    return (r["bid_open"] + r["ask_open"]) / 2


def h2_daily_table(m1: pd.DataFrame, start, end, S: str) -> pd.DataFrame:
    """Par jour de Londres : rendement et volatilité réalisée (M5) de la fenêtre signal S (calcul causal)."""
    m5 = ((m1["bid_close"] + m1["ask_close"]) / 2).resample("5min").last().dropna()
    lr = np.log(m5).diff()
    rows = []
    for day in weekdays(start - pd.Timedelta(days=120), end, "Europe/London"):
        s_end = (day + pd.Timedelta(hours=8, minutes=30)).tz_convert("UTC")
        if S == "ouverture":
            s_start = (day + pd.Timedelta(hours=8)).tz_convert("UTC")
        else:   # avec la nuit : depuis 17:00 New York la veille
            prev = (s_end.tz_convert("America/New_York") - pd.Timedelta(days=1)).normalize() + pd.Timedelta(hours=17)
            s_start = prev.tz_convert("UTC")
        p0, p1 = _price_at(m1, s_start), _price_at(m1, s_end)
        seg = lr[(lr.index >= s_start) & (lr.index < s_end)]
        rows.append({"day": day, "ret": p1 - p0, "vol": float((seg ** 2).sum()) if len(seg) else np.nan})
    return pd.DataFrame(rows).set_index("day")


def h2_events(tables: dict, start, end, S, T, q):
    ev = []
    for pair, tab in tables.items():
        tab = tab[S]
        thr = tab["vol"].shift(1).rolling(60, min_periods=40).quantile(q) if q else None
        for day, r in tab.iterrows():
            if not np.isfinite(r["ret"]) or r["ret"] == 0 or not np.isfinite(r["vol"]):
                continue
            if q and not (np.isfinite(thr.loc[day]) and r["vol"] > thr.loc[day]):
                continue
            if T == "derniere_demi_heure":
                t0, t1 = day + pd.Timedelta(hours=15, minutes=30), day + pd.Timedelta(hours=16)
            else:
                t0, t1 = day + pd.Timedelta(hours=8, minutes=30), day + pd.Timedelta(hours=12, minutes=30)
            t0, t1 = t0.tz_convert("UTC"), t1.tz_convert("UTC")
            if not (start <= t0 < end):
                continue
            ev.append(Event(t0, pair, 1 if r["ret"] > 0 else -1, PROJ, hard_exit=t1, tag="H2"))
    return ev


H2_GRID = [dict(S=s, T=t, q=q) for s, t, q in itertools.product(["ouverture", "avec_nuit"],
                                                                  ["derniere_demi_heure", "reste_seance"], [None, 0.5, 0.67])]


# ------------------------------------------------------------------ H3 cassure du range asiatique
def h3_events(m5s: dict, start, end, r_end, w_end, stop, k):
    ev = []
    for pair, b in m5s.items():
        b = b[(b.index >= start - pd.Timedelta(days=1)) & (b.index < end)]
        for day, g in b.groupby(b.index.normalize()):
            if day.weekday() >= 5:
                continue
            rng = g[(g.index.hour < r_end)]
            win = g[(g.index.hour >= r_end) & (g.index.hour < w_end)]
            if len(rng) < 6 * r_end or win.empty:
                continue
            hi, lo = rng["high"].max(), rng["low"].min()
            mid = (hi + lo) / 2
            up = win.index[(win["close"] > hi).to_numpy()]
            dn = win.index[(win["close"] < lo).to_numpy()]
            first_up = up[0] if len(up) else None
            first_dn = dn[0] if len(dn) else None
            if first_up is None and first_dn is None:
                continue
            if first_dn is None or (first_up is not None and first_up < first_dn):
                side, t_sig, sl = 1, first_up, (mid if stop == "milieu" else lo)
            else:
                side, t_sig, sl = -1, first_dn, (mid if stop == "milieu" else hi)
            t0 = t_sig + pd.Timedelta(minutes=5)              # ouverture de la bougie suivante
            if not (start <= t0 < end) or t0.hour >= w_end + 1:
                continue
            ev.append(Event(t0, pair, side, PROJ, tag="H3", sl_price=float(sl), tp_r=float(k)))
    return ev


H3_GRID = [dict(r_end=r, w_end=w, stop=s, k=k) for r, w, s, k in
           itertools.product([6, 7], [10, 12], ["milieu", "oppose"], [1.0, 2.0])]


# ------------------------------------------------------------------ déroulé commun
def evaluate(name, grid, make_events, sims, extra_exact=None):
    rows = []
    for cfg in grid:
        tr_is = run_portfolio(make_events(IS[0], IS[1], cfg), sims, 2)
        rows.append({"config": cfg, "IS": summarize(tr_is)})
    elig = [r for r in rows if r["IS"].get("trades", 0) >= 60 and r["IS"].get("t_jours") is not None]
    best = max(elig, key=lambda r: r["IS"]["t_jours"]) if elig else None
    out = {"hypothese": name, "grille_IS": rows, "choix": best["config"] if best else None}
    if best is None or best["IS"]["t_jours"] < 1.5:
        out["verdict"] = "ÉCHEC (optimisation)"
        out["raison"] = "aucune configuration avec t journalière ≥ 1,5 sur IS : validation non consommée"
    else:
        tr_val = run_portfolio(make_events(VAL[0], VAL[1], best["config"]), sims, 2)
        s = summarize(tr_val)
        halves = [summarize(window(tr_val, a, b)) for a, b in VAL_HALVES]
        sens = {"commission_0": summarize(tr_val, commission=0.0), "commission_5": summarize(tr_val, commission=5.0),
                "glissement_0.3": summarize(tr_val, slippage=0.3), "plus_0.5_pip": summarize(tr_val, extra=0.5),
                "plus_1.0_pip": summarize(tr_val, extra=1.0)}
        why = []
        if s.get("trades", 0) < 60:
            why.append("moins de 60 trades")
        if any((h.get("pips_moyen") or -1) <= 0 for h in halves):
            why.append("négative sur un semestre de validation")
        if (s.get("profit_factor") or 0) < 1.10:
            why.append("profit factor < 1,10")
        if (s.get("t_jours") or 0) < 1.65:
            why.append("t journalière < 1,65")
        if (sens["plus_0.5_pip"].get("pips_moyen") or -1) <= 0:
            why.append("négative avec +0,5 pip")
        if (sens["commission_5"].get("pips_moyen") or -1) <= 0:
            why.append("négative avec commission 5 $")
        out.update({"VAL": s, "VAL_semestres": halves, "VAL_sensibilite": sens,
                    "verdict": "RÉUSSITE (validation) → confirmation 2020-2023 requise" if not why else "ÉCHEC (validation)",
                    "raisons": why})
    if extra_exact is not None:
        out["version_exacte_source"] = extra_exact
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--only", nargs="*", default=["H1", "H2", "H3"])
    a = ap.parse_args()
    m1 = {p: load_m1(Path(a.data), p) for p in PAIRS}
    sims = {p: Simulator(p, m1[p], REALISTIC) for p in PAIRS}
    res = {}
    if "H1" in a.only:
        ex = {per: summarize(run_portfolio(h1_exact_events(*per), sims, 2)) for per in (IS, VAL)}
        res["H1"] = evaluate("H1 fix de Tokyo USDJPY", H1_GRID, lambda s, e, c: h1_events(s, e, **c), sims,
                             {"IS": ex[IS], "VAL": ex[VAL]})
    if "H2" in a.only:
        tables = {p: {S: h2_daily_table(m1[p], IS[0], VAL[1], S) for S in ("ouverture", "avec_nuit")} for p in PAIRS}
        res["H2"] = evaluate("H2 momentum filtré par la volatilité", H2_GRID, lambda s, e, c: h2_events(tables, s, e, **c), sims)
    if "H3" in a.only:
        m5s = {p: resample(m1[p], 5) for p in PAIRS}
        res["H3"] = evaluate("H3 cassure du range asiatique", H3_GRID, lambda s, e, c: h3_events(m5s, s, e, **c), sims)
    out = LAB / "results"
    out.mkdir(exist_ok=True)
    for k, v in res.items():
        (out / f"v3_{k}.json").write_text(json.dumps(v, indent=1, ensure_ascii=False, default=str))
        b = next((r for r in v["grille_IS"] if r["config"] == v["choix"]), None)
        print(f"\n== {v['hypothese']} : {v['verdict']}")
        print(f"   choix IS : {v['choix']} → {b['IS'] if b else '—'}")
        if "VAL" in v:
            print(f"   VAL : {v['VAL']}\n   raisons : {v.get('raisons')}")


if __name__ == "__main__":
    main()
