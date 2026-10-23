"""Strategy Discovery — calcule le score de preuve de chaque fiche (GRILLE.md), écarte les doublons d'échecs et
produit le classement. Aucun backtest ici.

Usage : python -m forex_lab.discovery.score [--rejected chemin/REJECTED_HYPOTHESES.md]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import unicodedata
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
CRITERIA = ("S", "H", "C", "R", "I", "F", "P")
PENALTIES = {"effet_en_declin": 3, "hors_paires": 2}
REQUIRED = ("id", "nom", "famille", "sources", "regles", "resultats_publies", "limites", "scores", "compatibilite",
            "doublon_de", "mots_cles")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def failure_texts(rejected_path: Path | None) -> dict[str, str]:
    """Textes des trois registres d'échecs (pour le contrôle automatique des doublons)."""
    out = {"ECHECS.md": (LAB / "ECHECS.md").read_text()}
    cand = yaml.safe_load((LAB / "candidates.yaml").read_text())["candidates"]
    out["candidates.yaml (ELIMINE)"] = "\n".join(f"{c['nom']} {c.get('raison', '')}" for c in cand if c["verdict"] == "ELIMINE")
    if rejected_path and rejected_path.exists():
        out["REJECTED_HYPOTHESES.md"] = rejected_path.read_text()
    else:
        try:
            out["REJECTED_HYPOTHESES.md"] = subprocess.run(
                ["git", "show", "origin/multi-agent-research:memory/REJECTED_HYPOTHESES.md"], cwd=LAB.parent,
                capture_output=True, text=True, check=True).stdout
        except Exception:
            out["REJECTED_HYPOTHESES.md"] = ""
    return {k: norm(v) for k, v in out.items()}


def auto_duplicates(fiche: dict, texts: dict[str, str]) -> list[str]:
    """Registres où TOUS les mots-clés d'un groupe apparaissent (signal d'alerte, la décision reste manuelle)."""
    hits = []
    for group in fiche.get("mots_cles", []):
        words = [norm(w) for w in group]
        for name, txt in texts.items():
            if all(re.search(re.escape(w), txt) for w in words):
                hits.append(f"{name} : {' + '.join(group)}")
    return hits


def evaluate(fiche: dict, texts: dict[str, str]) -> dict:
    missing = [k for k in REQUIRED if k not in fiche]
    if missing:
        raise ValueError(f"{fiche.get('id')}: champs manquants {missing}")
    sc = fiche["scores"]
    bad = [k for k in CRITERIA if not isinstance(sc.get(k), int) or not 0 <= sc[k] <= 3]
    if bad:
        raise ValueError(f"{fiche['id']}: scores invalides {bad}")
    raw = sum(sc[k] for k in CRITERIA)
    pen = sum(v for k, v in PENALTIES.items() if fiche.get("penalites", {}).get(k))
    total = raw - pen
    auto = auto_duplicates(fiche, texts)
    excl = list(fiche.get("exclusions", []))
    if fiche["doublon_de"]:
        excl.append(f"doublon : {fiche['doublon_de']}")
    if auto and not fiche["doublon_de"] and not fiche.get("fait_nouveau"):
        excl.append("doublon probable (contrôle automatique) sans fait nouveau documenté : " + " ; ".join(auto))
    niveau = "solide" if total >= 15 else "moyenne" if total >= 11 else "faible"
    return {"id": fiche["id"], "nom": fiche["nom"], "famille": fiche["famille"], "brut": raw, "penalite": pen,
            "score": total, "niveau": niveau, "exclue": bool(excl), "exclusions": excl, "alertes_doublon": auto,
            "compatibilite": fiche["compatibilite"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rejected", default=None)
    a = ap.parse_args()
    fiches = yaml.safe_load((HERE / "registre.yaml").read_text())["fiches"]
    texts = failure_texts(Path(a.rejected) if a.rejected else None)
    res = [evaluate(f, texts) for f in fiches]
    keep = sorted([r for r in res if not r["exclue"]], key=lambda r: (-r["score"], r["id"]))
    out = sorted([r for r in res if r["exclue"]], key=lambda r: r["id"])
    lines = ["# Strategy Discovery — classement des preuves (généré par score.py, ne pas éditer à la main)", "",
             "Score sur 21 (GRILLE.md) : ≥ 15 solide, 11-14 moyenne, ≤ 10 faible. Aucun backtest n'a été lancé.", "",
             "## Candidates retenues", "",
             "| Rang | ID | Stratégie | Famille | Score | Niveau | Horizon | Paires du projet | Données gratuites |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(keep, 1):
        c = r["compatibilite"]
        lines.append(f"| {i} | {r['id']} | {r['nom']} | {r['famille']} | {r['score']} ({r['brut']}−{r['penalite']}) | {r['niveau']} | "
                     f"{c['horizon']} | {c['paires']} | {c['donnees']} |")
    lines += ["", "## Écartées", "", "| ID | Stratégie | Motif |", "|---|---|---|"]
    for r in out:
        lines.append(f"| {r['id']} | {r['nom']} | {' ; '.join(r['exclusions'])} |")
    (HERE / "CLASSEMENT.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return res


if __name__ == "__main__":
    main()
