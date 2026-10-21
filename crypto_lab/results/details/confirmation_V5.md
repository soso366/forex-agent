# confirmation_V5 — résultats (frais 0,10 %/ordre + glissement 0,05 %/ordre)

| Stratégie | Plafond | Trades | Net USDT | Gain moyen % | Taux de gain | PF | t | DD max | P1 | P2 | P3 | Stress | Audit biais | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CombinedBinHAndClucV5 | origine | 477 | -1.49 | -0.006 | 69.8 % | 0.99 | -0.05 | 34.01 | 13.15 | -18.55 | 3.91 | -25.34 | — | **ÉCHEC** perdante sur au moins un bloc; profit factor < 1,15; t < 2 (pas distinguable du hasard); drawdown > 20 % du capital |
| CombinedBinHAndClucV5 | 30 min | 627 | 61.81 | 0.197 | 67.6 % | 1.29 | 2.03 | 32.01 | 20.42 | 37.9 | 3.48 | 30.46 | — | **FRAGILE** drawdown > 20 % du capital |
| CombinedBinHAndClucV5 | 45 min | 609 | 86.38 | 0.284 | 67.2 % | 1.43 | 3.23 | 21.18 | 28.53 | 39.04 | 18.81 | 55.93 | — | **ROBUSTE**  |
| CombinedBinHAndClucV5 | 60 min | 596 | 74.44 | 0.25 | 66.4 % | 1.35 | 2.68 | 18.97 | 18.39 | 32.11 | 23.94 | 44.64 | — | **ROBUSTE**  |
