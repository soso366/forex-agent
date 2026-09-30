"""Chaîne Dukascopy complète, testée hors ligne sur des fichiers bi5 au format binaire réel
(LZMA « alone », enregistrements big-endian : temps, open, close, low, high, volume)."""
import io
import lzma
import struct
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from helpers import UTC, tmp_cfg

from forex_agent.data import dukascopy as dk
from forex_agent.data.providers import CSVProvider, synthetic_m1


def encode_day(df: pd.DataFrame, day: date, symbol: str, side: str, order=("o", "c", "l", "h")) -> bytes:
    """Encode une journée au format Dukascopy (1440 bougies ; minutes sans cotation = plates, volume 0)."""
    p = dk.point(symbol)
    cols = {"BID": ("o", "h", "l", "c"), "ASK": ("ao", "ah", "al", "ac")}[side]
    ren = dict(zip(cols, ("o", "h", "l", "c")))
    start = pd.Timestamp(day, tz="UTC")
    d = df.loc[(df.index >= start) & (df.index < start + pd.Timedelta(days=1)), list(cols)].rename(columns=ren)
    if d.empty:
        return b""
    full = pd.date_range(start, periods=1440, freq="min", tz="UTC")
    r = d[["o", "h", "l", "c"]].reindex(full)
    vol = np.where(r["c"].notna(), 1.5, 0.0)
    last = r["c"].ffill().bfill()
    for k in "ohlc":
        r[k] = r[k].fillna(last)
    pts = {k: np.round(r[k].to_numpy() / p).astype(np.int64) for k in "ohlc"}
    rec = np.zeros(1440, dtype=np.dtype([("t", ">u4"), ("a", ">i4"), ("b", ">i4"), ("c", ">i4"),
                                          ("d", ">i4"), ("v", ">f4")]))
    rec["t"] = np.arange(1440) * 60
    for slot, k in zip("abcd", order):
        rec[slot] = pts[k]
    rec["v"] = vol
    out = rec.tobytes()
    return lzma.compress(bytes(out), format=lzma.FORMAT_ALONE)


class FakeDukascopy:
    """Remplace le réseau : sert des fichiers bi5 construits à partir d'un marché simulé."""

    def __init__(self, symbols, start, end, fail_once=None, order=("o", "c", "l", "h")):
        self.m1 = {s: synthetic_m1(s, datetime.combine(start, datetime.min.time(), UTC),
                                   datetime.combine(end + timedelta(days=1), datetime.min.time(), UTC), seed=3)
                   for s in symbols}
        self.fail_once, self.calls, self.order = set(fail_once or []), 0, order

    def __call__(self, url):
        self.calls += 1
        parts = url.split("/")
        symbol, y, m0, d, fname = parts[-5], int(parts[-4]), int(parts[-3]), int(parts[-2]), parts[-1]
        if url in self.fail_once:
            self.fail_once.discard(url)
            raise ConnectionError("coupure simulée")
        side = fname.split("_")[0]
        raw = encode_day(self.m1[symbol], date(y, m0 + 1, d), symbol, side, self.order)
        return raw or None                                 # jour sans cotation = 404


