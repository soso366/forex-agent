# E006 — audit Train (CRITIC)
**Verdict : REJECT (échantillon insuffisant), conséquence fidèle du protocole, pas un bug.** Aucune donnée Validation/OOS lue.

- Code = protocole : D, z = D/(ATR x sqrt(84)), ATR de la barre finie à 07:00 (label b-5 min), entrée open M1 07:05, historique du range = jours < k uniquement, filtre `rng >= 0,5 x moyenne(20 j)`. Pas de look-ahead ; sweep/réentrée = diagnostics post-entrée uniquement. Protocole+code commités (cdf842d), comptes (a4199f4) avant R (6488603).
- Reproduction (Train, EURUSD+GBPUSD, 237 paires-jours) : le filtre laisse passer 23 % / 15 % des jours ; |z| >= 1 : 7 % / 8,5 % (écart-type de z = 0,57-0,60) ; ensemble : 11 trades. SANS filtre : 18 trades seulement : le goulot est le seuil z >= 1 (estimation a priori « 30 % » fausse), pas le filtre. Le filtre est mal calibré (fenêtre Asie 7 h comparée à 0,5 x range de 24 h) : défaut de conception du protocole, pas du code.
- Seuil n >= 150 écrit d'avance, non abaissé : correct. Les R (11 trades, 72 % de stops, t jour 0,29, IC [-0,83 ; +1,75]) sont descriptifs ; critère no_sweep échoue (n=2, -1 R) : probable doublon V4-H1.
- REJECT justifié : même à z >= 0,8 (19 trades) le test est infaisable à 150. Ne pas relâcher z/filtre dans E006 (règle 7) ; une idée voisine = nouvelle hypothèse, seuils calibrés sur la distribution de z AVANT tout R.
