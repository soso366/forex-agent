# Protocole pré-enregistré — hypothèses inspirées de comptes de traders EUR/USD

Écrit le 25/10/2026 **avant** tout backtest de cette mission. Non modifiable après lecture des résultats.

## Point de départ honnête

Aucun des 5 traders étudiés ne publie ses règles d'entrée et de sortie, et l'historique trade par trade
de MQL5 exige une connexion. Il est donc **impossible de reproduire leurs stratégies**.
Ce qui suit teste **nos propres hypothèses**, construites uniquement à partir des statistiques publiques
de leurs comptes (durée moyenne, taux de réussite, rapport gain/perte, paires). Un résultat positif ou
négatif ne dit rien de la vraie stratégie du trader.

## Hypothèses (règles complètes, fixées maintenant)

Toutes sur EUR/USD, une position à la fois, risque 1 % du capital par trade, stop toujours posé,
pas de martingale, pas de grille, pas de renfort.

**H-K — retournement court (profil Kosciuszko : ~81 % de réussite, perte moyenne ≈ 2 × gain moyen, ~2 jours).**
Bougies H1. Vente si la clôture H1 précédente est au-dessus de la bande de Bollinger haute (20, k) et RSI(14) > 100 − r ;
achat symétrique. Objectif = 0,5 × ATR(14) H1 × m, stop = 1,0 × ATR(14) H1 × m. Sortie forcée après 48 h.
Grille walk-forward : k ∈ {2,0 ; 2,5}, r ∈ {25 ; 30}, m ∈ {1 ; 2} (8 combinaisons). Défaut : k=2,0, r=30, m=1.

**H-E — repli dans la tendance journalière (profil EUR Trader 2 : ~80 % de réussite, gain ≈ perte, ~4 jours).**
Tendance = clôture du dernier jour complet (jour de trading clôturant à 17 h New York) au-dessus (haussière) ou
au-dessous (baissière) de sa moyenne mobile exponentielle EMA(n) journalière. Entrée sur bougie H4 : en tendance
haussière, achat si RSI(14) H4 < 40 ; en baissière, vente si RSI(14) H4 > 60. Objectif = stop = f × ATR(14) journalier.
Sortie forcée après 5 jours.
Grille : n ∈ {20 ; 50}, f ∈ {0,5 ; 1,0}, seuils RSI {40/60 ; 35/65} (8 combinaisons). Défaut : n=50, f=0,5, 40/60.

**H-T — cassure intraday de Londres (profil TP TRADER : ~49 % de réussite, gain ≈ 1,67 × perte, ~3 h).**
Range asiatique = plus haut / plus bas BID de 00:00 à 07:00 UTC. Entre 07:00 et 11:00 UTC, première sortie du range
en clôture M15 : achat au-dessus, vente au-dessous. Stop = autre côté du range (plafonné à 40 pips ; jour ignoré si
range < 10 pips), objectif = R × risque. Sortie forcée à h_max UTC. Une seule position par jour.
Grille : R ∈ {1,5 ; 2,0}, h_max ∈ {12 ; 16}, plafond {30 ; 40 pips} (8 combinaisons). Défaut : R=1,5, h_max=12, 40 pips.

## Données et exécution

- EUR/USD Dukascopy M1 BID/ASK réels, **01/09/2024 → 31/08/2026** uniquement. L'OOS vierge 09/2023 → 08/2024 reste
  fermé ; il ne sera ouvert que pour une hypothèse ayant passé tous les critères ci-dessous.
- Moteur `lab/oss_eurusd/engine.py` (achat ASK / vente BID, stop et objectif suivis minute par minute, stop d'abord si ambigu).
- Coûts de base : spread réel + 7 $/lot + 0,2 pip de glissement par ordre au marché. Stress : 9 $/lot + 0,5 pip.
- Décisions sur bougies clôturées uniquement, exécution à l'ouverture de la bougie suivante.

## Validation

1. **Paramètres par défaut** : entraînement 09/2024→08/2025, validation 09/2025→08/2026.
2. **Walk-forward** : 4 fenêtres. Optimisation sur les 12 mois précédents (meilleur profit factor parmi les 8
   combinaisons, minimum 30 trades), puis application sans changement aux 3 mois suivants :
   09–11/2025, 12/2025–02/2026, 03–05/2026, 06–08/2026. Les 4 trimestres hors échantillon sont mis bout à bout.
3. Nombre total d'essais : 3 hypothèses × 8 combinaisons = 24 (à garder en tête : plus on essaie, plus un bon résultat peut être un hasard).

## Critères de réussite (tous obligatoires)

- Walk-forward hors échantillon : profit factor ≥ 1,20, au moins 60 trades, au moins 3 trimestres sur 4 positifs,
  drawdown ≤ 15 %, t-stat ≥ 2,0 ;
- Paramètres par défaut : résultat net positif en entraînement **et** en validation ;
- Résultat walk-forward encore positif avec les coûts stressés.

Sinon : **rejetée**.
