"""Analyse des échecs V2 sur 12 mois (sept. 2025 → août 2026), trades de référence V2 (aucun réglage du lab).

Sorties : research/v4/out/failures.json + tableaux texte.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from .data import PAIRS, PIP, atr, bars, load
from .sim import Market, simulate

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "v4" / "out"
REF = "a57fa9e4093d"


def ref_trades() -> pd.DataFrame:
    a = pickle.load(open(ROOT / "lab/results/trades_2025sep-2026feb" / f"{REF}.pkl", "rb"))
    b = pickle.load(open(ROOT / "lab/results/trades" / f"{REF}.pkl", "rb"))
    a["period"], b["period"] = "P1 sept.25-fév.26", "P2 mars-août 26"
    t = pd.concat([a, b], ignore_index=True)
    t = t[t["status"] == "closed"].copy()
    t["entry_dt"] = pd.to_datetime(t["entry_time"], utc=True)
    t = t[t["entry_dt"] >= pd.Timestamp("2025-09-08", tz="UTC")]
    return t.reset_index(drop=True)


def enrich(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sym, g in t.groupby("symbol"):
        m1 = load(sym)
        m5 = bars(m1, "5min")
        a5 = atr(m5)
        # volatilité relative : ATR M5 / médiane glissante 20 jours (même heure ignorée, simple)
        med = a5.rolling(288 * 20, min_periods=288 * 5).median()
        h1 = bars(m1, "1h")
        ema50_h1 = h1["c"].ewm(span=50, adjust=False).mean()
        # amplitude typique (mid) sur 30 min à cette heure : médiane des 20 derniers jours
        rng30 = (m1["mid"].rolling("30min").max() - m1["mid"].rolling("30min").min())
        for _, x in g.iterrows():
            et = x["entry_dt"]
            k5 = m5.index.searchsorted(et) - 1          # dernière M5 close avant l'entrée
            atr5 = a5.iloc[k5] if k5 >= 0 else np.nan
            vol = atr5 / med.iloc[k5] if k5 >= 0 and med.iloc[k5] > 0 else np.nan
            kh = h1.index.searchsorted(et) - 1
            htf = np.sign(h1["c"].iloc[kh] - ema50_h1.iloc[kh]) if kh >= 0 else 0
            d = 1 if x["direction"] == "BUY" else -1
            sd = abs(x["entry"] - x["initial_stop"])
            td = abs(x["target"] - x["entry"])
            i = m1.index.searchsorted(et)
            spread = m1["spread"].iloc[i] if i < len(m1) else np.nan
            # amplitude réalisée « normale » sur 30 min aux mêmes heures les 20 jours précédents
            same = [et - pd.Timedelta(days=k) + pd.Timedelta(minutes=30) for k in range(1, 29)]
            idx = rng30.index.searchsorted(same) - 1
            typ = np.nanmedian(rng30.iloc[np.clip(idx, 0, len(rng30) - 1)].to_numpy())
            rows.append({"id": x.name, "atr5_pips": atr5 / PIP[sym], "vol_ratio": vol, "htf_aligned": htf == d,
                         "stop_pips": sd / PIP[sym], "target_pips": td / PIP[sym], "target_R": td / sd if sd else np.nan,
                         "stop_atr": sd / atr5 if atr5 else np.nan, "target_atr": td / atr5 if atr5 else np.nan,
                         "spread_R": spread / sd if sd else np.nan, "typ30_pips": typ / PIP[sym],
                         "target_vs_typ30": td / typ if typ else np.nan})
    e = pd.DataFrame(rows).set_index("id")
    t = t.join(e)
    t["hour"] = t["entry_dt"].dt.hour
    t["vol_bucket"] = pd.cut(t["vol_ratio"], [0, 0.8, 1.25, 99], labels=["basse", "normale", "haute"])
    t["exit_kind"] = t["exit_reason"].str.split(" ").str[0].str.rstrip(":")
    return t


def mirror(t: pd.DataFrame) -> pd.DataFrame:
    """Même instant, même géométrie stop/cible, simulateur de recherche :
    sens du signal vs sens opposé vs sans cible. Mesure si le SENS contient de l'information."""
    out = []
    for sym, g in t.groupby("symbol"):
        m = Market(load(sym))
        d = np.where(g["direction"] == "BUY", 1, -1)
        sd = (g["entry"] - g["initial_stop"]).abs().to_numpy()
        td = (g["target"] - g["entry"]).abs().to_numpy()
        same = simulate(m, g["entry_dt"], d, sd, td)
        opp = simulate(m, g["entry_dt"], -d, sd, td)
        sym_geo = simulate(m, g["entry_dt"], d, sd, sd * 1.0)        # cible = 1R
        notgt = simulate(m, g["entry_dt"], d, sd, np.full(len(g), np.inf))
        out.append(pd.DataFrame({"id": g.index, "sim_same": same["r"].to_numpy(), "sim_opp": opp["r"].to_numpy(),
                                 "sim_1R": sym_geo["r"].to_numpy(), "sim_notarget": notgt["r"].to_numpy(),
                                 "sim_exit": same["exit"].to_numpy()}))
    return t.join(pd.concat(out).set_index("id"))


