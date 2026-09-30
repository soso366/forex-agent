"""Un CYCLE COMPLET de l'agent (appelé toutes les 5 minutes par le scheduler).

  1. lecture des positions existantes + rejeu M1 depuis le dernier cycle (SL/TP/30 min)
  2. récupération du marché (H1, M15, M5, M1) pour chaque paire
  3. analyse -> contexte -> régime
  4. gestion des positions ouvertes (HOLD / MOVE STOP / TAKE PROFIT / CLOSE)
  5. recherche d'opportunités : régime -> stratégies autorisées -> setups notés
  6. (optionnel) revue par le LLM, bornée aux candidats qualifiés
  7. contrôle du risque -> exécution paper
  8. journal (même quand rien ne se passe)
"""
from __future__ import annotations

import json
import traceback
from datetime import datetime, timedelta

from . import positions as pm
from .analysis.market import MarketContext, analyze
from .analysis.structure import news_blackout
from .brain.llm import LLMBrain, load_prompt
from .brain.router import ScanResult, scan_symbol
from .broker.paper import PaperBroker
from .config import Decision
from .data.providers import DataProvider, market_open_at
from .journal import Store
from .risk.manager import RiskManager


def new_trades_window(now: datetime, cfg: dict) -> tuple[bool, str]:
    s = cfg["sessions"]
    if now.weekday() == 4 and now.hour >= s.get("no_new_trades_friday_after_utc", 24):
        return False, "vendredi soir : pas de nouvelle position avant le week-end"
    for a, b in s["new_trades_utc"]:
        if a <= now.hour < b:
            return True, "session active"
    return False, f"hors sessions de trading ({now:%H:%M} UTC) : gestion des positions uniquement"


def _load_contexts(cfg: dict, provider: DataProvider, now: datetime) -> tuple[dict[str, MarketContext], dict[str, str]]:
    contexts, errors = {}, {}
    for sym in cfg["symbols"]:
        try:
            raw = {tf: provider.candles(sym, tf, now, n) for tf, n in cfg["bars"].items()}
            bid, ask = provider.quote(sym, now)
            ctx = analyze(sym, raw, bid, ask, now, cfg)
            blocked, why = news_blackout(now, sym, cfg)
            ctx.news_block = why if blocked else ""
            contexts[sym] = ctx
        except Exception as e:
            errors[sym] = f"données indisponibles : {e}"
    return contexts, errors


