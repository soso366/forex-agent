"""Simulateur de recherche : un trade = entrée au marché, stop, cible, sortie forcée après `hold` minutes.

Exécution réaliste sur M1 bid/ask :
- achat au ASK d'ouverture de la minute d'entrée, sortie au BID (stop/cible testés sur bid_low/bid_high) ;
- vente au BID, sortie au ASK ;
- stop et cible touchés dans la même minute → on compte le STOP (prudent) ;
- sortie au temps : clôture de la dernière minute (bid pour un achat, ask pour une vente).
Le R est mesuré par rapport à la distance de stop prévue à l'entrée (prix mid du signal → stop).
Aucune taille de position ni capital ici : on mesure l'avantage en R, coûts de spread inclus.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class Market:
    def __init__(self, df: pd.DataFrame):
        self.t = df.index.values
        self.bo, self.bh, self.bl, self.bc = (df[c].to_numpy() for c in ("bo", "bh", "bl", "bc"))
        self.ao, self.ah, self.al, self.ac = (df[c].to_numpy() for c in ("ao", "ah", "al", "ac"))

    def idx(self, times) -> np.ndarray:
        """Index de la première minute ≥ time."""
        return np.searchsorted(self.t, np.asarray(times, dtype="datetime64[ns]"))


def simulate(m: Market, entry_times, directions, stop_dist, target_dist, hold: int = 30,
             max_gap_min: int = 5) -> pd.DataFrame:
    """directions : +1 achat / -1 vente ; stop_dist, target_dist : distances en prix depuis le prix d'entrée
    (target_dist = np.inf → pas de cible, sortie au temps uniquement).
    Renvoie r, mfe_r, mae_r, exit ('stop' | 'target' | 'time' | 'skip'), minutes."""
    et = pd.DatetimeIndex(entry_times)
    et = (et.tz_convert("UTC").tz_localize(None) if et.tz is not None else et).values
    n = len(et)
    i0 = m.idx(et)
    d = np.asarray(directions, dtype=float)
    sd = np.asarray(stop_dist, dtype=float)
    td = np.asarray(target_dist, dtype=float)
    r = np.full(n, np.nan)
    mfe = np.full(n, np.nan)
    mae = np.full(n, np.nan)
    ex = np.array(["skip"] * n, dtype=object)
    mins = np.full(n, np.nan)
    end_ns = np.timedelta64(hold, "m")
    for k in range(n):
        i = i0[k]
        if i >= len(m.t) or not (sd[k] > 0):
            continue
        t_in = m.t[i]
        if t_in - et[k] > np.timedelta64(max_gap_min, "m"):
            continue                                    # pas de cotation proche de l'heure prévue
        j_end = np.searchsorted(m.t, t_in + end_ns)     # minutes [i, j_end) disponibles pendant la durée
        if j_end <= i:
            continue
        if d[k] > 0:
            px = m.ao[i]
            stop, tgt = px - sd[k], px + td[k]
            lo, hi = m.bl[i:j_end], m.bh[i:j_end]
            hit_s = np.nonzero(lo <= stop)[0]
            hit_t = np.nonzero(hi >= tgt)[0] if np.isfinite(td[k]) else np.array([], int)
            fav, adv = hi.max() - px, px - lo.min()
            last = m.bc[j_end - 1]
        else:
            px = m.bo[i]
            stop, tgt = px + sd[k], px - td[k]
            lo, hi = m.al[i:j_end], m.ah[i:j_end]
            hit_s = np.nonzero(hi >= stop)[0]
            hit_t = np.nonzero(lo <= tgt)[0] if np.isfinite(td[k]) else np.array([], int)
            fav, adv = px - lo.min(), hi.max() - px
            last = m.ac[j_end - 1]
        s_i = hit_s[0] if len(hit_s) else 10 ** 9
        t_i = hit_t[0] if len(hit_t) else 10 ** 9
        if s_i <= t_i and s_i < 10 ** 9:
            r[k], ex[k], mins[k] = -1.0, "stop", s_i + 1
            # glissement : si l'ouverture de la minute est déjà au-delà du stop, sortie à l'ouverture
            o = m.bo[i + s_i] if d[k] > 0 else m.ao[i + s_i]
            if (d[k] > 0 and o < stop) or (d[k] < 0 and o > stop):
                r[k] = d[k] * (o - px) / sd[k]
            # sinon perte exacte = stop
        elif t_i < 10 ** 9:
            r[k], ex[k], mins[k] = td[k] / sd[k], "target", t_i + 1
        else:
            r[k], ex[k], mins[k] = d[k] * (last - px) / sd[k], "time", j_end - i
        mfe[k], mae[k] = fav / sd[k], adv / sd[k]
    return pd.DataFrame({"r": r, "mfe_r": mfe, "mae_r": mae, "exit": ex, "minutes": mins})
