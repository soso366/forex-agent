# {id} — protocole (VERROUILLÉ au commit, ne plus modifier)
Auteur : QUANT

## Variantes (≤ 8, grille fixée ici)
## Données
- Train : sept. 2025 → fév. 2026
- Validation : mars → août 2026
- OOS verrouillé : (période jamais lue, préciser)
## Simulation
(entrée, coûts bid/ask, sortie au temps 30 min max, une position par paire)
## Critères Train → validation (tous requis)
## Critères validation → OOS
## Critères OOS : PASS / FAIL / INCONCLUSIVE
## Tests de robustesse obligatoires
- placebo (mêmes règles, autres heures / autres conditions prédéfinies)
- coûts +0,0 / 0,2 / 0,4 / 0,6 / 1,0 pip
- vue par jour (IC 95 % bootstrap), une paire par jour
- concentration : fins de mois, 5 meilleurs jours, meilleur trimestre, meilleure paire
