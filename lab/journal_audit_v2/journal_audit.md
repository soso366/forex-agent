# Audit du journal des trades

Période : 2025-09-08 15:35 → 2026-08-28 17:40

> Une observation du journal ne devient JAMAIS une règle automatiquement : observation → hypothèse → backtest → validation → OOS → éventuellement intégration.

## Global

| | n | win | esp. R | gain moy. | perte moy. | PF | total R |
|---|---|---|---|---|---|---|---|
| tous | 305 | 42% | -0.033 | 0.716 | -0.568 | 0.9 | -10.13 |

## Par stratégie

| | n | win | esp. R | gain moy. | perte moy. | PF | total R |
|---|---|---|---|---|---|---|---|
| BreakRetest_v2 | 84 | 43% | -0.033 | 0.708 | -0.589 | 0.9 | -2.80 |
| DoubleTopBottom_v1 | 83 | 37% | -0.134 | 0.601 | -0.573 | 0.63 | -11.16 |
| FlagBreakout_v1 | 102 | 44% | +0.021 | 0.698 | -0.513 | 1.07 | +2.18 |
| RangeFade_v2 ⚠ | 20 | 50% | +0.067 | 0.724 | -0.59 | 1.23 | +1.34 |
| TrendPullback_v2 ⚠ | 16 | 31% | +0.019 | 1.623 | -0.711 | 1.04 | +0.30 |

## Par paire

| | n | win | esp. R | gain moy. | perte moy. | PF | total R |
|---|---|---|---|---|---|---|---|
| EURUSD | 95 | 34% | -0.105 | 0.811 | -0.571 | 0.72 | -10.00 |
| GBPUSD | 103 | 44% | -0.011 | 0.681 | -0.547 | 0.97 | -1.09 |
| USDJPY | 107 | 47% | +0.009 | 0.686 | -0.585 | 1.03 | +0.95 |

## Par séance

| | n | win | esp. R | gain moy. | perte moy. | PF | total R |
|---|---|---|---|---|---|---|---|
| london | 115 | 50% | +0.015 | 0.651 | -0.611 | 1.05 | +1.67 |
| new_york | 91 | 36% | -0.158 | 0.557 | -0.565 | 0.56 | -14.40 |
| overlap_london_ny | 99 | 37% | +0.026 | 0.957 | -0.529 | 1.08 | +2.60 |

## Par heure (UTC)

| | n | win | esp. R | gain moy. | perte moy. | PF | total R |
|---|---|---|---|---|---|---|---|
| 7 ⚠ | 21 | 38% | -0.027 | 0.928 | -0.614 | 0.93 | -0.56 |
| 8 ⚠ | 21 | 52% | -0.088 | 0.496 | -0.73 | 0.75 | -1.84 |
| 9 | 30 | 53% | -0.016 | 0.543 | -0.656 | 0.95 | -0.49 |
| 10 ⚠ | 25 | 60% | +0.258 | 0.725 | -0.442 | 2.46 | +6.45 |
| 11 ⚠ | 18 | 39% | -0.105 | 0.666 | -0.595 | 0.71 | -1.89 |
| 12 ⚠ | 27 | 48% | +0.274 | 1.229 | -0.613 | 1.86 | +7.40 |
| 13 ⚠ | 19 | 21% | -0.169 | 1.068 | -0.499 | 0.57 | -3.21 |
| 14 ⚠ | 22 | 27% | -0.052 | 0.902 | -0.409 | 0.83 | -1.14 |
| 15 | 31 | 45% | -0.015 | 0.696 | -0.6 | 0.96 | -0.46 |
| 16 ⚠ | 25 | 28% | -0.206 | 0.626 | -0.53 | 0.46 | -5.16 |
| 17 ⚠ | 27 | 52% | -0.040 | 0.398 | -0.512 | 0.84 | -1.09 |
| 18 ⚠ | 24 | 33% | -0.192 | 0.683 | -0.629 | 0.54 | -4.61 |
| 19 ⚠ | 15 | 27% | -0.236 | 0.742 | -0.592 | 0.46 | -3.54 |

