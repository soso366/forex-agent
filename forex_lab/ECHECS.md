# Registre des échecs — Forex Strategy Research Lab

But : ne jamais refaire une expérience déjà perdue. Avant tout nouveau test, vérifier ici ET dans
`memory/REJECTED_HYPOTHESES.md` (branche multi-agent-research). Une stratégie ne revient que sur un **fait nouveau**
(donnée nouvelle, mécanisme nouveau), jamais pour un réglage de paramètres.

| Date | ID | Stratégie (source) | Résultat (sept. 2024 → août 2026, coûts bid/ask réels) | Fait nouveau qui justifierait un retest |
|---|---|---|---|---|
| 23/10/2026 | F01 | MACD Sample (MetaQuotes), H1, 3 paires | exact : 272 trades, +2,0 pips/trade mais t 0,5 (bruit), négatif sur 2 blocs sur 4, USDJPY −200 pips ; version 4 h : −1,9 pip/trade | aucun |
| 23/10/2026 | F02 | Moving Average (MetaQuotes), H1, 3 paires | exact : 1 686 trades, −0,9 pip/trade ; version 4 h : −1,0 pip/trade, négatif sur les 4 blocs | aucun |
| 23/10/2026 | F03 | Business day EURUSD/GBPUSD (Breedon-Ranaldo, QuantRocket : Sharpe 0,70 publié sur 2005-2019) | **effet inversé** : −2,2 pips/trade, t −3,2 (après audit V3, coûts réalistes : −3,0 pips/trade) ; vérification indépendante : en 2024-2026 l'EURUSD **monte** en heures européennes (+1,5 pip) et **baisse** en heures US (−2,0 pips) | aucun ; l'inverse est une observation après coup, PAS une stratégie (à ne tester que comme nouvelle hypothèse pré-enregistrée, avec l'historique 2020-2023) |
| 23/10/2026 | F04 | EA31337 RSI (signal d'entrée, réglages par défaut), M15 | −3,8 pips/trade (exact), −2,3 (4 h) | aucun |
| 23/10/2026 | F05 | EA31337 CCI, M15 | −1,3 pip/trade (exact), −0,5 (4 h), t négatif | aucun |
| 23/10/2026 | F06 | EA31337 Williams %R, M15 | −1,7 / −1,1 pip/trade, t ≈ −2,9 | aucun |
| 23/10/2026 | F07 | EA31337 Stochastic, M15 | −2,3 / −1,6 pip/trade, t ≈ −3 | aucun |
| 23/10/2026 | F08 | EA31337 Bands, M15 | −1,3 / −0,8 pip/trade, t ≈ −2,4 | aucun |
| 23/10/2026 | V3-H1 | Fix de Tokyo USDJPY (Krohn-Mueller-Whelan ; Ito-Yamada) : vente après le fix 00:55 UTC, 18 variantes (délai, durée ≤ 4 h, jours gotobi) | IS : meilleure +11,1 pips/trade (gotobi, 4 h) ; VAL : −2,9 ; **0/18 variantes positives en VAL** ; version papier (achat 17:00 NY → fix → vente jusqu'à 02:00 NY) négative même avant coûts sur les deux années | aucun pour ces fenêtres ; l'effet publié (1999-2019) a disparu en 2024-2026 |
| 23/10/2026 | V3-H2 | Momentum intrajournalier filtré par la volatilité (Gao et al. 2018), 12 variantes, 3 paires | IS : meilleure +2,3 pips/trade (t 2,06) ; VAL : −2,8 (t −3,4) ; **0/12 positives en VAL** ; renversement confirmé par un calcul indépendant | aucun (avec E007 : deux formes du momentum intrajournalier rejetées) |
| 23/10/2026 | V3-H3 | Cassure du range asiatique → Londres (TradingView, Backtrex, Crabel), 16 variantes, M5 | IS : meilleure 0,0 pip/trade, 1/16 positive ; validation non consommée | aucun (avec V4-H2 et X01 : cassure d'ouverture rejetée trois fois) |
| 24/10/2026 | D01 | Suivi de tendance 12 mois (Moskowitz-Ooi-Pedersen), positions d'un mois, 2 positions max, données FRED 1971 → 2023/08 + portage + frais de courtier (protocole pré-enregistré `forex_lab/trend/PROTOCOLE.md`) | 1972-2023 net : Sharpe 0,03, t 0,19, ≈ 0 %/an, perte max −42 % ; 2010-2023 : Sharpe −0,09 ; brut (sans frais) Sharpe 0,14 seulement ; critères C1, C2, C3 non remplis ; vérification indépendante (autre code, données BCE) identique | aucun ; USDJPY seul positif (Sharpe 0,33) = observation après coup, PAS une stratégie |

## Leçons du lot 1
- Les 5 oscillateurs d'EA31337 (achat en survente, vente en surachat sur M15) perdent **plus que le spread** :
  à cet horizon, acheter la faiblesse / vendre la force va à contre-courant sur ces paires en 2024-2026.
  Ne pas en conclure qu'il faut « inverser » : ce serait une règle trouvée après coup.
- Un effet publié (F03, Sharpe 0,70 jusqu'en 2019) peut s'inverser plus tard : un résultat public ancien ne prouve rien aujourd'hui.
- Contrôles du moteur : entrées au hasard ≈ 0 pip avant coûts (t −0,5) et perte nette = spread moyen réellement payé
  (0,66 pip EURUSD, 1,52 pip GBPUSD) → les pertes mesurées ne viennent pas d'une erreur de calcul.

## Éliminées sans test (résultats publics négatifs ou doublons) — voir candidates.yaml (X01 à X12)
London breakout, Connors RSI(2), Turtle, MACD+RSI, cassure PDH/PDL, order block / FVG, MACD+EMA200, three white soldiers,
double top/bottom, Bollinger+stochastique, momentum intrajournalier, saisonnalité horaire E005.

## Leçons de la phase V3
- Trois effets documentés (dont un très solide sur 20 ans) n'existent plus, ou s'inversent, en 2024-2026 sur nos paires.
- Les meilleurs résultats d'optimisation (jusqu'à +11 pips/trade, t ≈ 3) n'ont aucune valeur sans validation séparée :
  aucune variante ne survit à l'année suivante.
