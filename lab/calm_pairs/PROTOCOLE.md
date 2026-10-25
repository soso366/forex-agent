# Protocole pré-enregistré — paires « calmes » AUD/CAD, NZD/CAD, AUD/NZD

Écrit le 25/10/2026 **avant** d'avoir les données et avant tout backtest. Non modifiable après lecture des résultats.

## Pourquoi ces paires

Dans la recherche des 30 comptes, plusieurs des historiques les plus longs (Cradle, Black Mountain, Pinnacle Alpha,
MySingalStart, Calm Waters, Steady Long term, LazyProV2 AUDCAD) tradent ces paires en « retour à la moyenne ».
Mais leur drawdown sur equity publié est souvent élevé (16 à 42 %) et un avis public accuse Pinnacle Alpha de renforcer
ses positions perdantes : leurs historiques seront vérifiés trade par trade avant toute conclusion.

## Hypothèse testée (la nôtre, pas la leur) — H-C retour à la moyenne avec stop strict

Chaque paire testée **séparément**. Bougies H1, décision sur bougie clôturée, exécution à l'ouverture suivante.
- Vente si la clôture précédente est au-dessus de la bande de Bollinger haute (20, k) et RSI(14) > 100 − r ;
  achat symétrique.
- Objectif = moyenne de Bollinger au moment de l'entrée (prix fixé). Stop = s × ATR(14) H1. Sortie forcée après 48 h.
- Une seule position par paire, **aucun renfort, aucune grille, aucune martingale**, risque 1 % par trade.
- Si l'objectif est à moins de 0,5 × la distance du stop, l'entrée est ignorée.
- Grille walk-forward : k ∈ {2,0 ; 2,5}, r ∈ {25 ; 30}, s ∈ {1,5 ; 2,5} (8 combinaisons). Défaut : k=2,0, r=30, s=1,5.

## Données, coûts, validation

- Dukascopy M1 BID/ASK réels, 01/09/2024 → 31/08/2026 (export du workflow `export-crosses.yml`).
- Spread réel. Commission 7 $ par lot convertie dans la devise de cotation (taux fixes : 1 USD = 1,37 CAD ; 1 USD = 1,70 NZD).
  Glissement 0,2 pip (stress : 9 $ et 0,5 pip). Résultats exprimés en % du capital (calcul dans la devise de cotation).
- Mêmes étapes que `lab/traders_eurusd` : défaut entraînement 09/2024→08/2025 et validation 09/2025→08/2026,
  puis walk-forward en 4 trimestres (optimisation sur 12 mois, application aux 3 mois suivants).
- Nombre d'essais : 3 paires × 8 combinaisons = 24.

## Critères de réussite par paire (tous obligatoires)

Walk-forward : PF ≥ 1,20, ≥ 60 trades, ≥ 3 trimestres positifs sur 4, DD ≤ 15 %, t-stat ≥ 2,0 ;
défaut positif en entraînement **et** en validation ; walk-forward positif avec coûts stressés. Sinon : rejetée.

## Copie des traders (simulation uniquement)

Pour les traders dont l'historique est fourni, rejeu de leurs vrais trades à l'échelle d'un capital de 150 € (lot
minimum 0,01) pour mesurer ce qu'aurait donné une copie. Jamais d'abonnement payant ni de copie réelle sans
autorisation explicite.
