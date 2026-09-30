# Inventaire des paramètres — V2 (état au 30/09/2026)

Toutes les valeurs ci-dessous sont celles du premier vrai backtest (148 trades, Dukascopy mars→août 2026).
Les constantes qui étaient écrites en dur dans le code sont maintenant dans `config/settings.yaml`
**avec exactement la même valeur** (vérifié : rejeu identique avant/après).

Colonne *Origine* :
- **PDF** : valeur ou règle donnée explicitement par une source (NNFX/TTC/Wysetrade, ICT, vidéo « technical analysis », Trading Rush) ;
- **adaptation** : règle issue d'une source, mais chiffrée par nous (les sources parlent souvent en Daily ou restent qualitatives) ;
- **choix technique** : aucun appui dans les sources, choisi pour que le code fonctionne.

Colonne *Lab* : ✅ plage testée · ◻︎ non testé (raison indiquée) · 🔒 exclu volontairement (règle de sécurité).

## 1. Paramètres structurels (fixent le cadre, pas testés pour « optimiser »)

| Paramètre | Valeur | Concerne | Origine | Raison de la valeur | Lab |
|---|---|---|---|---|---|
| `scheduler.interval_minutes` | 5 | tout | ton cahier des charges | cycle demandé | 🔒 |
| `trading.max_hold_minutes` | 30 | toutes positions | ton cahier des charges | durée max demandée | ✅ lu seulement (voir bloc A) |
| `symbols` | EURUSD, GBPUSD, USDJPY | tout | ton cahier des charges | paires initiales | ✅ bloc B (retrait d'une paire) |
| `bars` H1/M15/M5/M1 | 120/160/150/60 | analyse | choix technique | assez d'historique pour EMA50, swings, jour précédent | ◻︎ (sans effet s'il y en a assez) |
| Timeframes contexte / entrée | H1+M15 / M5+M1 | analyse | PDF (TTC, ICT : HTF = biais, LTF = timing) + ton cahier | adaptés au scalping 30 min | 🔒 |
| EMA 9 / 20 / 50 | 9, 20, 50 | tendance, zones de valeur | PDF (vidéo TA : 20/50/200 ; TTC) | 200 inutile sur M5/M15 à 30 min | ◻︎ (définition, pas un réglage) |
| RSI / ATR | 14 / 14 | momentum, volatilité | PDF (vidéo TA : ATR 14) | standard | ◻︎ |
| Pente EMA20 | sur 5 bougies | tendance EMA | choix technique | éviter une EMA plate | ◻︎ |
| Fractales de swing | 2 bougies de chaque côté | structure, niveaux | adaptation (swings Wysetrade/ICT) | plus petit swing confirmé sans look-ahead | ◻︎ |
| Jour Forex | clôture 17:00 New York | PDH/PDL | PDF (ICT) + convention marché | standard FX | 🔒 |
| Dealing range | 96 M15 (24 h) | premium/discount | adaptation (ICT) | range intraday pour du 30 min | ◻︎ (lié à la définition) |
| Levier / capital | 30:1 / 50 € | compte | ton cahier + ESMA | — | 🔒 |

## 2. Paramètres de stratégie

