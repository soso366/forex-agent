"""Les 10 méthodes documentées (règles et paramètres de la source, voir PROTOCOLE.md)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from dsim import lots_for_notional, lots_for_risk, minute_path, rsi, stop_fill, wilder_atr


def _day_index(h, d):
    """Indice du jour de trading de chaque bougie ; len(d) si le jour n'existe pas (week-end) → ignoré."""
    keys = d.index.to_numpy()
    j = np.searchsorted(keys, h["day"].to_numpy())
    ok = (j < len(keys)) & (keys[np.minimum(j, len(keys) - 1)] == h["day"].to_numpy())
    return np.where(ok, j, len(keys))


def _bars(h):
    return h.itertuples(index=False)


# ------------------------------------------------------------------ M1 / M2 Turtle
def _shadow_outcomes(d, n_in, n_out, N):
    """Résultat hypothétique de chaque cassure S1 (pris ou non), sur barres journalières, comme dans les règles."""
    hi_in = d["high"].rolling(n_in).max().shift(1).to_numpy()
    lo_in = d["low"].rolling(n_in).min().shift(1).to_numpy()
    hi_out = d["high"].rolling(n_out).max().shift(1).to_numpy()
    lo_out = d["low"].rolling(n_out).min().shift(1).to_numpy()
    H, L, n = d["high"].to_numpy(), d["low"].to_numpy(), N.to_numpy()
    res = []          # (jour de cassure, jour de résolution, côté, gagnant)
    for j in range(len(d)):
        for side in (1, -1):
            lvl = hi_in[j] if side > 0 else lo_in[j]
            if np.isnan(lvl) or np.isnan(n[j - 1] if j else np.nan):
                continue
            if (side > 0 and H[j] > lvl) or (side < 0 and L[j] < lvl):
                stop = lvl - side * 2 * n[j - 1]
                for k in range(j, len(d)):
                    if side > 0 and L[k] <= stop:
                        res.append((j, k, side, False)); break
                    if side < 0 and H[k] >= stop:
                        res.append((j, k, side, False)); break
                    if k > j:
                        ex = lo_out[k] if side > 0 else hi_out[k]
                        if (side > 0 and L[k] <= ex) or (side < 0 and H[k] >= ex):
                            res.append((j, k, side, (ex - lvl) * side > 0)); break
    return res


def run_turtle(h, d, i0, i1, book, p):
    n_in, n_out, skip = p["n_in"], p["n_out"], p["skip"]
    N = wilder_atr(d, p["n_atr"])
    hi_in = d["high"].rolling(n_in).max().shift(1).to_numpy()
    lo_in = d["low"].rolling(n_in).min().shift(1).to_numpy()
    hi_fs = d["high"].rolling(55).max().shift(1).to_numpy()
    lo_fs = d["low"].rolling(55).min().shift(1).to_numpy()
    hi_out = d["high"].rolling(n_out).max().shift(1).to_numpy()
    lo_out = d["low"].rolling(n_out).min().shift(1).to_numpy()
    Nprev = N.shift(1).to_numpy()
    shadows = _shadow_outcomes(d, n_in, n_out, N) if skip else []
    jidx = _day_index(h, d)
    last_add = None
    for i, bar in enumerate(_bars(h.iloc[i0:i1]), start=i0):
        j = jidx[i]
        if j >= len(d) or j < 1:
            continue
        spread = bar.ao - bar.bo
        n = Nprev[j]
        if np.isnan(n) or np.isnan(hi_in[j]) or np.isnan(lo_out[j]):
            book.mark(bar.bc, bar.ac)
            continue
        s = book.side
        if s:
            stop = book.units[-1].stop
            ex = lo_out[j] if s > 0 else hi_out[j]
            lvl = max(stop, ex) if s > 0 else min(stop, ex)
            if (s > 0 and bar.bl <= lvl) or (s < 0 and bar.bh >= lvl):
                px = stop_fill(bar, lvl, -s)
                book.close_all(px, spread, bar.time, "stop" if lvl == stop else "sortie_canal")
                s = 0
            else:
                while len(book.units) < p["max_units"]:
                    nxt = last_add + s * 0.5 * n
                    if (s > 0 and bar.bh >= nxt) or (s < 0 and bar.bl <= nxt):
                        book.open(s, stop_fill(bar, nxt, s), spread, lots_for_risk(book.mark(bar.bo, bar.ao), 0.01, 2 * n), bar.time)
                        last_add = nxt
                        for u in book.units:
                            u.stop = last_add - s * 2 * n
                    else:
                        break
                st = book.units[-1].stop
                if (s > 0 and bar.bl <= st) or (s < 0 and bar.bh >= st):     # ajout puis stop dans la même heure
                    book.ambiguous += 1
                    book.close_all(st, spread, bar.time, "stop")
                    s = 0
        if not book.side:
            for side in (1, -1):
                lvl = hi_in[j] if side > 0 else lo_in[j]
                if not ((side > 0 and bar.bh > lvl) or (side < 0 and bar.bl < lvl)):
                    continue
                if skip:
                    prev = [x for x in shadows if x[0] < j and x[1] < j]
                    if prev and prev[-1][3]:
                        fs = hi_fs[j] if side > 0 else lo_fs[j]          # sécurité : cassure 55 jours prise quand même
                        if not ((side > 0 and bar.bh > fs) or (side < 0 and bar.bl < fs)):
                            continue
                        lvl = fs
                px = stop_fill(bar, lvl, side)
                book.open(side, px, spread, lots_for_risk(book.mark(bar.bo, bar.ao), 0.01, 2 * n), bar.time,
                          stop=px - side * 2 * n)
                last_add = px
                break
        book.mark(bar.bc, bar.ac)


