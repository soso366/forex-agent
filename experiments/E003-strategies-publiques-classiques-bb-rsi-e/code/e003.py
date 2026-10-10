"""E003 — stratégies publiques classiques (P1 BB+RSI, P2 EMA 9/21 + H1, P3 RSI2 Connors).

Règles : voir ../protocol.md (verrouillé). Réutilise research/v4/data.py et research/v4/sim.py en lecture seule.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research.v4.data import _read, atr, bars  # noqa: E402
from research.v4.engine import non_overlap  # noqa: E402
from research.v4.sim import Market, simulate  # noqa: E402

PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2}
INF = np.inf
WARMUP_DAYS = 3

VARIANTS = {
    "P1a": dict(h="P1", exit="sma", hours="session"), "P1b": dict(h="P1", exit="sma", hours="24h"),
    "P1c": dict(h="P1", exit="time", hours="session"), "P1d": dict(h="P1", exit="time", hours="24h"),
    "P2a": dict(h="P2", tgt=1.5, adx=False), "P2b": dict(h="P2", tgt=1.5, adx=True),
    "P2c": dict(h="P2", tgt=None, adx=False), "P2d": dict(h="P2", tgt=None, adx=True),
    "P3a": dict(h="P3", thr=10, stop=1.0), "P3b": dict(h="P3", thr=10, stop=2.0),
    "P3c": dict(h="P3", thr=5, stop=1.0), "P3d": dict(h="P3", thr=5, stop=2.0),
}


def neighbors(vid: str) -> list[str]:
    v = VARIANTS[vid]
    out = []
    for k, w in VARIANTS.items():
        if k != vid and w["h"] == v["h"] and sum(v[d] != w[d] for d in v if d != "h") == 1:
            out.append(k)
    return out


WINDOWS = {
    "train": dict(dirs=["m1_2025"], start="2025-09-01", end="2026-03-01"),
    "valA": dict(dirs=["m1_2025", "m1"], start="2026-03-01", end="2026-09-01"),
    "valB": dict(dirs=["m1_locked_2024", "m1_locked"], start="2024-09-01", end="2025-09-01"),
}


def load_window(name: str) -> dict:
    w = WINDOWS[name]
    return {s: _read([ROOT / "data" / d for d in w["dirs"]], s) for s in PAIRS}


# ------------------------------------------------------------------------------------------- indicateurs
def ema(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(span=n, adjust=False).mean()


def rsi(c: pd.Series, n: int) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def adx(b: pd.DataFrame, n: int = 14) -> pd.Series:
    up, dn = b["h"].diff(), -b["l"].diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = b["c"].shift()
    tr = np.maximum(b["h"] - b["l"], np.maximum((b["h"] - pc).abs(), (b["l"] - pc).abs()))
    a = 1 / n
    atr_ = tr.ewm(alpha=a, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, index=b.index).ewm(alpha=a, adjust=False).mean() / atr_
    ndi = 100 * pd.Series(ndm, index=b.index).ewm(alpha=a, adjust=False).mean() / atr_
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return dx.ewm(alpha=a, adjust=False).mean()


def features(m1: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par bougie M5 ; toutes les colonnes sont connues à la CLÔTURE de la bougie (aucune donnée future)."""
    b = bars(m1, "5min")
    c = b["c"]
    f = pd.DataFrame(index=b.index)
    f["c"], f["spread"] = c, b["spread"]
    f["atr"] = atr(b)
    f["sma20"] = c.rolling(20).mean()
    sd = c.rolling(20).std(ddof=0)
    f["bb_up"], f["bb_lo"] = f["sma20"] + 2 * sd, f["sma20"] - 2 * sd
    f["rsi14"], f["rsi2"] = rsi(c, 14), rsi(c, 2)
    f["e9"], f["e21"], f["e200"] = ema(c, 9), ema(c, 21), ema(c, 200)
    f["adx"] = adx(b)
    h1 = bars(m1, "1h")
    slope = np.sign(ema(h1["c"], 50).diff(3)).set_axis(h1.index + pd.Timedelta(hours=1))   # connue à la clôture H1
    close_t = b.index + pd.Timedelta(minutes=5)
    f["h1_slope"] = slope.reindex(close_t, method="ffill").to_numpy()
    f["close_t"] = close_t
    hr = close_t.hour + close_t.minute / 60
    f["session"] = (hr >= 7) & (hr < 20) & (close_t.weekday < 5)
    f["weekday"] = close_t.weekday < 5
    return f