class DukascopyTest(unittest.TestCase):
    def test_url_uses_zero_based_month(self):
        self.assertEqual(dk.day_url("EURUSD", date(2026, 3, 5), "BID"),
                         "https://datafeed.dukascopy.com/datafeed/EURUSD/2026/02/05/BID_candles_min_1.bi5")

    def test_decode_roundtrip_and_flat_minutes(self):
        day = date(2026, 3, 4)
        fake = FakeDukascopy(["USDJPY"], day, day)
        raw = fake(dk.day_url("USDJPY", day, "ASK"))
        df = dk.decode_bi5(raw, day, "USDJPY")
        self.assertEqual(len(df), 1440)
        src = fake.m1["USDJPY"]
        src = src[(src.index >= pd.Timestamp(day, tz="UTC")) & (src.index < pd.Timestamp(day, tz="UTC") + pd.Timedelta(days=1))]
        common = df.index.intersection(src.index)
        self.assertTrue(np.allclose(df.loc[common, "h"], src.loc[common, "ah"], atol=1e-3))
        self.assertTrue(np.allclose(df.loc[common, "c"], src.loc[common, "ac"], atol=1e-3))

    def test_full_chain_to_csvprovider_with_resume(self):
        tmp = Path(tempfile.mkdtemp())
        start, end = date(2026, 3, 2), date(2026, 3, 13)                 # 2 semaines, week-end inclus
        syms = ["EURUSD", "GBPUSD", "USDJPY"]
        first_url = dk.day_url("GBPUSD", date(2026, 3, 3), "ASK")
        fake = FakeDukascopy(syms, start, end, fail_once=[first_url])
        with redirect_stdout(io.StringIO()):
            rep = dk.prepare(syms, start, end, tmp / "raw", tmp / "m1", fetcher=fake, workers=2, log=lambda *_: None)
        self.assertEqual(len(rep["download"]["errors"]), 1)             # coupure rapportée, pas masquée
        self.assertIn("GBPUSD", rep["symbols"])
        calls_before = fake.calls
        rep = dk.prepare(syms, start, end, tmp / "raw", tmp / "m1", fetcher=fake, workers=2, log=lambda *_: None)
        self.assertEqual(fake.calls - calls_before, 1)                   # reprise : seul le fichier manquant
        self.assertEqual(rep["download"]["errors"], [])
        self.assertEqual(rep["validated_with_csvprovider"], syms)
        for s in syms:
            q = rep["symbols"][s]
            self.assertGreater(q["flat_minutes_removed"], 0)             # minutes du week-end retirées
            self.assertEqual(q["ask_below_bid_removed"], 0)
        prov = CSVProvider(syms, tmp / "m1")
        m1 = prov.m1("EURUSD", datetime(2026, 3, 7, tzinfo=UTC), datetime(2026, 3, 8, tzinfo=UTC))
        self.assertEqual(len(m1), 0)                                     # samedi : aucune minute
        self.assertTrue((prov.m1("EURUSD", datetime(2026, 3, 4, tzinfo=UTC),
                                 datetime(2026, 3, 5, tzinfo=UTC))["ac"] >= prov.m1(
            "EURUSD", datetime(2026, 3, 4, tzinfo=UTC), datetime(2026, 3, 5, tzinfo=UTC))["c"]).all())

    def test_wrong_binary_layout_is_refused_not_corrected(self):
        tmp = Path(tempfile.mkdtemp())
        day = date(2026, 3, 4)
        fake = FakeDukascopy(["EURUSD"], day, day, order=("h", "l", "c", "o"))
        dk.download(["EURUSD"], day, day, tmp, fetcher=fake, workers=1, log=lambda *_: None)
        with self.assertRaises(ValueError):
            dk.build_symbol("EURUSD", day, day, tmp)


class BacktestOnCsvTest(unittest.TestCase):
    def test_v2_backtest_runs_unchanged_on_csv_data(self):
        from forex_agent.__main__ import run_backtest
        tmp = Path(tempfile.mkdtemp())
        start, end = date(2026, 3, 2), date(2026, 3, 13)
        syms = ["EURUSD", "GBPUSD", "USDJPY"]
        dk.prepare(syms, start, end, tmp / "raw", tmp / "m1", fetcher=FakeDukascopy(syms, start, end),
                   workers=2, log=lambda *_: None)
        cfg = tmp_cfg(data={"provider": "csv", "csv_dir": str(tmp / "m1")})
        with redirect_stdout(io.StringIO()):
            text = run_backtest(cfg, warmup_days=5, out_dir=tmp / "bt", progress=False)
        self.assertIn("## Entonnoir par stratégie", text)
        self.assertIn("Cycles", text)
        self.assertTrue((tmp / "bt" / "report.md").exists())
        import sqlite3
        db = sqlite3.connect(tmp / "bt" / "journal.sqlite")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cycles WHERE error IS NOT NULL").fetchone()[0], 0)
        self.assertGreater(db.execute("SELECT COUNT(*) FROM cycles").fetchone()[0], 1000)


