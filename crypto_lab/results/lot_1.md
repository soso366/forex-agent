# lot_1 — résultats (frais 0,10 %/ordre + glissement 0,05 %/ordre)

| Stratégie | Plafond | Trades | Net USDT | Gain moyen % | Taux de gain | PF | t | DD max | P1 | P2 | P3 | Stress | Audit biais | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CombinedBinHAndClucV5 | origine | 293 | 65.02 | 0.444 | 76.5 % | 1.64 | 3.41 | 11.07 | 54.26 | -1.56 | 12.32 | — | aucun biais détecté | **FRAGILE** moins de 100 trades sur un bloc; perdante sur au moins un bloc; gain concentré (>50 % sur une paire ou un mois) |
| CombinedBinHAndClucV5 | 30 min | 343 | 68.28 | 0.398 | 68.2 % | 1.82 | 4.28 | 15.88 | 41.53 | 21.79 | 4.96 | — | aucun biais détecté | **FRAGILE** moins de 100 trades sur un bloc |
| CombinedBinHAndClucV5 | 45 min | 331 | 79.57 | 0.481 | 69.8 % | 2.03 | 5.4 | 8.63 | 43.94 | 21.34 | 14.29 | — | aucun biais détecté | **FRAGILE** moins de 100 trades sur un bloc |
| CombinedBinHAndClucV5 | 60 min | 324 | 75.82 | 0.468 | 71.0 % | 1.96 | 4.95 | 8.46 | 38.24 | 21.23 | 16.35 | — | aucun biais détecté | **FRAGILE** moins de 100 trades sur un bloc |
| CombinedBinHAndClucV6H | — | — | — | — | — | — | — | — | — | — | — | — | — | ERREUR :     nb = self.coerce_to_target_dtype(value, raise_on_upcast=True) /          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ /   File "/opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/s |
| CombinedBinHAndClucV8 | origine | 155 | 23.91 | 0.309 | 71.6 % | 1.58 | 2.31 | 6.52 | 8.94 | 17.43 | -2.47 | — | aucun biais détecté | **FRAGILE** moins de 100 trades sur un bloc; perdante sur au moins un bloc; gain concentré (>50 % sur une paire ou un mois) |
| CombinedBinHAndClucV8 | 30 min | 171 | 1.32 | 0.015 | 53.8 % | 1.04 | 0.17 | 7.95 | 0.56 | 4.53 | -3.77 | — | aucun biais détecté | **FRAGILE** moins de 100 trades sur un bloc; perdante sur au moins un bloc; profit factor < 1,15; t < 2 (pas distinguable du hasard); gain concentré (>50 % sur une paire ou un mois) |
| CombinedBinHAndClucV8 | 45 min | 163 | 7.1 | 0.087 | 56.4 % | 1.2 | 0.79 | 9.31 | 0.14 | 7.59 | -0.63 | — | aucun biais détecté | **FRAGILE** moins de 100 trades sur un bloc; perdante sur au moins un bloc; t < 2 (pas distinguable du hasard); gain concentré (>50 % sur une paire ou un mois) |
| CombinedBinHAndClucV8 | 60 min | 160 | 6.61 | 0.083 | 60.0 % | 1.18 | 0.77 | 8.76 | 0.58 | 7.24 | -1.21 | — | aucun biais détecté | **FRAGILE** moins de 100 trades sur un bloc; perdante sur au moins un bloc; t < 2 (pas distinguable du hasard); gain concentré (>50 % sur une paire ou un mois) |
