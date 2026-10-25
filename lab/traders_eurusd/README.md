# IA Research Engine — 30 comptes de traders EUR/USD : rapport final

Branche isolée `research/traders-eurusd`. Robot principal non modifié. Simulation uniquement, aucun trading réel.
Fichiers : `accounts.json` (fiches), `classement.csv` / `classement.md` (classement), `PROTOCOLE.md`
(écrit avant les backtests), `hypotheses.py`, `wf.py`, résultats dans `results/traders_eurusd/`.

## Verdict

- **Aucun des 30 comptes ne remplit tous les critères** (réel, ≥ 12 mois, PF ≥ 1,30, DD < 15 %, ≥ 300 trades,
  majoritairement EUR/USD, sans martingale ni grille). Le point qui fait le plus souvent échouer : le drawdown
  sur equity (pertes latentes), souvent bien plus élevé que le drawdown sur le solde affiché en avant.
- **Aucun des 5 traders retenus ne publie ses règles.** Leurs stratégies ne sont donc pas reproductibles ;
  il est impossible d'en faire un backtest fidèle, et aucun backtest « de leur stratégie » n'a été fait.
- **Nos 3 hypothèses inspirées de leurs profils ont toutes été rejetées** par le protocole fixé à l'avance.
  Aucune n'a passé nos tests. L'OOS vierge 09/2023 → 08/2024 reste fermé.

## Accès aux sources

| Source | Résultat |
|---|---|
| MQL5 Signals | Pages publiques lisibles (statistiques, symboles, descriptions). Historique trade par trade et export : **connexion obligatoire**. |
| Myfxbook | Pages de comptes **refusées** à la lecture automatique (erreur du site) ; seule la liste `/systems` s'affiche, sans liens ni nombre de trades. |
| FX Blue | Statistiques chargées en JavaScript : **non lisibles** ; pages « printable » partielles et anciennes (2019-2022). |
| Forex Factory (Trade Explorer) | **Refusé** par le site. |

Les 30 comptes viennent donc tous de MQL5 Signals. Tous les chiffres sont recopiés des pages publiques
(25/10/2026) ; « réel » est déduit du nom du serveur (Live/Real), MQL5 ne l'écrivant pas explicitement.

## Classement des 30 comptes

Voir `classement.md` (tableau complet avec liens). Les 15 premiers non exclus :

