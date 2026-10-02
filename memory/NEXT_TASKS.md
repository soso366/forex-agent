# Prochaines tâches (file d'attente — source exécutable : `python -m orchestrator plan`)

## Piste RECHERCHE
1. **[Researcher — cycle 3]** 1 à 2 hypothèses nouvelles. Piste suggérée par le Critic (à évaluer, pas imposée) : surréaction
   pendant les conférences de presse des banques centrales (Fed, BoJ, BCE, BoE), calendrier déclaré à l'avance ; ≈ 30
   événements/an → il faudrait de l'historique depuis ~2019 (nouvelle demande de données, distincte de l'OOS vierge).
2. **OOS vierge sept. 2023 → août 2024** : téléchargé ou en cours, mais NON LU. Verrou : `python -m orchestrator oos-gate E###`
   (ouvert seulement après Train ET Validation réussis).
3. **INTERDIT** : H3/E000, E001, E002 sous quelque forme que ce soit.

## Piste AUTOMATISATION (indépendante)
4. Le workflow `.github/workflows/agents-cycle.yml` est prêt (voir `orchestrator/AUTOMATION.md`). Bloqué par :
   (a) secret `ANTHROPIC_API_KEY` ou `CLAUDE_CODE_OAUTH_TOKEN` à ajouter par l'utilisateur ;
   (b) accord utilisateur pour copier CE SEUL fichier sur `main` (GitHub n'exécute les tâches planifiées que depuis main).
5. Tâche planifiée Claude externe « Forex — cycle Manager » : DÉSACTIVÉE (pas d'accès au dépôt privé).
