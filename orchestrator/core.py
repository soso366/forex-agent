"""Orchestrateur multi-agents : état, machine à étapes des expériences, garde-fous, rapport de cycle.

Les agents (Claude) communiquent UNIQUEMENT par fichiers :
  experiments/E###-slug/{hypothesis,precritique,protocol,audit,decision}.md + results/ + status.json
  orchestrator/state.json  (cycle courant, file de tâches, historique)
Ce module est déterministe : il dit au Manager quelle tâche confier à quel agent, vérifie les transitions
et les garde-fous. Il ne prend aucune décision de trading.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ORCH = ROOT / "orchestrator"
EXP = ROOT / "experiments"
MEM = ROOT / "memory"
REPORTS = ROOT / "reports"
STATE = ORCH / "state.json"
CONTROL = ORCH / "control.yaml"
PROTECTED = ORCH / "protected.json"
LOCK = ORCH / "cycle.lock"
AGENT_LOG = ORCH / "agent_log.jsonl"
LOCK_HOURS = 5

# Étapes, agent responsable de l'étape SUIVANTE, fichier attendu pour la franchir
STAGES = [
    ("PROPOSED", "critic", "precritique.md"),          # le Critic critique avant test
    ("PRECRITIQUED", "quant", "protocol.md"),          # le Quant écrit le protocole (critères) et le code
    ("PROTOCOL_LOCKED", "quant", "results/train.json"),
    ("TRAIN_DONE", "quant", "results/validation.json"),
    ("VALIDATED", "quant", "results/oos.json"),
    ("OOS_DONE", "critic", "audit.md"),
    ("AUDITED", "manager", "decision.md"),
    ("DECIDED", None, None),
    ("ARCHIVED", None, None),
]
ORDER = [s for s, _, _ in STAGES]
TERMINAL = {"DECIDED", "ARCHIVED"}
VERDICTS = {"KEEP", "REJECT", "RETEST", "INCONCLUSIVE", "PASS"}

# Fichiers protégés : baseline V2, Risk Manager, configuration officielle, H3 et ses critères.
PROTECTED_GLOBS = [
    "forex_agent/*.py", "forex_agent/analysis/*.py", "forex_agent/brain/*.py", "forex_agent/broker/*.py",
    "forex_agent/data/*.py", "forex_agent/risk/*.py", "forex_agent/strategies/*.py",
    "config/settings.yaml", "prompts/agent_system.md",
    "research/v4/*.py", "research/v4/PROTOCOLE.md",
]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return ""


# ------------------------------------------------------------------ contrôle et état
def control() -> dict:
    return yaml.safe_load(CONTROL.read_text(encoding="utf-8"))


def set_mode(mode: str) -> None:
    txt = CONTROL.read_text(encoding="utf-8")
    CONTROL.write_text(re.sub(r"^mode: \w+", f"mode: {mode}", txt, flags=re.M), encoding="utf-8")


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"cycle": 0, "cycle_open": False, "history": [], "notes": []}


def save_state(s: dict) -> None:
    STATE.write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------ expériences
def experiments() -> list[dict]:
    out = []
    for d in sorted(EXP.glob("E*")):
        st = d / "status.json"
        if st.exists():
            s = json.loads(st.read_text(encoding="utf-8"))
            s["dir"] = str(d.relative_to(ROOT))
            out.append(s)
    return out


def get(eid: str) -> tuple[Path, dict]:
    for d in EXP.glob(f"{eid}-*"):
        return d, json.loads((d / "status.json").read_text(encoding="utf-8"))
    raise SystemExit(f"expérience {eid} introuvable")


def write_status(d: Path, s: dict) -> None:
    s = {k: v for k, v in s.items() if k != "dir"}
    (d / "status.json").write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")


def next_id() -> str:
    ids = [int(m.group(1)) for d in EXP.glob("E*") if (m := re.match(r"E(\d+)", d.name))]
    return f"E{(max(ids) + 1 if ids else 1):03d}"


def new_experiment(title: str, family: str = "", legacy: dict | None = None) -> Path:
    st = load_state()
    active = [e for e in experiments() if e["stage"] not in TERMINAL]
    cap = control()["max_active_experiments"]
    if not legacy and len(active) >= cap:
        raise SystemExit(f"déjà {len(active)} expériences actives (max {cap}) : terminer avant d'en ouvrir")
    eid = next_id()
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    d = EXP / f"{eid}-{slug}"
    (d / "results").mkdir(parents=True)
    for name in ("hypothesis.md",):
        (d / name).write_text((ORCH / "templates" / name).read_text(encoding="utf-8")
                              .format(id=eid, title=title, cycle=st["cycle"], date=now()), encoding="utf-8")
    s = {"id": eid, "title": title, "family": family, "stage": "PROPOSED", "created": now(),
         "cycle": st["cycle"], "history": [{"stage": "PROPOSED", "at": now(), "by": "researcher"}]}
    if legacy:
        s.update(legacy)
    write_status(d, s)
    return d


def template(eid: str, name: str) -> Path:
    d, s = get(eid)
    p = d / name
    if not p.exists():
        p.write_text((ORCH / "templates" / name).read_text(encoding="utf-8").format(
            id=eid, title=s["title"], cycle=s.get("cycle", 0), date=now()), encoding="utf-8")
    return p


def advance(eid: str, stage: str, by: str, note: str = "", verdict: str | None = None) -> dict:
    d, s = get(eid)
    if stage not in ORDER:
        raise SystemExit(f"étape inconnue {stage}")
    cur = ORDER.index(s["stage"])
    tgt = ORDER.index(stage)
    if tgt <= cur and stage != "ARCHIVED":
        raise SystemExit(f"{eid} est déjà à {s['stage']} (pas de retour en arrière)")
    # la tâche de l'étape courante doit avoir produit son fichier
    _, agent, need = STAGES[cur]
    if need and stage != "ARCHIVED" and not (d / need).exists():
        raise SystemExit(f"{eid} : {need} manquant pour quitter {s['stage']}")
    if stage == "PROTOCOL_LOCKED":
        # verrou : empreinte du protocole + commit ; toute modification ultérieure est détectée par guard
        s["protocol_sha"] = sha(d / "protocol.md")
        s["protocol_commit"] = git("rev-parse", "--short", "HEAD")
    if stage == "DECIDED":
        if verdict not in VERDICTS:
            raise SystemExit(f"verdict requis parmi {sorted(VERDICTS)}")
        s["verdict"] = verdict
    if stage == "PRECRITIQUED" and verdict == "REJECT":
        s["verdict"], stage = "REJECT", "DECIDED"
    s["stage"] = stage
    s["history"].append({"stage": stage, "at": now(), "by": by, "note": note, **({"verdict": verdict} if verdict else {})})
    write_status(d, s)
    return s


# ------------------------------------------------------------------ ce que le Manager doit lancer
def plan() -> dict:
    """Tâches à confier maintenant, par agent. Les tâches d'expériences différentes sont parallélisables."""
    c = control()
    if c.get("mode") != "RUNNING":
        return {"mode": c.get("mode"), "tasks": [], "message": "système en PAUSE : ne rien lancer"}
    tasks = []
    exps = experiments()
    for e in exps:
        if e["stage"] in TERMINAL:
            continue
        if e.get("blocked_by"):
            tasks.append({"agent": "manager", "experiment": e["id"], "action": "vérifier le blocage",
                          "detail": e["blocked_by"], "parallel": True})
            continue
        i = ORDER.index(e["stage"])
        _, agent, need = STAGES[i]
        tasks.append({"agent": agent, "experiment": e["id"], "dir": e["dir"], "produce": need,
                      "action": ACTIONS.get(e["stage"], ""), "parallel": True})
    active = [e for e in exps if e["stage"] not in TERMINAL]
    room = min(c["max_new_hypotheses_per_cycle"], c["max_active_experiments"] - len(active))
    if room > 0:
        tasks.append({"agent": "researcher", "action": f"proposer au plus {room} hypothèse(s) forte(s) nouvelle(s)",
                      "produce": "experiments/E###-*/hypothesis.md (via python -m orchestrator new)", "parallel": True})
    return {"mode": "RUNNING", "cycle": load_state()["cycle"], "tasks": tasks}


