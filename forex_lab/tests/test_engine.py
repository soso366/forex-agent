"""Contrôles du moteur : prix d'exécution, priorité du stop, timing des signaux, sorties à l'heure."""
import numpy as np
import pandas as pd

from forex_lab.engine import Rules, Simulator, resample, run_bar_strategy


def m1_frame(n=600, start="2025-03-03 00:00", price=1.1000, spread=0.0001, path=None):
    idx = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    mid = np.full(n, price) if path is None else np.asarray(path, float)
    df = pd.DataFrame({"bid_open": mid, "bid_high": mid + 0.00005, "bid_low": mid - 0.00005, "bid_close": mid}, index=idx)
    for c in ("open", "high", "low", "close"):
        df[f"ask_{c}"] = df[f"bid_{c}"] + spread
    return df


def test_spread_cost_flat_market():
    sim = Simulator("EURUSD", m1_frame())
    tr = sim.run_position(1, pd.Timestamp("2025-03-03 01:00", tz="UTC"), Rules(cap_min=30))
    assert abs(tr.pips + 1.0) < 1e-6 and tr.reason == "temps"          # achat à l'ask, sortie au bid = −1 pip
    assert tr.exit_time == pd.Timestamp("2025-03-03 01:30", tz="UTC")


def test_stop_first_when_both_hit_same_minute():
    df = m1_frame()
    k = 70
    df.iloc[k, df.columns.get_loc("bid_high")] = 1.1100
    df.iloc[k, df.columns.get_loc("bid_low")] = 1.0900
    sim = Simulator("EURUSD", df)
    tr = sim.run_position(1, pd.Timestamp("2025-03-03 01:00", tz="UTC"), Rules(sl_pips=20, tp_pips=20))
    assert tr.reason == "stop" and tr.pips < 0


def test_signal_entry_next_bar_open_and_no_lookahead():
    path = np.r_[np.full(300, 1.1000), np.linspace(1.1000, 1.1100, 300)]
    df = m1_frame(path=path)
    bars = resample(df, 60)
    sig = np.zeros(len(bars), bool)
    sig[2] = True                                                      # signal à la clôture de la bougie 02:00-03:00
    sim = Simulator("EURUSD", df)
    trades = run_bar_strategy(sim, bars, sig, np.zeros(len(bars), bool), Rules(max_bars=1), 60)
    assert trades[0].entry_time == pd.Timestamp("2025-03-03 03:00", tz="UTC")
    assert abs(trades[0].entry - (df.loc[trades[0].entry_time, "ask_open"])) < 1e-12


def test_flat_hour_projet():
    sim = Simulator("EURUSD", m1_frame(n=1500, start="2025-03-03 19:00"))
    tr = sim.run_position(-1, pd.Timestamp("2025-03-03 20:30", tz="UTC"), Rules(cap_min=240, flat_utc_hour=21))
    assert tr.exit_time == pd.Timestamp("2025-03-03 21:00", tz="UTC")
