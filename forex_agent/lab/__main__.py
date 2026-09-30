"""Parameter Lab — ligne de commande.

  python -m forex_agent.lab cache                 # calcule le cache d'analyse (une fois)
  python -m forex_agent.lab block A               # teste le bloc A sur la config verrouillée, puis verrouille
  python -m forex_agent.lab block B | C | D
  python -m forex_agent.lab final                 # config verrouillée vs référence, hors-échantillon inclus

Les résultats vont dans lab/results/ (JSON + trades de chaque variante). La production
(config/settings.yaml) n'est JAMAIS modifiée par le lab.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ..config import ROOT, load_config
from . import blocks as B
from .runner import Variant, run_all
from .stats import PERIODS, breakdown, evaluate, metrics, period, with_r

UTC = timezone.utc
LAB = ROOT / "lab"
RES = LAB / "results"
DEFAULT_CACHE = Path("/home/claude/labcache/2026mar-aug")
START, END = datetime(2026, 3, 8, tzinfo=UTC), datetime(2026, 8, 31, 23, 59, tzinfo=UTC)


def lab_cfg() -> dict:
    return load_config(overrides={"data": {"provider": "csv"}})


def load_locked() -> dict:
    p = RES / "locked.json"
    return json.loads(p.read_text()) if p.exists() else {"overrides": {}, "lab": {}, "rescan": [], "history": []}


def save_locked(d: dict) -> None:
    RES.mkdir(parents=True, exist_ok=True)
    (RES / "locked.json").write_text(json.dumps(d, indent=2, ensure_ascii=False, default=str))


def base_variant(locked: dict) -> Variant:
    return Variant("base", "référence", None, copy.deepcopy(locked.get("overrides", {})),
                   tuple(sorted(locked.get("rescan", []))), locked.get("reclassify", False), locked.get("matrix"),
                   copy.deepcopy(locked.get("lab", {})))


def summarize(t, with_val=True) -> dict:
    t = with_r(t)
    out = {"IS": metrics(period(t, "IS")), "pairs_IS": breakdown(period(t, "IS"), "symbol"),
           "months_IS": breakdown(period(t, "IS"), "month"), "strategies_IS": breakdown(period(t, "IS"), "strategy")}
    if with_val:
        out["VAL"] = metrics(period(t, "VAL"))
        out["strategies_VAL"] = breakdown(period(t, "VAL"), "strategy")
    return out


def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return None if (np.isnan(x) or np.isinf(x)) else round(float(x), 4)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def run_block(name: str, cache: Path, workers: int = 2) -> dict:
    cfg = lab_cfg()
    locked = load_locked()
    params = {"A": B.block_a, "B": B.block_b, "C": B.block_c, "D": B.block_d}[name]()
    if name == "B":
        params.append(B.block_b_sessions())
    base = base_variant(locked)
    variants, index = [base], {}
    for p in params:
        for v in p.grid:
            if v == p.base:
                index[(p.name, repr(v))] = base.key
                continue
            var = p.variant(v, locked)
            variants.append(var)
            index[(p.name, repr(v))] = var.key
    heat = []
    if name == "A":                                  # cartes de stabilité 2D (information)
        for be in [None, 0.5, 0.75, 1.0, 1.25, 1.5]:
            for tr in [None, 0.5, 0.75, 1.0, 1.5, 2.0]:
                ov = copy.deepcopy(locked.get("overrides", {}))
                ov.setdefault("management", {}).update({"breakeven_at_r": be, "trail_ema20_after_r": tr})
                v = Variant("A", "BE×trail", (be, tr), ov, base.rescan, base.reclassify, base.matrix, base.lab)
                variants.append(v)
                heat.append(("breakeven_at_r × trail_ema20_after_r", be, tr, v.key))
        for rr in [1.2, 1.3, 1.5, 1.75, 2.0, 2.5]:
            for off in [0.0, 0.05, 0.1, 0.2, 0.3]:
                ov = copy.deepcopy(locked.get("overrides", {}))
                ov.setdefault("risk", {})["min_rr"] = rr
                ov.setdefault("strategy_params", {})["target_offset_atr"] = off
                v = Variant("A", "RR×offset", (rr, off), ov, base.rescan, base.reclassify, base.matrix, base.lab)
                variants.append(v)
                heat.append(("min_rr × target_offset_atr", rr, off, v.key))
    seen, uniq = set(), []
    for v in variants:
        if v.key not in seen:
            seen.add(v.key)
            uniq.append(v)
    out_dir = RES / "trades"
    trades = run_all(uniq, cfg, str(cache), str(ROOT / cfg["data"]["csv_dir"]), START, END, out_dir, workers)
    bt = with_r(trades[base.key])

    report = {"block": name, "locked_before": locked, "base": summarize(trades[base.key]), "params": [], "heatmaps": {}}
    accepted = []
    for p in params:
        exp_of = {}
        for v in p.grid:
            t = with_r(trades[index[(p.name, repr(v))]])
            exp_of[repr(v)] = metrics(period(t, "IS"))["exp"]
        rows = []
        for v in p.grid:
            key = index[(p.name, repr(v))]
            t = with_r(trades[key])
            row = {"value": v, "is_base": v == p.base, "summary": summarize(trades[key])}
            if v != p.base:
                nb = B.numeric_neighbors(p, v)
                numeric = v is None or (isinstance(v, (int, float)) and not isinstance(v, bool))
                has_nums = any(isinstance(g, (int, float)) and not isinstance(g, bool) for g in p.grid)
                ev = evaluate(bt, t, [exp_of[repr(n)] for n in nb] if (numeric and has_nums) else None)
                row.update({"criteria": ev["criteria"], "accepted": ev["accepted"], "paired": ev["paired"]})
                if ev["accepted"]:
                    accepted.append((ev["IS"]["exp"] - ev["IS_base"]["exp"], p, v, key))
            rows.append(row)
        report["params"].append({"name": p.name, "section": p.section, "key": p.key, "base": p.base,
                                 "note": p.note, "rows": rows})
    for title, a, b_, key in heat:
        t = with_r(trades[key])
        report["heatmaps"].setdefault(title, []).append(
            {"x": a, "y": b_, "IS": metrics(period(t, "IS")), "VAL": metrics(period(t, "VAL"))})

    # combinaison des réglages retenus, ajoutés un par un par ordre de gain
    accepted.sort(key=lambda x: x[0], reverse=True)
    new_locked = copy.deepcopy(locked)
    kept = []
    for gain, p, v, key in accepted:
        trial = copy.deepcopy(new_locked)
        var = p.variant(v, trial)
        trial["overrides"], trial["lab"] = var.overrides, var.lab
        trial["rescan"] = sorted(set(trial.get("rescan", [])) | set(p.rescan))
        trial["reclassify"] = trial.get("reclassify", False) or p.reclassify
        if not kept:
            new_locked, ok = trial, True
        else:
            tv = base_variant(trial)
            tt = run_all([tv], cfg, str(cache), str(ROOT / cfg["data"]["csv_dir"]), START, END, out_dir, 1)[tv.key]
            ev = evaluate(bt, with_r(tt))
            ok = ev["accepted"] or all(v2 for k2, v2 in ev["criteria"].items() if k2 != "C2_plateau" and v2 is not None)
            if ok:
                new_locked = trial
        if ok:
            kept.append({"param": p.name, "value": v, "gain_exp_IS": gain})
    final = base_variant(new_locked)
    ft = run_all([final], cfg, str(cache), str(ROOT / cfg["data"]["csv_dir"]), START, END, out_dir, 1)[final.key]
    report["locked_after"] = new_locked
    report["kept"] = kept
    report["after"] = summarize(ft)
    new_locked.setdefault("history", []).append({"block": name, "kept": kept})
    save_locked(new_locked)
    (RES / f"block_{name}.json").write_text(json.dumps(clean(report), indent=2, ensure_ascii=False, default=str))
    return report


def run_final(cache: Path, oos_caches: dict[str, Path] | None = None) -> dict:
    """Seul moment où le hors-échantillon est regardé : référence V2 contre config verrouillée."""
    cfg = lab_cfg()
    locked = load_locked()
    ref = base_variant({"overrides": {}, "lab": {}, "rescan": []})
    fin = base_variant(locked)
    tr = run_all([ref, fin], cfg, str(cache), str(ROOT / cfg["data"]["csv_dir"]), START, END, RES / "trades", 2)
    out = {"locked": locked, "periods": {k: [str(a), str(b)] for k, (a, b) in PERIODS.items()}}
    for label, v in (("reference", ref), ("locked", fin)):
        t = with_r(tr[v.key])
        out[label] = {p: metrics(period(t, p)) for p in PERIODS}
        out[label]["strategies_OOS"] = breakdown(period(t, "OOS"), "strategy")
        out[label]["pairs_OOS"] = breakdown(period(t, "OOS"), "symbol")
    (RES / "final.json").write_text(json.dumps(clean(out), indent=2, ensure_ascii=False, default=str))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="forex_agent.lab")
    ap.add_argument("--cache", default=str(DEFAULT_CACHE))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("cache")
    b = sub.add_parser("block")
    b.add_argument("name", choices=["A", "B", "C", "D"])
    sub.add_parser("final")
    a = ap.parse_args(argv)
    cache = Path(a.cache)
    if a.cmd == "cache":
        from .cache import build
        cfg = lab_cfg()
        build(cfg, ROOT / cfg["data"]["csv_dir"], cache, START, END, workers=2, log=lambda m: print(m, flush=True))
    elif a.cmd == "block":
        r = run_block(a.name, cache)
        print(json.dumps(clean({"kept": r["kept"], "base_IS": r["base"]["IS"], "after_IS": r["after"]["IS"],
                                "base_VAL": r["base"]["VAL"], "after_VAL": r["after"]["VAL"]}), indent=1,
                         ensure_ascii=False))
    elif a.cmd == "final":
        print(json.dumps(clean(run_final(cache)), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
