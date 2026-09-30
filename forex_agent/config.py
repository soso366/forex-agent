"""Chargement de la configuration et objets partagés."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "settings.yaml"


def load_config(path: str | Path | None = None, overrides: dict | None = None) -> dict:
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if overrides:
        cfg = deep_merge(cfg, overrides)
    import os
    if os.environ.get("FOREX_DATA_PROVIDER"):          # choix de la source de prix par variable (cloud)
        cfg["data"]["provider"] = os.environ["FOREX_DATA_PROVIDER"]
    if cfg.get("mode") != "paper":
        raise ValueError("V1 : seul le mode 'paper' est autorisé.")
    return cfg


def deep_merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def resolve_path(cfg: dict, key: str) -> Path:
    p = Path(cfg["paths"][key])
    return p if p.is_absolute() else ROOT / p


@dataclass
class Setup:
    """Opportunité détectée par une stratégie (avant tout contrôle de risque)."""
    symbol: str
    direction: str            # BUY | SELL
    strategy: str
    entry: float              # prix de référence (dernière clôture M5)
    stop: float
    target: float
    confirmations: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    id: str = ""
    essential: list[str] = field(default_factory=list)   # conditions obligatoires (entrée binaire)
    meta: dict[str, Any] = field(default_factory=dict)   # liquidité prise, cible nommée, déclencheur…

    @property
    def sign(self) -> int:
        return 1 if self.direction == "BUY" else -1

    @property
    def score(self) -> int:
        return sum(1 for v in self.confirmations.values() if v)

    @property
    def rr(self) -> float:
        risk = abs(self.entry - self.stop)
        return abs(self.target - self.entry) / risk if risk > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "symbol": self.symbol, "direction": self.direction,
            "strategy": self.strategy, "entry": self.entry, "stop": self.stop,
            "target": self.target, "rr": round(self.rr, 2), "score": self.score,
            "confirmations": self.confirmations, "essential": self.essential,
            "meta": self.meta, "notes": self.notes,
        }


@dataclass
class Decision:
    """Décision finale pour une paire ou une position, journalisée."""
    symbol: str
    action: str               # BUY | SELL | NO_TRADE | HOLD | MOVE_STOP | TAKE_PROFIT | CLOSE
    reason: str
    strategy: str | None = None
    trade_id: int | None = None
    details: dict = field(default_factory=dict)


def iso(ts: datetime | None) -> str | None:
    return ts.isoformat() if ts else None
