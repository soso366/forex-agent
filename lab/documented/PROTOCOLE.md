# Protocole pré-enregistré — 10 méthodes documentées, EUR/USD

Écrit le 25/10/2026 avant le téléchargement des données 2015-2023 et avant tout backtest. Non modifiable ensuite.

## Règle de départ

Seules des méthodes dont les règles complètes sont **publiées** sont programmées. Les paramètres sont ceux de la
source ; aucune optimisation. Là où la source laisse un détail ouvert, le choix est écrit ici à l'avance et signalé
comme « précision de notre part ». Les traders aux règles secrètes ne sont pas « reproduits ».

## Les 10 méthodes

| Code | Méthode | Source | Règles appliquées |
|---|---|---|---|
| M1 | Turtle Système 1 | Original Turtle Trading Rules (Faith) ; implémentation MQL5 publiée (mql5.com/en/articles/23448) | Entrée cassure du plus haut/bas 20 jours ; sortie cassure inverse 10 jours ; stop 2N (N = ATR 20 jours lissé Wilder) ; signal ignoré si le trade S1 précédent était gagnant ; 1 unité = 1 % de risque pour 2N ; ajout d'une unité tous les 0,5N, 4 unités max ; stop de toutes les unités à 2N de la dernière entrée |
| M2 | Turtle Système 2 | idem | Entrée 55 jours ; sortie 20 jours ; pas de filtre ; même N, stop, pyramide |
| M3 | Règle des 4 semaines (Donchian) | R. Donchian | Toujours en position : achat à la cassure du plus haut 20 jours, vente à la cassure du plus bas 20 jours (stop-and-reverse). Taille : 1 % de risque pour 2N (précision de notre part) |
| M4 | Momentum de série temporelle | Moskowitz, Ooi, Pedersen (2012) | Fin de mois : position du signe du rendement des 12 derniers mois, tenue 1 mois, exposition ciblant 10 % de volatilité annuelle (écart-type des rendements journaliers sur 60 jours), levier plafonné à 3 |
| M5 | Croisement moyennes 50/200 jours | méthode classique « golden cross » | Achat si SMA50 > SMA200 à la clôture, vente sinon ; toujours en position ; exposition 1× le capital |
| M6 | RSI(2) de Connors | Connors & Alvarez (2008) | Achat si clôture > SMA200 et RSI(2) < 10 ; vente si clôture < SMA200 et RSI(2) > 90 ; sortie à la clôture au-delà de la SMA5 ; pas de stop (comme la source) ; exposition 1× |
| M7 | Dual Thrust | Chalek ; tutoriel QuantConnect | Range = max(HH − LC, HC − LL) sur 4 jours ; niveau haut = ouverture du jour + 0,5 × range, bas = ouverture − 0,5 × range ; stop-and-reverse au franchissement ; exposition 1× |
| M8 | Effet de session | Breedon & Ranaldo (2011, SNB WP 2011-04) | Vente EUR/USD pendant la séance européenne, achat pendant la séance américaine. Heures (précision de notre part, la source ne donnant que des sessions approximatives) : vente de 07:00 à 12:00 heure de Londres, achat de 08:00 à 16:00 heure de New York ; exposition 1× |
| M9 | NR7 (Crabel) | T. Crabel (1990) | Si la journée a le plus petit range des 7 dernières : le lendemain, ordre d'achat au-dessus du plus haut et de vente sous le plus bas ; le premier déclenché annule l'autre ; stop = l'autre extrême ; sortie à la clôture du jour |
| M10 | Cassure d'ouverture « stretch » (Crabel) | T. Crabel (1990) | Stretch = moyenne sur 10 jours de l'écart entre l'ouverture et l'extrême le plus proche ; ordres stop à ouverture ± stretch ; stop = ouverture ; sortie à la clôture du jour |

Journée de trading : 17 h New York → 17 h New York. Positions de méthodes « exposition 1× » : notionnel = capital
(levier 1), ce qui rend leurs résultats comparables à un risque modéré.

## Données et exécution

- EUR/USD Dukascopy M1 BID/ASK. **Entraînement : 01/2015 → 12/2020.** **Validation 1 : 01/2021 → 08/2023.**
  **Validation 2 : 09/2024 → 08/2026.** L'OOS vierge 09/2023 → 08/2024 reste fermé.
- Simulation sur bougies H1 (BID/ASK) pour suivre les ordres stop et les stops ; si un stop et une entrée/sortie sont
  possibles dans la même heure, le cas défavorable est retenu. Achat au ASK, vente au BID.
- Coûts de base : spread réel + 7 $/lot + 0,2 pip par ordre au marché ou stop. Stress : 9 $/lot + 0,5 pip.
  Swaps non simulés (signalé comme limite pour M1-M5, positions longues).

## Contrôles

- Résultats par année et par trimestre, drawdown, plus longue série de pertes.
- Stabilité : chaque paramètre principal ±25 % (une seule variation à la fois) ; la méthode est « stable » si au moins
  70 % des variantes ont un PF > 1 sur l'ensemble validation 1 + validation 2.
- Pas d'optimisation : le « walk-forward » est ici un suivi année par année avec les paramètres publiés fixes.

## Critères de réussite (tous obligatoires, sur validation 1 + validation 2 réunies)

1. PF ≥ 1,30 avec coûts de base ; résultat positif avec coûts stressés ;
2. au moins 60 trades ;
3. drawdown ≤ 15 % ;
4. au moins 60 % des années positives sur l'ensemble 2015-2026 (hors OOS vierge) ;
5. entraînement positif (pas seulement la validation) ;
6. stabilité des paramètres (critère ci-dessus) ;
7. t-stat ≥ 2,6 (10 méthodes testées : seuil relevé pour limiter les faux positifs dus aux tests multiples).

Une méthode qui passe tout ouvre alors l'OOS vierge 09/2023 → 08/2024 (un seul essai), puis la phase EA MT5.
