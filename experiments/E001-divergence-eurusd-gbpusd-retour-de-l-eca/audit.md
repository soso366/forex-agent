# E001 — audit des résultats
Auteur : CRITIC · cycle 1 · 2026-10-02 — audit du Train (sept. 2025 → fév. 2026). Validation et OOS non exécutés
(`validation.json` / `oos.json` = skipped), conformément au protocole (« un seul échec → arrêt »).

| Variante | abs(z) / W / H | n | Esp. (R) | t | PF | Esp. +0,6 pip | IC 95 % jour | C1 d moyen [IC jour] | Score prudent |
|---|---|---|---|---|---|---|---|---|---|
| **V1 (sélectionnée)** | 2,5 / 15 / 20 | 78 | +0,085 | 0,87 | 1,28 | +0,010 | [−0,135 ; +0,441] | +0,139 [−0,058 ; +0,353] | −0,095 |
| V2 | 2,5 / 15 / 30 | 78 | +0,087 | 0,90 | 1,29 | +0,012 | [−0,127 ; +0,437] | +0,147 [−0,054 ; +0,362] | −0,111 |
| V3 | 2,5 / 30 / 20 | 77 | −0,095 | −0,98 | 0,76 | −0,164 | [−0,549 ; +0,196] | −0,084 | −0,150 |
| V4 | 2,5 / 30 / 30 | 77 | −0,111 | −1,01 | 0,74 | −0,180 | [−0,640 ; +0,231] | −0,144 | −0,163 |
| V5 | 3,0 / 15 / 20 | 27 | +0,289 | 1,47 | 2,29 | +0,223 | [−0,113 ; +1,208] | +0,341 [−0,054 ; +0,838] | −0,150 |
| V6 | 3,0 / 15 / 30 | 27 | +0,318 | 1,47 | 2,42 | +0,252 | [−0,111 ; +1,355] | +0,343 [−0,076 ; +0,851] | −0,163 |
| V7 | 3,0 / 30 / 20 | 37 | −0,150 | −1,15 | 0,64 | −0,218 | [−0,692 ; +0,185] | −0,121 | −0,163 |
| V8 | 3,0 / 30 / 30 | 37 | −0,163 | −1,19 | 0,63 | −0,231 | [−0,704 ; +0,157] | −0,137 | −0,163 |

## Overfitting / sélection après coup
- **Chronologie (git log)** : `bf58584` 2026-10-02 13:49:30 « protocole et code verrouillés » (protocol.md, code/,
  hypothesis, precritique) → `7e310c5` 13:49:58 « résultats Train ». Le commit des résultats ne touche ni protocol.md
  ni code/ (`git show --stat`). `python3 -m orchestrator guard` → « garde-fous OK … protocoles verrouillés intacts ».
- **Le Train a-t-il pu tourner avant le verrou ?** mtime `results/train.json` = 13:49:46, soit 16 s APRÈS le commit de
  verrouillage. J'ai relancé `run.py train` sur une copie du code dans le scratchpad : **durée 12,7 s, sortie
  identique** à `train.json` commité (comparaison JSON complète). Exécution post-verrou plausible et résultat
  reproductible. Réserve : `run.py` modifié à 13:49:07 (23 s avant le verrou) — des essais à blanc (crash/debug)
  avant commit ne sont pas exclus, mais rien ne montre qu'un R ait été lu avant.
- **Grille** : 8 variantes figées dans protocol.md (= plafond CLAUDE.md) ; la variante « deux jambes » a été retirée
  AVANT les données (motif écrit), toutes les variantes sont rapportées.
- **Sélection conforme** : aucune variante n'atteint n ≥ 100 (max 78) → `eligible_n100 = []` ; le protocole dit
  « la meilleure par score prudent est rapportée, mais le critère 1 échoue ». Score prudent max = V1 (−0,095) →
  V1 sélectionnée, correct (`run.py` l. 139–141). V5/V6 ont un score prudent de −0,150 / −0,163 (voisin V7/V8
  négatif) : la règle a fait exactement ce pour quoi elle existe.
- **Décision « Train échoue » correcte** : sur V1, échouent les critères 1 (n = 78 < 100, t = 0,87 < 2),
  2 (IC jour borne basse −0,135), 4 (sans les 5 meilleurs trades : −0,053 R), 6 (C1 : +0,139 mais IC [−0,058 ;
  +0,353] contient 0), 8 (P2 : +0,085 < 95e centile +0,105 ; P1 −0,040 → |P1| ≥ 0,03 aussi), 10 (top 5 jours = 139 %
  du R). Passent : 3 (PF 1,28), 5 (voisin V2 > 0), 7 (fautive +0,085 > inverse −0,073), 9 (+0,6 pip : +0,010, à peine).
  Six échecs sur dix, un seul suffisait.
