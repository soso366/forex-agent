"""Journal et persistance (SQLite + JSONL lisible).

Le compte paper, les positions et tout l'historique vivent ici : chaque cycle
(même lancé par un nouveau processus via cron) relit l'état existant."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS account (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    currency TEXT, starting_capital REAL, balance REAL, peak_equity REAL,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT, direction TEXT, strategy TEXT,
    entry REAL, stop REAL, initial_stop REAL, target REAL,
    units REAL, risk_eur REAL, margin_eur REAL,
    entry_time TEXT, last_checked TEXT, exit_time TEXT, exit_price REAL,
    duration_min REAL, entry_reason TEXT, exit_reason TEXT,
    pnl_eur REAL, balance_after REAL, status TEXT,
    intrabar_ambiguous INTEGER DEFAULT 0, setup_json TEXT,
    regime TEXT, session TEXT, killzone TEXT,
    mfe_r REAL DEFAULT 0, mae_r REAL DEFAULT 0, r_multiple REAL
);
CREATE TABLE IF NOT EXISTS position_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER, ts TEXT, action TEXT, old_stop REAL, new_stop REAL, price REAL, reason TEXT
);
CREATE TABLE IF NOT EXISTS cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, balance REAL, equity REAL, open_positions TEXT, markets TEXT,
    decisions TEXT, llm_status TEXT, prompt_hash TEXT, summary TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS market_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id INTEGER, ts TEXT, symbol TEXT, bid REAL, ask REAL, spread_pips REAL,
    timeframes TEXT, regime TEXT, trend TEXT, structure TEXT, volatility TEXT,
    context_json TEXT, strategies_considered TEXT, opportunities TEXT,
    chosen_strategy TEXT, decision TEXT, reason TEXT
);
CREATE TABLE IF NOT EXISTS ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, cycle_id INTEGER, ts TEXT, text TEXT
);
CREATE INDEX IF NOT EXISTS ix_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS ix_snap_cycle ON market_snapshots(cycle_id);
"""


def _j(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, default=str)


class Store:
    def __init__(self, db_path: str | Path, jsonl_path: str | Path | None = None):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        cols = {r[1] for r in self.db.execute("PRAGMA table_info(trades)")}
        for col, typ in (("regime", "TEXT"), ("session", "TEXT"), ("killzone", "TEXT"),
                         ("mfe_r", "REAL DEFAULT 0"), ("mae_r", "REAL DEFAULT 0"), ("r_multiple", "REAL")):
            if col not in cols:                       # migration d'un journal V1
                self.db.execute(f"ALTER TABLE trades ADD COLUMN {col} {typ}")
        self.db.commit()
        self.jsonl = Path(jsonl_path) if jsonl_path else None

    # ------------------------------------------------------------ compte
    def init_account(self, currency: str, capital: float, now: datetime) -> None:
        if self.db.execute("SELECT 1 FROM account WHERE id=1").fetchone() is None:
            self.db.execute("INSERT INTO account VALUES (1,?,?,?,?,?)",
                            (currency, capital, capital, capital, now.isoformat()))
            self.db.commit()

    def account(self) -> sqlite3.Row:
        return self.db.execute("SELECT * FROM account WHERE id=1").fetchone()

    def set_balance(self, balance: float, peak: float) -> None:
        self.db.execute("UPDATE account SET balance=?, peak_equity=? WHERE id=1", (balance, peak))
        self.db.commit()

    # ------------------------------------------------------------ trades
    def insert_trade(self, **f) -> int:
        cols = ",".join(f)
        cur = self.db.execute(f"INSERT INTO trades ({cols}) VALUES ({','.join('?' * len(f))})", tuple(f.values()))
        self.db.commit()
        return int(cur.lastrowid)

    def update_trade(self, trade_id: int, **f) -> None:
        sets = ",".join(f"{k}=?" for k in f)
        self.db.execute(f"UPDATE trades SET {sets} WHERE id=?", (*f.values(), trade_id))
        self.db.commit()

    def open_trades(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM trades WHERE status='open' ORDER BY id")]

    def trade(self, trade_id: int) -> dict:
        return dict(self.db.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone())

    def closed_trades(self, since: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM trades WHERE status='closed'", ()
        if since:
            q, args = q + " AND exit_time >= ?", (since,)
        return [dict(r) for r in self.db.execute(q + " ORDER BY exit_time", args)]

    def trades_opened_since(self, since: str) -> int:
        return self.db.execute("SELECT COUNT(*) FROM trades WHERE entry_time >= ?", (since,)).fetchone()[0]

    def event(self, trade_id: int, ts: datetime, action: str, old_stop: float | None,
              new_stop: float | None, price: float | None, reason: str) -> None:
        self.db.execute("INSERT INTO position_events (trade_id,ts,action,old_stop,new_stop,price,reason) "
                        "VALUES (?,?,?,?,?,?,?)", (trade_id, ts.isoformat(), action, old_stop, new_stop, price, reason))
        self.db.commit()

    # ------------------------------------------------------------ cycles
    def log_cycle(self, record: dict, snapshots: list[dict], ideas: list[str]) -> int:
        cur = self.db.execute(
            "INSERT INTO cycles (ts,balance,equity,open_positions,markets,decisions,llm_status,prompt_hash,summary,error)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (record["ts"], record["balance"], record["equity"], _j(record["open_positions"]),
             _j(record["markets"]), _j(record["decisions"]), record.get("llm_status"),
             record.get("prompt_hash"), record.get("summary"), record.get("error")))
        cid = int(cur.lastrowid)
        for s in snapshots:
            self.db.execute(
                "INSERT INTO market_snapshots (cycle_id,ts,symbol,bid,ask,spread_pips,timeframes,regime,trend,"
                "structure,volatility,context_json,strategies_considered,opportunities,chosen_strategy,decision,reason)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, record["ts"], s["symbol"], s.get("bid"), s.get("ask"), s.get("spread_pips"),
                 _j(s.get("timeframes")), s.get("regime"), _j(s.get("trend")), _j(s.get("structure")),
                 s.get("volatility"), _j(s.get("context")), _j(s.get("strategies_considered")),
                 _j(s.get("opportunities")), s.get("chosen_strategy"), s.get("decision"), s.get("reason")))
        for text in ideas:
            self.db.execute("INSERT INTO ideas (cycle_id,ts,text) VALUES (?,?,?)", (cid, record["ts"], text))
        self.db.commit()
        if self.jsonl:
            self.jsonl.parent.mkdir(parents=True, exist_ok=True)
            with open(self.jsonl, "a", encoding="utf-8") as f:
                f.write(_j({"cycle_id": cid, **record, "markets_detail": snapshots, "ideas": ideas}) + "\n")
        return cid

    def close(self) -> None:
        self.db.close()