ACTIONS = {
    "PROPOSED": "critique AVANT test : doublon ? falsifiable ? tests obligatoires ? verdict GO/REJECT dans precritique.md",
    "PRECRITIQUED": "écrire protocol.md (variantes ≤ 8, critères Train/Validation/OOS) + code, COMMITER, puis advance PROTOCOL_LOCKED",
    "PROTOCOL_LOCKED": "lancer le Train, écrire results/train.json (+ appliquer les critères du protocole)",
    "TRAIN_DONE": "si Train OK : validation → results/validation.json ; sinon results/validation.json = {\"skipped\": raison} et passer à l'audit",
    "VALIDATED": "si validation OK : OOS verrouillé (lecture unique) → results/oos.json ; sinon {\"skipped\": raison}",
    "OOS_DONE": "audit des résultats (overfitting, fuite, dépendance, coûts, corrélation) → audit.md avec verdict OK/RETEST/REJECT",
    "AUDITED": "auto-critique RESEARCHER/CRITIC/DATA → decision.md, puis advance DECIDED --verdict …, puis mettre à jour la mémoire",
}


# ------------------------------------------------------------------ garde-fous
def protected_files() -> list[Path]:
    out = []
    for g in PROTECTED_GLOBS:
        out += sorted(ROOT.glob(g))
    return sorted(set(out))


