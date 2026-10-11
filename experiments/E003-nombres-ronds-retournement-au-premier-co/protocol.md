# E003 — protocole (VERROUILLÉ au commit, ne plus modifier)
Auteur : QUANT · cycle 3 · 2026-10-11 · écrit AVANT toute donnée de marché. Aucune donnée n'était disponible
dans cette session (dossier `data/` absent, secret DATA_REPO_TOKEN absent) : aucun signal compté, aucun R calculé.
Seul le test synthétique (données fabriquées en mémoire) a été exécuté.
Implémentation : `code/e003.py` (règles), `code/run.py` (count / train / validation / oos), `code/test_synthetic.py`.
`research/v4/data.py`, `research/v4/sim.py`, `research/common/robustness.py`, `forex_agent/meta/exposure.py` et
`forex_agent/meta/journal_audit.py` sont importés, jamais modifiés.

## Règle principale unique : A (exigence 1 du Critic)
Toutes les décisions (Train, Validation, OOS) se prennent sur **A seule**. B à F et les voisins sont des diagnostics
rapportés, **jamais** choisis à la place de A. Si A a moins de 80 trades au Train : REJECT, aucun relâchement.

Données Dukascopy M1 bid/ask, index UTC = début de minute ; la minute t est connue à sa clôture.
Grille minute complète (minutes absentes = manquantes) : t−15, t+1, la fenêtre de 120 min et la durée sont en
**temps d'horloge** (horodatages), jamais en rangs de lignes (exigence 4).
- Paires : EURUSD, GBPUSD, USDJPY, chacune indépendamment ; pip = 0,0001 / 0,0001 / 0,01.
- mid = (bid + ask)/2 pour open/high/low/close de la minute.
- **ATR** = ATR 14 (EWM, `research/v4/data.atr`) des barres M5 mid (`data.bars`, étiquette = début). Chaque valeur
  est ré-étiquetée à la **fin** de sa barre (étiquette + 5 min) ; à la minute t on prend la dernière barre dont la
  fin ≤ début de t (barre entièrement terminée avant t). Contact à hh:07 → barre hh:00–hh:04 (exigence 3, testé).
  La même ATR(t) sert au filtre d'arrivée, au filtre 0,3 ATR, au stop et à la cible.
- **Grille de niveaux** de décalage o (pips) et d'espacement S : niveaux = (k·S + o) pips. Règle ronde : o = 0,
  S = 50 (x,xx00 et x,xx50 ; xxx,00 et xxx,50).
- **Fenêtre de premier contact** W = 120 min d'horloge [t−120, t−1], **toutes** les minutes (y compris avant 07:00
  et, le lundi, le dimanche soir si présent) ; au moins 75 % de minutes présentes, sinon pas de signal.
  maxAsk = max des ask high de la fenêtre ; minBid = min des bid low de la fenêtre.
- **VENTE** au niveau Ls = plus petit niveau de la grille > maxAsk + 0,5 pip (niveau jamais approché à moins de
  0,5 pip pendant 120 min ; un niveau franchi par un trou de cotation est aussi considéré comme déjà atteint) :
  1. contact : ask high_t ≥ Ls − 0,5 pip ;
  2. premier contact : garanti par la définition de Ls ;
  3. arrivée : mid close(t−15) ≤ Ls − 0,75·ATR(t) (dernière minute présente au plus 2 min avant t−15) ;
  4. non franchi : mid close_t < Ls ET mid high_t < Ls + 0,3·ATR(t).
- **ACHAT** symétrique : Lb = plus grand niveau < minBid − 0,5 pip ; bid low_t ≤ Lb + 0,5 pip ;
  mid close(t−15) ≥ Lb + 0,75·ATR ; mid close_t > Lb ET mid low_t > Lb − 0,3·ATR.
  Une minute qui contacte à la fois un niveau au-dessus et un niveau au-dessous : pas de signal.
- Heures : minute de contact t entre 07:00 et 19:30 UTC inclus, lundi → vendredi. Pas de calendrier.
- Entrée : ouverture de la minute t+1, qui doit exister (sinon pas de trade) : bid pour une vente, ask pour un
  achat (`sim.simulate`, `max_gap_min = 1`).
- Stop : k_stop·ATR(t) depuis le prix d'entrée, jamais élargi. Cible : 1,0 R (= k_stop·ATR). Stop et cible dans la
  même minute → stop. Glissement à l'ouverture si l'ouverture d'une minute dépasse le stop (sim.py).