- **Écriture d'état incohérente** : `status.json` enregistre `VALIDATED` et `OOS_DONE` à 11:49 UTC alors que la
  validation et l'OOS sont « skipped ». À corriger côté orchestrateur (le stage ne doit pas dire VALIDATED).

## Fuite de données / look-ahead
Lecture de `code/e001.py` — aucun look-ahead trouvé.
- **σx, σu, médiane de spread** (`_day_stats`, l. 110–147) : `prev = [v for v in valid if v < d][-NDAYS:]` →
  jours J−20…J−1, jour J exclu ; `if len(prev) < NDAYS: continue` → pas de min_periods réduit. Blocs non
  chevauchants construits en heure Europe/London puis convertis en UTC (`tz_localize(TZ)` … `tz_convert("UTC")`,
  l. 116–117) → DST correct (le Train contient le 26/10/2025).
- **ATR M5** (`_atr`, l. 104–108) : `bars` étiquette par le DÉBUT (`label="left"`, research/v4/data.py l. 54),
  `atr()` n'est pas décalé, mais l'index est avancé de +5 min puis `reindex(method="ffill")` → à la minute t, ATR de
  la dernière M5 [t−5, t) entièrement close. Conforme (équivaut au `shift(1)` du protocole).
- **Signal / entrée** : rE, rG, x, u utilisent mid(t) = clôture M1 t ; entrée `time = signal + 1 min` à l'ouverture
  (ask achat / bid vente, l. 239). ffill limité à 2 min = passé uniquement.
- **max_gap_min = 1** (l. 235) : tolère en théorie une entrée à t+2 si t+1 manque (écart avec la lettre du protocole),
  mais vérifié : **0 trade** entré ailleurs qu'à t+1 (V1 et V5), 0 « skip ». Sans effet.
- **Sortie anticipée** (l. 250–257) : z(s) calculé sur la clôture de la minute k, sortie à l'ouverture k+1 ; stop
  testé avant dans la même minute. Conforme au piège signalé en pré-critique. Détail : pas de contrôle de trou entre
  k et k+1 (sans effet mesurable ici).
- **Test de perturbation** (`test_lookahead.py`, exécuté dans train.json) : σx, σu, médianes, ATR avant J, et
  features à t0 = 2025-10-06 09:20 UTC inchangés quand le futur est bruité ; témoin « futur changé » vrai → `pass`.
- **Contrôle C1** : le plancher de mouvement du pool (0,9 × plus petit mouvement des trades E001) n'est pas écrit au
  protocole ; il n'utilise que des mouvements, pas des R → neutre.

## Dépendance (quelques trades/jours, une paire, une période)
- V1 : 78 trades sur 45 jours ; **top 5 jours = 139 % du R** ; sans eux −0,038 R ; sans les 5 meilleurs trades
  −0,053 R ; sans EURUSD (meilleure paire) +0,015 R ; jours de fin de mois = 73 % du R.
- V5 : 27 trades sur **16 jours** ; top 5 jours = 117 % ; sans GBPUSD −0,051 R (n = 12) ; 20 des 27 trades dans le
  trimestre déc.–fév. (sans lui : n = 7) ; **3 trades de jours de nouvelles = +4,54 R sur 7,80 R (58 %)**, dont le
  meilleur trade +3,67 R le 2026-02-05 à 11:55 UTC = 5 min avant la décision BoE (et jour BCE). Hors jours de
  nouvelles : +0,136 R, t = 0,83.

## Corrélation entre paires
Un trade par signal (une seule jambe), cooldown par paire, vue par jour en Europe/London : V1 = 45 jours,
+0,147 R/jour, IC [−0,135 ; +0,441]. La variante deux jambes (double comptage EURGBP) a été retirée avant test.
Répartition V1 : GBPUSD 45 / EURUSD 33 — pas de biais de jambe massif. Rien de caché ici ; la vue par jour seule
suffit à faire échouer.

## Coûts
V1 : +0,085 R brut → **+0,010 R à +0,6 pip** (t = 0,10) : la marge mesurée est mangée presque entièrement par un
coût réaliste, comme prédit en pré-critique (référence H5 retour ≈ −0,03 R). V5 : +0,289 → +0,223 R, mais sur 27
trades dont un à 3,67 R.

## Force statistique
- V1 : t = 0,87 par trade, IC jour contient 0 ; P2 (sens aléatoire) : E001 +0,085 < 95e centile +0,105 → pas
  distinguable d'un sens tiré au hasard aux mêmes minutes.
