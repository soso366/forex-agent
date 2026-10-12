# E006 — protocole (VERROUILLÉ au commit, ne plus modifier)
Auteur : QUANT · Code : `code/e006.py`, `code/run.py`, `code/test_synthetic.py` (test synthétique réussi avant verrouillage)

## Définitions (toutes fixées avant le run)
- Jour = date UTC, lundi à vendredi. Fenêtre principale a=00:00, b=07:00 UTC (fixe, pas de DST).
- D = mid_open(M1 de b) − mid_open(M1 de a) (mid = (bid+ask)/2 ; tolérance 2 min si la minute manque). Connu à b.
- ATR = ATR M5(14) (Wilder/ewm de data.atr) de la dernière barre M5 TERMINÉE à b (barre 06:55-07:00). Aucune barre ≥ b.
- z = D / (ATR × √84), 84 = nombre de barres M5 de 7 h. Aucune donnée postérieure à b dans z, direction ou filtre.
- Filtre : pas de trade si range mid(00:00-07:00) < 0,5 × (range journalier mid moyen des 20 derniers jours UTC COMPLETS
  précédents, jour courant exclu ; ≥ 10 jours requis). « ATR journalier » = ce range moyen high−low des 20 jours précédents.
- Entrée : sens opposé à D (fade), à l'open de la M1 de 07:05 UTC (ask si achat, bid si vente, spread réel de la barre).
  Interdit : close M5 de 07:05. Un trade par paire et par jour.
- R : 1 R = distance de stop = 3 × ATR M5 (à b), mesurée depuis le prix d'entrée. Spread de l'aller-retour inclus
  (achat ask / sortie bid). Stop testé sur bid_low/ask_high M1 ; stop et sortie temps même minute -> stop.
  Sortie : close M1 à 07:05 + hold (240 min -> 11:05), toujours < 21:00 UTC (assertion dans le code). Part des sorties
  par stop rapportée.
- Paires : critères sur EURUSD+GBPUSD (même sens de pari USD ; la vue par jour moyenne les deux paires). USDJPY à part (V6).
- DST : jours « UTC+1 » = Europe/London en heure d'été à 07:00 UTC ; « UTC+0 » sinon. Rapportés séparément (Train : surtout
  UTC+0 ; Validation : surtout UTC+1) ; aucun critère, mais lu par le Critic.
- Retouche du range (diagnostics postérieurs à l'entrée, jamais une règle) : `sweep` = le mid dépasse l'extrême du range 00-07
  du côté de D avant la sortie ; `reentry` = le mid touche le milieu du range 00-07 avant la sortie.

## Variantes (6 ≤ 8, aucune ne remplace la règle principale)
| id | z min | hold | condition | paires |
|---|---|---|---|---|
| V1 RÈGLE PRINCIPALE | 1,0 | 240 min | – | EURUSD+GBPUSD |
| V2 | 1,5 | 240 | – | EURUSD+GBPUSD |
| V3 | 1,0 | 120 | – | EURUSD+GBPUSD |
| V4 | 1,5 | 120 | – | EURUSD+GBPUSD |
| V5 | 1,0 | 240 | spread moyen 00-07 > médiane des 20 jours précédents | EURUSD+GBPUSD |
| V6 | 1,0 | 240 | – | USDJPY seul |
Tests (pas des variantes, rapportés tels quels) : V7 continuation (V1 à contre-sens) ; placebos de fenêtre ; voisins
z ∈ {0,8 ; 1,0 ; 1,25 ; 1,5} × hold {120 ; 180 ; 240}. Aucun n'est sélectionné.

## Données
- Train : sept. 2025 → fév. 2026 (`data/m1_2025`) · Validation : mars → août 2026 (`data/m1`, avec `m1_2025` chargé
  UNIQUEMENT pour l'échauffement 20 jours) · OOS vierge : sept. 2023 → août 2024, NON lu, seulement si `oos-gate E006` = OUVERT.

## Compte AVANT run
- Estimation a priori : ~125 jours × 2 paires = ~250 paires-jours, ~30 % à |z| ≥ 1 puis filtre range -> ~60-75 trades V1.
- `run.py count` calcule les signaux (V1..V6, placebos, voisins) SANS aucun R -> `results/signal_counts.json`, commité avant `train`
  (le train refuse sinon). Si V1 < **150** trades au Train : conclusion « ÉCHANTILLON INSUFFISANT » (passed=false), le seuil de z
  n'est PAS abaissé, aucune variante n'est promue ; les statistiques R sont alors descriptives seulement.

## Simulation
Moteur `research/v4/sim.py` (M1 bid/ask, `max_gap_min=1`), pas de cible, glissement à l'ouverture si gap au-delà du stop.

## Critères Train (tous requis ; V1, EURUSD+GBPUSD, coûts réels inclus)
1. n ≥ 150 (compté avant) ; moyenne ≥ +0,05 R par trade ; t-stat par JOUR (valeur du jour = moyenne des R des paires) ≥ 2,0.
2. IC 95 % bootstrap par jour (10 000 tirages, graine 11) : borne basse > 0.
3. Placebos : moyenne V1 > moyenne de CHAQUE placebo de fenêtre (07→12 entrée 12:05 ; 12→16 entrée 16:05 ; 09→13 entrée 13:05 ;
   00→04 entrée 04:05 ; même z ≥ 1, même hold 240, même filtre mis à l'échelle heures/7) ET placebo permuté (signe de D mélangé
   entre jours par paire, 1000 permutations, graine 7) p ≤ 0,05.
4. Gradient : moyenne(z ≥ 1,5) ≥ moyenne(1,0 ≤ |z| < 1,5), avec ≥ 20 trades dans z ≥ 1,5 (sinon non évaluable = échec).
5. Coûts : à +0,5 pip (aller-retour) moyenne ≥ 0 ; sans les 5 meilleurs jours moyenne > 0 ; ≥ 4 mois sur 6 positifs (somme de R/mois).
6. Test sweep (anti-doublon V4-H1) : les trades sans `sweep` ont n > 0 et moyenne > 0. Sinon verdict « doublon V4-H1 ».
Échec d'un critère -> REJECT immédiat ; `validation.json` et `oos.json` = `{"skipped": "Train échoué"}`.

## Critères Validation (mars → août 2026, V1 seulement, mêmes règles)
Même signe (moyenne > 0), moyenne ≥ 50 % de celle du Train, moyenne ≥ 0 à +0,5 pip, trades sans `sweep` de moyenne > 0.
Sinon REJECT. Rapportés sans critère : DST, USDJPY, V2..V7, placebos, concentration.

## Critères OOS (sept. 2023 → août 2024, lecture unique, seulement si oos-gate = OUVERT)
PASS : n ≥ 100, moyenne ≥ +0,03 R, IC 95 % par jour borne basse > 0, moyenne ≥ 0 à +0,5 pip, no-sweep > 0.
INCONCLUSIVE : n < 100 (non sauvé). FAIL sinon.

## Tests de robustesse obligatoires (tous dans results/*.json)
- placebo temporel (4 fenêtres) + permuté (1000) + continuation (V7) ; coûts +0,0 / 0,2 / 0,5 / 1,0 pip
- vue par jour (IC 95 % bootstrap), une paire par jour (`one_per_day`), sans les 5 meilleurs jours
- concentration : par paire, mois, trimestres, jour de semaine (lundi isolé), NFP (premier vendredi ; FOMC non daté : non testé)
- scission DST UTC+0 / UTC+1 ; sweep / ré-entrée ; USDJPY séparé ; gradient et voisins (diagnostics)
