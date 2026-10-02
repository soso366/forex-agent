# E001 — protocole (VERROUILLÉ au commit, ne plus modifier)
Auteur : QUANT · cycle 1 · 2026-10-02 · écrit AVANT tout calcul de résultat (aucun R calculé avant ce commit).

## Règle commune (fixe pour toutes les variantes)
Données M1 bid/ask Dukascopy, index UTC = début de minute. mid = (bid_close + ask_close)/2. Fuseau de séance :
Europe/London (DST géré par tz). Paires : EURUSD (E), GBPUSD (G).
- Grille minute : chaque série mid est réindexée sur la grille minute complète puis prolongée (ffill) au plus
  2 minutes ; au-delà = manquant (aucun signal).
- Minute de scan t : barre M1 étiquetée t avec t.minute % 5 == 0, heure locale Londres de t dans [07:00, 16:30],
  lundi–vendredi. Les calculs utilisent la clôture de la barre t (connue à t+1 min) et aucune minute > t.
- rE = ln(midE(t)/midE(t−W)), rG idem ; x = rE − rG ; u = (rE + rG)/2 ; W = fenêtre (15 ou 30 min).
- σx(J), σu(J) : écart-type (ddof=1) des x et u calculés sur des blocs NON chevauchants de W minutes
  (rendement entre les clôtures aux bornes 07:00, 07:00+W, … ≤ 16:30 Londres), sur les **20 jours de séance
  précédents** (J−20…J−1, jour J exclu). Un jour de séance compte s'il possède ≥ 50 % de blocs valides. Moins de
  20 jours précédents disponibles → pas de σ → pas de signal (aucun min_periods réduit). z = x / σx(J).
- Médiane de spread 20 j : par paire, médiane des spreads M1 (ask_close − bid_close) des minutes 07:00–16:30
  Londres des mêmes 20 jours précédents (J exclu). Filtre : spread(t) ≤ 2 × médiane pour E ET G.
- ATR M5 : `research/v4/data.bars(m1,"5min")` + `atr(…,14)` décalé d'une barre (`shift(1)`), lu à l'étiquette t :
  ATR des seules M5 clôturées à t (dernière M5 close = [t−5, t)).
- Déclencheur : |z| ≥ seuil ET |u| ≤ 1,0 σu(J) ET filtre spread.
- Jambe « fautive » : max(|ΔE|/ATR_E, |ΔG|/ATR_G) avec Δ = mid(t) − mid(t−W) en prix. Sens = convergence
  (E fautive : −sign(x) ; G fautive : +sign(x)). Le signal n'est gardé que si ce sens est aussi l'opposé du
  mouvement de la jambe (règle littérale de l'hypothèse) ; sinon ignoré (nombre publié).
- Entrée : ouverture de la M1 t+1 (ask achat / bid vente) ; si la barre t+1 n'existe pas → pas de trade
  (max_gap_min = 1). Stop = 1,5 × ATR M5 de la jambe tradée, depuis le prix d'entrée, jamais élargi. Pas de cible.
- Sortie : la première de (a) stop (testé sur bid_low pour un achat / ask_high pour une vente ; stop prioritaire ;
  si l'ouverture d'une minute est déjà au-delà du stop → sortie à cette ouverture), (b) **sortie anticipée** :
  à la clôture de chaque minute s ≥ t+1 on recalcule z(s) (même W, même σx(J)) ; si |z(s)| ≤ 0,5 → sortie à
  l'OUVERTURE de s+1 (bid achat / ask vente), (c) temps : clôture de la dernière minute de la durée H (même
  convention que `research/v4/sim.py`). Implémentation : `code/e001.py::simulate_trades` (conventions de sim.py
  + sortie anticipée ; sim.py non modifié).
- Une position par paire ; cooldown : pas de nouvelle entrée sur la même paire moins de 30 min après la
  précédente entrée sur cette paire. Les signaux sont pris dans l'ordre chronologique.
