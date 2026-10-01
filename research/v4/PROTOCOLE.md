# Recherche V4 — protocole pré-enregistré

Écrit et commité **avant** tout test des hypothèses V4. Les seuils ci-dessous ne changent pas après coup.

## Contraintes conservées
- Trades de 5 à 30 minutes maximum (sortie forcée à 30 min).
- Risque monétaire inchangé : la recherche mesure l'avantage en R, coûts de spread bid/ask inclus.
- Baseline V2 non modifiée (branche `research-v4`, dossier `research/v4/` séparé du moteur de production).
- Paper trading uniquement.

## Découpage temporel (nouveau)
| Rôle | Période | Usage |
|---|---|---|
| **Train / recherche** | 8 sept. 2025 → 28 fév. 2026 (T1 = sept.–nov., T2 = déc.–fév.) | seul endroit où l'on choisit une variante |
| **Validation** | 1 mars → 31 août 2026 (V1 = mars–mai, V2 = juin–août) | une seule variante par hypothèse, figée avant |
| **Hors-échantillon verrouillé** | 1 mars → 31 août 2025 (+ sept. 2024 → fév. 2025 si téléchargé à temps) | jamais regardé avant la fin ; une seule lecture |

Walk-forward : 4 fenêtres trimestrielles T1, T2, V1, V2 (+ OOS). Une stratégie doit être positive dans au moins 3 des 4.

Remarque d'honnêteté : sept. 2025 → août 2026 a déjà servi au Parameter Lab (stratégies V2). Les hypothèses V4 sont
nouvelles et n'ont été ajustées sur aucune de ces périodes, mais l'analyse des échecs V2 a regardé les 12 mois.
C'est pourquoi la preuve finale repose sur 2025 (et 2024), téléchargés exprès et jamais ouverts.

## Simulation
Entrée au marché à l'ouverture de la minute qui suit le signal (ASK à l'achat, BID à la vente) ; stop / cible testés sur
le côté de sortie (BID pour un achat, ASK pour une vente) ; stop et cible dans la même minute = stop ; glissement si
l'ouverture saute le stop ; sortie au temps à la clôture de la 30e minute. Une seule position par paire et par hypothèse
à la fois (pas de chevauchement). R = résultat / distance de stop.

## Hypothèses (5, grilles fixées ici)
Chaque hypothèse a au plus 8 variantes. Total ≤ 40 variantes → un t-stat de 2 seul ne suffit pas (≈ 2 faux positifs
attendus au seuil 5 %). D'où les critères multiples ci-dessous.

- **H1 Sweep & reclaim de liquidité (ICT, Judas swing)** — 07:00–10:00 et 12:00–15:00 UTC, le M5 dépasse le haut/bas
  de la séance asiatique (00:00–06:00 UTC) ou le PDH/PDL puis CLÔTURE de retour à l'intérieur → entrée dans le sens du
  retour. Stop au-delà de l'extrême du sweep + 0,1 ATR. Variantes : niveau {Asie, PDH/PDL} × sortie {temps seul, cible 1 R}
  × dépassement minimal {0, 0,2 ATR} = 8.
- **H2 Momentum d'ouverture (opening range)** — range des 30 premières minutes de Londres (07:00–07:30 UTC) et de
  New York (13:30–14:00 UTC) ; cassure en clôture M5 dans l'heure suivante → entrée dans le sens. Stop : milieu du range
  ou 1 ATR. Variantes : séance {Londres, NY} × stop {milieu, 1 ATR} × sortie {temps, 1,5 R} = 8.
- **H3 Fix de Londres (WM/Reuters 16:00 heure de Londres)** — effet documenté (pression avant le fix, retour après).
  À 16:00 Londres + 1 min, si le mouvement des 30 min précédentes dépasse k ATR(M5) → position opposée, 30 min.
  Stop 1,5 ATR. Variantes : k {0,5 ; 1,0 ; 1,5} × {tous les jours, fin de mois seulement} + 2 variantes « avant fix »
  (suivre la tendance de 15:30 à 16:00 Londres, k {0,5 ; 1,0}) = 8.
- **H4 Fix de Tokyo (09:55 JST = 00:55 UTC), USDJPY** — demande d'USD des importateurs avant le fix, surtout les jours
  gotobi (5, 10, 15, 20, 25, 30, fin de mois). Variantes : {achat 00:25→00:55, vente 00:56→01:26} × {tous les jours,
  gotobi} × stop {1 ATR, 2 ATR} = 8.
- **H5 Displacement M5 (ICT) : continuation ou essoufflement ?** — bougie M5 de corps ≥ k ATR clôturant dans ses 25 %
  extrêmes, 07:00–17:00 UTC. Variantes : sens {continuation, retour} × k {1,0 ; 1,5 ; 2,0} × séance {Londres, NY} (k = 1,5
  seulement pour la séance) → 8. Stop 1 ATR, sortie au temps.

## Critères (fixés avant les tests)
**Train → KEEP FOR VALIDATION** si TOUT est vrai :
1. espérance > 0 après spread, et t-stat ≥ 2,0 ;
2. n ≥ 60 trades ;
3. T1 et T2 tous deux positifs ;
4. au moins une variante voisine (un seul paramètre changé) aussi positive ;
5. espérance encore > 0 sans les 5 meilleurs trades ;
6. profit factor ≥ 1,10 ;
7. au moins 2 paires sur 3 positives (sauf H4, une seule paire par construction).
Une seule variante par hypothèse passe en validation (la meilleure au score prudent = pire des voisins).
Sinon : REJECT, ou RETEST si l'échec vient seulement du nombre de trades.

**Validation → candidate** : espérance > 0, PF > 1, V1 et V2 non négatifs.
**OOS verrouillé → retenue** : espérance > 0 et PF > 1 sur 2025. Sinon rejet, sans ré-ajustement.

## Router V4 (matrice de contexte)
Stratégie × régime × séance × volatilité × paire. Pour chaque cellule : n, espérance, intervalle de confiance bootstrap 90 %.
- EDGE : n ≥ 30 et borne basse > 0 ;
- NO EDGE (abstention) : n ≥ 30 et borne haute < 0 ;
- UNKNOWN sinon (défaut = NO TRADE).
Test préalable de **persistance** : les cellules mesurées sur Train ont-elles le même signe sur Validation ? Si la
corrélation de rang Train→Validation n'est pas positive, la matrice n'est pas utilisée pour filtrer (elle apprendrait du bruit).