- Sortie au temps : clôture de la dernière minute de la durée H. **Sortie forcée 20:00 UTC** : durée effective =
  min(H, minutes entre l'entrée et 20:00) (contact 19:30 avec H = 30 → 29 min, exigence/risque 11). Sortie ≤ 30 min.
- Une seule position par paire : après une entrée, la paire est bloquée jusqu'à entrée + durée effective
  (règle indépendante des résultats). Au plus un trade par paire, par niveau et par jour UTC.
- R = PnL / distance de stop, spread bid/ask réel inclus.

## Variantes (6 ≤ 8, grille fixée ici ; diagnostics sauf A)
| id | niveaux | H (min) | stop | cible |
|---|---|---|---|---|
| **A (principale)** | 00 + 50 (S = 50) | 20 | 1,0 ATR | 1,0 R |
| B | 00 seulement (S = 100) | 20 | 1,0 ATR | 1,0 R |
| C | 00 + 50 | 10 | 1,0 ATR | 1,0 R |
| D | 00 + 50 | 30 (coupée à 20:00) | 1,0 ATR | 1,0 R |
| E | 00 + 50 | 20 | 1,0 ATR | aucune (sortie au temps) |
| F | 00 + 50 | 20 | 0,75 ATR | 1,0 R |
B est aussi rapportée face à ses grilles de 100 pips décalées de +17 et +33 pips (diagnostic).

## Contrôles de sensibilité de A (exigence 12 ; jamais sélectionnés)
Tolérance de contact −0,5 pip et +1,5 pip (= 0,5 ± 1 pip) ; fenêtre 60 et 240 min ; arrivée 0,5 et 1,0 ATR.
Chacun ne change qu'un paramètre de A. Exigence : même signe que A (donc espérance > 0, A devant être > 0).

## Comptage à l'aveugle (exigence 2)
`run.py count` compte les signaux de A–F, des 6 voisins et des 28 grilles placebo, par paire et par mois, **sans
aucun appel au simulateur** → `results/signal_counts.json`. Ce fichier est **commité AVANT** `run.py train`
(le protocole étant verrouillé, les comptes ne sont pas recopiés ici ; `run.py train` refuse de tourner si le
fichier est absent ou non commité). Si n(A) < 80 au comptage, le Train est quand même exécuté et rapporté, puis
déclaré échoué (critère T1).

## Données
- Train : signaux du 2025-09-02 au 2026-02-28 (`data/m1_2025`, branche `data-2025sep-2026feb`).
- Validation : signaux du 2026-03-01 au 2026-08-31 (`data/m1_2025` + `data/m1` pour l'ATR et la fenêtre de 120 min).
  Les 12 mois sept. 2024 → août 2025 (OOS H3 consommé) ne sont PAS utilisés par E003.
- OOS vierge : signaux du 2023-09-04 au 2024-08-31 (`data/m1_oos2324_a` + `data/m1_oos2324_b`, branches
  `data-2023sep-2024feb`, `data-2024mar-aug`). **Jamais cloné, ouvert ni analysé avant que
  `python -m orchestrator oos-gate E003` réponde OUVERT** (Train ET Validation réussis) ; lu UNE fois
  (`run.py oos` vérifie la porte et refuse une seconde lecture).
- Rien n'est ré-optimisé après le Train : la validation et l'OOS portent sur A, paramètres identiques.

## Placebo de niveaux (juge principal du mécanisme ; exigence 5)
Même code, seul le décalage o change (S = 50, mêmes filtres, même simulation) :
- grilles nommées du Researcher : o = +17 et o = +33 pips ;
- distribution complète : o = 6 … 44 pips par pas de 1, en excluant ±5 pips autour de 0 et de 50 (donc 1–5 et
  45–49) et 20–30 (quart semi-rond) → **28 grilles** (6–19 et 31–44), qui contiennent +17 et +33.
- Rang centile de A = part des 28 grilles dont l'espérance R/trade est strictement inférieure à celle de A
  (≥ 90 % ⇔ A bat au moins 26 grilles sur 28).
- Différence D = espérance(A) − moyenne des espérances des 28 grilles ; **IC 95 % bootstrap par jour** UTC :
  tirage apparié des jours (union des jours avec au moins un trade, toutes grilles), 10 000 tirages, graine 11 ;
  à chaque tirage, espérance de chaque grille = somme des R des jours tirés / nombre de trades des jours tirés.

## Critères Train → validation (tous requis, sur A ; un seul échec → REJECT immédiat)
- T1 n ≥ 80 trades (3 paires).
- T2 espérance > +0,05 R/trade, spread réel inclus.
- T3 **t ≥ 2 calculé par jour** (somme des R du jour UTC, jours avec au moins un trade ; t = moyenne / (écart-type/√n)).
- T4 A bat **chacune** des grilles +17 et +33 d'au moins +0,06 R/trade.
- T5 rang centile de A ≥ 90 % parmi les 28 grilles décalées.
- T6 borne basse de l'IC 95 % bootstrap par jour de D > 0.
- T7 gradient 00 / 50 (exigence 11) : appliqué seulement si chaque groupe (trades A sur niveaux 00, sur niveaux 50)
  a ≥ 40 trades ; alors espérance(00) ≥ espérance(50) − 0,10 R. Moins de 40 dans un groupe → « non concluant »
  (pas une réussite ; ne fait pas échouer le Train, mais doit être tranché en validation, V8).
- T8 coûts : espérance > 0 avec +0,5 pip par trade, converti **trade par trade** (pips × pip / distance de stop,
  `robustness.costs`) ; +0,2 et +1,0 pip rapportés.
- T9 stress de cascade (exigence 9) : chaque sortie par stop exécutée au **pire prix de la minute du stop** (ask high
  pour une vente, bid low pour un achat ; R = min(R simulé, R au pire prix)). Espérance > 0 sous ce stress.
  Rapporter la perte moyenne des stops, la part des trades < −1,2 R, et le stress + 0,5 pip.
- T10 concentration (exigence 8) : R total > 0 et (a) part des 5 meilleurs jours ≤ 40 % du R total ; (b) paire la plus
  forte ≤ 70 % du R total ; (c) les deux moitiés du Train (sept.–nov. 2025, déc. 2025–fév. 2026) de R positif ;
  (d) au moins 4 mois sur 6 de R positif. Rapporter aussi le résultat sans les 5 meilleurs jours, sans la meilleure
  paire, par trimestre.
- T11 contacts créés par le spread (exigence 10) : trade dont le mid high_t (vente) reste à plus de 1 pip sous L
  (achat : mid low_t à plus de 1 pip au-dessus de L). Part ≤ 20 % des trades ET espérance de A sans eux > 0.
- T12 version « règles live » (exigence 7) : trades A rejoués chronologiquement avec au plus 2 positions ouvertes
  toutes paires confondues et jamais deux positions exposées à la même devise dans le même sens
  (`exposure.legs`) ; espérance > 0. `one_per_day` rapporté.
- T13 les 6 contrôles de sensibilité ont une espérance > 0 (même signe que A).
- T14 durée maximale des trades ≤ 30 min.
- T15 absence de look-ahead : test synthétique réussi ET test de perturbation sur données réelles réussi
  (perturber t0 et le futur ne change pas l'ATR à t0 ; perturber le futur > t0 ne change pas les extrêmes de la
  fenêtre ni le mid de t−15 ; l'ATR « naïve » doit changer, preuve que le test détecte la fuite).
Train échoué → `validation.json` et `oos.json` = {"skipped": "Train échoué"} ; aucune donnée de validation ni
d'OOS consommée.

## Critères validation → OOS (A, mars → août 2026, tous requis)
- V1 espérance ≥ +0,03 R/trade (donc de signe positif).
- V2 A > grille +17 ET A > grille +33 (placebo ≥ règle → REJECT).
- V3 rang centile ≥ 90 % parmi les 28 grilles.
- V4 D (A − moyenne des placebos) > 0.
- V5 espérance > 0 à +0,5 pip.
- V6 espérance > 0 sous le stress « pire prix de la minute ».
- V7 moyenne des R par jour > 0.
- V8 gradient 00 / 50 : espérance(00) ≥ espérance(50) − 0,10 R sur la validation si chaque groupe ≥ 40 trades ;
  sinon sur Train + Validation groupés ; toujours < 40 dans un groupe → **échec** (mécanisme non démontré).
- V9 5 meilleurs jours ≤ 40 % du R total (R total > 0) ; V10 paire la plus forte ≤ 70 % du R total.
Tout passe → `passed = true`, OOS seulement si `oos-gate` = OUVERT. Sinon `oos.json` = {"skipped": "Validation échouée"}.

## Critères OOS : PASS / FAIL / INCONCLUSIVE (lecture unique, sept. 2023 → août 2024, A)
- FAIL : espérance ≤ 0, OU espérance à +0,5 pip ≤ 0, OU rang centile < 50 % parmi les 28 grilles.
- PASS : n ≥ 60, espérance > +0,03 R, espérance à +0,5 pip > 0, espérance sous stress > 0, moyenne par jour > 0,
  rang centile ≥ 90 %, A > +17 et A > +33.
- INCONCLUSIVE : tout autre cas.

## Tests de robustesse et diagnostics obligatoires (rapportés au Train ; `full_report` en validation et OOS)
- Placebo : 28 grilles décalées + IC 95 % jour de D (décisif) ; +17 / +33 nommés.
- Coûts +0 / 0,2 / 0,5 / 1,0 pip (trade par trade) ; distribution de l'ATR en pips ; R par tercile d'ATR
  (diagnostic, aucun seuil d'ATR ajouté après coup).
- Stress « pire prix de la minute du stop ».
- Vue par jour : t par jour, `robustness.day_view` (IC 95 % bootstrap), `one_per_day`, version règles live.
- Concentration : `robustness.concentration`, `quarters`, moitiés, mois, 10 meilleurs trades (date, paire, niveau).
- Contacts créés par le spread (part, résultat sans eux).
- R par heure UTC de contact et par séance (07–12, 12–16, 16–19:30) ; par sens (achat / vente) ; sorties.
- Variantes B–F et 6 voisins : statistiques, coûts, stress (jamais sélectionnés).
- Diagnostic de cascade (critère 7 du Researcher, exigence 14) : contacts « premier contact + arrivée » dont la
  clôture mid de la minute de contact est ≥ 0,3 ATR au-delà du niveau ; mouvement mid des 5 min suivantes signé
  dans le sens du franchissement, en ATR (grille ronde, +17, +33). Rapporté uniquement ; interdit d'en faire une
  règle de continuation.
- Audit du journal (`journal_audit.audit`) sur les trades simulés de A (informatif).
- Diagnostic d'échantillon (risque 6 du Critic) : nombres de trades sur niveaux 00 et 50.
