# E003 — critique AVANT test
Auteur : CRITIC · cycle 3 · 2026-10-11

## Meilleure raison pour laquelle l'hypothèse est fausse
**Ce qui est mesuré sera surtout un « retour après une approche rapide », que l'on observe à n'importe quel
niveau. Le caractère « rond » du niveau n'y serait pour rien.** La condition 3 (mid à t−15 au moins 0,75 ATR sous L)
plus la condition 4 (mèche haute M1 puis clôture sous L) sélectionnent des minutes à mèche après un mouvement rapide.
C'est presque la définition de V4-H5 « displacement en retour » (≈ −0,03 R, REJECT), sans seuil de taille de bougie.
Tout effet positif peut venir de ce filtre de barre (rebond bid/ask, mèche) et non des ordres groupés. De plus :
- l'effet mesuré par Osler date de 1999–2000 (carnet d'une seule banque) et portait sur quelques points de
  probabilité. Aujourd'hui, les algorithmes placent leurs ordres quelques pips **avant** le niveau rond, si bien que
  le « mur » au niveau exact ±0,5 pip peut avoir disparu ;
- **le stop tombe dans la zone des stops groupés d'Osler.** L'entrée se fait environ 0,5 à 1 pip sous L et le stop
  1 ATR M5 au-dessus (≈ 3 à 6 pips sur EURUSD en séance calme), donc juste au-delà de L, là où Osler place les
  stop-loss. Quand le niveau cède, nos pertes se font précisément dans la cascade, avec un glissement au-delà de
  −1 R ;
- coût : avec un stop de 3 à 6 pips, un spread de 0,5 pip coûte déjà 0,08 à 0,17 R, et +1 pip en coûte 0,17 à
  0,33 R. Un effet de « quelques points de probabilité » sur une cible à 1 R (≈ +0,04 à +0,08 R brut) peut ne pas
  couvrir ce coût.

## Doublon / déjà testé ?
**Ce n'est pas un doublon.** `python -m orchestrator dupcheck` : « round number », « retournement niveau » → aucun
doublon. « nombre rond », « psychologique », « take profit » → seulement l'hypothèse E003 elle-même. Aucune ligne de
`memory/REJECTED_HYPOTHESES.md` ne porte sur des niveaux exogènes.
- V4-H1 (sweep & reclaim) et RangeFade_v2 utilisent des niveaux calculés à partir du prix passé. E003 utilise un
  niveau fixe, connu d'avance, sans franchissement. C'est différent.
- **La proximité réelle est avec V4-H5 « retour ».** E003 n'est pas un recyclage de H5 seulement si la grille ronde
  bat les grilles décalées. Le placebo de niveaux est donc **décisif**, et non un simple diagnostic. S'il échoue, E003
  est archivé avec H5, sans réglage de sauvetage.
- Aucun lien avec H3 / E000 (pas d'heure fixe), E001 (pas de relation entre paires) ou E002 (pas de condition de
  spread).

## Risques méthodologiques prévisibles (look-ahead, fuite, trop de variantes, échantillon, coûts, corrélation USD)
1. **Look-ahead ATR (même piège que pour E002).** `research/v4/data.py:51-54` étiquette les barres M5 par leur
   **début** (`label="left"`). Pour un contact à 10:07, prendre l'ATR de l'étiquette 10:05 avec un `reindex/ffill`
   revient à utiliser les minutes 10:05–10:09, donc des **données futures**. Il faut prendre la dernière M5 dont la
   **fin** est ≤ t (index décalé de +5 min, ou ATR déjà décalé avec `shift(1)`). La même ATR sert au filtre
   « arrivée », au filtre « 0,3 ATR » et au stop.
2. **« Premier contact depuis 120 min ».** La fenêtre de 120 min doit être en **temps d'horloge** et utiliser
   **toutes** les minutes, y compris avant 07:00 UTC. Sinon, chaque niveau déjà touché en séance asiatique paraît
   « nouveau » à 07:00, ce qui crée un amas artificiel de signaux à l'ouverture. Le lundi, la fenêtre doit inclure les
   cotations du dimanche soir. Le contact « bilatéral » (ask high ≥ L − 0,5 ou bid low ≤ L + 0,5) doit être appliqué
   de la même façon aux grilles placebo.
