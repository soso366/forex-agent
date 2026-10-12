# E004 — Absorption : pic de volume sans déplacement puis retour
Auteur : RESEARCHER · cycle 4 · 2026-10-12

## Mécanisme supposé
Une minute (ou 3 minutes) où l'activité (volume de ticks Dukascopy M1) est exceptionnelle mais où le prix
n'avance presque pas = un flux agressif d'un côté a été absorbé par de la liquidité passive de l'autre côté
(banque/teneur de marché qui se couvre, ordre iceberg). Le côté agressif est « piégé » et son impulsion est épuisée :
on parie sur un léger déplacement DANS LE SENS OPPOSÉ au côté agressif, tel que mesuré par la position de la clôture
dans le range de la minute et le signe des 3 minutes précédentes.

## Raison économique / microstructure / comportementale
Modèles d'impact de marché : volume élevé avec impact faible révèle de la profondeur cachée ; le prix tend à glisser
vers le côté du teneur de marché une fois son inventaire couvert. Aucun calendrier, aucune heure fixe, aucun niveau rond
(différent de H3, E001, E002, E003). Le volume est une information que toutes les rejetées ignorent.

## Conditions (règles objectives, sans donnée future)
- Paires : EURUSD, GBPUSD, USDJPY, chacune seule.
- Heures : 07:00–17:00 Europe/London (liquidité suffisante ; spread normal). Pas de signal si spread > 1,5 × médiane glissante.
- Déclencheur (barre M1 close t) : volume(t) ≥ percentile 95 du volume de la même minute-du-jour sur les 20 derniers jours
  ET |close−open|(t) ≤ 0,3 × ATR M1(60) ET aucune nouvelle d'agenda (non filtrable : voir risques).
  Sens agressif = signe de (close(t−3) → open(t)) ; entrée contre ce sens (si ce signe est nul : pas de trade).
- Entrée : ask/bid réel à l'ouverture de t+1. Stop 1,0 × ATR M5 ; cible 1,0 × ATR M5 ; sortie temporelle 30 min.
  Un trade à la fois par paire ; max 2 positions au total.
- Variantes ≤ 8 : seuil percentile (90/95/99), fenêtre de sens (3/5 min), sortie 15/30 min.

## Pourquoi 5–60 minutes
L'inventaire du teneur se couvre en quelques minutes ; au-delà de 60 min le bruit domine.

## Critères falsifiables (écrits avant tout résultat)
Rejet au Train (sept. 2025 → fév. 2026) si UNE condition est vraie, pour la règle principale (percentile 95, 30 min) :
- moins de 150 trades ; ou R moyen net de coûts ≤ +0,05 ; ou t ≤ 2 ;
- IC 95 % par jour contient 0 ; ou le résultat devient négatif en retirant les 5 meilleurs jours ;
- le placebo (même règle, volume de la même minute tiré d'un autre jour au hasard, 200 tirages) donne un R moyen
  ≥ celui de la règle réelle au 90e percentile des placebos : le volume n'apporte alors rien ;
- coûts +0,5 pip : R ≤ 0. Seul le Train est lu d'abord ; Validation puis OOS seulement si réussi.

## Risques d'échec
- Le volume de ticks M1 Dukascopy est un proxy (nombre de cotations, pas de transactions) : peut refléter les annonces,
  où le prix BOUGE (filtré par la condition de faible déplacement mais pas totalement).
- Effet probablement ≈ 0,5 pip < coût (spread). Fort risque de retour = bruit de bid/ask (rebond du prix).
- Pas de calendrier : annonces non exclues (même piège qu'E001).
- Données : nécessite DATA_REPO_TOKEN en session (même blocage qu'E003).

## Non-doublon
Vérifié contre memory/EXPERIMENTS.md et REJECTED_HYPOTHESES.md (dupcheck : aucun) : ni fixing, ni heure fixe, ni
nombre rond, ni divergence de paires, ni choc de spread, ni displacement de prix seul (V4-H5 n'utilise pas le volume).
Le colonne volume est la seule information nouvelle ; si le volume est constant/vide dans les fichiers, E004 est caduque.
