"""PaperBroker — compte simulé en EUR (50 € au départ), exécution bid/ask réaliste.

- Achat exécuté à l'ASK, vente au BID ; sorties du côté correspondant.
- Entre deux cycles, les bougies M1 sont rejouées : SL / TP touchés à la minute près.
- SL et TP dans la même minute : STOP D'ABORD (hypothèse prudente), flag intrabar_ambiguous.
- Gap au-delà du stop : exécution au prix d'ouverture (pire que le stop).
- Fermeture forcée à entrée + max_hold_minutes (30 min en V1).
Aucun ordre n'est jamais envoyé à un broker réel.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from .. import fx
from ..data.providers import DataProvider
from ..journal import Store


class PaperBroker:
    def __init__(self, store: Store, provider: DataProvider, cfg: dict):
        self.store, self.provider, self.cfg = store, provider, cfg
        self.ccy = cfg["account"]["currency"]
        self.max_hold = timedelta(minutes=cfg["trading"]["max_hold_minutes"])

    # ------------------------------------------------------------ état
    @property
    def balance(self) -> float:
        return float(self.store.account()["balance"])

    def mids(self, now: datetime) -> dict[str, float]:
        return fx.quote_mids(self.provider, self.cfg, now)

    def unrealized(self, trade: dict, bid: float, ask: float, mids: dict[str, float]) -> float:
        sign = 1 if trade["direction"] == "BUY" else -1
        exit_px = bid if sign == 1 else ask
        return fx.pnl_account(trade["symbol"], sign, trade["entry"], exit_px, trade["units"], mids, self.ccy)

    def equity(self, now: datetime) -> float:
        mids = self.mids(now)
        eq = self.balance
        for t in self.store.open_trades():
            bid, ask = self.provider.quote(t["symbol"], now)
            eq += self.unrealized(t, bid, ask, mids)
        return eq

    # ------------------------------------------------------------ ordres
    def open(self, symbol: str, direction: str, units: float, stop: float, target: float,
             risk_eur: float, margin_eur: float, strategy: str, reason: str, setup_json: str,
             now: datetime, extra: dict | None = None) -> int:
        bid, ask = self.provider.quote(symbol, now)
        entry = ask if direction == "BUY" else bid
        tid = self.store.insert_trade(
            symbol=symbol, direction=direction, strategy=strategy, entry=entry, stop=stop,
            initial_stop=stop, target=target, units=units, risk_eur=risk_eur, margin_eur=margin_eur,
            entry_time=now.isoformat(), last_checked=now.isoformat(), entry_reason=reason,
            status="open", setup_json=setup_json, **(extra or {}))
        self.store.event(tid, now, "OPEN", None, stop, entry, reason)
        return tid

    def close(self, trade: dict, price: float, when: datetime, reason: str, ambiguous: bool = False) -> float:
        sign = 1 if trade["direction"] == "BUY" else -1
        mids = self.mids(when)
        pnl = fx.pnl_account(trade["symbol"], sign, trade["entry"], price, trade["units"], mids, self.ccy)
        pnl -= trade["units"] / 100_000 * self.cfg["account"].get("commission_per_lot_eur", 0.0)
        pnl = round(pnl, 4)
        acc = self.store.account()
        balance = float(acc["balance"]) + pnl
        peak = max(float(acc["peak_equity"]), balance)
        self.store.set_balance(balance, peak)
        entry_time = datetime.fromisoformat(trade["entry_time"])
        r_unit = sign * (trade["entry"] - trade["initial_stop"])
        r_mult = sign * (price - trade["entry"]) / r_unit if r_unit > 0 else 0.0
        self.store.update_trade(
            trade["id"], status="closed", r_multiple=round(r_mult, 3), exit_time=when.isoformat(), exit_price=price,
            duration_min=round((when - entry_time).total_seconds() / 60, 1), exit_reason=reason,
            pnl_eur=round(pnl, 4), balance_after=round(balance, 4),
            intrabar_ambiguous=int(ambiguous or trade.get("intrabar_ambiguous") or 0))
        self.store.event(trade["id"], when, "CLOSE", trade["stop"], None, price, reason)
        return pnl

    def close_at_market(self, trade: dict, now: datetime, reason: str) -> float:
        bid, ask = self.provider.quote(trade["symbol"], now)
        return self.close(trade, bid if trade["direction"] == "BUY" else ask, now, reason)

    def modify_stop(self, trade: dict, new_stop: float, now: datetime, reason: str) -> None:
        """Appelé uniquement après validation par le Risk Manager (resserrer seulement)."""
        self.store.update_trade(trade["id"], stop=new_stop)
        self.store.event(trade["id"], now, "MOVE_STOP", trade["stop"], new_stop, None, reason)

    # ------------------------------------------------------------ rejeu M1
    def sync(self, now: datetime) -> list[dict]:
        """Rejoue les minutes écoulées depuis le dernier contrôle de chaque position."""
        closed = []
        for t in self.store.open_trades():
            res = self._sync_trade(t, now)
            if res:
                closed.append(res)
        return closed

    def _sync_trade(self, t: dict, now: datetime) -> dict | None:
        sign = 1 if t["direction"] == "BUY" else -1
        entry_time = datetime.fromisoformat(t["entry_time"])
        deadline = entry_time + self.max_hold
        start = datetime.fromisoformat(t["last_checked"])
        bars = self.provider.m1(t["symbol"], start, now)
        r_unit = sign * (t["entry"] - t["initial_stop"])
        exc = {"mfe": t.get("mfe_r") or 0.0, "mae": t.get("mae_r") or 0.0}

        def save_excursions():
            self.store.update_trade(t["id"], mfe_r=round(exc["mfe"], 3), mae_r=round(exc["mae"], 3))

        for ts, b in bars.iterrows():
            ts = ts.to_pydatetime()
            if ts >= deadline:
                save_excursions()
                px = b["o"] if sign == 1 else b["ao"]
                pnl = self.close(t, float(px), ts, f"TIME_STOP : durée max {self.max_hold.seconds // 60} min atteinte")
                return {"trade_id": t["id"], "reason": "TIME_STOP", "pnl": pnl}
            if sign == 1:
                o, hi, lo = b["o"], b["h"], b["l"]           # sortie d'un long = BID
                sl_hit, tp_hit = lo <= t["stop"], hi >= t["target"]
            else:
                o, hi, lo = b["ao"], b["ah"], b["al"]        # sortie d'un short = ASK
                sl_hit, tp_hit = hi >= t["stop"], lo <= t["target"]
            if r_unit > 0:                                    # excursions max favorable / adverse (en R)
                fav = (hi - t["entry"]) if sign == 1 else (t["entry"] - lo)
                adv = (t["entry"] - lo) if sign == 1 else (hi - t["entry"])
                exc["mfe"] = max(exc["mfe"], fav / r_unit)
                exc["mae"] = max(exc["mae"], adv / r_unit)
            if sl_hit:
                save_excursions()
                gap = sign * (t["stop"] - o) > 0             # ouverture déjà au-delà du stop
                px = float(o) if gap else t["stop"]
                label = "STOP_LOSS" if sign * (px - t["entry"]) < 0 else "STOP (protégé)"
                pnl = self.close(t, px, ts, f"{label} touché à {px}", ambiguous=bool(tp_hit))
                return {"trade_id": t["id"], "reason": "STOP", "pnl": pnl, "ambiguous": bool(tp_hit)}
            if tp_hit:
                save_excursions()
                gap = sign * (o - t["target"]) > 0
                px = float(o) if gap else t["target"]
                pnl = self.close(t, px, ts, f"TAKE_PROFIT : cible {t['target']} atteinte")
                return {"trade_id": t["id"], "reason": "TARGET", "pnl": pnl}
        save_excursions()
        if now >= deadline:                                  # échéance pile à l'heure du cycle
            pnl = self.close_at_market(t, now, f"TIME_STOP : durée max {self.max_hold.seconds // 60} min atteinte")
            return {"trade_id": t["id"], "reason": "TIME_STOP", "pnl": pnl}
        self.store.update_trade(t["id"], last_checked=now.isoformat())
        return None
