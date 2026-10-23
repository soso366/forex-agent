import numpy as np
import pandas as pd

from forex_lab.trend.tsmom import monthly_table, simulate


def _series(drift, n_years=4, seed=0):
    idx = pd.bdate_range("2001-01-01", periods=252 * n_years)
    rng = np.random.default_rng(seed)
    return pd.Series(np.exp(np.cumsum(drift + 0.004 * rng.standard_normal(len(idx)))), index=idx)


def _rates(v):
    return pd.Series(v, index=pd.period_range("2000-01", "2010-12", freq="M"))


def test_signal_ignores_future_prices():
    s = _series(0.0005)
    t1 = monthly_table(s, _rates(0.0), _rates(0.0), 12)
    s2 = s.copy()
    cut = t1.index[5].to_timestamp()  # mois de détention n°6 : on modifie tout ce qui suit le mois de signal
    s2[s2.index >= cut] *= 0.5
    t2 = monthly_table(s2, _rates(0.0), _rates(0.0), 12)
    assert (t1["signal"].iloc[:6] == t2["signal"].iloc[:6]).all()
    assert (t1["force"].iloc[:6] == t2["force"].iloc[:6]).all()


def test_trend_up_is_long_and_carry_sign():
    t = monthly_table(_series(0.001), _rates(0.05), _rates(0.01), 12)
    assert (t["signal"] == 1).all()
    assert np.allclose(t["portage"], 0.04 / 12)


def test_costs_charged_only_on_changes_and_max_positions():
    t = monthly_table(_series(0.001), _rates(0.0), _rates(0.0), 12)
    tabs = {"EURUSD": t, "GBPUSD": t.assign(force=t["force"] / 2), "USDJPY": t.assign(force=t["force"] / 3, prix=t["prix"] * 100)}
    free = simulate(tabs, 2, (0.0, 0.0))
    paid = simulate(tabs, 2, (1.5, 0.0))
    assert (free["positions"] == "EURUSD+ GBPUSD+").all()
    assert paid["changements"].iloc[0] == 2 and (paid["changements"].iloc[1:] == 0).all()
    assert np.isclose((free["net"] - paid["net"]).iloc[1:].abs().max(), 0)
