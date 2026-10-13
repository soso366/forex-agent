# E007 — protocole (VERROUILLÉ au commit, ne plus modifier)
Auteur : QUANT · cycle 6 · Code : code/e007.py, code/run.py

## Variantes (4 ≤ 8, grille fixée ici). SEULE la variante A décide ; B, C, D sont descriptives et ne peuvent pas sauver A.
- A : S = mid(clôture M1 de 12:59) − mid(clôture M1 de 07:59) (heure Europe/London, zoneinfo). Sens = signe(S). Entrée open M1 13:00
  (ask si achat, bid si vente), sortie close M1 de 16:59 (4 h exactes, hold=240 min). Aucun filtre de taille.
- B : A filtré par |S| ≥ médiane de |S| de la MÊME paire sur les 20 jours précédents seulement (sans look-ahead ; jours sans 20 antécédents ignorés).
- C : A avec sortie à 15:00 (hold=120).  D : signal 07:00→13:00 (S = mid(12:59) − mid(06:59)), même exécution que A.
- « ADR20 » est RETIRÉ (non défini dans la règle, non utilisé).

## Données
- Train : sept. 2025 → fév. 2026 = `data/m1_2025` UNIQUEMENT (jours ouvrés 2025-09-02 → 2026-02-27 ; exclus 24, 25, 26, 31 déc., 1er janv.).
- Validation : mars → août 2026 = `data/m1`. Lue seulement si train.json passed=true.
- OOS verrouillé : sept. 2023 → août 2024 (vierge), seulement si `oos-gate E007` = OUVERT. Jamais lu à ce stade.

## Simulation (correction du Critic : stop/R cohérents avec 4 h)
- Moteur `research/v4/sim.py` (bid/ask M1 réels, stop et temps ; stop = perte exacte ou ouverture au-delà). Une position par paire et par jour.
- Unité de R = stop catastrophe = 3 × ATR H1(14) (barres H1 UTC complètes, disponibles à l'entrée), pas de TP. R = pips nets / (3 ATR H1).
  Le stop est large (≈ 25–30 pips) et rapporté (part de sorties « stop »). Pips nets également rapportés.
- Sortie au temps à 4 h max, toujours avant 21:00 UTC (13:00→17:00 Londres = 12:00–16:00 UTC ou 13:00–17:00 UTC). Un trade dont la sortie dépasserait 21:00 UTC est ignoré.
- Jour ignoré si moins de 90 % des minutes de la fenêtre de trade, ou pas de cotation à ≤ 5 min des instants de signal.

## Critères Train (variante A, poolée 3 paires, tous requis — un échec = REJECT immédiat)
1. n ≥ 300 trades ; moyenne ≥ +0,05 R ; t-stat clusterisé par jour (somme R quotidienne) ≥ 2,0.
2. IC 95 % bootstrap par jour (rb.day_view) : borne basse > 0.
3. Placebo horaire : même règle (signal 5 h avant l'entrée, trade 4 h) décalée de k = ±1..8 h (k≠0, sortie ≤ 21:00 UTC, jour même) ; moyenne R
   du vrai horaire au rang ≤ ceil(10 % du nombre total de fenêtres, vrai inclus) ; ET le sens inversé (fade) a une moyenne < 0.
4. Coûts +0,5 pip aller-retour : moyenne ≥ 0.
5. Sans les 5 meilleurs jours : moyenne > 0 ; ≥ 2 paires sur 3 de moyenne > 0 ; ≥ 4 mois civils sur 6 de moyenne > 0.
6. Test par signe USD : sous-ensembles « signal = USD long » et « signal = USD court » (EURUSD/GBPUSD : sens = −USD ; USDJPY : sens = USD) ont chacun moyenne ≥ 0.
7. Sans jours NFP (1er vendredi du mois) ni FOMC (liste de E005) : moyenne > 0. (CPI : dates non fiables → non exclus, limite écrite.)
8. Sensibilité DST : sans les jours 2025-10-27 → 2025-10-31 (décalage Londres/New York) : moyenne > 0.
9. Contrôle E005 : moyenne de A > max(moyenne 13:00→17:00 USD long fixe, moyenne 13:00→17:00 USD court fixe), mêmes règles d'exécution
   (le signal doit apporter plus qu'un biais horaire constant).
Rapportés (non bloquants) : variantes B, C, D ; une paire par jour ; concentration ; trimestres ; part de stops ; pips.

## Critères validation → OOS (variante A inchangée, tous requis)
n ≥ 300 ; moyenne > 0 et ≥ 50 % de la moyenne Train ; coûts +0,5 pip moyenne ≥ 0 ; ≥ 2 paires sur 3 > 0 ; IC 95 % par jour borne basse > −0,02 R/jour ;
USD long et USD court sans signe opposé fort (chacun ≥ −0,02). Si échec : REJECT, OOS non lu.

## Critères OOS : PASS / FAIL / INCONCLUSIVE (lu UNE fois)
PASS : moyenne ≥ +0,05 R ; IC 95 % par jour borne basse > 0 ; ≥ 2 paires > 0 ; coûts +0,5 pip ≥ 0 ; placebo horaire rang ≤ 10 % ; USD long et court ≥ 0.
FAIL : moyenne ≤ 0 ou IC 95 % entièrement < 0. Sinon INCONCLUSIVE (= non validé).

## Tests de robustesse obligatoires
placebo horaire (± 1..8 h) · sens inversé · coûts +0,0/0,2/0,4/0,6/1,0 pip (rb.costs) · vue par jour IC 95 % · une paire par jour ·
concentration (fins de mois, 5 meilleurs jours, meilleur trimestre, meilleure paire) · USD long/court · hors NFP/FOMC · hors semaines DST · contrôle E005.
Aucun micro-réglage après Train. Hypothèse rejetée = archivée.
