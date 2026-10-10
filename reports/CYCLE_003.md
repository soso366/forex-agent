CYCLE #3
Hypothèses testées : E003 Stratégies publiques classiques — P1 Bollinger+RSI, P2 croisement EMA 9/21 + pente H1, P3 RSI(2) Connors (demande de l'utilisateur, avec compte 50 € à 1 % et 2 %)
Rejetées : P1, P2, P3 (Train)
En validation : aucune
En OOS : aucune
Meilleure piste : aucune ; P1/P2 battent le placebo sens aléatoire mais ≈ 0 R, négatives dès +0,5 pip
Problème principal : à 30 min, le spread absorbe tout l'avantage des règles publiques ; avec 50 € le lot minimum 0,01 rend la règle de 1 % presque inapplicable
Décision du Manager : E003 REJECT ; risque 2 % non adopté (aucun changement du Risk Manager / baseline)
Prochaine expérience : cycle 4 : Researcher ; OOS 2023-2024 reste verrouillé
Fichiers/branches modifiés : branche research-public-strategies (depuis multi-agent-research) ; experiments/E003-*, memory/EXPERIMENTS.md, memory/REJECTED_HYPOTHESES.md, memory/PROJECT_STATE.md, orchestrator/state.json, reports/CYCLE_003.md

## Compte de 50 € (24 mois, variante sélectionnée de chaque stratégie, équité finale)
| Stratégie | 1 % spread brut | 1 % +0,5 pip | 2 % spread brut | 2 % +0,5 pip |
|---|---|---|---|---|
| P1 BB+RSI | 42,88 € | 29,07 € | 28,95 € | 32,29 € |
| P2 EMA 9/21 | 28,54 € | 31,89 € | 29,06 € | 30,58 € |
| P3 RSI2 | 31,17 € | 29,24 € | 28,75 € | 31,86 € |
Sous ≈ 29 € le compte ne peut plus ouvrir 0,01 lot à 30:1 (arrêt).