## Par jour de semaine

| | n | win | esp. R | gain moy. | perte moy. | PF | total R |
|---|---|---|---|---|---|---|---|
| Friday | 46 | 54% | +0.138 | 0.693 | -0.522 | 1.58 | +6.36 |
| Monday | 51 | 33% | -0.173 | 0.736 | -0.627 | 0.59 | -8.81 |
| Thursday | 79 | 43% | +0.020 | 0.804 | -0.573 | 1.06 | +1.54 |
| Tuesday | 58 | 36% | -0.073 | 0.654 | -0.486 | 0.76 | -4.26 |
| Wednesday | 71 | 42% | -0.070 | 0.666 | -0.608 | 0.8 | -4.97 |

## Par type de sortie

| | n | win | esp. R | gain moy. | perte moy. | PF | total R |
|---|---|---|---|---|---|---|---|
| CLOSE | 61 | 8% | -0.419 | 0.4 | -0.492 | 0.07 | -25.56 |
| STOP_LOSS | 53 | 0% | -1.001 | — | -1.001 | — | -53.07 |
| TAKE_PROFIT ⚠ | 15 | 100% | +1.977 | 1.977 | — | — | +29.65 |
| TIME_STOP | 176 | 61% | +0.221 | 0.554 | -0.296 | 2.91 | +38.85 |

## Durée, MFE / MAE

- Durée médiane : gagnants 30.0 min, perdants 21.0 min
- MFE / MAE médians (R) : gagnants {'mfe': 0.93, 'mae': 0.29}, perdants {'mfe': 0.21, 'mae': 0.79}
- Gagnants devenus perdants (MFE ≥ +0,5 R puis perte) : 39 (22% des perdants)
- Sorties de gestion : {"n_management_exits": 76, "method": "prix après sortie", "measured": 76, "share_continued_0_5R": 0.395, "median_post_exit_mfe_r": 0.325}
- Séries de pertes max : {"BreakRetest_v2": 7, "DoubleTopBottom_v1": 7, "FlagBreakout_v1": 9, "RangeFade_v2": 2, "TrendPullback_v2": 4}
- Corrélations cachées : {"overlapping_pairs": 0, "days_with_2plus_trades": 88, "share_days_all_same_outcome": 0.35}

## Observations (hypothèses à tester, pas des règles)

- **stratégie** — BreakRetest_v2 : -0.03 R/trade sur 84 trades (PF 0.9) · n = 84 · *hypothèse à tester (backtest → validation → OOS)*
- **stratégie** — DoubleTopBottom_v1 : -0.13 R/trade sur 83 trades (PF 0.63) · n = 83 · *hypothèse à tester (backtest → validation → OOS)*
- **contexte perdant** — TrendPullback_v2 × TREND_DOWN : -0.43 R/trade sur 9 trades · n = 9 · *échantillon insuffisant : ne rien conclure*
- **contexte perdant** — EURUSD × 18 : -0.56 R/trade sur 10 trades · n = 10 · *échantillon insuffisant : ne rien conclure*
- **contexte perdant** — GBPUSD × 13 : -0.39 R/trade sur 8 trades · n = 8 · *échantillon insuffisant : ne rien conclure*
- **contexte perdant** — USDJPY × 8 : -0.39 R/trade sur 10 trades · n = 10 · *échantillon insuffisant : ne rien conclure*
- **contexte perdant** — DoubleTopBottom_v1 × EURUSD : -0.35 R/trade sur 27 trades · n = 27 · *échantillon insuffisant : ne rien conclure*
- **série** — BreakRetest_v2 : série de 7 pertes consécutives · n = 84 · *hypothèse à tester (backtest → validation → OOS)*
- **série** — DoubleTopBottom_v1 : série de 7 pertes consécutives · n = 83 · *hypothèse à tester (backtest → validation → OOS)*
- **série** — FlagBreakout_v1 : série de 9 pertes consécutives · n = 102 · *hypothèse à tester (backtest → validation → OOS)*

⚠ = moins de 30 trades : ne rien conclure.
