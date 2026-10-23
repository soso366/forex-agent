# IA TRADING V2 — Phase V3 : rapport de recherche (23/10/2026)

Objectif : trouver une stratégie Forex robuste, sans dépense ni API payante, avant toute démo.
Protocole écrit avant les calculs : `PROTOCOLE_V3.md` (commit 5cce3b8). Audit du moteur : `AUDIT_V3.md`.
Coûts inclus partout : spread bid/ask réel Dukascopy + commission 3 $/lot/côté + 0,1 pip de glissement ; 2 positions max.
Optimisation : sept. 2024 → août 2025 (IS). Validation unique : sept. 2025 → août 2026 (VAL).

## Tableau comparatif

| | H1 Fix de Tokyo USDJPY | H2 Momentum filtré par la volatilité | H3 Cassure du range asiatique |
|---|---|---|---|
| Source principale | Krohn, Mueller & Whelan (J. of Finance), 1999-2019 : renversement 4,8 bp/jour, t 10 | Gao, Han, Li & Zhou (JFE 2018), actions US ; RUB/USD ; futures chinois | Script TradingView « London BreakOut Classic », Backtrex, Crabel |
| Preuve publiée sur nos paires | Oui (JPY), mais **effet bien plus faible en 2014-2019**, résultats bruts | **Aucune** sur EURUSD/GBPUSD/USDJPY | **Négative** (Backtrex 2016-2026 : PF 0,87) |
| Configuration choisie sur IS | vente 00:56 UTC, 4 h, jours gotobi | signal 17:00 NY → 08:30 Londres, tenue 15:30-16:00 Londres, volatilité > médiane | range 00:00-06:00 UTC, entrée avant 10:00, stop bord opposé, objectif 2R |
| IS (optimisation) | 77 trades, **+11,1 pips/trade**, PF 2,38, t 2,96 | 246 trades, **+2,3 pips/trade**, PF 1,55, t 2,06 | 498 trades, **0,0 pip/trade**, PF 1,00, t 0,01 |
| Validation | 77 trades, **−2,9 pips/trade**, PF 0,71, t −1,06 | 288 trades, **−2,8 pips/trade**, PF 0,52, t −3,42 | non consommée (échec dès l'optimisation) |
| Semestres de validation | +2,8 / −8,4 pips/trade | −1,9 / −4,0 pips/trade | — |
| Configurations positives (IS → VAL) | 14/18 → **0/18** | 4/12 → **0/12** | 1/16 en IS |
| Version exacte de la source | IS −2,1 pips/trade (brut −1,0) ; VAL −3,6 (brut −2,5), t −3,2 | — | — |
| Sensibilité (validation) | négative même sans commission (−2,0) | négative même sans commission (−2,1) | — |
| Risques | 1 paire, 1 trade/jour, effet de calendrier en déclin, interventions BoJ (sauts de 50+ pips) | effet qui change de signe d'une année à l'autre ; corrélation USD entre paires | coût ≈ gain brut ; drawdown 1 021 pips en IS |
| **Verdict** | **ÉCHEC (validation)** | **ÉCHEC (validation)** | **ÉCHEC (optimisation)** |

Vérifications indépendantes : le renversement de H2 est confirmé par un calcul séparé du moteur (EURUSD : +2,1 pips/jour,
t 2,9 en IS ; −1,0, t −1,7 en VAL ; GBPUSD : +2,8, t 3,5 → −1,5, t −1,8). Fichiers : `results/v3_H1.json`, `v3_H2.json`, `v3_H3.json`.

## Ce que montrent ces résultats
- H1 et H2 ont le profil type du **sur-apprentissage** : excellents sur l'année d'optimisation, **aucune** des 18 et
  12 variantes n'est positive sur l'année suivante. Un paramétrage plus fin n'y changerait rien.
- Le fix de Tokyo, très solide sur 1999-2019 dans la littérature, est **absent ou inversé en 2024-2026**, même avant coûts.
- La cassure de session n'a même pas d'avantage sur l'année d'optimisation : le gain brut (≈ 0,9 pip) est mangé par les coûts.

## Bilan Forex intraday à ce jour
20 idées testées avec des règles fixées à l'avance, toutes en échec : 9 hypothèses des agents (E000-E009), 8 stratégies
open source (lot 1) et ces 3 hypothèses documentées. Les rares résultats positifs sur une période disparaissent sur la suivante.

## Recommandation : **abandon de ces trois stratégies ; pas de passage en démo ; recherche Forex intraday mise en pause**
1. **Aucune** des trois ne va en démo : aucune ne passe la validation, et le protocole interdit de les « réparer » avec les
   mêmes données.
2. La confirmation 2020-2023 n'est plus nécessaire pour ces trois-là (elle ne sert qu'aux stratégies qui réussissent la validation).
   Les données 2020-2023 restent utiles pour toute idée future.
3. Ne relancer une recherche Forex que sur un **fait nouveau** : une source de données différente (calendrier économique
   gratuit et fiable, positionnement des traders), ou un horizon plus long que 4 h si la règle du projet est assouplie.
4. Priorité au **robot crypto en paper trading** (seule piste qui a passé des tests hors échantillon), sans argent réel.
5. Comparaison avec MetaTrader 5 (facultative, gratuite) : si l'utilisateur exporte le rapport du testeur MT5 de l'EA
   « MACD Sample » (EURUSD H1), on pourra comparer les transactions une à une avec F01.
