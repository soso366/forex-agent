"""Vérifie que les paramètres utilisés sont EXACTEMENT ceux des fichiers d'origine.

Usage : python check_params.py <dossier_des_sources>
(le dossier est rempli par fetch_sources.py, commit figé dans sources.json)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from strategies import SBRAKNI_PARAMS, SMIZXE_PARAMS

INPUT_RE = re.compile(r"^\s*input\s+(?:const\s+)?(\w+)\s+(\w+)\s*=\s*([^;]+);", re.M)


def parse_inputs(src: str) -> dict:
    out = {}
    for typ, name, raw in INPUT_RE.findall(src):
        raw = raw.strip()
        if typ == "bool":
            val = raw == "true"
        elif typ in ("int", "long", "uint", "ulong"):
            val = int(raw)
        elif typ == "double":
            val = float(raw)
        elif raw.startswith("TP_"):
            val = {"TP_OPPOSITE_BB": 0, "TP_MIDDLE_BB": 1, "TP_FIXED_RR": 2}[raw]
        else:
            val = raw.strip('"')
        out[name] = val
    return out


def parse_set(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if "=" in line and not line.startswith(";"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def compare(used: dict, origin: dict, label: str) -> list[str]:
    errs = []
    for k, v in used.items():
        if k not in origin:
            errs.append(f"{label}: {k} absent du fichier d'origine")
        elif origin[k] != v:
            errs.append(f"{label}: {k} = {v} mais l'origine dit {origin[k]}")
    return errs


def main(root: str) -> int:
    root = Path(root)
    errs = []
    for ea in ("RsiLevel", "RsiReversal"):
        src = (root / "smizxe" / "src" / "Experts" / f"{ea}.mq5").read_text(encoding="utf-8", errors="replace")
        errs += compare(SMIZXE_PARAMS, parse_inputs(src), f"smizxe/{ea}")
    mr = root / "sbrakni" / "EA" / "MeanReversionScalper.mq5"
    origin = parse_inputs(mr.read_text(encoding="utf-8", errors="replace"))
    errs += compare(SBRAKNI_PARAMS, origin, "sbrakni/EA")
    # Écarts entre le fichier .set « Best » et les valeurs par défaut de l'EA (information)
    best = parse_set((root / "sbrakni" / "sets" / "MeanReversionScalper_Best.set").read_text(errors="replace"))
    diffs = []
    for k, v in best.items():
        if k in origin and str(origin[k]).lower() not in (v.lower(), str(float(v)) if v.replace('.', '', 1).isdigit() else v):
            try:
                if float(v) == float(origin[k]):
                    continue
            except ValueError:
                pass
            diffs.append(f"{k}: EA={origin[k]} / set Best={v}")
    print("Écarts .set Best vs EA :", diffs or "aucun")
    if errs:
        print("ÉCHEC — paramètres différents de l'origine :")
        print("\n".join(errs))
        return 1
    print("OK — paramètres identiques aux fichiers d'origine.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "sources"))
