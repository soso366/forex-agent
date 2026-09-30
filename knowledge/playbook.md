# Playbook stratégique — V2 (règles tirées des documents sources)

Sources dans `knowledge/sources/` :
- **NNFX_TTC_Wysetrade_synthese.pdf** — ta synthèse NNFX + The Trading Channel + Wysetrade + étude régimes.
- **ICT_41_episodes_synthese.pages / .txt** — ta synthèse des 41 épisodes ICT.
- **15-best-price-action-strategies…pdf** — Wysetrade, transcription.
- **the-only-technical-analysis-video…pdf** — vidéo « technical analysis » (objective trend, ATR, EMA, bougies, double top/bottom, flag, wedge).
- **top-5-best-trading-strategies…pdf** — Trading Rush (MACD, Bollinger, Ichimoku, Alligator, croisement de MM).

Chaque stratégie est une HYPOTHÈSE formalisée, versionnée, au statut `experimental`
tant que le journal n'a pas prouvé son espérance (voir « Validation »).

## Principes communs (appliqués dans le code)

| Principe | Source | Où dans le code |
|---|---|---|
| Régime avant signal ; P(gain \| signal, régime), pas P(gain \| signal) | synthèse TTC / étude régimes | `analysis/market.py`, `brain/router.py`, rapport par régime |
| Entrée binaire : toutes les conditions essentielles, sinon NO TRADE | NNFX | `strategies/base.py::qualifies` |
| Pas de pondération arbitraire (« +2 support ») : confirmations optionnelles journalisées, poids fixés par les stats | synthèse TTC/Wysetrade | `confirmations` hors `essential` |
| Tendance objective : tient tant que le plus bas du dernier pullback n'est pas CLÔTURÉ | vidéo TA | `structure.structure_trend` (protected level) |
| Tendance fraîche > épuisée (≤ 3 cassures, ≤ 2,5 ATR de l'EMA20) | Wysetrade | `TFView.fresh` |
| « D'où vient le prix » : pas d'entrée juste après une grosse impulsion contraire | Wysetrade | `base.opposite_impulse` |
| Zones, pas lignes ; résistance cassée → support | vidéo TA, TTC | BreakRetest (zone ± 0,25 ATR) |
| Déclencheurs objectifs : bougie 38,2 %, engulfing (couleur + corps plus grand), close above/below | vidéo TA | `structure.candle_trigger` |
| Stop à l'invalidation + tampon ATR ; taille adaptée au stop | vidéo TA, ICT, NNFX | `base.buffer`, Risk Manager |
| Cible = premier niveau de liquidité / structure opposé, choisi avant l'entrée ; jamais « pour le ratio » | ICT, vidéo TA | `base.build_setup` |
| Temps = composante du setup (killzones, annonces) | ICT | `structure.killzone`, `structure.news_blackout` |
| Liquidité nommée : PDH/PDL (jour Forex clos 17:00 New York), Asie, equal highs/lows, swings | ICT | `structure.liquidity_pools` |
| Premium / discount du dealing range 24 h | ICT | `MarketContext.zone` |
| Indicateurs = filtres / timing, jamais signal seul (RSI, MACD, MM) | TTC, vidéo TA, Trading Rush | confirmations optionnelles |
| « Missed trade ≠ chase trade » ; pas de ré-entrée après perte sur la paire (30 min) | ICT | Risk Manager |

## Régimes (calculés à chaque cycle)
| Régime | Définition | Stratégies |
|---|---|---|
| TREND_UP / DOWN | EMA H1 et M15 alignées, efficiency M15 ≥ 0,30, structure M15 non opposée | TrendPullback, BreakRetest, FlagBreakout, DoubleTopBottom, SweepMSS (dans le sens) |
| RANGE | efficiency < 0,25, largeur 3–15 ATR, bornes touchées ≥ 2 fois, pas de tendance H1+M15 | RangeFade, SweepMSS (deux sens) |
| CHOP / DEAD / VOLATILE | pas de biais clair / ATR trop faible / spike | aucune → NO TRADE |

## Stratégies

### TrendPullback_v2 — Wysetrade, TTC, vidéo TA, Trading Rush
Essentielles : **context** (régime + structure M15 dans le sens, H1 non opposé) · **fresh_trend** ·
**pullback** 30–78,6 % de la dernière jambe M5, sans impulsion contraire · **location** : extrême du pullback
à ≤ 0,3 ATR de l'EMA20/EMA50 M5 ou d'un ancien niveau · **trigger** : bougie objective, extrême du pullback
dans les 3 dernières bougies.
Optionnelles : pullback profond ≥ 50 %, bougies qui rétrécissent dans le pullback, M1 > EMA9, RSI repassé 50, MACD aligné, killzone.
Stop : extrême du pullback ± tampon. Cible : plus haut de la jambe ou premier niveau opposé.

### BreakRetest_v2 — vidéo TA, TTC, Wysetrade
Essentielles : **context** tendance · **break** : clôture ≥ 0,3 ATR au-delà d'un swing M15 (ou bougie de displacement),
niveau respecté ≥ 6 M5 avant · **retest** : retour dans la zone ± 0,25 ATR sans clôture franche de l'autre côté ·
**trigger** : bougie objective de l'autre côté du niveau, retest dans les 2 dernières bougies.
Stop : au-delà de la zone et de l'extrême du retest. Cible : premier niveau opposé.

### FlagBreakout_v1 — vidéo TA
Essentielles : **context** tendance · **pole** ≥ 2,5 ATR · **flag** 3–8 bougies, amplitude ≤ 50 % du mât, correction ≤ 50 % ·
**volatile_trend** : toutes les clôtures du côté de l'EMA20 M5 · **breakout** : clôture au-delà du drapeau, corps ≥ 0,5 ATR.
Stop : autre bord du drapeau ± tampon. Cible : niveau précédent, sinon projection du mât.

### DoubleTopBottom_v1 — vidéo TA, Wysetrade
Essentielles : **htf_aligned** (tendance dans le sens du pattern) · **second_touch** : 2e creux touche la zone de terminaison
[plus bas, plus bas des corps] du 1er, aucune clôture au-delà · **neckline_break** (clôture) · **neckline_retest** ·
**buying_pressure** (bougie dans le sens, au-delà de la neckline).
Stop : extrême du retour ± tampon. Cible : premier niveau opposé.

### SweepMSS_v2 — modèle ICT minimal
Essentielles : **bias** (range ou tendance dans le sens, H1 structurel non opposé) · **time** (killzone Londres 2–5 h NY
ou New York 7–10 h NY) · **sweep** d'une liquidité nommée (mèche ≥ 0,05 ATR au-delà, clôture revenue, niveau intact les
12 bougies précédentes) · **displacement** (corps ≥ 1 ATR, clôture dans les 30 % extrêmes) · **mss** (clôture au-delà du
dernier swing mineur antérieur au sweep) · **fvg** créée après le sweep · **retracement** dans la FVG intacte ·
**premium_discount** (achat en discount, vente en premium).
Optionnelles : liquidité externe prise, H1 structurel aligné.
Stop : extrême du sweep ± tampon. Cible : première liquidité opposée.

