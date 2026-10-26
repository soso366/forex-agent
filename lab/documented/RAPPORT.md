# IA TRADING V2 — Recherche élargie : tableau de bord

Branche `research/documented-strategies` (robot principal non modifié, simulation uniquement, aucun trading réel).
Mis à jour le 26/10/2026.

## 1. Sources consultées

| Plateforme | Accès | Ce qui a pu être lu |
|---|---|---|
| MQL5 Signals | ✅ public + historiques exportés par l'utilisateur | pages de 38 comptes, listes (85 comptes), 13 historiques trade par trade |
| ZuluTrade | ✅ via le navigateur de l'appli Claude (API publique) | 32 leaders : réel/démo, semaines, drawdown, paires, description |
| Myfxbook | ⚠️ liste `/systems` seulement ; pages de comptes refusées en lecture automatique ; navigateur : autorisation du site en attente | 15 systèmes (gain, drawdown) |
| cTrader Copy | ⚠️ liste partielle | 20 fournisseurs (ROI, ancienneté, symbole) — pas de drawdown ni de trades |
| Collective2 | ✅ mais **toutes les performances sont hypothétiques** (indiqué par le site) | 35 stratégies, dont 1 forex |
| eToro | ❌ page en JavaScript ; navigateur : autorisation du site en attente | — |
| Darwinex | ❌ pas de liste publique lisible | — |
| FX Blue | ❌ statistiques chargées en JavaScript ; pages « printable » partielles et anciennes | — |
| Forex Factory | ❌ refusé par le site | — |

Aucune restriction d'accès n'a été contournée.

## 2. Comptes étudiés : 225

Détail : `catalogue_comptes.csv` (lien, source, niveau de confiance, type de compte, ancienneté, instruments, trades, PF,
drawdown, règles publiques, risque, décision, raisons).

| Niveau de confiance | Signification | Comptes |
|---|---|---|
| A | historique trade par trade exporté et analysé | 13 |
| B | page détaillée lue (MQL5, ZuluTrade) | 57 |
| C | ligne de liste MQL5 | 85 |
| D | liste avec rendement/ancienneté seulement (cTrader, Myfxbook) | 35 |
| H | performance hypothétique (Collective2) | 35 |