def run_cycle(cfg: dict, provider: DataProvider, store: Store, now: datetime,
              brain: LLMBrain | None = None) -> dict:
    store.init_account(cfg["account"]["currency"], cfg["account"]["starting_capital"], now)
    brain = brain or LLMBrain(cfg)
    broker = PaperBroker(store, provider, cfg)
    risk = RiskManager(cfg, store)
    decisions: list[Decision] = []
    snapshots: dict[str, dict] = {}
    ideas: list[str] = []
    error = None
    _, prompt_hash = load_prompt(cfg)

    try:
        if not market_open_at(now, cfg["scheduler"]):
            decisions.append(Decision("*", "NO_TRADE", "marché Forex fermé (week-end)"))
            return _finish(cfg, store, broker, now, decisions, snapshots, ideas, brain.status, prompt_hash, None)

        # 1. positions existantes : rejeu des minutes écoulées (stops, cibles, 30 min)
        for ev in broker.sync(now):
            t = store.trade(ev["trade_id"])
            decisions.append(Decision(t["symbol"], "CLOSE", t["exit_reason"], t["strategy"], t["id"],
                                      {"pnl_eur": round(ev["pnl"], 4), "between_cycles": True}))

        # 2-3. marché -> contexte
        contexts, errors = _load_contexts(cfg, provider, now)
        for sym, err in errors.items():
            snapshots[sym] = {"symbol": sym, "decision": "NO_TRADE", "reason": err}

        # 4. gestion des positions ouvertes (déterministe)
        advice: dict[int, pm.PositionAdvice] = {}
        for t in store.open_trades():
            ctx = contexts.get(t["symbol"])
            if ctx is None:
                advice[t["id"]] = pm.PositionAdvice("HOLD", "pas de données ce cycle : stop et 30 min restent actifs")
            else:
                advice[t["id"]] = pm.evaluate(t, ctx, cfg["management"])

        # 5. recherche d'opportunités sur TOUTES les paires, même avec une position ouverte
        window_ok, window_reason = new_trades_window(now, cfg)
        scans: dict[str, ScanResult] = {sym: scan_symbol(ctx, cfg) for sym, ctx in contexts.items()}
        open_syms = {t["symbol"] for t in store.open_trades()}
        candidates = sorted((s for sym, r in scans.items() for s in r.qualified if sym not in open_syms),
                            key=lambda s: (s.rr, s.score), reverse=True)

        # 6. revue LLM (optionnelle, bornée)
        llm_out, llm_status = None, brain.status
        if brain.enabled and (candidates or advice):
            payload = {
                "time_utc": now.isoformat(),
                "account": {"balance": broker.balance, "equity": broker.equity(now),
                            "currency": cfg["account"]["currency"]},
                "new_trades_allowed": window_ok,
                "open_positions": [{**{k: t[k] for k in ("id", "symbol", "direction", "strategy", "entry", "stop",
                                                          "target", "entry_time")},
                                    "rule_advice": advice[t["id"]].action, "rule_reason": advice[t["id"]].reason}
                                   for t in store.open_trades()],
                "markets": {s: c.summary() for s, c in contexts.items()},
                "candidates": [c.to_dict() for c in candidates],
            }
            llm_out, llm_status = brain.review(payload, {c.id for c in candidates},
                                               {t["id"] for t in store.open_trades()})
            if llm_out:
                ideas = llm_out.get("ideas", [])

        # 4bis. application des décisions sur les positions (la plus protectrice l'emporte)
        llm_pos = {p["trade_id"]: p for p in (llm_out or {}).get("positions", [])}
        for t in store.open_trades():
            a = advice[t["id"]]
            action, reason, new_stop = a.action, a.reason, a.new_stop
            lp = llm_pos.get(t["id"])
            if lp and action not in ("CLOSE", "TAKE_PROFIT"):
                if lp["action"] in ("CLOSE", "TAKE_PROFIT"):
                    action, reason = lp["action"], f"LLM : {lp['reason']}"
                elif lp["action"] == "MOVE_STOP" and lp["new_stop"] is not None:
                    d = 1 if t["direction"] == "BUY" else -1
                    if new_stop is None or d * (lp["new_stop"] - new_stop) > 0:
                        action, new_stop, reason = "MOVE_STOP", lp["new_stop"], f"LLM : {lp['reason']}"
            ctx = contexts.get(t["symbol"])
            if action in ("CLOSE", "TAKE_PROFIT"):
                pnl = broker.close_at_market(t, now, f"{action} : {reason}")
                decisions.append(Decision(t["symbol"], action, reason, t["strategy"], t["id"], {"pnl_eur": round(pnl, 4)}))
            elif action == "MOVE_STOP" and ctx is not None:
                ok, why = risk.validate_stop_move(t, new_stop, ctx.bid, ctx.ask)
                if ok:
                    broker.modify_stop(t, new_stop, now, reason)
                    decisions.append(Decision(t["symbol"], "MOVE_STOP", reason, t["strategy"], t["id"],
                                              {"old_stop": t["stop"], "new_stop": new_stop}))
                else:
                    decisions.append(Decision(t["symbol"], "HOLD", f"stop inchangé ({why})", t["strategy"], t["id"]))
            else:
                decisions.append(Decision(t["symbol"], "HOLD", reason, t["strategy"], t["id"]))

        # 7. contrôle du risque puis exécution paper
        opened: dict[str, Decision] = {}
        refused: dict[str, str] = {}
        if not window_ok:
            for c in candidates:
                refused[c.symbol] = window_reason
        else:
            if llm_out is not None:
                cid = llm_out["new_trade"]["candidate_id"]
                if cid is None:
                    for c in candidates:
                        refused[c.symbol] = f"LLM : NO TRADE ({llm_out['new_trade']['reason']})"
                    candidates = []
                else:
                    candidates = [c for c in candidates if c.id == cid] + [c for c in candidates if c.id != cid]
            max_new = cfg["trading"]["max_new_trades_per_cycle"]
            for setup in candidates:
                if len(opened) >= max_new:
                    refused.setdefault(setup.symbol, "une seule nouvelle position par cycle : meilleur candidat retenu ailleurs")
                    continue
                bid, ask = provider.quote(setup.symbol, now)
                mids = broker.mids(now)
                verdict = risk.evaluate(setup, bid, ask, store.open_trades(), broker.equity(now),
                                        broker.balance, mids, now)
                if not verdict.approved:
                    refused[setup.symbol] = "Risk Manager : " + "; ".join(verdict.reasons)
                    continue
                why = f"{setup.strategy} — " + "; ".join(setup.notes)
                tid = broker.open(setup.symbol, setup.direction, verdict.units, setup.stop, setup.target,
                                  verdict.risk_eur, verdict.margin_eur, setup.strategy, why,
                                  json.dumps(setup.to_dict(), default=str), now,
                                  extra={"regime": contexts[setup.symbol].regime,
                                         "session": contexts[setup.symbol].session,
                                         "killzone": contexts[setup.symbol].killzone})
                opened[setup.symbol] = Decision(setup.symbol, setup.direction, why, setup.strategy, tid,
                                                {"units": verdict.units, "risk_eur": round(verdict.risk_eur, 4),
                                                 "risk_check": verdict.reasons[0]})
                decisions.append(opened[setup.symbol])

        # 8. snapshots par paire
        managed = {d.symbol: d for d in decisions if d.trade_id and d.action in ("HOLD", "MOVE_STOP", "CLOSE", "TAKE_PROFIT")}
        for sym, ctx in contexts.items():
            r = scans[sym]
            if sym in opened:
                dec, reason, strat = opened[sym].action, opened[sym].reason, opened[sym].strategy
            elif sym in managed and sym in open_syms:
                dec, reason, strat = managed[sym].action, managed[sym].reason, managed[sym].strategy
            else:
                dec, strat = "NO_TRADE", (r.best.strategy if r.best else None)
                reason = refused.get(sym) or ("; ".join(r.rejections[:4]) or "aucun setup")
                if not r.setups and not r.rejections:
                    reason = "aucun setup"
                decisions.append(Decision(sym, "NO_TRADE", reason, strat))
            snapshots[sym] = {
                "symbol": sym, "bid": ctx.bid, "ask": ctx.ask, "spread_pips": round(ctx.spread_pips, 2),
                "timeframes": {k: len(v) for k, v in ctx.frames.items()},
                "regime": ctx.regime, "trend": {"H1": ctx.h1.trend, "M15": ctx.m15.trend},
                "structure": {"H1": ctx.h1.structure, "M15": ctx.m15.structure},
                "volatility": ctx.volatility, "context": ctx.summary(),
                "strategies_considered": r.considered,
                "opportunities": [s.to_dict() for s in r.setups],
                "chosen_strategy": strat, "decision": dec, "reason": reason,
            }
        return _finish(cfg, store, broker, now, decisions, snapshots, ideas, llm_status, prompt_hash, None)
    except Exception:
        error = traceback.format_exc(limit=5)
        decisions.append(Decision("*", "NO_TRADE", "erreur pendant le cycle : aucune nouvelle position"))
        return _finish(cfg, store, broker, now, decisions, snapshots, ideas, brain.status, prompt_hash, error)


def _finish(cfg, store, broker, now, decisions, snapshots, ideas, llm_status, prompt_hash, error) -> dict:
    try:
        equity = broker.equity(now)
    except Exception:
        equity = broker.balance
    open_now = store.open_trades()
    actions = [d for d in decisions if d.action != "NO_TRADE"]
    summary = " | ".join(f"{d.symbol} {d.action}" for d in actions) or "NO TRADE sur toutes les paires"
    record = {
        "ts": now.isoformat(), "balance": round(broker.balance, 4), "equity": round(equity, 4),
        "open_positions": [{k: t[k] for k in ("id", "symbol", "direction", "entry", "stop", "target", "units", "entry_time")}
                           for t in open_now],
        "markets": list(snapshots),
        "decisions": [d.__dict__ for d in decisions],
        "llm_status": llm_status, "prompt_hash": prompt_hash, "summary": summary, "error": error,
    }
    record["cycle_id"] = store.log_cycle(record, list(snapshots.values()), ideas)
    return record
