# E008 — critique AVANT test
Auteur : CRITIC

## Meilleure raison pour laquelle l'hypothèse est fausse
Fade de mouvement = famille négative (E003, V4-H5, H3). Le mouvement 00:00→13:00 ≥ 0,30 ADR est souvent une tendance portée par des données (US 13:30) : le fade perd gros les jours de tendance (queue gauche) pour gagner peu ailleurs. Mécanisme inventory-control invoqué sans preuve à 4 h.

## Doublon / déjà testé ?
Pas de doublon strict (dupcheck : aucun ; ni E006 asiatique, ni H3 fix, ni E003). Mais proche de H3 « fade ponctuel » (sortie 17:00 englobe le fix 16:00, clause « jamais retester » à surveiller) : la sortie à 17:00 ne doit pas être justifiée par le fix. Quasi-anti-corrélé à E007 (même entrée 13:00, même sortie 17:00, sens opposé sur jours extrêmes) : E007 et E008 ne sont pas indépendants, comptés comme un seul test pour la sélection de famille.

## Risques méthodologiques prévisibles
- Puissance : 171 jours-paires (marge 21 sur 150), mais t ≥ 2,0 par jour exige un effet d'environ 0,15 R avec des jours-paires corrélés (USD commun : le nombre de jours indépendants peut être ~70-100). Probable INCONCLUSIVE ; ne pas abaisser le seuil.
- Seuil 0,30 « fixé par la distribution de |M| » : choisi en voyant des comptes, acceptable seulement s'il n'a pas été ajusté sur R. Variantes B/C/D : rapportées, pas de repêchage ; B (133) < 150 est irrecevable comme critère.
- DST : 00:00 Londres = 23:00 ou 00:00 UTC ; jours de changement d'heure (25 h/23 h), mid(00:00) et ADR sur jour calendaire Londres à gérer explicitement ; vérifier que 17:00 Londres reste < 21:00 UTC (oui).
- Look-ahead : ADR20 doit exclure le jour courant (high-low du jour J inclut le futur) ; ATR M5 à l'entrée en barres closes ; entrée à l'open M1 de 13:00 avec M calculé sur mid(13:00) = open de la même barre (autorisé seulement si c'est l'open, pas le close).
- R : stop 3 ATR large, R petit en pips ; vérifier que les pertes de tendance ne sont pas masquées par une normalisation par ATR différente de celle d'E007.
- Coûts : spread à 13:00 faible, mais le critère +0,5 pip doit être calculé sur la moyenne (pas seulement ≥ 0).

## Tests obligatoires à inclure dans le protocole
Placebo décalé ±1..6 h ET placebo de seuil (jours aléatoires à même fréquence) ; sens inverse (continuation) ; coûts +0,2/+0,5/+1 pip ; vue par jour (jours poolés, cluster USD) avec nombre de jours indépendants rapporté ; concentration (5 meilleurs jours, paire, mois) ; pire jour / queue gauche ; conditionnement exclu des jours d'annonces US en simple rapport (non filtre) ; comptage final avant R, INCONCLUSIVE si < 150 ; corrélation de P&L journalier avec E007 rapportée.

## Verdict : GO sous conditions
Conditions : ADR20 strictement passé et vérifié par test unitaire ; DST testé ; critère 1 inchangé (150, t ≥ 2,0 par jour, pas de repêchage via B/C/D) ; protocole commité avant tout R.