def snapshot_protected() -> dict:
    return {str(p.relative_to(ROOT)): sha(p) for p in protected_files()}


def guard() -> list[str]:
    """Problèmes détectés (liste vide = OK)."""
    issues = []
    ref = json.loads(PROTECTED.read_text(encoding="utf-8"))["files"]
    cur = snapshot_protected()
    for f, h in ref.items():
        if f not in cur:
            issues.append(f"fichier protégé supprimé : {f}")
        elif cur[f] != h:
            issues.append(f"fichier protégé modifié : {f}")
    for f in cur:
        if f not in ref:
            issues.append(f"nouveau fichier dans une zone protégée : {f}")
    for e in experiments():
        if e.get("protocol_sha"):
            p = ROOT / e["dir"] / "protocol.md"
            if not p.exists() or sha(p) != e["protocol_sha"]:
                issues.append(f"{e['id']} : protocole modifié après verrouillage (interdit)")
    br = git("rev-parse", "--abbrev-ref", "HEAD")
    if br in ("main", "master"):
        issues.append("travail sur main : interdit sans accord de l'utilisateur")
    return issues


def lock_protected(approved_by: str) -> None:
    PROTECTED.write_text(json.dumps({"approved_by": approved_by, "at": now(), "files": snapshot_protected()},
                                    indent=1, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------ doublons
def dupcheck(words: list[str]) -> list[str]:
    hits = []
    files = [MEM / "EXPERIMENTS.md", MEM / "REJECTED_HYPOTHESES.md"] + sorted(EXP.glob("E*/hypothesis.md"))
    for f in files:
        if not f.exists():
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            low = line.lower()
            if all(w.lower() in low for w in words):
                hits.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()[:160]}")
    return hits


# ------------------------------------------------------------------ cycles et rapport
def open_cycle() -> int:
    s = load_state()
    if not s.get("cycle_open"):
        s["cycle"] += 1
        s["cycle_open"] = True
        s["history"].append({"cycle": s["cycle"], "opened": now()})
        save_state(s)
    return s["cycle"]


def report(decision: str, best: str, problem: str, next_exp: str, close: bool = True) -> str:
    s = load_state()
    cyc = s["cycle"]
    exps = experiments()
    this = [e for e in exps if any(h.get("at", "") >= _opened(s, cyc) for h in e["history"])]
    tested = [e for e in this if ORDER.index(e["stage"]) >= ORDER.index("TRAIN_DONE")]
    rejected = [e for e in this if e.get("verdict") == "REJECT"]
    in_val = [e for e in exps if e["stage"] in ("TRAIN_DONE",) and e.get("verdict") != "REJECT"]
    in_oos = [e for e in exps if e["stage"] == "VALIDATED"]
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    changed = git("diff", "--stat", "--name-only", f"{s.get('last_report_commit') or 'HEAD~1'}", "HEAD")
    names = lambda L: ", ".join(f"{e['id']} {e['title']}" for e in L) or "aucune"
    txt = "\n".join([
        f"CYCLE #{cyc}",
        f"Hypothèses testées : {names(tested)}",
        f"Rejetées : {names(rejected)}",
        f"En validation : {names(in_val)}",
        f"En OOS : {names(in_oos)}",
        f"Meilleure piste : {best}",
        f"Problème principal : {problem}",
        f"Décision du Manager : {decision}",
        f"Prochaine expérience : {next_exp}",
        f"Fichiers/branches modifiés : branche {branch} ; " + (", ".join(changed.splitlines()[:12]) or "—"),
    ])
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / f"CYCLE_{cyc:03d}.md").write_text(txt + "\n" + agent_table(cyc), encoding="utf-8")
    if close:
        s["cycle_open"] = False
        s["last_report_commit"] = git("rev-parse", "HEAD")
        s["history"].append({"cycle": cyc, "closed": now(), "decision": decision})
        save_state(s)
    return txt


