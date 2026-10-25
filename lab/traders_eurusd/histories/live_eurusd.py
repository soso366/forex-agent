"""Performance RÉELLE (historique exporté) de la partie EUR/USD de chaque trader, et gestion des positions.
Usage : python live_eurusd.py <dossier_des_csv>  → live_eurusd.json"""
import json, re, sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from analyze import NAMES, load_deals, load_positions


def averaging(e):
    e = e.sort_values("t_open"); first = worse = better = 0
    for _, r in e.iterrows():
        side = 1 if r.type == "Buy" else -1
        op = e[(e.type == r.type) & (e.t_open < r.t_open) & (e.t_close > r.t_open)]
        if len(op) == 0:
            first += 1
        elif (r.price - op.price.iloc[0]) * side < 0:
            worse += 1
        else:
            better += 1
    return first, worse, better


def main(folder):
    out = []
    for f in sorted(Path(folder).glob("*.csv")):
        sid = re.search(r"(\d{6,7})\.history", f.name).group(1)
        head = f.read_text(encoding="utf-8-sig").splitlines()[0]
        df = load_deals(f) if "Direction" in head else load_positions(f)
        e = df[df.type.isin(["Buy", "Sell"]) & df.symbol.str.upper().str.startswith("EURUSD")].copy()
        e["net"] = e.profit.fillna(0) + e.commission.fillna(0) + e.swap.fillna(0)
        e = e.sort_values("t_close")
        cum = e.net.cumsum().to_numpy()
        dd = float(np.max(np.maximum.accumulate(np.concatenate([[0], cum]))[1:] - cum)) if len(cum) else 0
        years = {}
        for y, g in e.groupby(e.t_close.dt.year):
            gp, gl = g.net[g.net > 0].sum(), -g.net[g.net < 0].sum()
            years[int(y)] = {"trades": int(len(g)), "pf": round(gp / gl, 2) if gl > 0 else None, "net": round(float(g.net.sum()), 2)}
        gp, gl = e.net[e.net > 0].sum(), -e.net[e.net < 0].sum()
        a, w, b = averaging(e)
        sl = (e.sl > 0).mean() if "sl" in e and e.sl.notna().any() else 0.0
        out.append({"trader": NAMES.get(sid, sid), "signal": f"https://www.mql5.com/en/signals/{sid}",
                    "trades_eurusd": int(len(e)), "pf_eurusd": round(gp / gl, 2) if gl > 0 else None,
                    "net_eurusd": round(float(e.net.sum()), 2), "dd_max_cumul_eurusd": round(dd, 2),
                    "dd_sur_net_pct": round(100 * dd / e.net.sum(), 1) if e.net.sum() > 0 else None,
                    "annees": years, "annees_perdantes": [y for y, v in years.items() if v["net"] < 0],
                    "stop_pose_pct": round(100 * float(sl), 1),
                    "ajouts_a_prix_pire_pct": round(100 * w / max(a + w + b, 1), 1)})
        print(json.dumps(out[-1], ensure_ascii=False))
    (Path(__file__).parent / "live_eurusd.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
