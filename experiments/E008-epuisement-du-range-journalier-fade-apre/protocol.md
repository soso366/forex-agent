# E008 - protocole (VERROUILLE au commit, ne plus modifier)
Auteur : QUANT · Code : `code/e008.py`, `code/run.py`, `code/test_synthetic.py` (tests synthetiques reussis avant verrouillage :
pas de look-ahead, ADR20 sans jour courant, DST 26/10/2025, sortie 17:00 Londres).

## Definitions (fixees avant tout R)
- Jour = date calendaire Europe/London (zoneinfo, DST gere), lundi a vendredi. mid = (bid+ask)/2. Paires : EURUSD, GBPUSD, USDJPY.
- ADR20 = moyenne des (high-low) mid des 20 derniers jours Londres valides (>= 1000 minutes de donnees) STRICTEMENT anterieurs
  au jour courant (le jour courant n'est jamais lu) ; >= 10 jours requis (sinon pas de trade).
- M = (mid_open(M1 de 13:00 Londres) - mid_open(M1 de 00:00 Londres)) / ADR20. L'open de la barre d'entree est connu a l'instant
  d'entree (pas de close). Tolerance 2 min si la minute manque (comme E006).
- Signal : |M| >= 0,30 -> trade CONTRE le sens de M (fade). Entree a l'open M1 de 13:00 Londres (ask si achat, bid si vente).
  Sortie : close de la derniere M1 avant 17:00 Londres (hold 240 min). Stop catastrophe 3 x ATR M5(14) (derniere barre M5 terminee
  a 13:00, label 12:55) ; 1 R = 3 ATR ; pas de TP. Un trade par paire par jour. Sortie toujours < 21:00 UTC (assertion).
  Stop et sortie temps dans la meme minute -> stop. Moteur `research/v4/sim.py` (max_gap_min=1).
- Pas de repechage : le seuil 0,30 vient du comptage (sans R) fait par le RESEARCHER ; aucun reglage sur R.

## Variantes (4 <= 8, rapportees ; seule A est jugee)
| id | signal/entree | seuil | hold |
|---|---|---|---|
| A REGLE PRINCIPALE | 13:00 | 0,30 | 240 |
| B | 13:00 | 0,40 | 240 (rapportee seulement ; < 150 trades attendu) |
| C | 13:00 | 0,30 | 120 (sortie 15:00) |
| D | 12:00 (M calcule a 12:00) | 0,30 | 240 (sortie 16:00) |
B, C, D ne remplacent jamais A et ne peuvent pas sauver un echec de A.

## Donnees
Train : sept. 2025 -> fev. 2026 = `data/m1_2025` UNIQUEMENT. Les ~10 premiers jours (ADR20 indisponible) sont exclus.
Validation : mars -> aout 2026 (`data/m1`, avec `m1_2025` charge UNIQUEMENT pour l'echauffement ADR). OOS vierge 2023-24 : NON lu,
seulement si `oos-gate E008` = OUVERT. Un seul passage OOS.

## Compte AVANT run
`run.py count` calcule les signaux (A, B, C, D, placebos horaires) SANS aucun R -> `results/signal_counts.json`, commite avant
`train` (le train refuse sinon). Si A < **150** trades au Train : verdict INCONCLUSIVE (`passed=false`, `inconclusive=true`), le seuil
n'est PAS abaisse, aucune variante n'est promue ; les R sont alors descriptifs seulement.

## Criteres Train (tous requis ; A, 3 paires, couts bid/ask reels)
1. n >= 150 (compte avant) ; moyenne >= +0,05 R/trade ; t-stat par JOUR >= 2,0 (valeur du jour = moyenne des R des paires tradees ce
   jour ; nombre de jours independants rapporte).
2. IC 95 % bootstrap par jour (10 000 tirages, graine 11) : borne basse > 0.
3. Placebos : (a) horaire : meme regle (M calcule a 13:00+s, entree a 13:00+s, hold 240 plafonne a 20:55 UTC), s dans +-1..6 h
   (12 placebos) ; la moyenne de A doit etre strictement superieure a celle de CHAQUE placebo (rang 1 sur 13 = top 10 %) ;
   (b) jours aleatoires : par paire, memes nombres de jours tires au hasard parmi les jours valides, meme direction (contre M),
   sans seuil, 1000 tirages, graine 7 ; p = part des tirages >= moyenne reelle <= 0,05 ; (c) sens inverse (continuation, memes
   trades a contre-sens) : moyenne < 0.
4. Couts : a +0,5 pip (aller-retour) moyenne >= 0 (rapportes aussi +0,2 et +1).
5. Concentration : sans les 5 meilleurs jours moyenne > 0 ; >= 2 paires sur 3 de moyenne > 0 ; >= 4 mois sur 6 positifs (somme de R/mois).
Rapports sans critere : queue gauche (pire jour, pire trade, 5e percentile, part de stops), DST (heure d'ete / d'hiver
separees), jours d'annonce US (rapport, pas filtre), correlation des P&L journaliers avec E007 (si ses trades existent),
variantes B/C/D, une paire par jour (robustness.one_per_day), `rb.full_report`.
Echec d'un critere 1-5 -> REJECT immediat ; `validation.json` et `oos.json` = `{"skipped": "Train echoue"}`.

## Criteres Validation (mars -> aout 2026, A seulement, memes regles)
Moyenne > 0 de meme signe, >= 50 % de la moyenne Train, moyenne >= 0 a +0,5 pip, IC 95 % jour rapporte, sens inverse < 0.
OOS (si oos-gate OUVERT) : memes regles, lu une seule fois.