**Comptes retenus : 0.** Raisons principales : règles non publiées, drawdown > 15 %, EUR/USD non dominant,
gestion à risque non borné (renforts de positions perdantes, grilles, martingales — mesurés sur les 13 historiques :
de 25 % à 70 % des entrées sont des ajouts à un prix plus mauvais chez 12 d'entre eux), performances hypothétiques.

## 3. Stratégies identifiées

Aucun trader ne publie de règles reproductibles. Les 10 méthodes testées sont des méthodes **publiées en entier**
(voir `PROTOCOLE.md`, écrit avant les données) :
Turtle S1 et S2, règle des 4 semaines (Donchian), momentum 12 mois (Moskowitz et al. 2012), SMA 50/200,
RSI(2) de Connors, Dual Thrust, effet de session (Breedon & Ranaldo 2011), NR7 et « stretch » (Crabel).

Hypothèses déduites de l'historique des traders (classées à part, ce ne sont pas leurs stratégies) :
H-K, H-E, H-T (`lab/traders_eurusd`) et H-C sur paires calmes (`lab/calm_pairs`).

## 4. Stratégies testées et éliminées

### Hypothèses H-C, paires calmes (données Dukascopy 09/2024 → 08/2026, backtest exécuté sur GitHub)

| Paire | Entraînement | Validation | Walk-forward | Décision |
|---|---|---|---|---|
| AUD/CAD | PF 0,79, −15,7 % | PF 0,67, −29,2 % | PF 0,78, 55 trades, 1/4 trimestre + | Rejetée |
| NZD/CAD | PF 0,52, −40,9 % | PF 0,42, −48,9 % | PF 0,42, 56 trades, 0/4 | Rejetée |
| AUD/NZD | PF 0,39, −38,1 % | PF 0,38, −59,3 % | PF 0,40, 75 trades, 0/4 | Rejetée |

Lecture : sans renfort de positions, le retour à la moyenne avec un vrai stop perd nettement sur ces paires ; les
excès de prix ont souvent continué (taux de réussite 21-31 % pour un objectif ≈ 2 × le stop). Le résultat des
traders de ces paires vient de leur moyenne à la baisse, pas d'un avantage d'entrée.

### Hypothèses H-K / H-E / H-T (EUR/USD) — rejetées (voir `lab/traders_eurusd/README.md`).

### 10 méthodes documentées

Exécuté sur GitHub (run 40278185796), EUR/USD Dukascopy M1 bid/ask, 01/2015 → 08/2023 et 09/2024 → 08/2026,
coûts de base (spread réel, 7 $/lot, 0,2 pip). Paramètres de la source, aucune optimisation.
Résultats bruts : `results/documented/results.json` et journaux `results/documented/trades/` (60 journaux recontrôlés
indépendamment : 0 écart).

| Méthode | Entraînement 2015-2020 | Validation 1 (2021-08/2023) | Validation 2 (09/2024-08/2026) | Validation réunie : trades / PF / t | DD max | Années + | Décision |
|---|---|---|---|---|---|---|---|
| Turtle Système 1 | PF 0,51, -39,84 % | PF 0,48, -21,49 % | PF 0,54, -13,92 % | 65 / 0,50 / -2,36 | 22,39 % | 1/12 | Rejetée (PF<1,30, perd avec coûts stressés, DD>15 %, <60 % d'années positives, entraînement négatif, instable, t<2,6) |
| Turtle Système 2 | PF 0,69, -16,00 % | PF 0,23, -19,49 % | PF 0,81, -4,22 % | 32 / 0,50 / -1,32 | 22,70 % | 4/12 | Rejetée (PF<1,30, perd avec coûts stressés, <60 trades, DD>15 %, <60 % d'années positives, entraînement négatif, instable, t<2,6) |
| Donchian 4 semaines | PF 0,53, -15,32 % | PF 0,42, -11,15 % | PF 2,17, 6,18 % | 47 / 0,80 / -0,59 | 12,88 % | 4/12 | Rejetée (PF<1,30, perd avec coûts stressés, <60 trades, <60 % d'années positives, entraînement négatif, instable, t<2,6) |
| Momentum 12 mois | PF 0,94, -3,47 % | PF 1,02, 0,92 % | PF 0,48, -17,92 % | 58 / 0,77 / -0,85 | 20,76 % | 4/12 | Rejetée (PF<1,30, perd avec coûts stressés, <60 trades, DD>15 %, <60 % d'années positives, entraînement négatif, instable, t<2,6) |
| SMA 50/200 | PF 1,12, 1,70 % | PF 2,04, 5,34 % | PF 0,32, -8,97 % | 9 / 0,80 / -0,25 | 16,39 % | 7/12 | Rejetée (PF<1,30, perd avec coûts stressés, <60 trades, DD>15 %, <60 % d'années positives, instable, t<2,6) |
| RSI(2) Connors | PF 0,98, -0,31 % | PF 1,02, 0,23 % | PF 0,39, -4,78 % | 50 / 0,75 / -0,71 | 7,23 % | 6/12 | Rejetée (PF<1,30, perd avec coûts stressés, <60 trades, <60 % d'années positives, entraînement négatif, instable, t<2,6) |
| Dual Thrust | PF 0,84, -16,96 % | PF 0,82, -9,99 % | PF 1,07, 2,36 % | 254 / 0,91 / -0,52 | 15,72 % | 4/12 | Rejetée (PF<1,30, perd avec coûts stressés, DD>15 %, <60 % d'années positives, entraînement négatif, instable, t<2,6) |
| Effet de session | PF 1,05, 21,69 % | PF 0,95, -6,87 % | PF 0,85, -13,70 % | 2422 / 0,92 / -1,54 | 15,83 % | 4/12 | Rejetée (PF<1,30, perd avec coûts stressés, DD>15 %, <60 % d'années positives, t<2,6) |
| NR7 (Crabel) | PF 1,04, 3,74 % | PF 0,98, -0,90 % | PF 0,97, -0,68 % | 182 / 0,97 / -0,14 | 6,97 % | 6/12 | Rejetée (PF<1,30, perd avec coûts stressés, <60 % d'années positives, t<2,6) |
| Stretch (Crabel) | PF 0,82, -89,92 % | PF 0,89, -55,06 % | PF 0,77, -58,20 % | 1207 / 0,84 / -2,13 | 66,87 % | 0/12 | Rejetée (PF<1,30, perd avec coûts stressés, DD>15 %, <60 % d'années positives, entraînement négatif, instable, t<2,6) |

Lecture : **aucune des 10 méthodes publiées ne gagne de façon fiable sur l'EUR/USD avec des coûts réalistes.**
Les plus proches de l'équilibre (NR7, Dual Thrust en 2024-2026, effet de session sur 2015-2020) restent sous un PF de
1,1 et redeviennent perdantes sur les autres périodes. L'effet de session de Breedon & Ranaldo, net en 1997-2007,
ne survit plus après les coûts : légèrement positif en 2015-2020 (PF 1,06), négatif ensuite. Le Donchian gagne en
2024-2026 (PF 2,17) mais perd sur 2015-2023 : instable.

## 5. Finalistes

**Aucun.** Aucune stratégie n'a passé les contrôles ; l'OOS vierge 09/2023 → 08/2024 reste fermé.

## 6. Compte démo MT5

Non lancé : aucune stratégie n'a passé les contrôles. Préparation existante (branche `test/oss-eurusd`) : script de
test MT5 et workflow Windows, bloqués tant qu'aucun compte démo n'est fourni (secrets `MT5_LOGIN`, `MT5_PASSWORD`,
`MT5_SERVER`).

## 7. Prochaines actions

1. Ne pas programmer d'EA MT5 ni de compte démo : aucune stratégie ne le justifie.
2. Pistes restantes, à décider : (a) EUR/USD n'offre pas d'avantage simple exploitable après coûts sur les méthodes
   publiées testées — envisager des horizons plus longs ou d'autres actifs ; (b) laisser le robot crypto en simulation
   comme prévu ; (c) toute nouvelle idée passe par le même protocole (règles écrites avant les données).
3. Sites restant à lire avec l'autorisation de l'utilisateur dans le navigateur : eToro, Myfxbook (pages de comptes),
   Darwinex, FX Blue, Forex Factory.