- **V5/V6 (+0,29 / +0,32 R, n = 27) = bruit de sélection, pas un signal à retester** :
  1. V5 et V6 sont **les mêmes 27 entrées** (seul H change ; 22/27 sorties anticipées) : ce n'est pas une
     confirmation croisée mais un seul tirage compté deux fois.
  2. t = 1,47 → p unilatéral ≈ 0,08 ; la grille contient 4 ensembles de signaux distincts (abs(z) × W) → p corrigé
     ≈ 0,3 (Bonferroni) ; sur 8 variantes, le meilleur t attendu sous H0 est ≈ 1,4–1,8 : V5 est au niveau du bruit.
  3. Retirer UN trade (BoE 05/02, +3,67 R) ramène V5 à +0,159 R ; retirer les 5 meilleurs → −0,062 R.
  4. V5 ⊂ V1 (même W, seuil plus haut) : différence des totaux V1 − V5 = 6,61 − 7,80 = −1,2 R sur ≈ 51 trades
     (≈ −0,02 R/trade). Tout le « résultat » de E001 est donc concentré dans 27 trades / 16 jours dont 3 jours de
     nouvelles.
  5. Le voisin direct V7 (même seuil 3,0, W = 30) est à −0,150 R : l'effet n'existe qu'à un point de la grille.
  6. Puissance : avec σ ≈ 1,02 R/trade, un vrai +0,15 R exigerait ≈ 185 trades pour t = 2, soit ≈ 3,4 ans au rythme
     de 27 trades / 6 mois. Le seuil 3,0 avait été annoncé inutilisable en pré-critique (< 60 trades) avant test.
  Retester abs(z) ≥ 3,0 serait précisément un micro-réglage de seuil choisi après lecture du Train.

## Paramètres trop précis (voisins)
Sur W = 30, les 4 variantes sont négatives (−0,095 à −0,163) : le phénomène ne survit pas à un doublement de la
fenêtre de mesure, alors que le mécanisme annoncé (résorption en 10–30 min) le prédisait pour 15 ET 30 min. Seule la
paire W = 15 est positive, et seulement grâce au sous-ensemble abs(z) ≥ 3.

## Revue adversariale (forex_agent/meta/adversarial.py) sur un échantillon de trades
`review()` exige les objets setup/ctx du moteur live ; ses 4 questions sont appliquées à la main aux trades types.
- **Meilleur trade V5, GBPUSD 2026-02-05 11:55 UTC, +3,67 R (sortie au temps)** — meilleure raison d'être faux :
  signal 5 min avant la décision BoE de 12:00 ; le gain vient du saut de l'annonce, pas d'un retour d'impact
  temporaire. Contexte contradictoire : jour BCE + BoE (liste NEWS_DAYS). Risque caché : même mise exposée à un saut
  dans l'autre sens. Invalidation : tout signal dans les 15 min avant une banque centrale.
- **V1, 2026-01-20 13:30 et 2026-01-22 13:35 UTC (+2,23 R / +1,58 R)** : heure des publications US 08:30 ET → le
  filtre « dollar calme » mesuré sur 15 min passés n'élimine pas un choc USD qui commence à t. Invalidation : u qui
  grandit dans les minutes suivant l'entrée.
- **V1, 2025-12-31 15:50 et 2025-12-16 15:05 UTC (+2,60 / +2,13 R, sortie au temps)** : séance de fin d'année
  illiquide et pré-fixing de 16:00 → retours mécaniques connus (famille H3), pas EURGBP.
- Conclusion : les plus gros gains viennent de nouvelles, de l'heure US ou du voisinage du fix — exactement les
  explications concurrentes listées en pré-critique.

## Verdict imposé : REJECT
Protocole et code verrouillés avant les résultats (commit bf58584, 16 s avant train.json ; relance identique en
12,7 s), aucun look-ahead, décision « Train échoue » conforme (6 critères sur 10 échouent sur V1). V5/V6 = un seul
ensemble de 27 trades, t = 1,47, porté par un trade BoE et 3 jours de nouvelles, voisin W = 30 négatif : bruit de
sélection. Aucune expérience clairement différente n'est justifiée par ces données ; un retest à abs(z) ≥ 3 serait un
micro-réglage. À archiver comme « divergence EUR/GBP intrajournalière : non distinguable du retour à la moyenne
d'une paire seule après coûts ». Action annexe : corriger l'orchestrateur, qui a écrit VALIDATED/OOS_DONE dans
status.json alors que validation et OOS sont skipped.

Verdict imposé : REJECT
