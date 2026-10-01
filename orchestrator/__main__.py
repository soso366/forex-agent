"""CLI de l'orchestrateur.

  python -m orchestrator status                 état du système, expériences, mode
  python -m orchestrator plan                   tâches à confier maintenant (JSON) — utilisé par le Manager
  python -m orchestrator open-cycle             ouvre le cycle suivant
  python -m orchestrator new "titre" [--family F]   crée experiments/E###-titre/hypothesis.md (Researcher)
  python -m orchestrator template E### fichier.md   crée precritique.md / protocol.md / audit.md / decision.md
  python -m orchestrator advance E### ÉTAPE --by agent [--verdict V] [--note "…"]
  python -m orchestrator dupcheck mot1 mot2 …   cherche un doublon dans la mémoire et les expériences
  python -m orchestrator guard                  garde-fous (fichiers protégés, protocoles verrouillés, branche)
  python -m orchestrator report --decision … --best … --problem … --next …   rapport de fin de cycle
  python -m orchestrator pause | resume         interrupteur (orchestrator/control.yaml)
  python -m orchestrator lock-protected --approved-by "utilisateur, <date>"   (UNIQUEMENT après accord explicite)
"""
from __future__ import annotations

import argparse
import json
import sys

from . import core


def main(argv=None):
    ap = argparse.ArgumentParser(prog="orchestrator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("plan")
    sub.add_parser("open-cycle")
    n = sub.add_parser("new")
    n.add_argument("title")
    n.add_argument("--family", default="")
    t = sub.add_parser("template")
    t.add_argument("eid")
    t.add_argument("name", choices=["precritique.md", "protocol.md", "audit.md", "decision.md"])
    a = sub.add_parser("advance")
    a.add_argument("eid")
    a.add_argument("stage")
    a.add_argument("--by", required=True, choices=["manager", "researcher", "quant", "critic", "developer"])
    a.add_argument("--verdict", default=None)
    a.add_argument("--note", default="")
    d = sub.add_parser("dupcheck")
    d.add_argument("words", nargs="+")
    sub.add_parser("guard")
    r = sub.add_parser("report")
    r.add_argument("--decision", required=True)
    r.add_argument("--best", required=True)
    r.add_argument("--problem", required=True)
    r.add_argument("--next", required=True, dest="next_exp")
    r.add_argument("--keep-open", action="store_true")
    sub.add_parser("pause")
    sub.add_parser("resume")
    lp = sub.add_parser("lock-protected")
    lp.add_argument("--approved-by", required=True)
    x = ap.parse_args(argv)

    if x.cmd == "status":
        st, c = core.load_state(), core.control()
        print(f"mode : {c['mode']} · cycle {st['cycle']} ({'ouvert' if st.get('cycle_open') else 'fermé'})")
        for e in core.experiments():
            print(f"  {e['id']} [{e['stage']}{' · ' + e['verdict'] if e.get('verdict') else ''}] {e['title']}"
                  + (f"  (bloqué : {e['blocked_by']})" if e.get("blocked_by") else ""))
        issues = core.guard()
        print("garde-fous : OK" if not issues else "garde-fous : " + " | ".join(issues))
    elif x.cmd == "plan":
        print(json.dumps(core.plan(), indent=1, ensure_ascii=False))
    elif x.cmd == "open-cycle":
        print(f"cycle {core.open_cycle()} ouvert")
    elif x.cmd == "new":
        print(core.new_experiment(x.title, x.family))
    elif x.cmd == "template":
        print(core.template(x.eid, x.name))
    elif x.cmd == "advance":
        s = core.advance(x.eid, x.stage, x.by, x.note, x.verdict)
        print(f"{s['id']} → {s['stage']}" + (f" ({s['verdict']})" if s.get("verdict") else ""))
    elif x.cmd == "dupcheck":
        hits = core.dupcheck(x.words)
        print("\n".join(hits) if hits else "aucun doublon trouvé")
    elif x.cmd == "guard":
        issues = core.guard()
        if issues:
            print("GARDE-FOUS VIOLÉS :\n- " + "\n- ".join(issues))
            sys.exit(1)
        print("garde-fous OK : baseline, Risk Manager, H3 et protocoles verrouillés intacts")
    elif x.cmd == "report":
        print(core.report(x.decision, x.best, x.problem, x.next_exp, close=not x.keep_open))
    elif x.cmd == "pause":
        core.set_mode("PAUSED")
        print("système en PAUSE")
    elif x.cmd == "resume":
        core.set_mode("RUNNING")
        print("système RELANCÉ")
    elif x.cmd == "lock-protected":
        core.lock_protected(x.approved_by)
        print("empreintes des fichiers protégés mises à jour")


if __name__ == "__main__":
    main()
