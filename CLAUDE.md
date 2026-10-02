# forex-agent — instructions permanentes pour tout agent (humain ou IA)

Lis ce fichier, puis `memory/PROJECT_STATE.md`, avant toute action. La mémoire du projet est dans `memory/` ;
la conversation qui l'a produite n'est pas nécessaire.

## Le projet en 10 lignes
- Agent de trading Forex autonome en **PAPER TRADING uniquement** (aucun broker réel, aucun argent réel).
- Paires : **EURUSD, GBPUSD, USDJPY**. Scan **toutes les 5 minutes**. Trades de **5 à 30 minutes maximum**.
- Capital de référence **50 €**, risque 1 % par trade, **max 2 positions**, Risk Manager déterministe (`forex_agent/risk/manager.py`).
- Données : Dukascopy M1 **bid + ask** réelles (spread réel inclus dans toutes les mesures).
- Objectif actuel : **trouver un avantage robuste** à 5–30 min. Aucun n'est démontré à ce jour (voir `memory/STRATEGIES.md`).
- Langue de travail et des rapports : **français**. L'utilisateur n'est pas développeur : rapports courts, sans jargon inutile.

## Système multi-agents (branche `multi-agent-research`)
5 agents définis dans `.claude/agents/` : `manager`, `researcher`, `quant`, `critic`, `developer`.
Le **Manager** est la session principale ; il lance les 4 autres avec l'outil Agent (sous-agents).
Ils communiquent **uniquement par fichiers** dans `experiments/E###-*/` et `orchestrator/state.json`.
Outils communs : `python -m orchestrator <commande>` (voir `orchestrator/README.md`).

## Limites d'autorité — STOP et demander l'accord de l'utilisateur avant :
argent réel · broker live · clés de trading live · augmentation du risque · modification du Risk Manager ·
suppression d'une protection · modification de la baseline officielle · merge vers `main` / production.
Tout le reste (recherche, hypothèses, backtests, validation, OOS, placebo, coûts, audits, corrections de bugs dans
le code de recherche, nouvelles branches `research-*`, documentation, mémoire) continue **sans demander**.

## Fichiers protégés (ne jamais modifier sans accord explicite)
Vérifiés par `python -m orchestrator guard` et par la CI (`.github/workflows/agents-guard.yml`) :
baseline V2 (`forex_agent/` sauf `forex_agent/meta/` et `forex_agent/lab/`), `config/settings.yaml`,
Risk Manager, H3 et ses critères (`research/v4/hypotheses.py`, `research/v4/oos_check.py`, `research/v4/PROTOCOLE.md`).

## Règles de méthode (non négociables)
1. Avant toute expérience : lire `memory/EXPERIMENTS.md` et `memory/REJECTED_HYPOTHESES.md` (pas de doublon).
2. Max **3 hypothèses** nouvelles par cycle, max **8 variantes** par hypothèse.
3. Critères de succès **écrits et commités AVANT** de regarder la validation et l'OOS. Jamais modifiés après.
4. Découpage : Train sept. 2025 → fév. 2026 · Validation mars → août 2026 · OOS verrouillé sept. 2024 → août 2025
   (voir `memory/PROJECT_STATE.md` : l'OOS 2024-2025 est consommé par H3 ; les hypothèses suivantes ont besoin d'un
   nouvel OOS jamais lu, à télécharger).
5. **OOS vierge sept. 2023 → août 2024** : aucun agent ne le clone, ne l'ouvre ni ne l'analyse tant que
   `python -m orchestrator oos-gate E###` ne répond pas OUVERT (Train ET Validation réussis). Une expérience qui échoue au
   Train est REJECT immédiatement : pas de Validation, pas d'OOS.
6. Une observation (journal, graphique) ne devient **jamais** une règle sans : hypothèse → backtest → validation → OOS.
7. On ne sauve pas une hypothèse rejetée avec des micro-réglages. Une hypothèse rejetée est archivée.
8. Mesures en **R**, coûts bid/ask inclus ; toujours : test placebo, coûts +0,2 à +1 pip, concentration
   (jours, paire, trimestre), vue par jour quand les paires sont corrélées (USD commun).
9. Ne jamais défendre une idée parce qu'on l'a proposée (auto-critique : RESEARCHER → CRITIC → DATA).

## Meta-skills existantes (services partagés, ne pas dupliquer)
- Revue adversariale : `forex_agent/meta/adversarial.py` → Critic (et revue de chaque setup dans le cycle live).
- Audit exposition / corrélation : `forex_agent/meta/exposure.py` → Quant, Manager, Risk Manager (informatif).
- Audit du journal : `forex_agent/meta/journal_audit.py` (`python -m forex_agent journal-audit`) → Researcher, Quant.
- Auto-critique RESEARCHER / CRITIC / DATA : `knowledge/META_SKILLS.md` → Manager avant toute conclusion.
- Outils de robustesse génériques (placebo, coûts, vue par jour, concentration) : `research/common/robustness.py`.