- R = PnL / distance de stop ; spread bid/ask réel inclus.

## Variantes (≤ 8, grille fixée ici) — une seule jambe ; |u| ≤ 1 σu, spread ≤ 2×, stop 1,5 ATR, cooldown 30 fixes
| id | seuil abs(z) | W (min) | H sortie (min) |
|---|---|---|---|
| V1 | 2,5 | 15 | 20 |
| V2 | 2,5 | 15 | 30 |
| V3 | 2,5 | 30 | 20 |
| V4 | 2,5 | 30 | 30 |
| V5 | 3,0 | 15 | 20 |
| V6 | 3,0 | 15 | 30 |
| V7 | 3,0 | 30 | 20 |
| V8 | 3,0 | 30 | 30 |
Variante « deux jambes à demi-risque » ABANDONNÉE (même pari EURGBP compté deux fois, deux spreads ; grille ≤ 8).
Voisins d'une variante = les 3 variantes qui diffèrent d'UNE dimension (seuil, W ou H).
Toutes les variantes sont rapportées (stats, coûts, vue par jour, contrôles).

## Sélection (Train uniquement)
- Éligibilité : n ≥ 100 trades sur le Train.
- Score prudent(v) = min(espérance de v, espérance de chacun de ses 3 voisins). Variante sélectionnée = score
  prudent maximal parmi les éligibles (égalité → plus petit id). Si aucune n'est éligible : la meilleure par score
  prudent est rapportée, mais le critère Train 1 échoue.

## Données
- Train : 2025-09-01 → 2026-02-28 (data/m1_2025). Signaux seulement après 20 jours de séance d'historique.
- Validation A : 2026-03-01 → 2026-08-31 (data/m1). L'historique 20 j (σ, médiane de spread) peut utiliser
  février 2026 (passé) ; aucun trade hors fenêtre.
- Validation B : 2024-09-01 → 2025-08-31 (data/m1_locked_2024 + data/m1_locked). Contaminée pour H3 mais jamais
  utilisée pour E001. Premiers 20 jours de séance = historique seulement.
- OOS vierge : 2023-09-01 → 2024-08-31 (en téléchargement, memory/DATA_REQUESTS.md). Jamais ouvert avant que la
  validation soit passée ; lu UNE fois.
- La validation ne porte que sur la variante sélectionnée au Train.

## Simulation
Voir « Règle commune » : entrée t+1 M1, coûts bid/ask réels, sortie ≤ 30 min, une position par paire.
Coûts additionnels : 0 / 0,2 / 0,4 / 0,6 / 1,0 pip par trade (`robustness.costs`, colonne `stop` = distance de stop
en prix).

