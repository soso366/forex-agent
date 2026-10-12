# E003 — audit du Train (CRITIC)

Verdict final : **CONFIRM_REJECT**

## 1. Conformité au protocole verrouillé
- `sha256(protocol.md)` = `d43d2b5c…64a2`, identique à `status.json` (`protocol_sha`). Aucun changement.
- `git diff 7b277ef HEAD -- protocol.md code` : vide. Ni protocole ni code modifiés après le verrouillage (7b277ef, 18:43) ; les commits suivants ne touchent que `status.json` et `results/`.
- Ordre des commits : `signal_counts.json` (2cd444e, 20:08:04) avant `train.json` (e26f8d7, 20:08:24). `run.py` vérifie que le fichier est suivi par git et propre (lignes 104-105). Exigence 2 respectée.
- `train.json` : `passed=false` ; T1, T7, T14, T15 réussis, les 14 autres critères échouent. Le verdict suit la règle « un seul échec → REJECT ». Aucun critère relâché ni réinterprété.

## 2. Fuite / look-ahead
- `lookahead_real` et `synthetic_test` passent pour les 3 paires. Le contrôle « ATR naïve » détecte bien la fuite (`sanity_naive_atr_leaks=true`), donc le test n'est pas vide.
- `e003.py` lignes 129-130 : extrêmes de fenêtre avec `.rolling(...).shift(1)`, donc sans la minute t. Ligne 156 : mid(t−15) par décalage positif. Ligne 190 : `shifted(..., -5)` est un diagnostic de cascade (rapporté seulement, pas une règle).
- Pas de fuite visible. Si fuite il y avait, elle améliorerait le résultat, or celui-ci est nul : l'objection est sans conséquence.

## 3. Cohérence des chiffres (A, 360 trades)
- Espérance −0,0097 R (t = −0,19) ; par jour −0,028 R (125 jours, IC 95 % [−0,31 ; +0,25]). À 0,5 pip : −0,112 R (t = −2,24). Stress prix pire : −0,128 R.
- Placebo : rang centile 67,9 % (seuil 90 %), moyenne des 28 grilles −0,051 R. D = +0,041 R, IC 95 % jour [−0,058 ; +0,142], donc T6 échoue aussi. A est battue par la grille +17 (+0,063 R, diff −0,073). L'espérance moyenne négative des grilles montre que le coût/spread domine le signal, pas un effet des nombres ronds.
- Pas de dépendance à quelques jours à discuter : le résultat est déjà ≤ 0 en global.

## 4. Les 2 choix signalés
- **IC 95 % par jour éliminatoire (T6)** : justifié. Les trades d'un même jour sont corrélés (USD commun, 127 jours pour 360 trades). Le protocole le fixe avant les données. T6 est de plus redondant : T2, T3, T4, T5 échouent seuls. Retirer T6 ne changerait rien.
- **Comptage des signaux dans un fichier séparé** : c'est une exigence du protocole, pas un ajout. Le fichier ne contient aucun R (aucun appel au simulateur) et a été commité avant le Train. Il n'ouvre aucune porte de sélection : n(A) = 360 ≥ 80 (T1 réussi), donc le comptage n'a rien filtré.

## 5. Validation et OOS non consommés
- `validation.json` et `oos.json` = `{"skipped": "Train échoué"}`.
- `python -m orchestrator oos-gate E003` répond **FERMÉ**.
- Aucun dossier `data/m1_oos2324_*` n'existe. `data/m1_locked*` sont les OOS d'expériences antérieures, pas celui d'E003. Aucune trace de lecture de l'OOS vierge 2023-24.

## 6. Points à ne pas recycler
- Seuls EURUSD (+0,095 R, 107 trades, t = 1,03), le niveau 00 (+0,081 R) et la moitié sept.–nov. (+0,067 R) sont positifs. Aucun n'est significatif et ils ont été trouvés après coup parmi des découpes multiples : c'est du bruit. Les récupérer (B, EURUSD seul, 00 seul) serait une sélection post hoc interdite par la règle 7. Le gradient 00/50 (T7 « réussi ») est lui-même incohérent avec un mécanisme : le niveau 50 perd −0,086 R et A reste négative.
- Hypothèse archivable dans `memory/REJECTED_HYPOTHESES.md` : « retournement au premier contact des niveaux 00/50 à 5–30 min, ATR(14, M5), stop 1 ATR / cible 1 R ».

## Verdict : CONFIRM_REJECT
Protocole respecté, pas de fuite, échec net (14 critères sur 18), Validation et OOS vierge intacts. Pas de RETEST.
