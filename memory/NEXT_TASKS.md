# Prochaines tâches (file d'attente du Manager — la source exécutable est `orchestrator/state.json`)

1. **[BLOQUÉ par données]** Lire le verdict OOS final de H3 dès que `data-2025mar-aug` ET `data-2024sep-2025feb`
   existent : `python -m research.v4.oos_check` (une seule fois, aucun ajustement). Enregistrer le verdict.
   - PASS → préparer H3 en paper trading séparé de la baseline (demander l'accord avant tout merge vers `main`).
   - FAIL / INCONCLUSIVE → archiver H3 dans `experiments/` + `REJECTED_HYPOTHESES.md`.
2. **[Data]** Télécharger un NOUVEL OOS jamais lu pour les prochaines hypothèses (ex. sept. 2023 → août 2024).
3. **[Cycle 1 — Researcher]** Nouvelle famille (≤ 3 hypothèses) dans la direction « retour à la moyenne à heure
   précise / flux » ou microstructure, en excluant tout ce qui est dans `REJECTED_HYPOTHESES.md`.
   Pistes possibles (non validées) : RangeFade reformulée pour produire ≥ 100 trades/an ; fins de mois
   (rééquilibrages) ; ouverture des marchés actions (NY cash open) comme flux ; observations du journal M-01.
4. **[Quant]** Généraliser les tests de robustesse (placebo, coûts, vue par jour) via `research/common/robustness.py`.
