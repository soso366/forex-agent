"""Test D01 — suivi de tendance (momentum de série temporelle), selon PROTOCOLE.md. Aucun réglage choisi sur les données.

Usage : python -m forex_lab.trend.tsmom [--data forex_lab/trend/data]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PAIRS = {  # paire -> (série de cours, transformation vers la cotation, taux devise de base, taux devise de cotation)
    "EURUSD": ("DEXUSEU", 1, "IR3TIB01EZM156N", "TB3MS"),
    "GBPUSD": ("DEXUSUK", 1, "IR3TIB01GBM156N", "TB3MS"),
    "USDJPY": ("DEXJPUS", 1, "TB3MS", "IR3TIB01JPM156N"),
}
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2}
COSTS = {"standard": (1.5, 0.01), "stress": (3.0, 0.02)}
DEV_END = pd.Period("2023-08", "M")
VIRGIN = (pd.Period("2023-09", "M"), pd.Period("2024-08", "M"))
RECENT_START = pd.Period("2024-09", "M")
SUBS = {"avant 2000": (None, pd.Period("1999-12", "M")), "2000-2009": (pd.Period("2000-01", "M"), pd.Period("2009-12", "M")),
        "2010-2023/08": (pd.Period("2010-01", "M"), DEV_END)}


def read_fred(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    s = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s.index = pd.to_datetime(df.iloc[:, 0])
    return s.dropna()


def load(data: Path):
    daily, rates = {}, {}
    for p, (code, _, rb, rq) in PAIRS.items():
        daily[p] = read_fred(data / f"{code}.csv")
        for r in (rb, rq):
            if r not in rates:
                m = read_fred(data / f"{r}.csv")
                m.index = m.index.to_period("M")
                rates[r] = m / 100.0
    return daily, rates


def monthly_table(daily: pd.Series, rate_base: pd.Series, rate_quote: pd.Series, lookback: int) -> pd.DataFrame:
    """Une ligne par mois de signal m : signal, force, rendement du mois m+1 (cours et portage)."""
    px = daily.groupby(daily.index.to_period("M")).last()
    lr = np.log(daily).diff().dropna()
    vol = lr.groupby(lr.index.to_period("M")).apply(list)
    months = px.index
    rows = []
    for i in range(lookback, len(months) - 1):
        m, nxt = months[i], months[i + 1]
        if nxt != m + 1 or months[i - lookback] != m - lookback:
            continue
        r_lb = px.iloc[i] / px.iloc[i - lookback] - 1
        last12 = [x for mm in [m - k for k in range(12)] if mm in vol.index for x in vol[mm]]
        sig_vol = float(np.std(last12, ddof=1) * math.sqrt(252)) if len(last12) > 100 else np.nan
        rb = rate_base.reindex(pd.period_range(rate_base.index.min(), m, freq="M")).ffill()
        rq = rate_quote.reindex(pd.period_range(rate_quote.index.min(), m, freq="M")).ffill()
        if m not in rb.index or m not in rq.index or pd.isna(rb[m]) or pd.isna(rq[m]):
            continue
        rows.append({"mois_signal": m, "mois": nxt, "signal": float(np.sign(r_lb)), "force": abs(r_lb) / sig_vol if sig_vol else np.nan,
                     "spot": px.iloc[i + 1] / px.iloc[i] - 1, "portage": (rb[m] - rq[m]) / 12, "prix": px.iloc[i]})
    return pd.DataFrame(rows).set_index("mois")


def simulate(tables: dict[str, pd.DataFrame], max_pos: int | None, cost: tuple[float, float], pairs=None) -> pd.DataFrame:
    """Rendement mensuel net du portefeuille (levier 1 au total, positions de taille égale)."""
    pairs = pairs or list(tables)
    months = sorted(set().union(*[set(tables[p].index) for p in pairs]))
    pip_rt, markup = cost
    prev: dict[str, float] = {}
    out = []
    for mo in months:
        cand = {p: tables[p].loc[mo] for p in pairs if mo in tables[p].index and tables[p].loc[mo, "signal"] != 0
                and not pd.isna(tables[p].loc[mo, "force"])}
        chosen = sorted(cand, key=lambda p: -cand[p]["force"])
        if max_pos:
            chosen = chosen[:max_pos]
        n = max_pos or len(pairs)
        if not chosen:
            out.append({"mois": mo, "net": 0.0, "brut": 0.0, "portage": 0.0, "positions": "", "changements": 0})
            prev = {}
            continue
        w = 1.0 / n
        gross = carry = costs = 0.0
        changes = 0
        cur = {}
        for p in chosen:
            r = cand[p]
            s = r["signal"]
            cur[p] = s
            gross += w * s * (r["spot"] + r["portage"])
            carry += w * s * r["portage"]
            costs += w * markup / 12
            if prev.get(p) != s:
                changes += 1
                costs += w * pip_rt * PIP[p] / r["prix"]  # aller-retour compté à l'ouverture
        out.append({"mois": mo, "net": gross - costs, "brut": gross, "portage": carry, "positions": " ".join(f"{p}{'+' if cur[p] > 0 else '-'}" for p in chosen),
                    "changements": changes})
        prev = cur
    return pd.DataFrame(out).set_index("mois")


def summary(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 2:
        return {"mois": int(len(r))}
    mu, sd = r.mean(), r.std(ddof=1)
    eq = (1 + r).cumprod()
    return {"mois": int(len(r)), "debut": str(r.index[0]), "fin": str(r.index[-1]),
            "rendement_annuel_pct": round(100 * ((1 + r).prod() ** (12 / len(r)) - 1), 2),
            "moyenne_mensuelle_pct": round(100 * mu, 3), "sharpe": round(mu / sd * math.sqrt(12), 2) if sd else None,
            "t": round(mu / (sd / math.sqrt(len(r))), 2) if sd else None,
            "perte_max_pct": round(100 * float((eq / eq.cummax() - 1).min()), 1), "mois_gagnants_pct": round(100 * float((r > 0).mean()), 1)}


def window(df: pd.DataFrame, a, b) -> pd.DataFrame:
    idx = df.index
    m = np.ones(len(idx), bool)
    if a is not None:
        m &= idx >= a
    if b is not None:
        m &= idx <= b
    return df[m]


def report(port: pd.DataFrame) -> dict:
    dev = window(port, None, DEV_END)
    rec = window(port, RECENT_START, None)
    return {"developpement": summary(dev["net"]), "developpement_brut": summary(dev["brut"]),
            "part_portage_pct_par_mois": round(100 * dev["portage"].mean(), 3),
            "sous_periodes": {k: summary(window(port, a, b)["net"]) for k, (a, b) in SUBS.items()},
            "recent_indicatif": summary(rec["net"])}


def run(data: Path) -> dict:
    daily, rates = load(data)
    res = {"protocole": "forex_lab/trend/PROTOCOLE.md", "donnees": {p: [str(daily[p].index[0].date()), str(daily[p].index[-1].date())] for p in daily}}
    tables = {lb: {p: monthly_table(daily[p], rates[PAIRS[p][2]], rates[PAIRS[p][3]], lb) for p in PAIRS} for lb in (1, 3, 6, 12)}
    for lb in tables:  # période vierge : supprimée avant tout calcul
        for p in tables[lb]:
            t = tables[lb][p]
            tables[lb][p] = t[~((t.index >= VIRGIN[0]) & (t.index <= VIRGIN[1]))]
    official = {c: simulate(tables[12], 2, COSTS[c]) for c in COSTS}
    rep = report(official["standard"])
    stress = report(official["stress"])
    sp = rep["sous_periodes"]
    crit = {k: bool(v) for k, v in {
        "C1 Sharpe ≥ 0,3 et t ≥ 2": (rep["developpement"].get("sharpe") or -9) >= 0.3 and (rep["developpement"].get("t") or -9) >= 2,
        "C2 2010-2023/08 > 0": (sp["2010-2023/08"].get("moyenne_mensuelle_pct") or -1) > 0,
        "C3 stress > 0": (stress["developpement"].get("moyenne_mensuelle_pct") or -1) > 0,
        "C4 ≥ 2 sous-périodes sur 3 > 0": sum((v.get("moyenne_mensuelle_pct") or -1) > 0 for v in sp.values()) >= 2,
    }.items()
    }
    res["officiel_2_positions"] = {"standard": rep, "stress": stress, "criteres": crit, "verdict": "PASSE" if all(crit.values()) else "ÉCHEC"}
    res["info_3_paires"] = report(simulate(tables[12], None, COSTS["standard"]))
    res["info_par_paire"] = {p: report(simulate(tables[12], None, COSTS["standard"], [p])) for p in PAIRS}
    res["info_durees"] = {f"{lb} mois": report(simulate(tables[lb], 2, COSTS["standard"]))["developpement"] for lb in (1, 3, 6)}
    port = official["standard"]
    res["serie_mensuelle"] = [{"mois": str(i), "net_pct": round(100 * r.net, 3), "positions": r.positions} for i, r in port.iterrows()]
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "data"))
    a = ap.parse_args()
    res = run(Path(a.data))
    (HERE / "resultats.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    o = res["officiel_2_positions"]
    print(json.dumps({k: o[k] for k in ("criteres", "verdict")}, ensure_ascii=False, indent=1))
    print(json.dumps(o["standard"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
