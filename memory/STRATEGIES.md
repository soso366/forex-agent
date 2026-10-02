# Stratégies — statut actuel

## Baseline V2 (code sur `main`, `forex_agent/strategies/`) — NE PAS MODIFIER sans accord
| Stratégie | Statut | Preuve (12 mois, 305 trades V2) |
|---|---|---|
| BreakRetest_v2 | DROP (recherche) | 84 trades, −0,03 R ; +0,13 puis −0,20 R selon la période |
| DoubleTopBottom_v1 | DROP | 83 trades, −0,13 R, négative dans les deux périodes |
| FlagBreakout_v1 | DROP | 102 trades, ≈ 0 R |
| TrendPullback_v2 | INSUFFICIENT DATA | 16 trades |
| RangeFade_v2 | MODIFY (piste) | 20 trades ; seule où le sens porte de l'information (miroir +0,42 vs −0,54) |
| SweepMSS_v2 | INSUFFICIENT DATA | ≈ 0 trade |
« DROP » est un verdict de recherche : la baseline reste inchangée tant que l'utilisateur ne décide pas.

## Candidates
| ID | Statut | Règle | Prochaine étape |
|---|---|---|---|
| — | Aucune candidate validée | — | nouvelle hypothèse au cycle 3 |

## Archivées
| ID | Verdict | Résumé |
|---|---|---|
| V4-H3 / E000 fix de Londres | FAIL OOS → REJECT | 577 trades OOS, −0,108 R, PF 0,74 ; ne jamais retester |
| E001 divergence EURUSD-GBPUSD | REJECT (Train) | 78 trades, t 0,87, porté par quelques jours d'annonces |
| E002 choc de spread | REJECT (Train) | 8 trades, portés par 3-4 événements (Fed, BoJ, panne CME) |

## Leçons générales (à respecter dans toute nouvelle stratégie)
- À 5–30 min, la famille **continuation / cassure** est négative (H2, H5, figures V2).
- La famille **retour à la moyenne à heure précise** (H3) a échoué hors-échantillon : les résultats positifs Train/Validation étaient du bruit de sélection et de période.
- Cibles structurelles de swing incompatibles avec 30 min : préférer sortie au temps ou cible ≤ 1–1,5 R.
- L'avantage éventuel est petit (≈ 1 pip) : toujours tester +0,2 à +1 pip de coût.