### RangeFade_v2 — Wysetrade, ICT (journée de consolidation) — expérimentale
Essentielles : **context** RANGE · **location** borne ± 15 % de la largeur, côté opposé au milieu · **rejection**
(mèche ≥ 50 % d'une des 3 dernières bougies) · **trigger** (bougie objective).
Optionnelles : bougies qui rétrécissent à l'approche, RSI extrême, M15 plat.
Stop : au-delà de la borne ± tampon. Cible : milieu du range ou niveau plus proche.

## Gestion des positions (chaque cycle)
- Displacement M5 contraire ≥ 1,2 ATR → CLOSE (invalidation narrative, ICT).
- Régime retourné contre la position ou VOLATILE → CLOSE.
- +1R : stop au break-even ; +1,5R : verrouille +0,5R ; trailing sous l'EMA20 M5 au-delà de +1R (vidéo TA).
- ≥ 80 % du chemin et momentum qui se retourne → TAKE PROFIT.
- 30 minutes → fermeture automatique.

## Validation (NNFX, étude régimes, ICT)
Backtest → optimisation raisonnable → hors échantillon → forward (paper) → démo → éventuellement réel.
Juger sur ≥ 100 trades par stratégie : espérance (R), drawdown, profit factor, stabilité par régime et
par session, MFE/MAE, après spread. Jamais sur le win rate seul, jamais sur 5 exemples.

## Pas encore codé (identifié → à formaliser → à tester)
- SMT divergence EURUSD/GBPUSD (ICT) — confirmation uniquement.
- Order Blocks, Breakers, OTE (ICT) — raffinements, jamais signal seul.
- Midnight Open / 8:30 Open comme références (ICT).
- Calendrier économique automatique (CPI, FOMC…) : seul le NFP est calculé ; les autres se saisissent dans `news.events`.
- Ichimoku, Bollinger, Alligator (Trading Rush) : à tester comme filtres de régime, pas comme signaux.
- Wedges / triangles (vidéo TA, Wysetrade).
