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

_Résultats en cours d'exécution sur GitHub (EUR/USD 2015 → 08/2023 + 09/2024 → 08/2026) — section complétée dès la fin du run._

## 5. Finalistes

Aucun pour l'instant.

## 6. Compte démo MT5

Non lancé : aucune stratégie n'a passé les contrôles. Préparation existante (branche `test/oss-eurusd`) : script de
test MT5 et workflow Windows, bloqués tant qu'aucun compte démo n'est fourni (secrets `MT5_LOGIN`, `MT5_PASSWORD`,
`MT5_SERVER`).

## 7. Prochaines actions

1. Terminer la lecture des 10 méthodes documentées et appliquer les critères du protocole.
2. Si une méthode passe : ouvrir l'OOS vierge 09/2023 → 08/2024 (un seul essai), puis écrire l'EA MT5.
3. Sites restant à lire avec l'autorisation de l'utilisateur dans le navigateur : eToro, Myfxbook (pages de comptes),
   Darwinex, FX Blue, Forex Factory.