# ------------------------------------------------------------------------------------------- signaux
def signals(f: pd.DataFrame, vid: str, sym: str) -> pd.DataFrame:
    v = VARIANTS[vid]
    c, a = f["c"].to_numpy(), f["atr"].to_numpy()
    rows = []
    if v["h"] == "P1":
        hours = f["session"].to_numpy() if v["hours"] == "session" else f["weekday"].to_numpy()
        up, lo, r14, sma, spr = (f[k].to_numpy() for k in ("bb_up", "bb_lo", "rsi14", "sma20", "spread"))
        armed_buy = armed_sell = True
        for i in range(len(f)):
            if not np.isfinite(up[i]) or not np.isfinite(r14[i]) or not np.isfinite(a[i]):
                continue
            if c[i] >= lo[i]:
                armed_buy = True
            if c[i] <= up[i]:
                armed_sell = True
            d = 0
            if c[i] < lo[i] and r14[i] < 30 and armed_buy:
                d, armed_buy = 1, False
            elif c[i] > up[i] and r14[i] > 70 and armed_sell:
                d, armed_sell = -1, False
            if d == 0 or not hours[i]:
                continue
            tgt = INF
            if v["exit"] == "sma":
                tgt = abs(sma[i] - c[i])
                if tgt < 2 * spr[i]:
                    continue
            rows.append((i, d, 1.5 * a[i], tgt))
    elif v["h"] == "P2":
        e9, e21, sl, ad, ses = (f[k].to_numpy() for k in ("e9", "e21", "h1_slope", "adx", "session"))
        for i in range(1, len(f)):
            if not ses[i] or not np.isfinite(a[i]) or not np.isfinite(sl[i]):
                continue
            d = 0
            if e9[i] > e21[i] and e9[i - 1] <= e21[i - 1] and sl[i] > 0:
                d = 1
            elif e9[i] < e21[i] and e9[i - 1] >= e21[i - 1] and sl[i] < 0:
                d = -1
            if d == 0 or (v["adx"] and not (ad[i] >= 25)):
                continue
            rows.append((i, d, a[i], v["tgt"] * a[i] if v["tgt"] else INF))
    else:
        r2, e200, ses = (f[k].to_numpy() for k in ("rsi2", "e200", "session"))
        lo_t, hi_t = v["thr"], 100 - v["thr"]
        for i in range(len(f)):
            if not ses[i] or not np.isfinite(a[i]) or not np.isfinite(r2[i]):
                continue
            d = 1 if (r2[i] < lo_t and c[i] > e200[i]) else (-1 if (r2[i] > hi_t and c[i] < e200[i]) else 0)
            if d:
                rows.append((i, d, v["stop"] * a[i], INF))
    if not rows:
        return pd.DataFrame(columns=["time", "sym", "dir", "stop", "target"])
    idx, d, sd, td = map(np.array, zip(*rows))
    return pd.DataFrame({"time": f["close_t"].to_numpy()[idx], "sym": sym, "dir": d.astype(int),
                         "stop": sd.astype(float), "target": td.astype(float)})


# ------------------------------------------------------------------------------------------- simulation
class Data:
    def __init__(self, name: str):
        self.name = name
        w = WINDOWS[name]
        self.start = pd.Timestamp(w["start"], tz="UTC") + pd.Timedelta(days=WARMUP_DAYS)
        self.end = pd.Timestamp(w["end"], tz="UTC")
        self.m1 = load_window(name)
        self.feat = {s: features(self.m1[s]) for s in PAIRS}
        self.mkt = {s: Market(self.m1[s]) for s in PAIRS}
        self.mid = {s: self.m1[s]["mid"] for s in PAIRS}

    def sigs(self, vid: str) -> pd.DataFrame:
        parts = [signals(self.feat[s], vid, s) for s in PAIRS]
        sig = pd.concat([p for p in parts if len(p)], ignore_index=True)
        t = pd.DatetimeIndex(sig["time"])
        sig = sig[(t >= self.start) & (t < self.end)]
        return non_overlap(sig.sort_values("time").reset_index(drop=True), 30)

    def simulate(self, sig: pd.DataFrame) -> pd.DataFrame:
        parts = []
        for sym, g in sig.groupby("sym"):
            res = simulate(self.mkt[sym], g["time"], g["dir"], g["stop"], g["target"], 30)
            parts.append(pd.concat([g.reset_index(drop=True), res], axis=1))
        t = pd.concat(parts, ignore_index=True).dropna(subset=["r"]).sort_values("time").reset_index(drop=True)
        t["time"] = pd.DatetimeIndex(t["time"]).tz_localize("UTC") if pd.DatetimeIndex(t["time"]).tz is None else t["time"]
        return t

    def trades(self, vid: str) -> pd.DataFrame:
        return self.simulate(self.sigs(vid))


