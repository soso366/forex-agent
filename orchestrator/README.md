# Système multi-agents de recherche (forex-agent)

## Les 5 agents (`.claude/agents/`)
| Agent | Fichier | Rôle | Écrit |
|---|---|---|---|
| Manager / Orchestrator | `manager.md` | lit la mémoire, distribue, fait auditer, décide, met à jour la mémoire, enchaîne | `decision.md`, `memory/*`, `reports/` |
| Researcher | `researcher.md` | ≤ 3 hypothèses fortes par cycle | `hypothesis.md` |
| Quant / Backtester | `quant.md` | protocole verrouillé, code, Train / Validation / OOS, robustesse | `protocol.md`, `code/`, `results/*.json` |
| Critic | `critic.md` | réfuter avant et après test, peut imposer REJECT / RETEST | `precritique.md`, `audit.md` |
| Developer | `developer.md` | code, tests, bugs, outils, baseline intacte | code, `tests/` |

## Communication : uniquement par fichiers
```
experiments/E###-titre/
  status.json        étape + historique (écrit par l'orchestrateur)
  hypothesis.md      RESEARCHER
  precritique.md     CRITIC (GO / REJECT avant test)
  protocol.md        QUANT (critères écrits avant les données ; empreinte verrouillée)
  code/  results/    QUANT (train.json, validation.json, oos.json)
  audit.md           CRITIC (OK / RETEST / REJECT)
  decision.md        MANAGER (KEEP / REJECT / RETEST / INCONCLUSIVE / PASS)
orchestrator/state.json   numéro de cycle, historique
memory/*.md               connaissance durable du projet
```

## Machine à étapes
PROPOSED → PRECRITIQUED → PROTOCOL_LOCKED → TRAIN_DONE → VALIDATED → OOS_DONE → AUDITED → DECIDED → ARCHIVED
`python -m orchestrator plan` dit quel agent doit produire quel fichier pour chaque expérience.

## Meta-skills partagées (pas de duplication)
| Meta-skill | Code | Utilisée par |
|---|---|---|
| Revue adversariale | `forex_agent/meta/adversarial.py` | Critic (+ cycle live) |
| Audit exposition / corrélation | `forex_agent/meta/exposure.py` | Quant, Manager, Risk Manager (informatif) |
| Audit du journal | `forex_agent/meta/journal_audit.py` | Researcher, Quant |
| Auto-critique RESEARCHER / CRITIC / DATA | `knowledge/META_SKILLS.md` + `templates/decision.md` | Manager |

## Garde-fous
`python -m orchestrator guard` (et la CI `agents-guard.yml` à chaque push) : fichiers protégés (baseline, Risk
Manager, configuration, H3) identiques aux empreintes `protected.json` ; protocoles verrouillés non modifiés ;
pas de travail sur `main`.

## Autonomie
- Tâche planifiée Claude (cloud) : lance une session « Manager » à intervalle régulier, qui exécute un cycle.
- GitHub Actions : `agents-guard.yml` (garde-fous + tests à chaque push), `agents-watchdog.yml` (alerte par issue
  GitHub si aucun cycle depuis 48 h), `export-data.yml` (téléchargements Dukascopy demandés par le Quant).

## Arrêter / reprendre
- `orchestrator/control.yaml` : `mode: PAUSED` / `mode: RUNNING` (modifiable depuis le site GitHub), ou
  `python -m orchestrator pause` / `resume`, ou demander à Claude.
- Couper complètement : désactiver la tâche planifiée « Forex — cycle Manager » dans Claude.
