# Forex Strategy Research Lab — rapport du lot 1 (23/10/2026)

## Ce qui a été fait
1. Recherche de stratégies Forex open source **documentées** (règles complètes) : EA31337 (≈ 67 stratégies, GPL-3.0),
   exemples officiels MetaTrader (MACD Sample, Moving Average), stratégie « business day » (article Breedon-Ranaldo,
   code QuantRocket, résultat publié), et 12 backtests publics indépendants (Backtrex).
2. Tri (`candidates.yaml`) : **8 testées**, **2 reportées**, **12 éliminées sans test** (résultats publics négatifs
   ou déjà rejetées par le projet).
3. Critères écrits et publiés **avant** tout calcul (`CRITERES.md`, commit d8c2f8c).
4. Backtests sur Dukascopy M1 bid/ask, sept. 2024 → août 2026, 3 paires, règles d'origine sans optimisation,
   versions « exact » et « projet » (4 h max, fermé à 21:00 UTC). Moteur contrôlé par 4 tests unitaires, un placebo
   (entrées au hasard) et une vérification indépendante de F03.

## Résultat : aucune stratégie retenue (0 sur 16 configurations)

| Rang | ID | Stratégie | Meilleure version | Verdict |
|---|---|---|---|---|
| 1 | F01 | MACD Sample (MetaQuotes, H1) | exact : +2,0 pips/trade, t 0,5 | FRAGILE : indistinguable du hasard, perdante sur 2 blocs sur 4 |
| 2 | F05 | EA31337 CCI (M15) | projet : −0,5 pip/trade | ÉCHEC |
| 3 | F08 | EA31337 Bands (M15) | projet : −0,8 pip/trade | ÉCHEC |
| 4 | F02 | Moving Average (MetaQuotes, H1) | exact : −0,9 pip/trade | ÉCHEC |
| 5 | F06 | EA31337 Williams %R (M15) | projet : −1,1 pip/trade | ÉCHEC |
| 6 | F07 | EA31337 Stochastic (M15) | projet : −1,6 pip/trade | ÉCHEC |
| 7 | F03 | Business day EURUSD/GBPUSD | −2,1 pips/trade, t −3,6 | ÉCHEC — l'effet publié s'est inversé |
| 8 | F04 | EA31337 RSI (M15) | projet : −2,3 pips/trade | ÉCHEC |

Tableau complet : `results/lot_1.md` ; détail par bloc et par paire : `results/lot_1.json` ; échecs : `ECHECS.md`.

## Limites honnêtes
- EA31337 : seuls les **signaux d'entrée** sont reproduits exactement (réglages par défaut) ; sa gestion de sortie dépend
  de son framework et de fichiers d'optimisation non publiés en clair → remplacée par sa sortie à 30 bougies.
  Le projet EA31337 ne publie lui-même aucun résultat chiffré.
- Les EA MetaTrader lisent la bougie en cours ; ici le signal est lu à la clôture (exécution à l'ouverture suivante).
- 2 ans de données : l'historique 2020-2023 en cours de téléchargement permettra de revérifier F01 et de tester F09.

## Prochaines étapes
1. F09 (fix de Tokyo USDJPY les jours « gotobi ») dès que l'historique 2020-2023 est disponible.
2. Aucune autre stratégie EA31337 sans raison nouvelle (tester les 67 et garder la meilleure = sur-apprentissage).
3. Les agents de recherche reçoivent ces échecs dans leur registre pour ne pas les refaire.