def placebo_random(d: Data, sig: pd.DataFrame, n_draws: int = 200, seed: int = 3) -> np.ndarray:
    """Mêmes signaux, mêmes stops/cibles, sens tiré au hasard → distribution de l'espérance."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_draws):
        s = sig.copy()
        s["dir"] = rng.choice([-1, 1], len(s))
        out.append(d.simulate(s)["r"].mean())
    return np.array(out)


def lookahead_check(d: Data, vid: str, n: int = 80, seed: int = 9) -> dict:
    """Recalcule les signaux sur des données tronquées à la clôture de la bougie du signal (30 jours d'historique) :
    le signal doit être identique (même sens, même stop, même cible)."""
    sig = d.sigs(vid)
    rng = np.random.default_rng(seed)
    pick = sig.iloc[np.sort(rng.choice(len(sig), min(n, len(sig)), replace=False))]
    bad = 0
    for _, s in pick.iterrows():
        t = pd.Timestamp(s["time"])
        m1 = d.m1[s["sym"]]
        cut = m1[(m1.index >= t - pd.Timedelta(days=30)) & (m1.index < t)]
        g = signals(features(cut), vid, s["sym"])
        g = g[pd.DatetimeIndex(g["time"]) == t]
        ok = len(g) == 1 and int(g["dir"].iloc[0]) == int(s["dir"]) and \
            np.isclose(g["stop"].iloc[0], s["stop"], rtol=1e-3) and \
            (np.isclose(g["target"].iloc[0], s["target"], rtol=1e-3) or (np.isinf(g["target"].iloc[0]) and np.isinf(s["target"])))
        bad += 0 if ok else 1
    return {"checked": int(len(pick)), "mismatch": int(bad)}


# ------------------------------------------------------------------------------------------- compte 50 €
def eur_per_price_unit(sym: str, t, mid: dict) -> float:
    """Valeur en € d'un mouvement de 1,0 (en prix) pour 0,01 lot (1 000 unités de la devise de base)."""
    eurusd = float(mid["EURUSD"].asof(t))
    if sym in ("EURUSD", "GBPUSD"):
        return 1000.0 / eurusd
    return 1000.0 / float(mid["USDJPY"].asof(t)) / eurusd


def margin_eur(sym: str, t, mid: dict, lev: float = 30.0) -> float:
    eurusd = float(mid["EURUSD"].asof(t))
    base_eur = {"EURUSD": 1.0, "GBPUSD": float(mid["GBPUSD"].asof(t)) / eurusd, "USDJPY": 1.0 / eurusd}[sym]
    return 1000.0 * base_eur / lev


def account(tr: pd.DataFrame, mid: dict, risk: float, extra_pips: float = 0.0, force_min: bool = False,
            eq0: float = 50.0, lev: float = 30.0) -> dict:
    """Rejoue les trades (déjà triés) sur un compte : une position à la fois, lot min 0,01."""
    eq, peak, maxdd, taken, skipped, real_risk = eq0, eq0, 0.0, 0, 0, []
    busy_until = None
    curve = []
    kill20 = None
    pnl_list = []
    for _, x in tr.iterrows():
        t = pd.Timestamp(x["time"])
        if busy_until is not None and t < busy_until:
            continue
        if eq < margin_eur(x["sym"], t, mid, lev):
            curve.append((t, eq))
            break
        per_lot_stop = x["stop"] * eur_per_price_unit(x["sym"], t, mid)          # € perdus au stop pour 0,01 lot
        max_by_margin = int(eq // margin_eur(x["sym"], t, mid, lev))
        n = min(int((risk * eq) // per_lot_stop), max_by_margin)
        if n < 1:
            if not force_min:
                skipped += 1
                continue
            n = 1
        r = x["r"] - extra_pips * PIP[x["sym"]] / x["stop"]
        pnl = r * per_lot_stop * n
        real_risk.append(per_lot_stop * n / eq)
        eq += pnl
        pnl_list.append((pnl, per_lot_stop * n / max(eq - pnl, 1e-9), r))
        taken += 1
        busy_until = t + pd.Timedelta(minutes=float(x["minutes"]) + 1)
        peak = max(peak, eq)
        dd = 1 - eq / peak
        maxdd = max(maxdd, dd)
        if kill20 is None and dd >= 0.20:
            kill20 = str(t.date())
        curve.append((t, eq))
    return {"final": round(eq, 2), "taken": taken, "skipped_risk_too_small": skipped,
            "skipped_share": round(skipped / max(1, taken + skipped), 3),
            "avg_real_risk_pct": round(100 * float(np.mean(real_risk)), 2) if real_risk else None,
            "max_dd_pct": round(100 * maxdd, 1), "kill_switch_20pct_date": kill20,
            "_pnl": pnl_list, "_curve": curve}


def monte_carlo(pnl_list, eq0: float = 50.0, n: int = 1000, seed: int = 5) -> dict:
    """Rééchantillonne (avec remise) les trades pris, en gardant leur R et leur risque relatif (% d'équité)."""
    if not pnl_list:
        return {}
    rng = np.random.default_rng(seed)
    rr = np.array([p[2] for p in pnl_list])
    rk = np.array([p[1] for p in pnl_list])
    finals, half, dd20 = [], 0, 0
    for _ in range(n):
        k = rng.integers(0, len(rr), len(rr))
        eq, peak, hit50, hit20 = eq0, eq0, False, False
        for j in k:
            eq *= 1 + rr[j] * rk[j]
            peak = max(peak, eq)
            hit50 |= eq <= eq0 * 0.5
            hit20 |= eq <= peak * 0.8
        finals.append(eq)
        half += hit50
        dd20 += hit20
    return {"p_lose_50pct": round(half / n, 3), "p_drawdown_20pct": round(dd20 / n, 3),
            "median_final": round(float(np.median(finals)), 2),
            "p10_final": round(float(np.quantile(finals, .1)), 2), "p90_final": round(float(np.quantile(finals, .9)), 2)}