if __name__ == "__main__":
    unittest.main()


class CloudPipelineTest(unittest.TestCase):
    """La commande unique utilisée par le déploiement cloud."""

    def _cfg(self, tmp):
        return tmp_cfg(data={"provider": "csv", "csv_dir": str(tmp / "m1")})

    def test_pipeline_produces_the_three_files(self):
        from forex_agent.__main__ import run_pipeline
        tmp = Path(tempfile.mkdtemp())
        start, end = date(2026, 3, 2), date(2026, 3, 13)
        syms = ["EURUSD", "GBPUSD", "USDJPY"]
        with redirect_stdout(io.StringIO()):
            code = run_pipeline(self._cfg(tmp), start, end, results_dir=tmp / "results", data_root=tmp / "data",
                                fetcher=FakeDukascopy(syms, start, end), progress=False)
        self.assertEqual(code, 0)
        for f in ("report.md", "trades.csv", "quality_report.json", "pipeline.log", "STATUS.txt", "run_meta.json"):
            self.assertTrue((tmp / "results" / f).exists(), f)
        self.assertTrue((tmp / "results" / "STATUS.txt").read_text().startswith("OK"))

    def test_pipeline_failure_is_reported_not_hidden(self):
        from forex_agent.__main__ import run_pipeline

        def down(url):
            raise ConnectionError("réseau coupé")
        tmp = Path(tempfile.mkdtemp())
        with redirect_stdout(io.StringIO()):
            code = run_pipeline(self._cfg(tmp), date(2026, 3, 2), date(2026, 3, 4), results_dir=tmp / "results",
                                data_root=tmp / "data", fetcher=down, retry_wait=0, progress=False)
        self.assertEqual(code, 1)
        status = (tmp / "results" / "STATUS.txt").read_text()
        self.assertTrue(status.startswith("ÉCHEC"))
        self.assertIn("téléchargement", status)
        self.assertIn("réseau coupé", (tmp / "results" / "pipeline.log").read_text())

    def test_interrupted_backtest_resumes_to_the_same_result(self):
        import sqlite3
        from unittest import mock
        import forex_agent.__main__ as cli
        from forex_agent.scheduler import replay as real_replay
        tmp = Path(tempfile.mkdtemp())
        start, end = date(2026, 3, 2), date(2026, 3, 13)
        syms = ["EURUSD", "GBPUSD", "USDJPY"]
        dk.prepare(syms, start, end, tmp / "raw", tmp / "m1", fetcher=FakeDukascopy(syms, start, end),
                   workers=2, log=lambda *_: None)
        cfg = self._cfg(tmp)

        def interrupted(c, s, e, **kw):                      # coupure au milieu du rejeu
            real_replay(c, s, s + timedelta(days=2), **kw)
            raise KeyboardInterrupt("coupure simulée")
        with redirect_stdout(io.StringIO()), mock.patch.object(cli, "replay", interrupted):
            with self.assertRaises(KeyboardInterrupt):
                cli.run_backtest(cfg, 5, tmp / "bt_resume", progress=False)
        with redirect_stdout(io.StringIO()) as out:
            cli.run_backtest(cfg, 5, tmp / "bt_resume", progress=False, resume=True)
        self.assertIn("REPRISE", out.getvalue())
        with redirect_stdout(io.StringIO()):
            cli.run_backtest(cfg, 5, tmp / "bt_full", progress=False)

        def summary(d):
            db = sqlite3.connect(tmp / d / "journal.sqlite")
            r = (db.execute("SELECT COUNT(*) FROM cycles").fetchone()[0],
                 db.execute("SELECT COUNT(*), ROUND(SUM(pnl_eur), 6) FROM trades WHERE status='closed'").fetchone())
            db.close()
            return r
        self.assertEqual(summary("bt_resume"), summary("bt_full"))
