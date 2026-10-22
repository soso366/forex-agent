# Strategy Research Lab — rapport du lot 1 (22/10/2026)

Robot crypto, simulation uniquement. Spot Binance, achat seul, capital 150 USDT, 2 positions max, mise 50 USDT,
frais 0,10 %/ordre + glissement 0,05 %/ordre. Code des stratégies téléchargé au commit épinglé, logique inchangée.
Critères écrits avant les tests : `CRITERES.md`. Tableaux complets : `results/`.

## Classement

| Rang | Stratégie | Meilleure durée max | Fiabilité | Résumé |
|---|---|---|---|---|
| 1 | **CombinedBinHAndClucV5** | **45 min** (60 min presque équivalent) | **Candidate au paper trading, confiance moyenne** | Positive sur 2023-2026 (5 paires), **confirmée sur 10 paires jamais testées** (ROBUSTE : PF 1,43, t 3,2, 609 trades), **positive en 2022** malgré le krach (PF 1,24, drawdown 26 USDT). Aucun biais d'anticipation détecté. |
| 2 | CombinedBinHAndClucV8 | origine (sans plafond) | Faible | Légèrement positive sans plafond, mais perdante sur 2025-2026 ; avec 30/45/60 min, indistinguable du hasard. Non retenue. |
| — | CombinedBinHAndClucV6H | — | Non testable | Plante avec les versions actuelles de pandas (conversion de type). Corriger demanderait de toucher à sa logique : écartée pour l'instant. |

Une seule stratégie solide, pas trois : on ne force pas de sélection.

## 2e confirmation sur 30 autres cryptos (22/10/2026) : ÉCHEC
Critères écrits avant le test (`CRITERES.md`). Sur 30 cryptos moins importantes (NEAR, UNI, FIL, ICP, APT…), V5 / 45 min
est à peine positive (+43 USDT, profit factor 1,06, t 0,86), **perdante sur 2023-mi-2024** et **perdante avec un glissement
doublé**. Seules 16 cryptos sur 30 sont gagnantes. Le résultat ne se généralise donc pas à toutes les cryptos :
il tient sur les 15 plus grosses (BTC, ETH, SOL… jusqu'à ETC), pas sur les plus petites, où les chutes rapides
continuent plus souvent au lieu de rebondir.
Conséquence (règle fixée avant le test) : le paper trading reste limité aux 15 cryptos actuelles ; pas de 2e suivi.
Le paper trading devient le test décisif : la confiance dans V5 baisse d'un cran.

## Ce que montrent les durées
- Pour V5, **imposer une sortie à 45-60 min améliore nettement le résultat** par rapport à la version d'origine
  (qui garde ses positions ≈ 2,5 h en moyenne) : profit factor 2,0 contre 1,6 sur le lot 1, 1,43 contre 0,99 sur les nouvelles paires.
- 30 min est trop court : environ 58 % des trades sont coupés par le plafond, le gain moyen baisse et le drawdown monte.
- Environ la moitié des trades à 45 min se ferment au plafond ; les autres sortent avant, sur l'objectif de +1,8 %.

## Points de vigilance (V5, plafond 45 min)
- **Achat seul après une forte chute** (≥ 1,75 % en 5 min sous la bande de Bollinger) : elle « rattrape les couteaux ».
  Au 2e semestre 2022 (FTX), elle perd 14,5 USDT ; en 2022 le gain dépend surtout d'un ou deux mois.
- **Peu de trades** : environ 90 par an sur 5 paires, 160 par an sur 10 paires. Plus de paires = plus de signaux.
- Les entrées se font pendant des chutes rapides : le glissement réel peut dépasser 0,05 %. Avec 0,10 %/ordre,
  elle reste positive (+56 USDT sur la confirmation, +14 USDT sur 2022) mais la marge se réduit.
- Backtest ≠ réel : files d'attente d'ordres, pannes d'exchange et délais ne sont pas simulés.

## Candidats écartés ou de référence
NostalgiaForInfinity X7 (lot 2, très coûteux et conçu pour des positions de plusieurs jours), sélection de
freqtrade-strategies (lot 2), HUGE collection (écartée : 480 fichiers sans licence, risque de sélection après coup),
Momentum SashRajj (écartée : rotation de portefeuille, pas de l'intraday), résultats nishu88, awesome-systematic-trading,
trading-backtest (références, pas de stratégie testable). Détails : `candidates.yaml`.

## Prochaines étapes avant toute validation
1. **Paper trading « en avant »** de V5 / 45 min sur les 15 paires : des données que personne n'a encore vues,
   pendant 4 à 8 semaines, avec le même moteur.
2. Comparer chaque semaine le paper trading au backtest (nombre de trades, gain moyen, glissement réel).
3. Lot 2 (NostalgiaForInfinity, 2-3 stratégies officielles Freqtrade) avec les mêmes critères.
4. Aucun argent réel sans accord explicite de l'utilisateur.