3. **Minutes manquantes.** « t−15 », « t+1 » et « 20 min » doivent être calculés sur les **horodatages**, pas sur la
   position dans le tableau. `research/v4/sim.py:28-52` tolère par défaut `max_gap_min=5` : il faut imposer
   `max_gap_min=1` (l'entrée doit avoir lieu à l'ouverture de t+1, sinon pas de trade).
4. **Stop optimiste en cas de cascade.** `sim.py:74-80` ne modélise le glissement que si l'**ouverture** de la minute
   dépasse déjà le stop. Si le stop est traversé en cours de minute dans une cascade, la perte est comptée à
   exactement −1 R. C'est précisément le risque principal d'E003, donc ce cas est sous-estimé.
5. **Contacts créés par le spread.** Pour une vente, le contact se lit sur l'**ask** high. Si le spread s'élargit
   (après 19:00 UTC, annonces), l'ask peut toucher L alors que le mid en est loin : on obtient un contact « fantôme »
   sans aucun mur touché.
6. **Échantillon.** L'estimation de 190 à 370 trades n'a pas été mesurée. Ma propre estimation, après les filtres 2
   à 4, est d'environ 0,3 à 0,8 trade par jour et par paire, soit **110 à 300 trades**. Le seuil de 80 trades est
   probablement atteint pour A. Pour B (niveaux 00 seulement), il est incertain (≈ 40 à 120 trades). Le critère 3
   (comparaison 00 / 50) peut donc reposer sur 40 trades d'un côté, ce qui n'a pas de puissance statistique.
