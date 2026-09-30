"""Exécution des variantes du Parameter Lab (en parallèle, résultats mis en cache sur disque)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

from ..config import deep_merge
from .sim import Engine, LabData

_ENGINE: Engine | None = None


@dataclass
class Variant:
    block: str
    param: str
    value: object
    overrides: dict = field(default_factory=dict)       # fusionnés dans la config
    rescan: tuple = ()                                   # stratégies à recalculer
    reclassify: bool = False
    matrix: dict | None = None
    lab: dict = field(default_factory=dict)              # filtres du Bloc B

    @property
    def key(self) -> str:
        blob = json.dumps([self.overrides, sorted(self.rescan), self.reclassify, self.matrix, self.lab],
                          sort_keys=True, default=str)
        return hashlib.sha1(blob.encode()).hexdigest()[:12]


def _init(cache_dir, csv_dir, cfg):
    global _ENGINE
    _ENGINE = Engine(LabData(cache_dir, csv_dir, cfg))


def _run(args):
    v, cfg, start, end, out = args
    path = Path(out) / f"{v.key}.pkl"
    if path.exists():
        return v.key
    c = deep_merge(cfg, v.overrides)
    t = _ENGINE.run(c, start, end, rescan=set(v.rescan), reclassify=v.reclassify, matrix=v.matrix, lab=v.lab)
    t.to_pickle(path)
    return v.key


def run_all(variants: list[Variant], cfg: dict, cache_dir: str, csv_dir: str, start: datetime, end: datetime,
            out_dir: str | Path, workers: int = 2, log=print) -> dict[str, pd.DataFrame]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    todo = [(v, cfg, start, end, str(out)) for v in variants if not (out / f"{v.key}.pkl").exists()]
    # les plus lourdes (recalcul de stratégies) d'abord, pour équilibrer les deux cœurs
    todo.sort(key=lambda a: (len(a[0].rescan) + 3 * a[0].reclassify), reverse=True)
    if todo:
        log(f"{len(todo)} variantes à simuler ({len(variants) - len(todo)} déjà en cache)")
        with Pool(workers, initializer=_init, initargs=(cache_dir, csv_dir, cfg)) as pool:
            for i, k in enumerate(pool.imap_unordered(_run, todo), 1):
                log(f"  {i}/{len(todo)} {k}")
    return {v.key: pd.read_pickle(out / f"{v.key}.pkl") for v in variants}
