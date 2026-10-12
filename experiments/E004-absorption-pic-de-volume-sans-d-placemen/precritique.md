# E004 — critique AVANT test
Auteur : CRITIC · 2026-10-12

## Meilleure raison pour laquelle l'hypothèse est fausse
1. **La colonne volume n'existe pas dans les données locales.** `data/m1_2025/{EURUSD,GBPUSD,USDJPY}.csv` ont pour seules
   colonnes `time, bid_open…bid_close, ask_open…ask_close` (vérifié sur les 3 fichiers, Train sept. 2025 → fév. 2026 ;
   `data/m1/` idem). `forex_agent/data/dukascopy.py` décode bien `vol` (`decode_bi5`, ligne 53-61) mais `build_symbol`
   (ligne ~190) ne le recopie pas dans le DataFrame final : il ne s'en sert que pour supprimer les minutes plates
   (`active = vol>0`, `flat_minutes_removed` = 39 536 pour EURUSD). Les fichiers `.bi5` bruts ne sont pas dans le dépôt.
   L'hypothèse précise elle-même : « si le volume est constant/vide, E004 est caduque » — il est ABSENT, donc intestable
   en l'état. Reconstruire demande de retélécharger les `.bi5` (réseau + `DATA_REPO_TOKEN`/Dukascopy, même blocage qu'E003)
   et de modifier le code de données (hors `forex_agent/lab/`, `forex_agent/meta/` : fichier protégé → accord requis ;
   à faire dans un script de recherche séparé sous `experiments/E004-*/code/`).
2. Si le volume est récupéré : c'est un **nombre de mises à jour de cotation**, pas de transactions, séparé en BID et ASK
   (deux valeurs différentes, laquelle ? non spécifié). Il suit l'heure, la volatilité et les annonces ; « pic sans
   déplacement » est en partie un artefact de minutes à cotation rapide qui reviennent au milieu (bruit bid/ask).
3. Effet attendu ≈ 0,5 pip < spread médian 0,4 pip + slippage de sortie ; stop = cible = 1 ATR M5 sur 30 min : coût
   en R non négligeable. Les rejetées voisines (V4-H5 retour ≈ −0,03 R, E002) montrent que le « retour » est mangé par le coût.

## Doublon / déjà testé ?
`python -m orchestrator dupcheck` : aucun doublon. Aucune rejetée n'utilise le volume. Proche cependant de V4-H5
(déplacement faible/fort puis retour) : le filtre volume est la seule nouveauté, donc le placebo « volume » est le juge.
Pas de REJECT pour doublon.

## Risques méthodologiques prévisibles
- **Falsifiable** : oui (critères chiffrés écrits avant résultat). Pas de look-ahead dans le déclencheur si le percentile
  est calculé sur les 20 jours PRÉCÉDENTS strictement (exclure le jour courant) et l'entrée à l'ouverture de t+1.
- **Fuseau** : 07:00–17:00 Europe/London (DST) vs minute-du-jour du percentile : la « même minute-du-jour » doit être en
  heure de Londres, sinon le décalage DST de ~2 semaines (mars/oct.) mélange des minutes ; Train inclut le passage
  du 26 oct. 2025.
- **Puissance** : 20 jours × minute-du-jour × p95 → ~5 % des barres éligibles × filtre faible déplacement × sens non nul ×
  un trade à la fois × 3 paires corrélées (USD) : le seuil « ≥ 150 trades » est probablement atteint, mais les trades
  sont groupés autour d'annonces (E001/E002 le montrent) ; t ≥ 2 avec ~150 trades exige ≈ +0,16 R, très au-dessus du plausible.
- **Annonces** : pas de calendrier. Une condition de volume élevé sélectionne justement les annonces (moins d'écart de prix
  mais volume massif ≈ minutes NFP/FOMC). Le risque E001 est maximal ici.
- **ATR M1(60) et ATR M5** : définir sans la barre courante pour le M5 en cours (pas de barre M5 incomplète).
- Variantes : 3 × 2 × 2 = 12 combinaisons annoncées, mais « ≤ 8 » : en choisir 8 AVANT, règle principale p95/3 min/30 min.
- Pas de sens agressif quand close(t−3)→open(t) est « nul » : ne pas utiliser un seuil d'égalité flottant (ticks entiers).

## Tests obligatoires à inclure dans le protocole
1. **Étape 0 (porte)** : contrôle de qualité du volume sur le Train : non constant, > 0, corrélé à |return| et au spread,
   profil intraday plausible ; fixer BID, ASK ou somme. Sinon arrêt, pas de trade calculé.
2. Placebo du hypothesis (volume d'un autre jour, 200 tirages) à conserver, PLUS un placebo « faible déplacement seul,
   sans condition de volume » (isole V4-H5) et un placebo de sens inversé (continuation).
3. Coûts +0,2 / +0,5 / +1 pip ; vue par jour (3 paires agrégées par jour, IC 95 %) ; sans les 5 meilleurs jours ;
   concentration par paire et par mois ; exclusion des ±15 min autour des heures rondes de publication (proxy d'agenda).
4. Voisins : p90 et p99, 5 min, sortie 15 min doivent être de même signe, pas seulement la règle principale.
5. Comptage des signaux à l'aveugle (sans R) avant le calcul du R, comme E003.
6. Protocole commité avant tout résultat ; Validation/OOS seulement si le Train réussit (`oos-gate`). Ne pas toucher
   `data/m1_oos2324_*`.

## Verdict : REJECT (en l'état : intestable)
Motif : la donnée centrale (volume) n'est pas dans les CSV locaux ; aucune mesure ne peut être faite sans ré-extraction
(téléchargement bi5 + script hors fichiers protégés). Ce n'est pas un rejet de fond de l'idée.
**Fait nouveau permettant de rouvrir** : un fichier `volume` M1 (BID et ASK) pour sept. 2025 → fév. 2026 produit par un
script de recherche et validé par l'étape 0 ci-dessus. Alors verdict GO sous conditions 1-6, avec attente réaliste
d'un effet < coût (probabilité de succès faible).
