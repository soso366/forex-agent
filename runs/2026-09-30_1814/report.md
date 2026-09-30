# Rejeu V2 sur données Dukascopy M1 (EURUSD, GBPUSD, USDJPY)

Période des cycles : 2026-03-08T21:00:00+00:00 → 2026-08-31T23:55:00+00:00

## Vue d'ensemble

- Cycles : **36,324** (erreurs : 0)
- Décisions paire × cycle : NO_TRADE 108,237, HOLD 541, BUY 93, SELL 55, CLOSE 31, MOVE_STOP 15
- NO TRADE : **108,237** sur 108,972 décisions
- Régimes observés : CHOP 57,139, RANGE 31,984, TREND_UP 8,672, TREND_DOWN 5,591, DEAD 4,246, VOLATILE 1,340
- Capital : 50.00 → 48.03 EUR (-3.95 %), plus haut 50.00
- Positions encore ouvertes à la fin : 0

## Résultats

| Mesure | Valeur |
|---|---|
| Trades | 148 |
| Gagnants / perdants | 59 / 89 |
| Win rate | 39.9 % |
| PnL | -1.97 EUR |
| PnL en R | -7.02 R |
| Expectancy | -0.047 R / trade |
| Profit factor | 0.88 |
| Drawdown max | 7.96 % (3.98 EUR, 11.09 R) |
| MFE moyen / médian | 0.61 R / 0.41 R |
| MAE moyen / médian | 0.60 R / 0.58 R |
| Durée moyenne | 23.1 min |
| Sorties par limite 30 min | 82 (55 %) |
| Cas SL/TP ambigus (stop d'abord) | 0 |

Raisons de sortie : TIME_STOP 82, CLOSE 31, STOP_LOSS 25, TAKE_PROFIT 10

### Par stratégie

| Groupe | Trades | Gagnants / perdants | Win rate | PnL | PnL R | Expectancy R |
|---|---|---|---|---|---|---|
| BreakRetest_v2 | 42 | 14 / 28 | 33 % | -2.72 | -8.37 | -0.199 |
| DoubleTopBottom_v1 | 45 | 17 / 28 | 38 % | -2.41 | -7.08 | -0.157 |
| FlagBreakout_v1 | 44 | 19 / 25 | 43 % | +1.06 | +1.94 | +0.044 |
| RangeFade_v2 | 12 | 7 / 5 | 58 % | +0.62 | +3.06 | +0.255 |
| TrendPullback_v2 | 5 | 2 / 3 | 40 % | +1.48 | +3.42 | +0.684 |

### Par paire

| Groupe | Trades | Gagnants / perdants | Win rate | PnL | PnL R | Expectancy R |
|---|---|---|---|---|---|---|
| EURUSD | 45 | 17 / 28 | 38 % | +0.66 | -0.43 | -0.010 |
| GBPUSD | 54 | 24 / 30 | 44 % | -1.61 | -0.94 | -0.017 |
| USDJPY | 49 | 18 / 31 | 37 % | -1.03 | -5.65 | -0.115 |

### Par régime à l'entrée

| Groupe | Trades | Gagnants / perdants | Win rate | PnL | PnL R | Expectancy R |
|---|---|---|---|---|---|---|
| RANGE | 12 | 7 / 5 | 58 % | +0.62 | +3.06 | +0.255 |
| TREND_DOWN | 48 | 16 / 32 | 33 % | -1.36 | -5.06 | -0.105 |
| TREND_UP | 88 | 36 / 52 | 41 % | -1.23 | -5.02 | -0.057 |

### Par session

| Groupe | Trades | Gagnants / perdants | Win rate | PnL | PnL R | Expectancy R |
|---|---|---|---|---|---|---|
| london | 49 | 22 / 27 | 45 % | -0.15 | -1.63 | -0.033 |
| new_york | 54 | 19 / 35 | 35 % | -3.36 | -10.97 | -0.203 |
| overlap_london_ny | 45 | 18 / 27 | 40 % | +1.53 | +5.59 | +0.124 |

### Par killzone

| Groupe | Trades | Gagnants / perdants | Win rate | PnL | PnL R | Expectancy R |
|---|---|---|---|---|---|---|
| london | 17 | 10 / 7 | 59 % | +1.47 | +2.83 | +0.167 |
| new_york_am | 29 | 9 / 20 | 31 % | +0.71 | +1.71 | +0.059 |
| — | 102 | 40 / 62 | 39 % | -4.15 | -11.56 | -0.113 |

## Entonnoir par stratégie

Détections = occurrences paire × cycle où le motif existe ; un même motif présent sur plusieurs cycles consécutifs est compté à chaque cycle.

| Stratégie | Détections | Refusées (conditions) | Qualifiées | Qualifiées non exécutées | Exécutées | Gagnants / perdants |
|---|---|---|---|---|---|---|
| BreakRetest_v2 | 6,103 | 5,961 | 142 | 100 | 42 | 14 / 28 |
| DoubleTopBottom_v1 | 9,471 | 9,332 | 139 | 94 | 45 | 17 / 28 |
| FlagBreakout_v1 | 4,485 | 4,369 | 116 | 72 | 44 | 19 / 25 |
| RangeFade_v2 | 11,154 | 11,129 | 25 | 13 | 12 | 7 / 5 |
| SweepMSS_v2 | 9,150 | 9,150 | 0 | 0 | 0 | 0 / 0 |
| TrendPullback_v2 | 7,940 | 7,922 | 18 | 13 | 5 | 2 / 3 |

### BreakRetest_v2

Conditions essentielles manquantes (une détection peut en manquer plusieurs) :
- trigger : 5,235
- rr : 4,862
- retest : 3,648
- break : 1,002
- spread : 285
- news : 1

Qualifiées mais non exécutées, raison :
- hors sessions de trading (#:# UTC) : gestion des positions uniquement : 68
- position déjà ouverte ou gérée sur la paire : 14
- autre setup exécuté sur la paire (DoubleTopBottom_v1) : 5
- Risk Manager : stop # pips hors bornes [#, #] : 4
- vendredi soir : pas de nouvelle position avant le week-end : 3
- Risk Manager : perte récente sur GBPUSD : pas de ré-entrée avant # min (pas de chase / revenge) : 3
- Risk Manager : pause anti-revenge après # pertes : 2
- une seule nouvelle position par cycle : meilleur candidat retenu ailleurs : 1

### DoubleTopBottom_v1

Conditions essentielles manquantes (une détection peut en manquer plusieurs) :
- neckline_retest : 8,476
- rr : 7,801
- buying_pressure : 4,951
- spread : 356
- news : 1

Qualifiées mais non exécutées, raison :
- hors sessions de trading (#:# UTC) : gestion des positions uniquement : 40
- position déjà ouverte ou gérée sur la paire : 30
- Risk Manager : pause anti-revenge après # pertes : 6
- autre setup exécuté sur la paire (BreakRetest_v2) : 5
- vendredi soir : pas de nouvelle position avant le week-end : 5
- Risk Manager : stop # pips hors bornes [#, #] : 2
- une seule nouvelle position par cycle : meilleur candidat retenu ailleurs : 2
- Risk Manager : perte récente sur GBPUSD : pas de ré-entrée avant # min (pas de chase / revenge) : 1

### FlagBreakout_v1

Conditions essentielles manquantes (une détection peut en manquer plusieurs) :
- breakout : 3,924
- rr : 3,439
- volatile_trend : 884
- spread : 650
- news : 1

Qualifiées mais non exécutées, raison :
- hors sessions de trading (#:# UTC) : gestion des positions uniquement : 36
- position déjà ouverte ou gérée sur la paire : 17
- une seule nouvelle position par cycle : meilleur candidat retenu ailleurs : 7
- Risk Manager : risque corrélé avec GBPUSD (même exposition USD) : 3
- Risk Manager : stop # pips hors bornes [#, #] : 3
- Risk Manager : risque corrélé avec EURUSD (même exposition USD) : 2
- autre setup exécuté sur la paire (BreakRetest_v2) : 2
- Risk Manager : pause anti-revenge après # pertes : 1

### RangeFade_v2

Conditions essentielles manquantes (une détection peut en manquer plusieurs) :
- rr : 10,875
- trigger : 7,227
- rejection : 6,397
- spread : 507
- location : 191
- news : 17

Qualifiées mais non exécutées, raison :
- position déjà ouverte ou gérée sur la paire : 5
- hors sessions de trading (#:# UTC) : gestion des positions uniquement : 4
- vendredi soir : pas de nouvelle position avant le week-end : 2
- une seule nouvelle position par cycle : meilleur candidat retenu ailleurs : 1
- Risk Manager : perte récente sur GBPUSD : pas de ré-entrée avant # min (pas de chase / revenge) : 1

### SweepMSS_v2

Conditions essentielles manquantes (une détection peut en manquer plusieurs) :
- rr : 8,926
- retracement : 8,587
- mss : 8,518
- displacement : 6,715
- fvg : 6,648
- time : 6,011
- premium_discount : 4,283
- bias : 3,684
- spread : 628
- news : 15

Qualifiées mais non exécutées, raison :
- aucune

### TrendPullback_v2

Conditions essentielles manquantes (une détection peut en manquer plusieurs) :
- rr : 6,528
- trigger : 6,487
- pullback : 3,814
- location : 3,554
- fresh_trend : 3,010
- spread : 643
- context : 480
- news : 7

Qualifiées mais non exécutées, raison :
- hors sessions de trading (#:# UTC) : gestion des positions uniquement : 11
- Risk Manager : stop # pips hors bornes [#, #] : 1
- position déjà ouverte ou gérée sur la paire : 1

## Lecture

148 trades : échantillon exploitable, à confirmer hors échantillon avant toute décision.
Aucun paramètre, aucune cible, aucune durée ni aucun risque n'ont été modifiés pour ce rejeu.