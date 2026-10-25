"""Traductions ligne à ligne des EA testables. Paramètres = valeurs d'origine.

Chaque dictionnaire PARAMS utilise les noms exacts des `input` MQL5 :
check_params.py vérifie automatiquement qu'ils sont identiques aux fichiers
d'origine (commit figé dans sources.json).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import (POINT, PIP, TICK_VALUE, Sim, atr_mt5, bands_mt5, normalize_lot_clamp,
                    normalize_lot_floor, resample, rsi_mt5, server_hour)

# ---------------------------------------------------------------- smizxe/mt5-agent-toolkit
SMIZXE_PARAMS = {
    "InpRsiPeriod": 14, "InpBuyLevel": 30.0, "InpSellLevel": 70.0,
    "InpRiskPercent": 1.0, "InpStopLossPoints": 300, "InpTakeProfitPoints": 600,
    "InpMaxPositions": 1, "InpMaxTradesPerDay": 5, "InpMaxSpreadPoints": 30,
}
SMIZXE_TF = "1h"


def run_smizxe(m1: pd.DataFrame, bars: pd.DataFrame, i0: int, i1: int, sim: Sim, mode: str):
    """mode = 'level' (RsiLevel.mq5) ou 'reversal' (RsiReversal.mq5)."""
    P = SMIZXE_PARAMS
    rsi = rsi_mt5(bars["bid_close"].to_numpy(), P["InpRsiPeriod"])
    start = bars["start"].to_numpy()
    day = bars["time"].dt.date.to_numpy()          # heure serveur Exness = UTC
    entries_per_day: dict = {}
    for b in range(i0, i1):
        m0 = int(start[b])
        sim.advance_to(m0)
        sim.mark(m0)
        r1, r2 = rsi[b - 1], rsi[b - 2]
        if np.isnan(r1) or np.isnan(r2):
            continue
        spread_pts = round((sim.ao[m0] - sim.bo[m0]) / POINT)
        if spread_pts > P["InpMaxSpreadPoints"]:
            continue
        if sim.pos is not None:                       # InpMaxPositions = 1
            continue
        if P["InpMaxTradesPerDay"] > 0 and entries_per_day.get(day[b], 0) >= P["InpMaxTradesPerDay"]:
            continue
        if mode == "level":
            long_, short_ = r1 < P["InpBuyLevel"], r1 > P["InpSellLevel"]
        else:
            long_ = r2 <= P["InpBuyLevel"] and r1 > P["InpBuyLevel"]
            short_ = r2 >= P["InpSellLevel"] and r1 < P["InpSellLevel"]
        if not (long_ or short_):
            continue
        side = 1 if long_ else -1
        sl_dist = P["InpStopLossPoints"] * POINT
        lot = normalize_lot_floor(sim.balance * P["InpRiskPercent"] / 100.0 / (P["InpStopLossPoints"] * TICK_VALUE))
        if lot <= 0.0:
            sim.refused_lot += 1
            continue
        quote = sim.ao[m0] if side > 0 else sim.bo[m0]
        sl = round(quote - side * sl_dist, 5)
        tp = round(quote + side * P["InpTakeProfitPoints"] * POINT, 5)
        sim.open(side, m0, quote, sl, tp, lot, f"rsi={r1:.1f}")
        entries_per_day[day[b]] = entries_per_day.get(day[b], 0) + 1


# ---------------------------------------------------------------- sbrakni/mean-reversion-mql5
SBRAKNI_PARAMS = {   # valeurs par défaut de EA/MeanReversionScalper.mq5
    "InpBBPeriod": 20, "InpBBDeviation": 1.75, "InpRSIPeriod": 7, "InpRSIOversold": 10.0,
    "InpRSIOverbought": 90.0, "InpATRPeriod": 14, "InpRiskPercent": 1.0, "InpFixedLots": 0.1,
    "InpSLMultiplier": 1.5, "InpTPMode": 0, "InpTPRRRatio": 2.0, "InpMaxBarsInTrade": 30,
    "InpMaxSpreadPips": 3.0, "InpCooldownBars": 3, "InpUseTimeFilter": True, "InpSessionStart": 7,
    "InpSessionEnd": 20, "InpUseBBWidthFilter": True, "InpBBWidthLookback": 200,
    "InpBBWidthMinPctile": 30.0, "InpRequireConfirmation": False, "InpMinRR": 1.0,
}
SBRAKNI_TF = "5min"


def run_sbrakni(m1, bars, i0, i1, sim: Sim, hour_mode: str = "utc", params: dict | None = None):
    P = dict(SBRAKNI_PARAMS, **(params or {}))
    c = bars["bid_close"].to_numpy()
    bbu, bbm, bbl = bands_mt5(c, P["InpBBPeriod"], P["InpBBDeviation"])
    rsi = rsi_mt5(c, P["InpRSIPeriod"])
    atr = atr_mt5(bars["bid_high"].to_numpy(), bars["bid_low"].to_numpy(), c, P["InpATRPeriod"])
    hours = server_hour(bars["time"], hour_mode)
    start = bars["start"].to_numpy()
    look = P["InpBBWidthLookback"]
    hist = np.zeros(look)
    idx = 0
    bars_in_trade = 0
    bars_since = P["InpCooldownBars"] + 1
    assert P["InpTPMode"] == 0 and not P["InpRequireConfirmation"]
    for b in range(i0, i1):
        m0 = int(start[b])
        sim.advance_to(m0)
        sim.mark(m0)
        bars_since += 1
        if np.isnan(bbu[b - 1]) or np.isnan(rsi[b - 1]) or np.isnan(atr[b - 1]):
            continue
        width = (bbu[b - 1] - bbl[b - 1]) / bbm[b - 1] if bbm[b - 1] > 0 else 0.0
        hist[idx] = width
        idx = (idx + 1) % look
        if sim.pos is not None:
            bars_in_trade += 1
            if P["InpMaxBarsInTrade"] > 0 and bars_in_trade >= P["InpMaxBarsInTrade"]:
                sim.close_market(m0, "sortie_au_temps")
                bars_in_trade = 0
            continue
        if bars_since < P["InpCooldownBars"]:
            continue
        if P["InpUseTimeFilter"] and not (P["InpSessionStart"] <= hours[b] < P["InpSessionEnd"]):
            continue
        spread_pips = round((sim.ao[m0] - sim.bo[m0]) / POINT) * POINT / PIP
        if spread_pips > P["InpMaxSpreadPips"]:
            continue
        a1 = atr[b - 1]
        if a1 <= 0:
            continue
        if P["InpUseBBWidthFilter"]:
            valid = hist > 0
            if valid.sum() >= 50:
                pct = (hist[valid] < width).sum() / valid.sum() * 100.0
                if pct < P["InpBBWidthMinPctile"]:
                    continue
        buy = c[b - 1] < bbl[b - 1] and rsi[b - 1] < P["InpRSIOversold"]
        sell = c[b - 1] > bbu[b - 1] and rsi[b - 1] > P["InpRSIOverbought"]
        if buy:
            entry = sim.ao[m0]
            sl = entry - P["InpSLMultiplier"] * a1
            sl_dist = entry - sl
            tp = bbu[b - 1]
            if tp <= entry:
                tp = entry + a1
            if (tp - entry) / sl_dist < P["InpMinRR"]:
                continue
            side = 1
        elif sell:
            entry = sim.bo[m0]
            sl = entry + P["InpSLMultiplier"] * a1
            sl_dist = sl - entry
            tp = bbl[b - 1]
            if tp >= entry:
                tp = entry - a1
            if (entry - tp) / sl_dist < P["InpMinRR"]:
                continue
            side = -1
        else:
            continue
        risk_money = sim.balance * P["InpRiskPercent"] / 100.0
        lots = normalize_lot_clamp(risk_money / ((sl_dist / POINT) * TICK_VALUE))
        sim.open(side, m0, entry, round(sl, 5), round(tp, 5), lots, f"rsi={rsi[b-1]:.1f}")
        bars_in_trade = 0
        bars_since = 0


STRATEGIES = {
    "smizxe_RsiLevel": (SMIZXE_TF, lambda m1, bars, i0, i1, sim: run_smizxe(m1, bars, i0, i1, sim, "level")),
    "smizxe_RsiReversal": (SMIZXE_TF, lambda m1, bars, i0, i1, sim: run_smizxe(m1, bars, i0, i1, sim, "reversal")),
    "sbrakni_MeanReversion": (SBRAKNI_TF, lambda m1, bars, i0, i1, sim: run_sbrakni(m1, bars, i0, i1, sim, "utc")),
}
# Variantes de contrôle (même stratégie, mêmes paramètres, seule la convention change)
CONTROLS = {
    "sbrakni_MeanReversion_heure_serveur_EET": (SBRAKNI_TF, lambda m1, bars, i0, i1, sim: run_sbrakni(m1, bars, i0, i1, sim, "eet_ny")),
    "sbrakni_MeanReversion_set_Best": (SBRAKNI_TF, lambda m1, bars, i0, i1, sim: run_sbrakni(m1, bars, i0, i1, sim, "utc", {"InpMaxSpreadPips": 1.0})),
}
