"""Risk Manager — déterministe et indépendant de l'intelligence de l'agent.

Lui seul décide : taille, risque maximal, exposition totale, nombre de positions,
stop obligatoire. Aucune stratégie ni le LLM ne peuvent le contourner.

Interdits structurels :
- pas de martingale : la taille dépend uniquement du capital × % fixe ;
- après des pertes le % de risque ne peut que BAISSER, puis pause (anti-revenge) ;
- stop obligatoire, jamais élargi, jamais supprimé ; aucune taille "bonus" pour un beau setup.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .. import fx
from ..config import Setup, resolve_path
from ..journal import Store


@dataclass
class Verdict:
    approved: bool
    reasons: list[str] = field(default_factory=list)
    units: float = 0.0
    risk_eur: float = 0.0
    margin_eur: float = 0.0
    risk_pct: float = 0.0
    entry: float = 0.0


def sign(direction: str) -> int:
    return 1 if direction == "BUY" else -1


class RiskManager:
    def __init__(self, cfg: dict, store: Store):
        self.cfg, self.r, self.store = cfg, cfg["risk"], store
        self.ccy = cfg["account"]["currency"]
        self.kill_path = resolve_path(cfg, "kill_switch")

    # --------------------------------------------------------- état global
    def _consecutive_losses(self) -> tuple[int, datetime | None]:
        n, last_loss = 0, None
        for t in reversed(self.store.closed_trades()):
            if (t["pnl_eur"] or 0) < 0:
                n += 1
                last_loss = last_loss or datetime.fromisoformat(t["exit_time"])
            else:
                break
        return n, last_loss

    def risk_pct(self) -> float:
        """% de risque par trade. Ne peut que diminuer après des pertes, jamais augmenter."""
        losses, _ = self._consecutive_losses()
        base = self.r["risk_per_trade_pct"]
        if losses >= 2:
            return min(base, self.r["reduced_risk_pct_after_losses"])
        return base

    def trading_allowed(self, now: datetime, equity: float) -> tuple[bool, str]:
        acc = self.store.account()
        peak = max(float(acc["peak_equity"]), equity)
        dd = (peak - equity) / peak * 100 if peak > 0 else 0
        if dd >= self.r["max_drawdown_pct"] and not self.kill_path.exists():
            self.kill_path.parent.mkdir(parents=True, exist_ok=True)
            self.kill_path.write_text(f"{now.isoformat()} drawdown {dd:.1f}%\n")
        if self.kill_path.exists():
            return False, f"KILL SWITCH actif ({self.kill_path.name}) — aucune nouvelle position"
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        day_pnl = sum(t["pnl_eur"] or 0 for t in self.store.closed_trades(since=day_start))
        start_of_day_equity = equity - day_pnl
        if start_of_day_equity > 0 and -day_pnl / start_of_day_equity * 100 >= self.r["daily_loss_limit_pct"]:
            return False, f"limite de perte journalière atteinte ({day_pnl:.2f} {self.ccy})"
        if self.store.trades_opened_since(day_start) >= self.r["max_trades_per_day"]:
            return False, "nombre max de trades du jour atteint"
        losses, last_loss = self._consecutive_losses()
        if losses >= self.r["max_consecutive_losses"] and last_loss:
            until = last_loss + timedelta(minutes=self.r["cooldown_minutes_after_losses"])
            if now < until:
                return False, f"pause anti-revenge après {losses} pertes (jusqu'à {until:%H:%M} UTC)"
        return True, "ok"

    def open_risk_eur(self, trades: list[dict], mids: dict[str, float]) -> float:
        """Risque restant réel : ce qui serait perdu si tous les stops actuels étaient touchés."""
        total = 0.0
        for t in trades:
            dist = sign(t["direction"]) * (t["entry"] - t["stop"])
            if dist > 0:
                total += dist * t["units"] * fx.ccy_to_account(fx.split(t["symbol"])[1], mids, self.ccy)
        return total

    # --------------------------------------------------------- nouveau trade
    def evaluate(self, setup: Setup, bid: float, ask: float, open_trades: list[dict],
                 equity: float, balance: float, mids: dict[str, float], now: datetime) -> Verdict:
        v = Verdict(False)
        d = sign(setup.direction)
        sym = setup.symbol
        pip = fx.pip_size(sym)

        ok, why = self.trading_allowed(now, equity)
        if not ok:
            v.reasons.append(why)
            return v
        if len(open_trades) >= self.r["max_open_positions"]:
            v.reasons.append(f"déjà {len(open_trades)} positions (max {self.r['max_open_positions']})")
            return v
        if any(t["symbol"] == sym for t in open_trades):
            v.reasons.append(f"position déjà ouverte sur {sym}")
            return v
        cooldown = self.cfg["trading"].get("reentry_cooldown_minutes", 0)
        if cooldown:
            recent = [t for t in self.store.closed_trades(since=(now - timedelta(minutes=cooldown)).isoformat())
                      if t["symbol"] == sym and (t["pnl_eur"] or 0) < 0]
            if recent:
                v.reasons.append(f"perte récente sur {sym} : pas de ré-entrée avant {cooldown} min (pas de chase / revenge)")
                return v
        if self.r.get("block_same_currency_same_direction", True):
            new_exp = {fx.split(sym)[0]: d, fx.split(sym)[1]: -d}
            for t in open_trades:
                td = sign(t["direction"])
                exp = {fx.split(t["symbol"])[0]: td, fx.split(t["symbol"])[1]: -td}
                shared = [c for c in new_exp if exp.get(c) == new_exp[c]]
                if shared:
                    v.reasons.append(f"risque corrélé avec {t['symbol']} (même exposition {', '.join(shared)})")
                    return v

        spread_pips = (ask - bid) / pip
        max_spread = self.r["max_spread_pips"].get(sym, self.r["max_spread_pips"]["default"])
        if spread_pips > max_spread:
            v.reasons.append(f"spread {spread_pips:.1f} pips > max {max_spread}")
            return v

        entry = ask if d == 1 else bid                      # prix d'exécution réel
        v.entry = entry
        if setup.stop is None or not math.isfinite(setup.stop):
            v.reasons.append("stop-loss absent : trade interdit")
            return v
        dist = d * (entry - setup.stop)
        if dist <= 0:
            v.reasons.append("le prix a déjà dépassé le stop")
            return v
        stop_pips = dist / pip
        if stop_pips < self.r["min_stop_pips"] or stop_pips > self.r["max_stop_pips"]:
            v.reasons.append(f"stop {stop_pips:.1f} pips hors bornes [{self.r['min_stop_pips']}, {self.r['max_stop_pips']}]")
            return v
        rr = d * (setup.target - entry) / dist
        if rr < self.r["min_rr"]:
            v.reasons.append(f"R:R au prix d'exécution {rr:.2f} < {self.r['min_rr']}")
            return v

        pct = self.risk_pct()
        base_capital = min(balance, equity)
        risk_budget = base_capital * pct / 100
        q2a = fx.ccy_to_account(fx.split(sym)[1], mids, self.ccy)
        step = self.r.get("unit_step", 1)
        units = math.floor(risk_budget / (dist * q2a) / step) * step
        if units < self.r.get("min_units", 1):
            v.reasons.append(f"taille minimale impossible avec {risk_budget:.2f} {self.ccy} de risque et un stop de {stop_pips:.1f} pips")
            return v
        risk_eur = units * dist * q2a

        # Marge : avec un petit compte, un stop serré implique une grosse taille nominale.
        # On RÉDUIT la taille pour tenir dans la marge autorisée (le risque baisse, jamais l'inverse).
        leverage = self.cfg["account"]["leverage"]
        used = sum(t.get("margin_eur") or 0 for t in open_trades)
        margin_room = equity * self.r["max_margin_usage_pct"] / 100 - used
        margin_per_unit = fx.margin_account(sym, 1, leverage, mids, self.ccy)
        max_units_margin = math.floor(max(margin_room, 0) / margin_per_unit / step) * step
        capped = False
        if units > max_units_margin:
            units, capped = max_units_margin, True
            risk_eur = units * dist * q2a
            if units < self.r.get("min_units", 1) or risk_eur < 0.25 * risk_budget:
                v.reasons.append(f"marge insuffisante : {margin_room:.2f} {self.ccy} disponibles "
                                 f"(stop {stop_pips:.1f} pips trop serré pour ce capital)")
                return v

        total = self.open_risk_eur(open_trades, mids) + risk_eur
        max_total = base_capital * self.r["max_total_risk_pct"] / 100
        if total > max_total + 1e-9:
            v.reasons.append(f"risque total {total:.2f} > max {max_total:.2f} {self.ccy}")
            return v

        margin = units * margin_per_unit
        v.approved = True
        v.units, v.risk_eur, v.margin_eur, v.risk_pct = units, risk_eur, margin, pct
        v.reasons.append(f"{units:.0f} unités, risque {risk_eur:.2f} {self.ccy} ({pct}% max), stop {stop_pips:.1f} pips, "
                         f"R:R {rr:.2f}, marge {margin:.2f}" + (" — taille réduite par la marge" if capped else ""))
        return v

    # --------------------------------------------------------- gestion du stop
    def validate_stop_move(self, trade: dict, new_stop: float, bid: float, ask: float) -> tuple[bool, str]:
        """Un stop ne peut que se RESSERRER, et doit rester du bon côté du prix."""
        if new_stop is None or not math.isfinite(new_stop):
            return False, "suppression du stop interdite"
        d = sign(trade["direction"])
        if d * (new_stop - trade["stop"]) <= 0:
            return False, "élargir ou garder le stop à l'identique est refusé (resserrer uniquement)"
        exit_px = bid if d == 1 else ask
        min_gap = fx.pip_size(trade["symbol"]) * 1.0
        if d * (exit_px - new_stop) < min_gap:
            return False, "nouveau stop trop proche ou au-delà du prix actuel"
        return True, "ok"
