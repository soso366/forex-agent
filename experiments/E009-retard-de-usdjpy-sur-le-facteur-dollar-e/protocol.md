# E009 - protocole (VERROUILLE au commit, ne plus modifier)
Auteur : QUANT · Code : `code/e009.py`, `code/run.py`, `code/test_synthetic.py` (tests synthetiques reussis avant verrouillage :
z(t)/ATR independants des prix posteriores a la cloture de la barre, sigma strictement passe, entree apres cloture, <= 2 trades/jour,
cooldown, DST, sortie <= 17:00 Londres et < 21:00 UTC, pipeline complet sur donnees synthetiques).

## Definitions (fixees avant tout R)
- Fuseau Europe/London (zoneinfo). mid = (bid+ask)/2. Barres M5 label gauche [L, L+5) ; le signal est evalue a la CLOTURE tc = L+5 min,
  entree a l'open M1 de tc (ask si achat, bid si vente). Rendement log 30 min = log c[L] - log c[L-30 min] (6 barres, NaN si trou).
- usd = -(r_EURUSD + r_GBPUSD)/2 ; g = r_USDJPY - usd ; z = g / sigma, sigma = ecart-type des 2000 observations de g PRECEDENTES
  (`rolling(2000).std().shift(1)`). Les 2000 premieres barres du jeu de donnees (~7 jours ouvres de sept. 2025) n'ont pas de z : aucun
  signal. Aucune donnee de l'OOS 2024-25 ni 2023-24 n'est chargee (echauffement = debut du Train).
- Signal : |z| >= 2,0, tc entre 08:00 et 15:00 Londres (15:00 exclu). z>0 -> VENTE USDJPY, z<0 -> ACHAT. Selection chronologique :
  cooldown 2 h (ou duree de detention si plus longue), max 2 trades/jour (jour Londres), une seule position.
- Sortie : close M1 a +2 h (variante A) ou 17:00 Londres si plus tot (et jamais apres 20:55 UTC). Stop catastrophe 3 x ATR M5(14) (derniere
  barre terminee a tc) ; 1 R = 3 ATR ; pas de TP. Stop et temps dans la meme minute -> stop. Moteur `research/v4/sim.py` (max_gap_min=1).
- Le seuil 2,0 vient du comptage du RESEARCHER (sans R). Aucun reglage sur R.

## Variantes (4 <= 8 ; seule A est jugee)
| id | seuil | hold |
|---|---|---|
| A REGLE PRINCIPALE | 2,0 | 120 |
| B | 2,0 | 60 |
| C | 2,0 | 240 (plafond) |
| D | 2,5 | 120 |
B, C, D rapportees seulement, ne peuvent pas sauver A.

## Donnees
Train : sept. 2025 -> fev. 2026 = `data/m1_2025` UNIQUEMENT. Validation : mars -> aout 2026 (`data/m1` + `m1_2025` pour l'echauffement de sigma).
OOS vierge 2023-24 : NON lu, seulement si `oos-gate E009` = OUVERT, un seul passage.

## Compte AVANT run
`run.py count` -> `results/signal_counts.json` (A, B, C, D, placebos, repartition horaire), commite avant `train` (le train refuse sinon).
Si A < **150** : INCONCLUSIVE (`passed=false`, `inconclusive=true`), seuil NON abaisse, aucune variante promue.

## Criteres Train (tous requis ; A, couts bid/ask reels, R)
1. n >= 150 ; moyenne >= +0,05 R ; t-stat par JOUR >= 2,0 (valeur du jour = moyenne des R du jour).
2. IC 95 % bootstrap par jour (10 000 tirages, graine 11) : borne basse > 0.
3. Placebos : (a) « USDJPY seul » (z calcule sur r_USDJPY seul, memes regles) : moyenne A - moyenne placebo > 0,03 R ; (b) facteur permute
   (usd d'un autre jour ouvre, meme tranche de 5 min UTC, 500 permutations, graine 5, z recalcule avec la meme procedure) : moyenne A >= 95e
   centile ; (c) horaires : memes regles avec fenetre de signal et heure limite (17:00) decalees de s heures, s dans +-1..6 (12 placebos, hold
   plafonne a 20:55 UTC, trade ignore si < 30 min) : moyenne de A strictement superieure a celle de CHAQUE placebo (rang 1/13). Sens inverse
   (continuation) : rapporte, informatif.
4. Couts : +0,5 pip (aller-retour) moyenne >= 0 (aussi +0,2 et +1 rapportes).
5. Concentration : sans les 5 meilleurs jours moyenne > 0 ; >= 4 mois sur 6 positifs (somme de R par mois d'entree) ; aucun mois > 25 % du total.
6. Annonces : trades dont [entree-30 min ; sortie] contient 08:30 New York (12:30 ou 13:30 UTC, calcule via America/New_York) vs les autres ;
   moyenne HORS annonces > 0 requise.
7. Derive : moyenne ajustee (R - sens x R moyen d'un achat a chaque barre M5 de la fenetre, par heure Londres, hold 2 h, hors spread) >= 0,03 R.
Rapports sans critere : achats vs ventes, par heure Londres (si une heure ou 13:00-14:00 > 35 % des trades : recalcul avec sigma conditionnel
a l'heure, diagnostic), semaines NFP, queue gauche, stop en pips et cout en R, spread d'entree en pips, une paire/jour (identique : une seule
paire), `rb.full_report`, variantes B/C/D.
Echec d'un critere 1-7 -> REJECT immediat ; `validation.json` et `oos.json` = `{"skipped": "Train echoue"}`.

## Criteres Validation (mars -> aout 2026, A seulement, memes regles)
Moyenne > 0 de meme signe, >= 50 % de la moyenne Train, moyenne >= 0 a +0,5 pip, sens inverse < 0 (rapporte aussi IC 95 % jour).
OOS (si oos-gate OUVERT) : memes regles, lu une seule fois.