7. **Puissance du critère placebo.** Avec environ 250 trades et un écart-type d'environ 1 R par trade, l'erreur type
   de la **différence** entre la grille ronde et un placebo est d'environ 0,09 R. Le seuil de +0,06 R est donc
   **plus petit que le bruit** : battre deux placebos de 0,06 R par chance est plausible (de l'ordre de 15 à 25 %
   sous l'hypothèse nulle). Deux grilles seulement donnent un placebo trop pauvre.
8. **Variantes.** A à F font 6 variantes. Le placebo est un contrôle, pas une variante (≤ 8, conforme). Mais si la
   décision au Train peut se prendre sur « la meilleure des 6 », il y a sélection après coup.
9. **Corrélation USD et règles live.** Les 3 paires partagent l'USD. Un même choc USD peut faire toucher des ronds
   sur EURUSD et GBPUSD dans la même heure. Le Risk Manager interdit deux positions dans le même sens sur la même
   devise et limite à 2 positions : le résultat brut sur 3 paires surestime ce qui est réellement exécutable.
10. **Trimestres.** Le Train (sept. 2025 → fév. 2026) ne contient qu'un seul trimestre complet (T4 2025). Le critère
    « un seul trimestre porte tout » est donc presque impossible à vérifier tel qu'il est écrit.
11. **Variante D (30 min) et sortie forcée à 20:00.** Un contact à 19:30 entre à 19:31 et devrait sortir à 20:01 :
    il est coupé par la sortie forcée de 20:00. C'est mineur, mais doit être écrit.

## Tests obligatoires à inclure dans le protocole (placebo, coûts, vue par jour, concentration…)
Le Quant DOIT verrouiller dans `protocol.md`, **commité avant toute lecture de R au Train** :
1. **Règle principale unique = A.** Les critères 1, 2, 4 et 5 se décident sur A seule. B à F sont des diagnostics
   rapportés, jamais choisis à la place de A. Aucun relâchement des filtres si A < 80 trades : c'est un REJECT.
2. **Comptage à l'aveugle.** Avant de calculer un seul R, le Quant compte et écrit dans `protocol.md` le nombre de
   signaux de A, B et des placebos (par paire et par mois).
3. **ATR sans fuite.** ATR 14 M5 mid issue de la dernière barre **terminée** avant t (voir risque 1). Ajouter un test
   unitaire : pour un contact à hh:07, l'ATR utilisée doit être celle de la barre hh:00–hh:04 ou d'une barre
   antérieure.
4. **Horodatages** pour t−15, la fenêtre de 120 min (temps d'horloge, minutes hors 07–19:30 incluses), t+1 et la
   durée. Imposer `max_gap_min=1`.
5. **Placebo décisif renforcé.** Garder le critère du Researcher (A doit battre **chacune** des grilles +17 et
   +33 pips d'au moins +0,06 R par trade). AJOUTER une **distribution complète des grilles décalées** : décalages de
   +6 à +44 pips par pas de 1 pip, en excluant ±5 pips autour de 0, autour de 50 et autour de +25 (le « mur
   déplacé » et le quart semi-rond ne sont pas des placebos). Même code, seul le paramètre de décalage change. La
   grille ronde doit être au **90e percentile ou plus** de cette distribution (en espérance R par trade), sinon c'est
   un REJECT. Rapporter aussi la différence « ronde − moyenne des placebos » avec un **IC 95 % bootstrap par jour**.
6. **Coûts** : +0,2, +0,5 et +1 pip, convertis en R **trade par trade** (pips divisés par la distance du stop en
   pips), et non par une moyenne. L'espérance de A doit rester > 0 à +0,5 pip. Rapporter la distribution de l'ATR en
   pips, et le R par tercile d'ATR (diagnostic seulement, pas de seuil d'ATR ajouté après coup).
7. **Vue par jour** (USD commun) : somme des R par jour UTC, t de Student par jour et IC 95 % bootstrap
   (`research/common/robustness.py::day_view`). Le critère t ≥ 2 du Train se calcule **par jour**. Rapporter aussi
   `one_per_day` et une version qui applique les règles live : max 2 positions, pas deux positions de même devise
   dans le même sens.
8. **Concentration** (`robustness.concentration`, `quarters`) : part du R total sur les 5 meilleurs jours (≤ 40 %),
   part de la paire la plus forte (≤ 70 %), résultat sans les 5 meilleurs jours. Remplacer « un trimestre porte
   tout » par : **les deux moitiés du Train (sept.–nov. 2025 et déc. 2025–fév. 2026) doivent être de signe positif**,
   et au moins 4 mois sur 6 positifs.
9. **Stress de cascade** (exigé, décisif pour les coûts) : recalculer A en exécutant chaque sortie par stop au **pire
   prix de la minute du stop** (ask high pour une vente, bid low pour un achat). Rapporter la perte moyenne des
   stops, la part des pertes < −1,2 R et l'espérance obtenue. Si l'espérance de A devient ≤ 0 sous ce stress, le
   noter comme échec du critère coûts.
10. **Contacts créés par le spread** : compter les contacts où le mid high (vente) reste à plus de 1 pip sous L
    (ou, pour un achat, le mid low à plus de 1 pip au-dessus de L). Rapporter A en excluant ces contacts. Si plus de
    20 % des trades sont dans ce cas, le résultat de A n'est pas recevable tel quel.
11. **Critère 3 (comparaison 00 / 50)** : il ne s'applique que si chaque groupe a au moins 40 trades. Sinon, il est
    déclaré « non concluant », ce qui n'est **pas** une réussite, et la validation doit le retester.
12. **Voisins (diagnostic)** : tolérance de contact ±1 pip, fenêtre de premier contact 60 et 240 min, arrivée 0,5 et
    1,0 ATR. Les variantes A et voisines doivent avoir le même signe. Elles ne sont jamais sélectionnées.
13. **Rapports horaires** : R par heure UTC et par séance, pour détecter une concentration (ex. 07:00 artificiel ou
    après 19:00 à spread large).
14. **Diagnostic de cascade** (critère 7 du Researcher) : le rapporter uniquement. Interdit d'en faire une règle de
    continuation (famille rejetée).
15. **OOS vierge 2023-2024** : fermé tant que `python -m orchestrator oos-gate E003` ne répond pas OUVERT. Un échec
    au Train entraîne un REJECT immédiat, sans validation ni OOS.

## Verdict : GO
L'hypothèse est nouvelle et falsifiable. Le niveau est exogène, ce qui permet un placebo propre. Toutes les
conditions sont calculables à la clôture de t, en UTC explicite, sans calendrier, pour une entrée à t+1. **GO sous
conditions** : les exigences 1 à 11 ci-dessus doivent figurer dans `protocol.md` verrouillé, et le placebo de
grilles décalées (exigence 5) est le juge principal. Si la grille ronde ne se distingue pas des grilles décalées,
E003 est classé comme un « retour après approche » (famille H5) et archivé, même si son espérance est positive.