def grp(t, by):
    g = t.groupby(by, observed=True)["r_multiple"]
    res = pd.DataFrame({"n": g.size(), "exp": g.mean(), "R": g.sum(), "win": g.apply(lambda r: (r > 0).mean())})
    res["t"] = g.mean() / (g.std(ddof=1) / np.sqrt(g.size()))
    return res.round(3)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t = enrich(ref_trades())
    t = mirror(t)
    t.to_pickle(OUT / "v2_trades_enriched.pkl")
    pd.set_option("display.width", 200)
    lines = []
    def show(title, df):
        lines.append(f"\n### {title}\n{df.to_string()}")
    show("Global par période", grp(t, "period"))
    show("Stratégie × période", grp(t, ["strategy", "period"]))
    show("Stratégie × régime", grp(t, ["strategy", "regime"]))
    show("Stratégie × session", grp(t, ["strategy", "session"]))
    show("Stratégie × paire", grp(t, ["strategy", "symbol"]))
    show("Stratégie × volatilité", grp(t, ["strategy", "vol_bucket"]))
    show("Stratégie × H1 aligné", grp(t, ["strategy", "htf_aligned"]))
    show("Heure UTC", grp(t, "hour"))
    show("Sortie", grp(t, "exit_kind"))
    geo = t.groupby("strategy")[["stop_pips", "target_pips", "target_R", "stop_atr", "target_atr", "spread_R",
                                 "typ30_pips", "target_vs_typ30", "mfe_r", "mae_r"]].median().round(2)
    show("Géométrie médiane", geo)
    t["reach"] = t["mfe_r"] >= t["target_R"]
    show("Part des trades dont la cible a été atteinte (MFE ≥ cible)", t.groupby("strategy")["reach"].mean().round(3).to_frame())
    show("MFE/MAE gagnants vs perdants", t.assign(w=t["r_multiple"] > 0).groupby(["strategy", "w"])[["mfe_r", "mae_r", "duration_min"]].median().round(2))
    mir = t.groupby("strategy")[["r_multiple", "sim_same", "sim_opp", "sim_1R", "sim_notarget"]].mean().round(3)
    mir["n"] = t.groupby("strategy").size()
    show("Test du miroir (espérance R) : signal vs sens opposé, même instant/géométrie", mir)
    allm = t[["r_multiple", "sim_same", "sim_opp", "sim_1R", "sim_notarget"]].mean().round(3)
    show("Miroir global", allm.to_frame())
    # persistance : les cellules qui gagnaient en P1 gagnent-elles en P2 ?
    cells = []
    for by in (["strategy", "regime"], ["strategy", "session"], ["strategy", "symbol"], ["strategy", "vol_bucket"],
               ["strategy", "symbol", "session"]):
        g = t.groupby(by + ["period"], observed=True)["r_multiple"].agg(["mean", "size"]).unstack("period")
        g = g[(g["size"] >= 8).all(axis=1)]
        if len(g) >= 4:
            p = g["mean"].corr(method="spearman").iloc[0, 1]
            same_sign = (np.sign(g["mean"].iloc[:, 0]) == np.sign(g["mean"].iloc[:, 1])).mean()
            cells.append({"découpage": " × ".join(by), "cellules": len(g), "corr_rang_P1_P2": round(p, 2),
                          "même_signe": round(same_sign, 2)})
    show("Persistance des cellules (≥ 8 trades dans chaque période)", pd.DataFrame(cells))
    txt = "\n".join(lines)
    (OUT / "failures.txt").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
