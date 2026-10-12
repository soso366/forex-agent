# E005 — audit Train (CRITIC)
**Verdict : REJECT confirmé.** Aucune donnée Validation/OOS lue.

- Fidélité au protocole : code = protocole (8 variantes, A seule jugée, 10 placebos, 5000 permutations, R = pips/ATR, stop 3 ATR). Protocole + code commités (d18fffc) avant les résultats (7fe9d72). Compte 372 = 124 jours x 3 paires conforme.
- Fuite : ATR décalé de +5 min (disponible en fin de barre), entrée à l'open M1 de l'heure locale Londres (zoneinfo, DST correct). Seule nuance : l'exclusion des jours à < 90 % de minutes regarde la fenêtre future (effet négligeable, 372/372 signaux conservés).
- Résultat : moyenne +0,076 R / +0,38 pip mais t par jour = 0,22 ; IC 95 % jour [-1,65 ; +2,34] ; rang placebo 3/11 ; permutation p = 0,42 ; à +0,5 pip moyenne -0,045 R ; 8 critères sur 14 échouent. Le signe positif est du bruit (les coûts réels l'effacent).
- Piège à refuser : la contrepartie B (inverse, 14-18 h) affiche +0,40 R, la variante A_5h +0,19 R. Non jugées, 8 variantes (seuil t = 2,5) : les promouvoir serait une sélection après coup (règle 7). Pas de résurrection sans nouvelle hypothèse + nouvel OOS.
- Pas de bug expliquant l'échec ; REJECT justifié, Validation/OOS correctement non consommés.