# ------------------------------------------------------------------ M3 Donchian 4 semaines
def run_donchian(h, d, i0, i1, book, p):
    n_ = p["n"]
    N = wilder_atr(d, 20).shift(1).to_numpy()
    hi = d["high"].rolling(n_).max().shift(1).to_numpy()
    lo = d["low"].rolling(n_).min().shift(1).to_numpy()
    jidx = _day_index(h, d)
    for i, bar in enumerate(_bars(h.iloc[i0:i1]), start=i0):
        j = jidx[i]
        if j >= len(d) or np.isnan(hi[j]) or np.isnan(N[j]):
            book.mark(bar.bc, bar.ac); continue
        spread = bar.ao - bar.bo
        up, dn = bar.bh > hi[j], bar.bl < lo[j]
        if up and dn:
            book.ambiguous += 1
        for side, ok, lvl in ((1, up, hi[j]), (-1, dn, lo[j])):
            if ok and book.side != side:
                px = stop_fill(bar, lvl, side)
                book.close_all(px, spread, bar.time, "retournement")
                book.open(side, px, spread, lots_for_risk(book.mark(bar.bo, bar.ao), 0.01, 2 * N[j]), bar.time)
        book.mark(bar.bc, bar.ac)


# ------------------------------------------------------------------ M4 Momentum 12 mois
def run_tsmom(h, d, i0, i1, book, p):
    c = d["close"]
    ret12 = c / c.shift(p["lookback_days"]) - 1
    vol = c.pct_change().rolling(60).std() * np.sqrt(252)
    month = d.index.to_period("M")
    jidx = _day_index(h, d)
    last_month = None
    for i, bar in enumerate(_bars(h.iloc[i0:i1]), start=i0):
        j = jidx[i]
        if j >= len(d) or j < 1:
            continue
        m = month[j]
        spread = bar.ao - bar.bo
        if m != last_month and h["day"].iloc[i] == d.index[j]:
            last_month = m
            r, v = ret12.iloc[j - 1], vol.iloc[j - 1]
            if not (np.isnan(r) or np.isnan(v) or v <= 0):
                side = 1 if r > 0 else -1
                book.close_all(bar.bo, spread, bar.time, "rééquilibrage")
                lev = min(p["target_vol"] / v, 3.0)
                book.open(side, bar.bo, spread, lots_for_notional(book.mark(bar.bo, bar.ao), bar.bo, lev), bar.time)
        book.mark(bar.bc, bar.ac)


# ------------------------------------------------------------------ M5 SMA 50/200, M6 RSI(2), M7 Dual Thrust (signaux journaliers)
def _first_bar_of_day(h):
    return h["day"].ne(h["day"].shift(1)).to_numpy()