## Contrôles et placebos (définitions fixées)
- C1 « même mouvement sans divergence » (décisif) : mêmes minutes de scan, mêmes heures, même filtre spread, même W,
  |z| < 1 (pas de condition sur u : l'autre paire a suivi), jambe = celle au plus grand |Δ|/ATR, sens = opposé à
  son mouvement, même stop, sortie = stop ou temps H (la sortie anticipée sur z n'a pas de sens ici), sans cooldown
  (estimateur de l'espérance conditionnelle). Appariement : pour chaque trade E001, les ≤ 5 candidats de contrôle de
  la MÊME paire dont le mouvement |Δ|/ATR est dans ±10 % du sien (les 5 plus proches en mouvement) ;
  contrôle_i = moyenne de leurs R. Différence d_i = R_i − contrôle_i (trades sans appariement exclus de d, nombre
  publié). IC 95 % de la moyenne de d par bootstrap de JOURS (Europe/London, 10 000 tirages, graine 11).
  Diagnostic : même calcul avec E001 sans sortie anticipée.
- C2 « jambe inverse » : mêmes signaux, trade de l'AUTRE jambe dans le sens de la convergence (stop 1,5 ATR de
  cette jambe, même sortie que E001, cooldown appliqué au flux C2).
- P1 placebo décalé 60 min : z, u, spread et choix de jambe évalués à t−60 (σ du jour J inchangé), entrée t+1,
  même stop et mêmes sorties (sortie anticipée sur z(s) courant), même cooldown.
- P2 sens aléatoire : mêmes entrées que E001, chaque trade simulé dans les deux sens, 1000 tirages de sens
  aléatoires (graine 7) ; on compare l'espérance E001 au 95e centile.
- Jours de nouvelles (diagnostic UNIQUEMENT, aucun filtre) : NFP = premier vendredi du mois ; dates BCE et BoE
  (liste fixe dans `code/e001.py::NEWS_DAYS`, calendriers publics connus) ; CPI UK et CPI zone euro NON disponibles
  hors ligne → non inclus (limite déclarée). Résultat avec / sans ces jours.
- Test de non-look-ahead : `code/test_lookahead.py` (perturbation des prix à partir du jour J → σx(J), σu(J),
  médiane de spread(J) et ATR aux minutes < J inchangés) ; exécuté par `run.py train`, résultat dans train.json.

## Critères Train → validation (tous requis, sur la variante sélectionnée)
1. n ≥ 100, espérance > +0,05 R, t ≥ 2 (par trade).
2. Vue par jour (Europe/London) : borne basse de l'IC 95 % bootstrap > 0.
3. PF ≥ 1,10.
4. Espérance > 0 après retrait des 5 meilleurs trades.
5. Au moins un voisin d'espérance > 0.
6. C1 : moyenne de d ≥ +0,05 R ET borne basse IC 95 % (jours) de d > 0.
7. C2 : espérance jambe fautive > espérance jambe inverse.
8. P1 : |espérance| < 0,03 R. P2 : espérance E001 > 95e centile des sens aléatoires.
9. Coûts +0,6 pip : espérance > 0.
10. Concentration : 5 meilleurs jours < 40 % du R total ; sans le meilleur trimestre > 0 ; sans la meilleure paire > 0.
Un seul échec → arrêt (validation.json et oos.json = skipped).

## Critères validation → OOS (variante sélectionnée, rien n'est ré-optimisé)
1. Espérance > 0 sur Validation A ET sur Validation B (séparément).
2. Espérance groupée (A+B) ≥ +0,03 R.
3. Coûts +0,6 pip : espérance groupée > 0.
4. Vue par jour groupée : borne basse IC 95 % > 0.
5. C1 groupé : moyenne de d > 0.
6. 5 meilleurs jours < 40 % du R total groupé.
Tout passe → VALIDATED, OOS en attente des données (blocked_by). Sinon oos.json = skipped.

## Critères OOS : PASS / FAIL / INCONCLUSIVE (lecture unique, sept. 2023 → août 2024)
- PASS : n ≥ 60, espérance > +0,03 R, espérance à +0,6 pip > 0, moyenne par jour > 0, C1 d moyen > 0.
- FAIL : espérance ≤ 0 OU espérance à +0,6 pip ≤ 0.
- INCONCLUSIVE : tout autre cas (n < 60, ou 0 < espérance ≤ 0,03 R, ou C1 ≤ 0 avec espérance positive).

## Tests de robustesse obligatoires (toutes variantes au Train ; variante sélectionnée ensuite, full_report)
- placebo (P1 décalé 60 min, P2 sens aléatoire) + contrôles C1, C2
- coûts +0,0 / 0,2 / 0,4 / 0,6 / 1,0 pip
- vue par jour (IC 95 % bootstrap, tz Europe/London), une paire par jour
- concentration : fins de mois, 5 meilleurs jours, meilleur trimestre, meilleure paire ; répartition EURUSD/GBPUSD
- jours de nouvelles (diagnostic) ; nombre de signaux ignorés (sens incohérent)
