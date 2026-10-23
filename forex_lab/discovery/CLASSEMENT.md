# Strategy Discovery — classement des preuves (généré par score.py, ne pas éditer à la main)

Score sur 21 (GRILLE.md) : ≥ 15 solide, 11-14 moyenne, ≤ 10 faible. Aucun backtest n'a été lancé.

## Candidates retenues

| Rang | ID | Stratégie | Famille | Score | Niveau | Horizon | Paires du projet | Données gratuites |
|---|---|---|---|---|---|---|---|---|
| 1 | D01 | Suivi de tendance / momentum de série temporelle (12 mois) | tendance | 15 (18−3) | solide | mensuel (incompatible ≤ 4 h) | oui, mais preuve sur panier large | oui (Dukascopy journalier) |
| 2 | D02 | Portage (carry) des devises du G10 | portage | 10 (13−3) | faible | mensuel (incompatible ≤ 4 h) | partiel (portage entre EUR, GBP, JPY, USD) | oui (taux publics BCE, Fed, BoE, BoJ) |
| 3 | D07 | Momentum transversal des devises (1 à 12 mois) | momentum | 10 (15−5) | faible | mensuel (incompatible ≤ 4 h) | non (≈ 40 devises) | partiel |
| 4 | D03 | Dollar avant les changements de taux de la Fed (FOMC) | evenement | 9 (9−0) | faible | 2 jours (incompatible ≤ 4 h) | oui (EUR, GBP, JPY dans le panier) | incertain (fed funds futures) |
| 5 | D04 | Vente du dollar les jours d'annonce FOMC | evenement | 9 (9−0) | faible | 1 jour (adaptable en intrajournalier, sortie avant 21:00 UTC) | oui | oui (calendrier FOMC public + Dukascopy) |
| 6 | D05 | Couverture actions avant le fix de Londres de fin de mois | flux | 7 (7−0) | faible | intrajournalier (≤ 4 h avant 16:00 Londres) | oui | oui (Dukascopy + indices actions) |
| 7 | D06 | Stratégie actions → devises autour du fix WM (Sheth-Teeple) | flux | 6 (6−0) | faible | intrajournalier | inconnu | oui |
| 8 | D08 | Dérive après annonce macro (réaction des 15 premières minutes) | evenement | 4 (4−0) | faible | intrajournalier | oui (EURUSD) | oui (calendrier BLS + Dukascopy) |

## Écartées

| ID | Stratégie | Motif |
|---|---|---|
| D09 | Règles techniques simples (moyennes mobiles, filtres) sur le Forex | doublon : F01 MACD Sample, F02 Moving Average, X04 MACD + RSI |
| D10 | Saisonnalité horaire du dollar (fenêtres européennes / américaines) | doublon : F03 Business day, X12 / E005 |
| D11 | Vente du yen après le fix de Tokyo | doublon : V3-H1 Fix de Tokyo |
| D12 | Momentum intrajournalier (première demi-heure → fin de journée) | doublon : V3-H2, X11, E007 |
| D13 | Cassure d'ouverture (range asiatique / Londres) | doublon : V3-H3, V4-H2, X01 |
