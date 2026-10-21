# Lot 1 — résultats (frais 0,10 %/ordre + glissement 0,05 %/ordre)

| Stratégie | Plafond | Trades | Net USDT | Gain moyen % | Taux de gain | PF | t | DD max | P1 | P2 | P3 | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CombinedBinHAndClucV5 | origine | 293 | 65.02 | 0.444 | 76.5 % | 1.64 | 3.41 | 11.07 | 54.26 | -1.56 | 12.32 | **FRAGILE** moins de 100 trades sur un bloc; perdante sur au moins un bloc; gain concentré (>50 % sur une paire ou un mois) |
| CombinedBinHAndClucV5 | 30 min | 343 | 68.28 | 0.398 | 68.2 % | 1.82 | 4.28 | 15.88 | 41.53 | 21.79 | 4.96 | **FRAGILE** moins de 100 trades sur un bloc |
| CombinedBinHAndClucV5 | 45 min | 331 | 79.57 | 0.481 | 69.8 % | 2.03 | 5.4 | 8.63 | 43.94 | 21.34 | 14.29 | **FRAGILE** moins de 100 trades sur un bloc |
| CombinedBinHAndClucV5 | 60 min | 324 | 75.82 | 0.468 | 71.0 % | 1.96 | 4.95 | 8.46 | 38.24 | 21.23 | 16.35 | **FRAGILE** moins de 100 trades sur un bloc |
| CombinedBinHAndClucV6H | — | — | — | — | — | — | — | — | — | — | — | ERREUR :     df['hlv'] = np.where(df['close'] > df['smaHigh'], 1, np.where(df['close'] < df['smaLow'], -1, np.NAN)) /                                                                                             |
| CombinedBinHAndClucV8 | — | — | — | — | — | — | — | — | — | — | — | ERREUR :     df['hlv'] = np.where(df['close'] > df['smaHigh'], 1, np.where(df['close'] < df['smaLow'], -1, np.NAN)) /                                                                                             |