| Rang | Compte | Semaines | PF | Pire DD % | Trades | EUR/USD % | Ce qui manque |
|---|---|---|---|---|---|---|---|
| 1 | [EansPRO V3 EURUSD](https://www.mql5.com/en/signals/2378489) | 195 | 2,37 | 21,2 | 1 484 | 100 | DD |
| 2 | [LazyPro v23 EURUSD](https://www.mql5.com/en/signals/2378484) | 192 | 2,32 | 15,7 | 1 604 | 100 | DD |
| 3 | [TP TRADER](https://www.mql5.com/en/signals/1932739) | 358 | 1,62 | 8,9 | 14 719 | 35 | part EUR/USD |
| 4 | [Kosciuszko HR](https://www.mql5.com/en/signals/1858780) | 192 | 2,32 | 24,0 | 5 723 | 46 | DD, part EUR/USD |
| 5 | [Kosciuszko](https://www.mql5.com/en/signals/1750957) | 210 | 2,30 | 15,7 | 6 713 | 44 | DD, part EUR/USD |
| 6 | [Van PM](https://www.mql5.com/en/signals/2391620) | 105 | 1,59 | 7,2 | 1 923 | 23 | serveur non indiqué, part EUR/USD |
| 7 | [EUR Trader 2](https://www.mql5.com/en/signals/2367606) | 82 | 3,89 | 21,7 | 288 | 97 | DD, < 300 trades |
| 8 | [EURUSD121](https://www.mql5.com/en/signals/2341798) | 86 | 2,07 | 38,5 | 1 177 | 99 | DD |
| 9 | [WolvesVN EU](https://www.mql5.com/en/signals/2385213) | 318 | 1,49 | 17,4 | 2 349 | 69 | DD |
| 10 | [EURUSD Quant Signal](https://www.mql5.com/en/signals/2350829) | ? | 3,64 | 12,9 | 320 | 100 | chiffres présentés comme backtest |
| 11 | [DARK HOLE AZ v1 EU](https://www.mql5.com/en/signals/2311566) | 86 | 1,98 | 46,2 | 2 494 | 100 | DD |
| 12 | [EURUSD Algo Trading](https://www.mql5.com/en/signals/2379670) | 35 | 1,79 | 35,9 | 2 029 | 100 | < 12 mois, DD |
| 13 | [SFE Portfolio1](https://www.mql5.com/en/signals/138420) | 573 | 1,44 | 23,0 | 3 343 | 4 | DD, part EUR/USD |
| 14 | [EEVCC Night IC 6](https://www.mql5.com/en/signals/2361862) | 278 | 1,33 | 9,6 | 6 416 | 11 | part EUR/USD |
| 15 | [IcmLowLeverage](https://www.mql5.com/en/signals/2200565) | 180 | 7,89 | 32,1 | 336 | 17 | DD, part EUR/USD |

Exclus d'office (martingale, grille ou renfort déclarés par l'auteur ou visibles dans son texte) :
Expert EURUSD Sys01/02/03, GrattMarMic, EU Zone Arsenal, Couple, TT ic 001.

Points d'attention publiés : EansPRO et LazyPro ont un meilleur trade ≈ 170 fois le gain moyen (résultat
possiblement porté par quelques trades) ; EUR Trader 2 affiche une charge de dépôt maximale de 87,77 % ;
Van PM a un pire trade de −5 920 $ contre un gain moyen de 143 $.

## Les 5 traders étudiés en détail

| Trader | Règles publiées (confirmé) | Ce que montrent les statistiques (pas des règles) | Reproductible ? |
|---|---|---|---|
| Kosciuszko | 8 robots aux réglages différents, retournements sur paires EUR, arrêt des nouvelles positions à 30 % de DD | ~81 % de réussite, perte moyenne ≈ 2 × gain moyen, ~2 jours par trade | Non |
| EUR Trader 2 | « EUR/USD uniquement, capital d'abord », manuel | ~80 % de réussite, gain ≈ perte, ~4 jours, 47 % achats / 53 % ventes | Non |
| TP TRADER | Aucune | ~49 % de réussite, gain ≈ 1,67 × perte, ~3 h | Non |
| EansPRO V3 / LazyPro v23 | Aucune (même slogan, même broker XM : probablement le même auteur — déduction) | 71-77 % de réussite, 1-2 jours, EUR/USD 100 % | Non |
| WolvesVN EU | Aucune | ~69 % de réussite, perte moyenne > gain moyen, ~5 jours | Non |

## Backtests réellement exécutés (nos hypothèses, pas leurs stratégies)

EUR/USD Dukascopy M1 bid/ask réels, 09/2024 → 08/2026, spread réel + 7 $/lot + 0,2 pip. Risque 1 %.

| Hypothèse (inspirée de) | Défaut entraînement | Défaut validation | Walk-forward hors échantillon | Décision |
|---|---|---|---|---|
| H-K retournement court (Kosciuszko) | 242 trades, PF 0,89, −8,7 % | 244 trades, PF 0,60, −34,7 % | 89 trades, PF 0,79, −7,0 %, 2/4 trimestres | **Rejetée** |
| H-E repli dans la tendance (EUR Trader 2) | 54 trades, PF 1,27, +6,4 % | 67 trades, PF 1,11, +3,5 % | 40 trades, PF 1,34, +5,8 %, DD 3,1 %, t = 0,91, 2/4 trimestres | **Rejetée** |
| H-T cassure de Londres (TP TRADER) | 200 trades, PF 0,72, −16,8 % | 204 trades, PF 0,61, −21,7 % | 204 trades, PF 0,87, −11,3 %, 1/4 trimestre | **Rejetée** |

H-E est la seule hypothèse positive partout, y compris avec coûts stressés (walk-forward +4,95 %), mais elle échoue
sur trois critères : trop peu de trades (40 < 60), t-stat 0,91 (< 2, donc indiscernable du hasard) et seulement 2
trimestres positifs sur 4. C'est une piste faible, pas une stratégie validée. 24 combinaisons ont été essayées au total.

Contrôles effectués : tests d'absence de look-ahead (modifier le futur ne change aucune décision passée), journée
D1 close à 17 h New York, recalcul indépendant des profit factors depuis les journaux de trades, aucun chevauchement
de positions, aucun cas stop/objectif ambigu dans la même minute.

## Ce qui débloquerait la suite

1. Un compte MQL5 (gratuit) permettrait d'exporter l'historique trade par trade de ces signaux : on pourrait alors
   déduire des règles (heures, déclencheurs) avec un vrai échantillon. Je ne peux pas créer ce compte à votre place.
2. Les backtests MT5 demandent Windows + un compte démo (workflow déjà préparé sur la branche `test/oss-eurusd`).
