# E003 — Stratégies publiques classiques (BB+RSI, EMA 9/21, RSI2 Connors) et petit compte 50 €
Auteur : RESEARCHER · cycle 3 · 2026-10-10 · demande directe de l'utilisateur

## Origine
L'utilisateur demande si les stratégies qu'on trouve gratuitement sur GitHub (bots d'exemple freqtrade, EA MT4/MT5,
tutoriels) peuvent servir à faire grossir un petit compte, et veut voir l'effet d'un risque « un peu plus élevé »
(2 % au lieu de 1 %). Trois familles parmi les plus copiées, chacune = une hypothèse distincte (max 3 par cycle).

## Mécanismes supposés (un par hypothèse)
- **P1 — Bollinger(20,2) + RSI(14), retour à la moyenne** : après un excès de court terme (clôture hors bande ET RSI
  extrême), les preneurs de liquidité impatients ont poussé trop loin ; les teneurs de marché ramènent le prix vers la
  moyenne. Stratégie d'exemple la plus répandue des bots retail.
- **P2 — Croisement EMA 9/21 dans le sens de la tendance H1** : le momentum de court terme, aligné sur la tendance
  horaire, persiste quelques dizaines de minutes (suivi de tendance « MA cross »).
- **P3 — RSI(2) de Connors, repli dans la tendance** : un repli brutal (RSI2 < 10) dans une tendance (prix au-dessus de
  l'EMA 200) est acheté par les participants de tendance ; retour rapide (inverse pour la vente).

## Conditions (objectives, sans futur) — détail chiffré dans protocol.md
- Paires : EURUSD, GBPUSD, USDJPY. Bougies M5 (mid), indicateurs connus à la clôture.
- Heures : 07:00–20:00 UTC (sauf variante « toutes heures » de P1).
- Entrée à l'ouverture de la minute suivant la clôture M5 ; stop ATR obligatoire ; sortie ≤ 30 min.

## Pourquoi 5–30 minutes
Contrainte permanente du projet. Les versions publiques sont souvent en M5–M15 avec sorties rapides.

## Critères falsifiables
Une hypothèse est fausse si, au Train (sept. 2025 → fév. 2026), aucune variante n'a une espérance > 0 après spread réel
avec t ≥ 2, ou si l'effet disparaît avec +0,5 pip de coût, ou s'il dépend d'un trimestre, d'une paire ou de 5 jours.

## Risques d'échec (attendus)
- Les mesures du projet montrent qu'à 30 min les signaux techniques ont un sens ≈ aléatoire et que le spread suffit à
  rendre l'espérance négative (V2, V4-H5). Prior : échec probable pour les trois.
- P1 ressemble à V4-H5 « retour » (≈ −0,03 R) ; P2 à la continuation (V4-H5, négative).

## Partie « mise » (descriptive, pas une hypothèse de signal)
Rejouer les trades de la meilleure variante Train de chaque famille sur un compte de 50 € à 1 % et 2 % de risque, avec les
contraintes réelles d'un petit compte (lot minimum 0,01, levier 30:1). Objectif : montrer ce que change un risque plus
élevé. **Aucune modification du Risk Manager ni de la baseline** : simulation de recherche uniquement.

## Non-doublon
`orchestrator dupcheck` : aucun doublon (bollinger rsi / ema croisement / connors rsi2 pullback).
- ≠ V4-H5 : déclencheur différent (bande + RSI, croisement, RSI2), pas une bougie de displacement. Si P1 ne fait pas
  mieux que V4-H5 « retour », il sera archivé comme tel.
- ≠ V4-H1 / H2 (niveaux de séance), ≠ E001 (relation entre paires), ≠ micro-réglage V2 (aucun paramètre V2 réutilisé).
