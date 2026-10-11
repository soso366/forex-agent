# Prochaines tâches (file d'attente — source exécutable : `python -m orchestrator plan`)

## Piste RECHERCHE
0. **[BLOQUANT — utilisateur]** Le cycle GitHub Actions n'a pas accès aux données : secret `DATA_REPO_TOKEN` absent ou non transmis à l'étape Claude du workflow (bootstrap : « indisponibles »). Sans lui, aucun backtest.
0b. **[Quant — E003]** Dès que les données sont là : `bash orchestrator/bootstrap.sh`, `run.py count` → commit `results/signal_counts.json`, puis `run.py train` → Critic → décision. Le Critic doit aussi relire les 2 choix signalés par le Quant (IC 95 % jour rendu éliminatoire ; comptage des signaux dans un fichier séparé).
1. **[Researcher]** 1 hypothèse nouvelle possible (cycle 3 : une seule, E003). Piste suggérée par le Critic (à évaluer, pas imposée) : surréaction
   pendant les conférences de presse des banques centrales (Fed, BoJ, BCE, BoE), calendrier déclaré à l'avance ; ≈ 30
   événements/an → il faudrait de l'historique depuis ~2019 (nouvelle demande de données, distincte de l'OOS vierge).
2. **OOS vierge sept. 2023 → août 2024** : téléchargé ou en cours, mais NON LU. Verrou : `python -m orchestrator oos-gate E###`
   (ouvert seulement après Train ET Validation réussis).
3. **INTERDIT** : H3/E000, E001, E002 (et toute variante d'E003 hors protocole) sous quelque forme que ce soit.

## Piste AUTOMATISATION (indépendante)
4. Le workflow `.github/workflows/agents-cycle.yml` est prêt (voir `orchestrator/AUTOMATION.md`). Bloqué par :
   (a) secret `ANTHROPIC_API_KEY` ou `CLAUDE_CODE_OAUTH_TOKEN` à ajouter par l'utilisateur ;
   (b) accord utilisateur pour copier CE SEUL fichier sur `main` (GitHub n'exécute les tâches planifiées que depuis main).
5. Tâche planifiée Claude externe « Forex — cycle Manager » : DÉSACTIVÉE (pas d'accès au dépôt privé).