### Communs
| Paramètre | Valeur | Origine | Raison | Lab |
|---|---|---|---|---|
| `stop_buffer_atr` (≈ « ATR stop multiplier ») | 0,5 ATR M5 | adaptation (vidéo TA : 1 ATR au-delà du swing, en Daily) | 1 ATR M5 donnait des stops trop larges pour 30 min | ✅ bloc C |
| `target_offset_atr` | 0,05 ATR + spread | choix technique | sortir juste avant le niveau (vidéo TA : « ne pas viser au-delà d'un niveau ») | ✅ bloc A |
| `target_min_spreads` | 2 spreads | choix technique | ignorer un niveau collé au prix | ◻︎ |
| `opposite_displacement_atr` (entrée) | 1,5 ATR | adaptation (Wysetrade « d'où vient le prix ») | impulsion contraire nette | ✅ bloc C |
| `displacement_atr` | 1,0 ATR | adaptation (ICT « grande expansion ») | corps ≥ 1 ATR = expansion claire | ✅ bloc C |
| `displacement_close_pos` | 30 % extrêmes | adaptation (ICT « closes directionnelles ») | clôture près de l'extrême | ◻︎ |
| Déclencheurs 38,2 % / engulfing / close above-below | 38,2 %, corps > précédent | **PDF** (vidéo TA, règles exactes) | reprises telles quelles | 🔒 (règle de la source) |

### TrendPullback_v2
| Paramètre | Valeur | Origine | Raison | Lab |
|---|---|---|---|---|
| `min_pullback_pct` / `max_pullback_pct` (profondeur de pullback) | 30 % / 78,6 % | adaptation (Wysetrade : 25–30 % = peu profond, ≥ 50 % = meilleur) | accepter les pullbacks « corrects » à « profonds » | ✅ bloc C |
| `tp_min_leg_atr` | 2 ATR | choix technique | une vraie impulsion | ✅ bloc C |
| `tp_leg_lookback` | 30 M5 | choix technique | 2 h 30 de contexte | ◻︎ |
| `tp_value_zone_atr` (distance support/EMA) | 0,3 ATR | adaptation (vidéo TA : EMA20/50 zone de valeur ; zones et non lignes) | tolérance de contact | ✅ bloc C |
| Fresh trend (`fresh_max_bos` / `fresh_max_ext_atr`) | ≤ 3 cassures / ≤ 2,5 ATR de l'EMA20 | adaptation (Wysetrade : tendance fraîche vs épuisée) | chiffrage de « fraîche » | ✅ bloc C |

### BreakRetest_v2
| Paramètre | Valeur | Origine | Raison | Lab |
|---|---|---|---|---|
| `br_zone_atr` (tolérance du retest) | 0,25 ATR | adaptation (TTC/vidéo TA : zones) | zone autour du niveau | ✅ bloc C |
| `br_break_min_atr` | 0,1 ATR | choix technique | clôture réellement au-delà | ✅ bloc C |
| `br_strong_break_atr` / `br_break_displacement` | 0,3 ATR / corps 0,6 ATR | adaptation (vidéo TA : cassure en « momentum candle ») | cassure franche | ◻︎ |
| `br_hold_bars` | 6 M5 | choix technique | le niveau a vraiment tenu avant | ◻︎ |
| `br_fall_through_atr` | 0,1 ATR | choix technique | pas de réintégration franche | ◻︎ |
| `br_level_lookback_m15` | 48 M15 (12 h) | choix technique | niveaux intraday récents | ◻︎ |

### FlagBreakout_v1
| Paramètre | Valeur | Origine | Raison | Lab |
|---|---|---|---|---|
| `flag_pole_atr` | 2,5 ATR | adaptation (vidéo TA : « impulsive move ») | mât significatif | ✅ bloc C |
| `flag_max_range_ratio` / `flag_max_retrace` | 50 % / 50 % | choix technique | un drapeau reste petit face au mât | ◻︎ |
| `flag_ema_tol_atr` | 0,2 ATR | **PDF** (vidéo TA : flag seulement au-dessus / près de l'EMA20) + tolérance | « near the 20 » | ◻︎ |
| `flag_break_body_atr` | 0,5 ATR | adaptation | vraie bougie de cassure | ✅ bloc C |

### DoubleTopBottom_v1
| Paramètre | Valeur | Origine | Raison | Lab |
|---|---|---|---|---|
| Zone de terminaison | [plus bas, plus bas des corps] | **PDF** (vidéo TA, règle exacte) | reprise telle quelle | 🔒 |
| `dt_retest_atr` | 0,25 ATR | adaptation (vidéo TA : retour sur neckline) | tolérance | ✅ bloc C |
| `dt_min_separation` | 4 M5 | choix technique | deux creux distincts | ◻︎ |

### SweepMSS_v2 (ICT)
| Paramètre | Valeur | Origine | Raison | Lab |
|---|---|---|---|---|
| `sweep_beyond_atr` | 0,05 ATR | adaptation (ICT : prise de liquidité) | vraie mèche au-delà | ◻︎ |
| `sweep_lookback` / `sweep_clean_bars` | 8 / 12 M5 | choix technique | sweep récent, niveau intact avant | ◻︎ |
| `fvg_min_atr` (taille minimale FVG) | 0 (toute FVG) | adaptation (ICT : « toutes les FVG ne se valent pas » — pas chiffré) | non filtré en V2 | ◻︎ (0 trade : rien à mesurer) |
| `fvg_entry_tol_atr` (distance de retracement FVG) | 0,1 ATR | choix technique | entrée dans/au bord de la FVG | ◻︎ (idem) |
| Premium / discount | 50 % du dealing range 24 h | **PDF** (ICT : > 50 % premium) | règle de la source | ◻︎ (idem) |
| `equal_level_tol_atr` (equal highs/lows) | 0,1 ATR M15 | adaptation (ICT) | deux sommets « égaux » à 0,1 ATR près | ✅ bloc C (agit aussi sur les cibles) |

### RangeFade_v2
| Paramètre | Valeur | Origine | Raison | Lab |
|---|---|---|---|---|
| `rf_edge_pct` | 15 % de la largeur | choix technique | proximité de la borne | ◻︎ (12 trades : trop peu) |
| `rf_wick_pct` | 50 % de la bougie | adaptation (Wysetrade : mèche longue au niveau) | rejet net | ◻︎ (idem) |

## 3. Paramètres de sortie

| Paramètre | Valeur | Origine | Raison | Lab |
|---|---|---|---|---|
| `max_hold_minutes` | 30 | ton cahier des charges | **non modifiable** sans ton accord | 🔒 (mesuré, pas changé) |
| `min_rr` | 1,5 | adaptation (Trading Rush testait à 1,5:1) | seuil d'entrée net de spread | ✅ bloc A |
| `breakeven_at_r` (break-even) | +1 R | adaptation (vidéo TA : « roll stops to break even ») | protéger un trade avancé | ✅ bloc A |
| `lock_at_r` / `lock_r` (protection du profit) | +1,5 R → verrouille +0,5 R | choix technique | cliquet | ✅ bloc A |
| `trail_ema20_after_r` / `trail_offset_atr` (trailing) | dès +1 R, EMA20 ± 0,3 ATR | **PDF** (vidéo TA : EMA20 comme trailing stop) + adaptation | laisser courir | ✅ bloc A |
| `take_profit_near_target` | 80 % du chemin + momentum qui tourne | choix technique | encaisser avant le niveau | ✅ bloc A |
| `opposite_displacement_atr` (sortie) | 1,2 ATR | adaptation (ICT : displacement opposé = invalidation) | sortie anticipée | ✅ bloc A |
| `momentum_exit_r` / `momentum_rsi_band` | sous −0,3 R, RSI à 5 pts du 50 | choix technique | sortie anticipée | ✅ bloc A |
| `regime_flip_exit` / `chop_exit` | activés | adaptation (NNFX/ICT : invalidation narrative) | sortie anticipée | ✅ bloc A |

## 4. Paramètres de filtre

| Paramètre | Valeur | Origine | Raison | Lab |
|---|---|---|---|---|
| `sessions.new_trades_utc` (horaires) | 07:00–20:00 UTC | adaptation (sessions Londres + New York) | liquidité | ✅ bloc B |
| `no_new_trades_friday_after_utc` | 19:00 | choix technique | éviter le week-end | ◻︎ |
| `killzones_ny` | Londres 2–5 h, NY 7–10 h (heure NY) | **PDF** (ICT) | reprises telles quelles | ✅ bloc B (killzone obligatoire ou non) |
| `news.blackout` | ±30 min, NFP auto | adaptation (ICT/NNFX) | pas d'entrée sur annonce | ◻︎ (seul le NFP est connu : 6 événements) |
| `max_spread_pips` | 2,0 / 2,5 GBP / 2,0 JPY | choix technique | spread anormal | ✅ bloc B |
| `max_spread_to_stop_ratio` | 25 % | choix technique | coût vs risque | ✅ bloc B |
| Régime : `er_trend_min` / `er_range_max` | 0,30 / 0,25 | choix technique (efficiency ratio) | séparer tendance / bruit | ✅ bloc D |
| Régime : `vol_extreme_ratio` / `dead_atr_spread_mult` (seuils de volatilité) | 2,5× / 1,2× spread | choix technique | pas de trade en spike ni en marché mort | ✅ bloc B |
| Régime : range 3–15 ATR, 2 contacts, bande 15 % | — | choix technique | définition d'un range propre | ◻︎ |
| `reentry_cooldown_minutes` | 30 | adaptation (ICT « missed ≠ chase ») | anti-revenge | 🔒 (règle de sécurité) |

## 5. Paramètres de risque — **identiques pendant tout le lab**

| Paramètre | Valeur | Origine | Lab |
|---|---|---|---|
| `risk_per_trade_pct` | 1 % | ton cahier des charges | 🔒 |
| `max_total_risk_pct` | 2 % | ton cahier des charges | 🔒 |
| `max_open_positions` | 2 | ton cahier des charges | 🔒 |
| `max_trades_per_day` | 12 | choix technique | 🔒 |
| `daily_loss_limit_pct` / `max_drawdown_pct` | 3 % / 20 % | choix technique | 🔒 |
| `max_consecutive_losses` / cooldown / risque réduit | 3 / 60 min / 0,5 % | ton cahier (anti-revenge) | 🔒 |
| `min_stop_pips` / `max_stop_pips` | 3 / 20 pips | choix technique | 🔒 |
| `max_margin_usage_pct` | 60 % | choix technique | 🔒 |
| `block_same_currency_same_direction` | oui | ton cahier (corrélation) | 🔒 |
