"""Simulateur de référence, écrit indépendamment du moteur (calcul vectorisé par trade), pour comparer les transactions
une à une. Couvre : entrée au marché, stop, objectif, sortie à l'heure limite. Volontairement lent et simple.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import pip


def reference_trade(m1: pd.DataFrame, symbol: str, side: int, entry_time: pd.Timestamp,
                    sl_pips: float | None, tp_pips: float | None, exit_by: pd.Timestamp):
    p = pip(symbol)
    w = m1[m1.index >= entry_time]
    if w.empty:
        return None
    t0 = w.index[0]
    entry = w["ask_open"].iloc[0] if side > 0 else w["bid_open"].iloc[0]
    # fenêtre de vie : de la minute d'entrée jusqu'à la dernière minute strictement avant exit_by
    life = w[w.index < exit_by] if exit_by > t0 else w.iloc[:1]
    if side > 0:
        adverse, favorable, opens = life["bid_low"].to_numpy(), life["bid_high"].to_numpy(), life["bid_open"].to_numpy()
        sl = entry - sl_pips * p if sl_pips else -np.inf
        tp = entry + tp_pips * p if tp_pips else np.inf
        hit_sl, hit_tp = adverse <= sl, favorable >= tp
    else:
        adverse, favorable, opens = life["ask_high"].to_numpy(), life["ask_low"].to_numpy(), life["ask_open"].to_numpy()
        sl = entry + sl_pips * p if sl_pips else np.inf
        tp = entry - tp_pips * p if tp_pips else -np.inf
        hit_sl, hit_tp = adverse >= sl, favorable <= tp
    first_sl = int(np.argmax(hit_sl)) if hit_sl.any() else None
    first_tp = int(np.argmax(hit_tp)) if hit_tp.any() else None
    if first_sl is not None and (first_tp is None or first_sl <= first_tp):
        k = first_sl
        px = sl if k == 0 else (min(opens[k], sl) if side > 0 else max(opens[k], sl))
        return {"entry_time": t0, "exit_time": life.index[k], "entry": entry, "exit": px, "reason": "stop"}
    if first_tp is not None:
        k = first_tp
        px = tp if k == 0 else (max(opens[k], tp) if side > 0 else min(opens[k], tp))
        return {"entry_time": t0, "exit_time": life.index[k], "entry": entry, "exit": px, "reason": "objectif"}
    after = w[w.index >= exit_by]
    if after.empty:
        return None
    px = after["bid_open"].iloc[0] if side > 0 else after["ask_open"].iloc[0]
    return {"entry_time": t0, "exit_time": after.index[0], "entry": entry, "exit": px, "reason": "temps"}
