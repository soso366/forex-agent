# Test de 4 projets GitHub de stratégies EUR/USD — rapport

Branche isolée `test/oss-eurusd`. Robot principal non modifié. Simulation uniquement, aucun trading réel.
Protocole fixé avant les calculs : [PROTOCOLE.md](PROTOCOLE.md). Résultats bruts : `results/oss_eurusd/`.

## Verdict

**Aucune des trois stratégies testables ne passe le critère. Les trois sont rejetées pour EUR/USD.**
Les deux autres projets n'ont pas pu être testés ici (MetaTrader 5 sous Windows indispensable).

## Résultats obtenus par nos tests (EUR/USD, Dukascopy M1 bid/ask réels, coûts de base)

Capital 10 000 $, risque 1 % par trade (paramètres d'origine). Spread réel + 7 $/lot + glissement 0,2 pip.

| Stratégie | Période | Trades | Profit factor | Rentabilité | Drawdown max | Réussite |
|---|---|---|---|---|---|---|
| smizxe RsiLevel (H1) | Entraînement 09/24→08/25 | 187 | 0,81 | −22,3 % | 34,3 % | 29,9 % |
| | Validation 09/25→08/26 | 142 | 0,86 | −13,4 % | 22,7 % | 31,7 % |
| smizxe RsiReversal (H1) | Entraînement | 147 | 0,81 | −18,4 % | 28,3 % | 29,9 % |
| | Validation | 121 | 0,81 | −14,4 % | 20,3 % | 30,6 % |
| sbrakni MeanReversion (M5) | Entraînement | 139 | 0,93 | −7,1 % | 21,5 % | 37,4 % |
| | Validation | 132 | 0,83 | −17,2 % | 26,5 % | 26,5 % |

Coûts stressés (9 $/lot, glissement 0,5 pip) : RsiLevel −25,4 % / −16,3 % ; RsiReversal −21,4 % / −17,3 % ;
MeanReversion −19,6 % / −30,1 %. Aucun t-stat positif ; aucun cas stop/objectif ambigu dans la même minute.

Contrôles (mêmes paramètres, seule la convention change) : MeanReversion avec heure serveur UTC+2/+3 →
PF 0,81 / 0,84 ; avec le fichier `.set Best` (spread max 1 pip au lieu de 3) → PF 0,92 / 0,83. Conclusion inchangée.

Petit capital (150) : les deux EA smizxe ne prennent **aucune** position (lot calculé < 0,01, l'EA refuse) ;
MeanReversion force le lot minimum 0,01 (risque réel supérieur à 1 %) et reste perdant (PF 0,90 / 0,86).

## Résultats publiés par les auteurs (NON vérifiés, NON obtenus par nous)

| Projet | Ce que l'auteur annonce | Remarque |
|---|---|---|
| smizxe RsiReversal | EURUSDm H1, 01–06/2024 : 57 trades, PF 1,45, +1 563 $, DD 6,8 % | Période située dans notre OOS vierge (non lue). Six mois seulement. |
| NadirAli AutoLot20Pip | EURUSD M5, 01/2025–09/2026 : 19 trades, PF 1,37, +189,59 $, DD 4,38 % | 19 trades : échantillon trop petit pour conclure. |
| sbrakni MeanReversion | 3 ans : 344 trades, PF 1,51, +262 %, DD 16,4 % | Obtenu sur des **données synthétiques** générées par l'auteur. Son propre rapport « données réelles » affiche 0 trade. |
| NYAO Scalper | Or (XAUUSD) : +93,8 % sur 9 mois | L'auteur écrit lui-même qu'EUR/USD a perdu −49 % dans son test. |

## Fichiers, licences et anomalies

| Projet | Licence | Contenu | Testé ici ? |
|---|---|---|---|
| smizxe/mt5-agent-toolkit | MIT | 2 EA RSI en source (.mq5) + outils PowerShell | Oui |
| NadirAliOfficial/eurusd-scalper-ea | Propriétaire, binaire seul, décompilation interdite | Uniquement `AutoLot20PipScalper_v2.ex5` (version d'essai limitée dans le temps) | Non — MT5 requis, règles incomplètes |
| sbrakni/mean-reversion-mql5 | **Aucune licence** (tous droits réservés) | EA .mq5 + moteur Python + rapports | Oui |
| elrizwiraswara/nyao_scalper_mt5 | BSD 3-Clause | EA de 8 185 lignes, réglé pour l'or | Non — MT5 requis, non conçu pour EUR/USD |

Anomalies relevées dans le code d'origine (non corrigées, conformément à la consigne) :
- **sbrakni** : l'EA lit `symInfo.Ask()` / `Bid()` sans jamais appeler `RefreshRates()`. En MT5, ces prix restent probablement à 0, ce qui ferait rejeter les achats (stop négatif) et bloquer les ventes. L'EA tel que publié risque donc de ne prendre aucun trade. Nos tests utilisent la logique documentée avec les vrais prix ; à confirmer dans MT5.
- **sbrakni** : stop à 1,5 × ATR M5 souvent de 1 à 3 pips → lots très gros (jusqu'à ~7 lots sur 10 000 $) et coûts qui pèsent lourd.
- **NYAO** : distances écrites en points d'or (stop de 20 $) et remises à l'échelle automatiquement ; appliquées telles quelles à EUR/USD, elles n'ont plus de sens. Il faudrait inventer des réglages, ce qui sortirait de « paramètres d'origine ».

## Ce qui bloque pour NadirAli et NYAO

1. Ils ne tournent que dans le **testeur MetaTrader 5 sous Windows** (pas disponible ici).
2. Le testeur exige d'être **connecté à un compte** : il faut un **compte DÉMO** MT5 (je ne peux pas en créer un pour vous).
3. Tout est prêt : `mt5/run_mt5_tests.ps1`, fichiers `.set` d'origine et le workflow GitHub `oss-eurusd-mt5.yml` (Windows). Il suffit d'ajouter les secrets `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER` (démo ; le script refuse un serveur non démo) puis de modifier `mt5/trigger.txt`. Non testé à ce jour : l'installation silencieuse de MT5 sur GitHub et le téléchargement des ticks réels (plusieurs Go) peuvent échouer ; le binaire NadirAli d'essai peut être expiré.

## Tests automatiques

Workflow `oss-eurusd-tests.yml` (à chaque modification de ce dossier sur la branche) : tests du moteur
(indicateurs MT5, coûts, stop d'abord, absence de look-ahead), téléchargement des sources au commit figé,
contrôle que les paramètres sont identiques aux fichiers d'origine, puis rejeu complet des backtests et
vérification qu'ils redonnent exactement ces résultats.