def run_sma(h, d, i0, i1, book, p):
    c = d["close"]
    fast, slow = c.rolling(p["fast"]).mean().shift(1).to_numpy(), c.rolling(p["slow"]).mean().shift(1).to_numpy()
    first = _first_bar_of_day(h)
    jidx = _day_index(h, d)
    for i, bar in enumerate(_bars(h.iloc[i0:i1]), start=i0):
        j = jidx[i]
        if first[i] and j < len(d) and not np.isnan(slow[j]):
            side = 1 if fast[j] > slow[j] else -1
            spread = bar.ao - bar.bo
            if book.side != side:
                book.close_all(bar.bo, spread, bar.time, "croisement")
                book.open(side, bar.bo, spread, lots_for_notional(book.mark(bar.bo, bar.ao), bar.bo), bar.time)
        book.mark(bar.bc, bar.ac)


def run_rsi2(h, d, i0, i1, book, p):
    c = d["close"]
    r = rsi(c, 2).shift(1).to_numpy()
    sma_t = c.rolling(p["trend"]).mean().shift(1).to_numpy()
    sma_x = c.rolling(p["exit"]).mean().shift(1).to_numpy()
    cl = c.shift(1).to_numpy()
    first = _first_bar_of_day(h)
    jidx = _day_index(h, d)
    for i, bar in enumerate(_bars(h.iloc[i0:i1]), start=i0):
        j = jidx[i]
        if first[i] and j < len(d) and not np.isnan(sma_t[j]):
            spread = bar.ao - bar.bo
            s = book.side
            if (s > 0 and cl[j] > sma_x[j]) or (s < 0 and cl[j] < sma_x[j]):
                book.close_all(bar.bo, spread, bar.time, "sortie_sma5")
            if not book.side:
                if cl[j] > sma_t[j] and r[j] < p["lo"]:
                    book.open(1, bar.bo, spread, lots_for_notional(book.mark(bar.bo, bar.ao), bar.bo), bar.time)
                elif cl[j] < sma_t[j] and r[j] > 100 - p["lo"]:
                    book.open(-1, bar.bo, spread, lots_for_notional(book.mark(bar.bo, bar.ao), bar.bo), bar.time)
        book.mark(bar.bc, bar.ac)


def run_dual_thrust(h, d, i0, i1, book, p):
    n, k = p["n"], p["k"]
    hh = d["high"].rolling(n).max().shift(1); ll = d["low"].rolling(n).min().shift(1)
    hc = d["close"].rolling(n).max().shift(1); lc = d["close"].rolling(n).min().shift(1)
    rng = np.maximum(hh - lc, hc - ll).to_numpy()
    first = _first_bar_of_day(h)
    jidx = _day_index(h, d)
    up = dn = np.nan
    for i, bar in enumerate(_bars(h.iloc[i0:i1]), start=i0):
        j = jidx[i]
        if j >= len(d) or np.isnan(rng[j]):
            book.mark(bar.bc, bar.ac); continue
        if first[i]:
            up, dn = bar.bo + k * rng[j], bar.bo - k * rng[j]
        spread = bar.ao - bar.bo
        hit_up, hit_dn = bar.bh >= up, bar.bl <= dn
        if hit_up and hit_dn:
            book.ambiguous += 1
            order = (1, -1) if book.side < 0 else (-1, 1)        # cas défavorable : retournement contre la position
        else:
            order = (1,) if hit_up else (-1,) if hit_dn else ()
        for side in order:
            if book.side != side:
                lvl = up if side > 0 else dn
                px = stop_fill(bar, lvl, side)
                book.close_all(px, spread, bar.time, "retournement")
                book.open(side, px, spread, lots_for_notional(book.mark(bar.bo, bar.ao), px), bar.time)
        book.mark(bar.bc, bar.ac)


# ------------------------------------------------------------------ M8 effet de session
def run_session(h, d, i0, i1, book, p):
    for i, bar in enumerate(_bars(h.iloc[i0:i1]), start=i0):
        spread = bar.ao - bar.bo
        if bar.weekday < 5:
            if bar.ldn_hour == p["eu_start"] and book.side == 0:
                book.open(-1, bar.bo, spread, lots_for_notional(book.mark(bar.bo, bar.ao), bar.bo), bar.time)
            elif bar.ldn_hour == p["eu_end"] and book.side < 0:
                book.close_all(bar.bo, spread, bar.time, "fin_europe")
            if bar.ny_hour == p["us_start"] and book.side == 0:
                book.open(1, bar.bo, spread, lots_for_notional(book.mark(bar.bo, bar.ao), bar.bo), bar.time)
            elif bar.ny_hour == p["us_end"] and book.side > 0:
                book.close_all(bar.bo, spread, bar.time, "fin_usa")
        book.mark(bar.bc, bar.ac)


