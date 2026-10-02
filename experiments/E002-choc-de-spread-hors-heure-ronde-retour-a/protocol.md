# E002 — protocole (VERROUILLÉ au commit, ne plus modifier)
Auteur : QUANT · cycle 2 · 2026-10-02 · écrit AVANT tout calcul de résultat (aucun R calculé avant ce commit ;
seuls le nombre de signaux et le test de non-look-ahead ont été exécutés, comme l'exige le Critic).

## Règle commune (fixe pour toutes les variantes)
Données M1 bid/ask Dukascopy, index UTC = début de minute ; une minute t est connue à sa clôture (t + 1 min).
Paires : EURUSD, GBPUSD, USDJPY, chacune indépendamment. Grille minute complète (minutes absentes = manquantes) ;
tous les décalages (t−3, t+1…t+5, m+1) sont en HORODATAGE, pas en rang d'index.
- Spread : s_t = max(ask_open − bid_open, ask_close − bid_close). mid = (bid + ask)/2 (clôture, haut, bas).
- ref_t : médiane de tous les s des minutes du même créneau de 30 min UTC (48 créneaux/jour) sur les **20 jours
  ouvrés précédents** (lundi–vendredi ayant des cotations ; jour courant exclu). Moins de 20 jours → pas de signal.
- ATR M5 : `research/v4/data.bars(m1, "5min")` + `atr(…, 14)` (mid). Chaque valeur est réétiquetée à la FIN de sa
  barre (étiquette + 5 min) et lue en asof à la clôture de t (t + 1 min) : seules les M5 terminées au plus tard à la
  clôture de t sont utilisées (fuite `atr_now` signalée par le Critic évitée ; vérifiée par le test).
- Δ_t = mid_close(t) − mid_close(t−3) ; mid_close(t−3) prolongé (ffill) au plus 2 minutes ; minute t présente.
- Heures : 06:00 ≤ t < 20:00 UTC, lundi–vendredi ; exclus 20:30–22:30 UTC (redondant) et lundi avant 07:00 UTC.
- Minute hors ronde : min(t.minute mod 15, 15 − t.minute mod 15) > 2 (40 minutes sur 60).
- Déclencheur à t : s_t ≥ k × ref_t ET |Δ_t| ≥ 1,0 × ATR ET heures ET minute hors ronde.
- Normalisation : m = première minute PRÉSENTE de (t, t+5] avec s_m ≤ 1,5 × ref_m ; aucune → pas de trade.
- Extrême X : max des mid_high de [t−2, m] si Δ > 0 (min des mid_low si Δ < 0). Retracé = sign(Δ)·(X − mid_close(m))/|Δ| ;
  > 0,5 → pas de trade. Niveau de retour 50 % : L = X − sign(Δ)·0,5·|Δ|.
- Entrée : ouverture de la minute m+1 (doit exister ; ask pour un achat, bid pour une vente), sens = −sign(Δ).
  Si le prix d'entrée exécutable a déjà atteint ou dépassé L → pas de trade (toutes variantes ; le retour est fait).
- Stop : 1,5 × ATR (lu à t) depuis le prix d'entrée, jamais élargi. Cible (si variante « cible ») : niveau L.
- Sortie : `research/v4/sim.simulate(…, hold=H, max_gap_min=1)` : stop prioritaire, glissement à l'ouverture,
  cible, sinon clôture de la dernière minute de la durée H. R = PnL / distance de stop, spread bid/ask réel inclus.
- Une position par paire ; épisode : signaux traités par ordre chronologique de t ; une entrée sur une paire bloque
  toute nouvelle entrée sur cette paire pendant 30 min (≥ H, donc jamais deux positions sur la même paire).
- Implémentation : `code/e002.py` (sim.py et data.py importés, non modifiés), `code/run.py`, `code/test_lookahead.py`.

## Variantes (≤ 8, grille fixée ici) — 3 axes binaires de l'hypothèse, rien d'autre
| id | seuil k (× ref) | H (min) | cible 50 % |
|---|---|---|---|
| V1 (règle principale) | 3,0 | 15 | oui |
| V2 | 3,0 | 15 | non |
| V3 | 3,0 | 30 | oui |
| V4 | 3,0 | 30 | non |
| V5 (repli pré-déclaré) | 2,5 | 15 | oui |
| V6 | 2,5 | 15 | non |
| V7 | 2,5 | 30 | oui |
| V8 | 2,5 | 30 | non |
Voisins = les 3 variantes qui diffèrent d'UNE dimension. Règle principale = V1 ; si V1 a < 80 trades au Train,
la règle principale devient V5 (seul relâchement autorisé ; pas de 2×, pas d'ATR 0,8, pas de normalisation 10 min).

## Nombre de signaux (compté AVANT toute lecture de R — `run.py count`, Train)
Les entrées ne dépendent que de k (H et la cible ne changent que la sortie) :
| k | trades (après cooldown) | EURUSD | GBPUSD | USDJPY | chocs isolés (contrôle données) |
|---|---|---|---|---|---|
| 3,0 (V1–V4) | **8** | 0 | 1 | 7 | 0 |
| 2,5 (V5–V8) | **18** | 0 | 3 | 15 | 0 |
Conséquence écrite avant les résultats : V1 < 80 → règle principale = V5 ; V5 a aussi < 80 trades → **aucune
variante n'est éligible (n ≥ 80) et le critère Train 1 ne peut pas être rempli**. Aucun autre relâchement n'est
permis : le Train sera exécuté et rapporté intégralement (toutes variantes, contrôles), puis déclaré échoué si le
critère n'est pas rempli. Entonnoir (k = 3, Train, 3 paires) : ~1 180 minutes s ≥ 3×ref dans les heures, ~590 hors
minute ronde, 75 avec |Δ| ≥ 1 ATR, 23 normalisées en ≤ 5 min, 8 trades après filtres de retracement / niveau L.

## Sélection (Train uniquement)
- Éligibilité : n ≥ 80 trades au Train.
- Score prudent(v) = min(espérance de v, espérances de ses 3 voisins). Retenue = score prudent maximal parmi les
  éligibles (égalité → plus petit id). Aucune éligible → meilleur score prudent rapporté, critère 1 échoue.
- Le t ≥ 2 est exigé AUSSI sur la règle principale pré-déclarée (critère 2), pas seulement sur la retenue.

## Données
- Train : 2025-09-01 → 2026-02-28 (data/m1_2025 uniquement). Premiers 20 jours ouvrés = historique de ref.
- Validation A : 2026-03-01 → 2026-08-31 (data/m1 ; l'historique de ref peut utiliser février 2026).
- Validation B : 2024-09-01 → 2025-08-31 (data/m1_locked_2024 + data/m1_locked) ; jamais utilisée pour E002.
- OOS vierge : 2023-09-01 → 2024-08-31. Jamais cloné ni ouvert avant `python -m orchestrator oos-gate E002` = OUVERT
  (Train ET Validation réussis) ; lu UNE fois.
- La validation ne porte que sur la variante retenue au Train ; rien n'est ré-optimisé.

## Simulation
Entrée à l'ouverture de m+1, coûts bid/ask réels, sortie ≤ 30 min (H = 15 ou 30), une position par paire,
`max_gap_min = 1`. Coûts additionnels : 0 / 0,2 / 0,4 / 0,5 / 0,6 / 1,0 pip par trade (`robustness.costs`).

## Contrôles et placebos (définitions fixées ; imposés par le Critic)
- C1 « même mouvement, spread normal » (décisif) : même code, mêmes heures, même minute hors ronde, même |Δ| ≥ 1 ATR,
  mais s_t < 1,5 × ref_t ; même normalisation (première minute ≤ t+5 avec s ≤ 1,5 ref), même filtre de retracement,
  entrée à m+1, même stop, même sortie, même cooldown. Écart = espérance E002 − espérance C1 ; IC 95 % de l'écart
  par bootstrap de JOURS (UTC), tirage indépendant dans chaque échantillon, 10 000 tirages, graine 11.
- C2 minutes rondes : même règle sur les chocs à ±2 min de :00/:15/:30/:45. Décisif seulement si n ≥ 50.
- C3 artefact de cotation : Δ recalculé sur le côté exécutable. A1 (littéral Critic) : ask si Δ_mid > 0, bid si
  Δ_mid < 0 (même signe requis). A2 (prudent) : bid ET ask ont bougé dans le sens de Δ_mid, Δ = le plus petit des
  deux mouvements. Règle principale rejouée avec ce Δ (déclencheur, retracement, niveau L).
- P1 placebo temporel : pour chaque trade, minute u tirée au hasard dans la même heure UTC du même jour, entrée à
  u+1, sens opposé au mouvement mid des 3 dernières minutes, stop 1,5 ATR(u), même H, cible 50 % de ce mouvement
  depuis l'extrême de [u−2, u] si la variante a une cible ; 200 tirages, graine 5 ; 95e centile des espérances.
- Contrôle données (critère 7 chiffré) : choc « isolé » = voisins t−1 et t+1 avec s < 1,5 ref ET mouvement mid de
  t−3 à t−1 < 0,25 |Δ| ; part des trades et du R, résultat sans eux.
- Jours fériés / liquidité mince (liste pré-déclarée `code/e002.py::HOLIDAYS`) et lundis : avec / sans.
- Vue par épisode : entrées à ±2 min sur plusieurs paires = un épisode (R moyenné).
- Test de non-look-ahead : `code/test_lookahead.py` (perturbation du futur → ref, s, ATR, Δ du présent inchangés ;
  sensibilité : l'ATR « naïf » à l'étiquette de début M5 change, donc le test détecte la fuite). Exécuté par `run.py train`.

## Critères Train → validation (tous requis ; variante retenue sauf mention)
1. n ≥ 80, espérance > +0,05 R, t ≥ 2 (par trade).
2. Règle principale pré-déclarée (V1, ou V5 si n(V1) < 80) : espérance > 0 et t ≥ 2.
3. PF ≥ 1,10.
4. Espérance > 0 après retrait des 5 meilleurs trades.
5. Au moins un voisin d'espérance > 0.
6. Vue par jour (UTC) : borne basse de l'IC 95 % bootstrap > 0.
7. C1 : écart ≥ +0,08 R ET borne basse IC 95 % (jours) de l'écart > 0.
8. C2 : si n(C2) ≥ 50, espérance hors ronde − espérance ronde ≥ +0,05 R ; si n < 50, non décisif (rapporté, mécanisme
   déclaré NON confirmé).
9. C3 : espérance A1 > 0 ET (n(A2) ≥ 30 et espérance A2 > 0).
10. P1 : espérance > 95e centile du placebo temporel.
11. Coûts : espérance > 0 à +0,5 pip ET à +0,6 pip.
12. Concentration : 5 meilleurs jours < 40 % du R total ; plus gros épisode < 40 % ; sans meilleur trimestre > 0 ;
    sans meilleure paire > 0.
13. Sans les chocs isolés : espérance > 0.
14. Sans les jours fériés pré-déclarés : espérance > 0.
15. Test de non-look-ahead réussi.
Un seul échec → Train échoué : validation.json et oos.json = {"skipped": "Train échoué"}, aucune donnée de
validation ni d'OOS consommée.

## Critères validation → OOS (variante retenue, rien n'est ré-optimisé)
1. Espérance > 0 sur Validation A ET sur Validation B (séparément).
2. Espérance groupée (A+B) ≥ +0,03 R.
3. Coûts +0,6 pip : espérance groupée > 0.
4. Vue par jour groupée : borne basse IC 95 % > 0.
5. C1 groupé : écart > 0.
6. 5 meilleurs jours < 40 % du R total groupé.
Tout passe → VALIDATED (passed = true), OOS seulement après oos-gate. Sinon oos.json = skipped.

## Critères OOS : PASS / FAIL / INCONCLUSIVE (lecture unique, sept. 2023 → août 2024)
- PASS : n ≥ 60, espérance > +0,03 R, espérance à +0,6 pip > 0, moyenne par jour > 0, écart C1 > 0.
- FAIL : espérance ≤ 0 OU espérance à +0,6 pip ≤ 0.
- INCONCLUSIVE : tout autre cas (n < 60, ou 0 < espérance ≤ 0,03 R, ou écart C1 ≤ 0 avec espérance positive).

## Tests de robustesse obligatoires (toutes variantes au Train ; variante retenue ensuite, full_report)
- placebo temporel P1 + contrôles C1 (spread normal), C2 (minutes rondes), C3 (artefact A1/A2)
- coûts +0,0 / 0,2 / 0,4 / 0,5 / 0,6 / 1,0 pip
- vue par jour (IC 95 % bootstrap, UTC), une paire par jour, vue par épisode
- concentration : fins de mois, 5 meilleurs jours, plus gros épisode, meilleur trimestre, meilleure paire,
  10 plus gros trades (date, paire, contexte)
- contrôle données (chocs isolés), jours fériés et lundis
