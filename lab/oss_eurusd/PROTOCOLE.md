# Protocole pré-enregistré — test de 4 projets GitHub EUR/USD

Écrit **avant** le premier lancement des backtests (25/10/2026). Rien ici ne sera modifié après avoir vu les résultats.

## Règles

- Branche isolée `test/oss-eurusd`. Le robot principal (`forex_agent/`, `config/`, Risk Manager) n'est pas touché.
- Simulation uniquement. Aucun broker, aucune clé, aucun trading réel.
- Stratégies et paramètres **d'origine**, sans optimisation ni choix de période après coup. Un test automatique compare les paramètres utilisés avec ceux lus dans les fichiers `.mq5` d'origine (commit figé dans `sources.json`).
- Les résultats publiés par les auteurs ne sont jamais présentés comme nos résultats.

## Données

- EUR/USD, Dukascopy, bougies M1 BID et ASK réelles (dépôt privé `soso366/forex-data`).
- **Entraînement** : 01/09/2024 → 31/08/2025. **Validation** : 01/09/2025 → 31/08/2026.
- Chaque période est un test séparé : capital neuf de 10 000 $, état de l'EA remis à zéro. Les indicateurs utilisent l'historique antérieur disponible (comme le testeur MT5).
- La période 09/2023 → 08/2024 (OOS vierge du projet) **n'est pas lue**.
- Aucune stratégie n'est réglée ici : « entraînement » et « validation » sont deux périodes indépendantes qui servent à vérifier la stabilité.

## Exécution simulée

- Bougies H1 / M5 reconstruites à partir du M1 (heures UTC). Indicateurs calculés comme MT5 (RSI de Wilder, Bandes de Bollinger à écart-type de population, ATR = moyenne simple du True Range), sur le prix BID comme un graphique MT5.
- Décision à l'ouverture de la bougie suivante, avec les bougies clôturées uniquement.
- Achat au ASK, vente au BID (spread réel minute par minute).
- Stop et objectif suivis minute par minute. Stop et objectif touchés dans la même minute : **stop d'abord**, et le cas est compté.
- Coûts **de base** : spread réel + commission 7 $ par lot aller-retour + glissement défavorable 0,2 pip sur chaque ordre au marché (entrée, stop, sortie au temps). L'objectif (ordre limite) n'a pas de glissement.
- Coûts **stressés** : spread réel + commission 9 $ par lot + glissement 0,5 pip.
- Heure serveur : UTC (heure du serveur Exness, broker visé par smizxe). Variante de contrôle UTC+2/+3 (heure serveur la plus courante) pour le filtre horaire de sbrakni.
- Compte en USD, valeur du pip 10 $ par lot, pas de lot 0,01, minimum 0,01. Swaps non simulés (positions de quelques heures).

## Critère de décision (fixé à l'avance)

Une stratégie n'est retenue « à approfondir » que si, **avec les coûts de base, sur l'entraînement ET sur la validation** :
1. profit factor ≥ 1,20 ;
2. au moins 30 transactions par période ;
3. drawdown maximum ≤ 20 % ;
4. résultat net positif aussi avec les coûts stressés.

Sinon : **rejetée** pour EUR/USD. Une stratégie retenue n'est pas pour autant prouvée : il faudrait ensuite l'OOS vierge et un contrôle par backtest-auditor avant toute démo.