def _opened(s: dict, cyc: int) -> str:
    for h in s["history"]:
        if h.get("cycle") == cyc and "opened" in h:
            return h["opened"]
    return ""


# ------------------------------------------------------------------ verrou de cycle (un seul Manager à la fois)
def lock_acquire(owner: str) -> tuple[bool, str]:
    """Le verrou est un fichier commité et poussé : deux sessions (interactive et planifiée) ne travaillent jamais en même temps."""
    git("pull", "-q", "--ff-only")
    if LOCK.exists():
        d = json.loads(LOCK.read_text(encoding="utf-8"))
        age = (datetime.now(timezone.utc) - datetime.strptime(d["at"], "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc))
        if age.total_seconds() < LOCK_HOURS * 3600:
            return False, f"cycle déjà en cours ({d['owner']}, depuis {d['at']})"
    LOCK.write_text(json.dumps({"owner": owner, "at": now()}, ensure_ascii=False), encoding="utf-8")
    git("add", str(LOCK.relative_to(ROOT)))
    git("commit", "-qm", f"Verrou de cycle : {owner}")
    r = subprocess.run(["git", "push", "-q"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        git("reset", "-q", "--hard", "HEAD~1")        # un autre Manager a poussé avant nous : on s'efface
        return False, f"push du verrou impossible ({r.stderr.strip()[:120]})"
    return True, "verrou acquis"


def lock_release() -> None:
    if LOCK.exists():
        LOCK.unlink()


# ------------------------------------------------------------------ journal des agents réellement invoqués
def log_agent(cycle: int, agent: str, task: str, produced: str, start: str, end: str, result: str, next_dep: str) -> None:
    with open(AGENT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"cycle": cycle, "agent": agent, "task": task, "produced": produced, "start": start,
                            "end": end, "result": result, "next": next_dep}, ensure_ascii=False) + "\n")


def agent_table(cycle: int) -> str:
    if not AGENT_LOG.exists():
        return ""
    rows = [json.loads(l) for l in AGENT_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r["cycle"] == cycle]
    if not rows:
        return ""
    out = ["", "## Agents réellement invoqués", "", "| Agent | Tâche reçue | Fichier produit | Début | Fin | Résultat | Dépendance suivante |",
           "|---|---|---|---|---|---|---|"]
    out += [f"| {r['agent']} | {r['task']} | {r['produced']} | {r['start']} | {r['end']} | {r['result']} | {r['next']} |" for r in rows]
    return "\n".join(out) + "\n"