# ------------------------------------------------------------------ M9 NR7, M10 stretch (Crabel) : un trade par jour, sortie à la clôture
def _day_breakout(h, d, i0, i1, book, levels):
    """levels[j] = (niveau haut, niveau bas, stop long, stop court) ou None ; sortie à la dernière bougie du jour."""
    jidx = _day_index(h, d)
    last = h["day"].ne(h["day"].shift(-1)).to_numpy()
    done_day = None
    for i, bar in enumerate(_bars(h.iloc[i0:i1]), start=i0):
        j = jidx[i]
        spread = bar.ao - bar.bo
        lv = levels.get(j) if j < len(d) else None
        if book.side and lv is not None:
            st = book.units[0].stop
            s = book.side
            if (s > 0 and bar.bl <= st) or (s < 0 and bar.bh >= st):
                book.close_all(stop_fill(bar, st, -s), spread, bar.time, "stop")
        if lv is not None and not book.side and done_day != j:
            up, dn, st_l, st_s = lv
            hu, hd = bar.bh >= up, bar.bl <= dn
            if hu and hd:
                book.ambiguous += 1
            for side, ok, lvl, st in ((1, hu, up, st_l), (-1, hd, dn, st_s)):
                if ok:
                    px = stop_fill(bar, lvl, side)
                    book.open(side, px, spread, lots_for_risk(book.mark(bar.bo, bar.ao), 0.01, abs(px - st)), bar.time, stop=st)
                    done_day = j
                    _, stopped, amb = minute_path(h, i, side, lvl, st)     # ordre réel entrée / stop, à la minute
                    if stopped:
                        book.ambiguous += int(amb)
                        book.close_all(stop_fill(bar._replace(bo=st), st, -side), spread, bar.time, "stop")
                    break
        if book.side and last[i]:
            book.close_all(bar.bc, bar.ac - bar.bc, bar.time, "cloture_jour")
        book.mark(bar.bc, bar.ac)


def run_nr7(h, d, i0, i1, book, p):
    rng = d["high"] - d["low"]
    nr = (rng == rng.rolling(p["n"]).min()).shift(1).fillna(False).to_numpy()
    H, L = d["high"].shift(1).to_numpy(), d["low"].shift(1).to_numpy()
    levels = {j: (H[j], L[j], L[j], H[j]) for j in range(len(d)) if nr[j]}
    _day_breakout(h, d, i0, i1, book, levels)


def run_stretch(h, d, i0, i1, book, p):
    o = d["open"]
    near = np.minimum(d["high"] - o, o - d["low"])
    st = near.rolling(p["n"]).mean().shift(1).to_numpy()
    O = o.to_numpy()
    levels = {j: (O[j] + st[j] * p["mult"], O[j] - st[j] * p["mult"], O[j], O[j]) for j in range(len(d)) if not np.isnan(st[j]) and st[j] > 0}
    _day_breakout(h, d, i0, i1, book, levels)


METHODS = {
    "M1_turtle_S1": (run_turtle, dict(n_in=20, n_out=10, n_atr=20, skip=True, max_units=4), ["n_in", "n_out"]),
    "M2_turtle_S2": (run_turtle, dict(n_in=55, n_out=20, n_atr=20, skip=False, max_units=4), ["n_in", "n_out"]),
    "M3_donchian_4_semaines": (run_donchian, dict(n=20), ["n"]),
    "M4_momentum_12_mois": (run_tsmom, dict(lookback_days=252, target_vol=0.10), ["lookback_days"]),
    "M5_sma_50_200": (run_sma, dict(fast=50, slow=200), ["fast", "slow"]),
    "M6_rsi2_connors": (run_rsi2, dict(trend=200, exit=5, lo=10), ["trend", "exit", "lo"]),
    "M7_dual_thrust": (run_dual_thrust, dict(n=4, k=0.5), ["n", "k"]),
    "M8_effet_session": (run_session, dict(eu_start=7, eu_end=12, us_start=8, us_end=16), []),
    "M9_nr7_crabel": (run_nr7, dict(n=7), ["n"]),
    "M10_stretch_crabel": (run_stretch, dict(n=10, mult=1.0), ["n", "mult"]),
}
