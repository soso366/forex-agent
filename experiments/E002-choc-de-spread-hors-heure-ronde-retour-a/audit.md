# E002 — audit des résultats
Auteur : CRITIC · cycle 2 · 2026-10-02 · porte sur results/train.json (validation et OOS non exécutés : `{"skipped": "Train échoué"}`)

## Overfitting / sélection après coup
- Ordre des commits conforme : `222bf4d` (16:18:31 +0200, protocol.md + code/ verrouillés) AVANT `5a5e1c7`
  (16:19:13, results/ + status). `status.json.protocol_commit = 222bf4d`. Aucune modification de protocol.md après.
- Seul élément connu avant le verrouillage : le nombre de signaux (8 à 3×, 18 à 2,5×), comme exigé par la
  précritique (point 4). Le protocole en tire la conséquence AVANT les R : « aucune variante n'est éligible
  (n ≥ 80) et le critère Train 1 ne peut pas être rempli ». Pas de relâchement supplémentaire (ni 2×, ni ATR 0,8,
  ni normalisation 10 min) : conforme.
- Choix de variante conforme : règle principale = V5 (n(V1) = 8 < 80), `eligible_n80 = []`, « retenue » = V2 au
  seul titre du meilleur score prudent rapporté (0,509 = min(V2, V1, V4, V6)), comme écrit dans le protocole.
  V2 n'est PAS une variante validable : c'est la meilleure de 8 sur 8 trades, donc la plus exposée au biais de
  sélection.

## Fuite de données / look-ahead
- ATR : `e002.py` réétiquette l'ATR M5 à la FIN de la barre (`a.index + 5 min`) puis lit en asof à t + 1 min
  (clôture de t) → seules les M5 terminées sont utilisées ; la fuite `atr_now` (étiquette de début) est évitée.
  `test_lookahead.py` le confirme et prouve sa sensibilité (`sensitivity_naive_atr_t0_changes = True`, 3 paires).
- ref_t : `_ref()` n'utilise que `bd[k-20:k]` (20 jours ouvrés précédents, jour courant exclu) ; test
  `ref_day_J_unchanged = True`.
- Δ, normalisation, extrême X, filtre 50 % : uniquement minutes ≤ m ; décalages en horodatage (grille complète).
- Entrée à l'ouverture de m+1 (`f.ao[e]`/`f.bo[e]`, minute présente exigée) ; `simulate(..., max_gap_min=1)`. Conforme.
- Verdict : pas de look-ahead détecté. `lookahead_test.pass = True`.

## Dépendance (quelques trades/jours, une paire, une période)
Les 8 trades (identiques pour V1–V4, seule la sortie change), reconstruits depuis `code/e002.py`, R de V2 :

| # | choc (UTC) | entrée | paire | R V2 | contexte |
|---|---|---|---|---|---|
| 1 | 2025-10-29 18:36 | 18:41 | USDJPY | +0,95 | **conférence de presse Powell (FOMC, décision 18:00, presser 18:30 UTC)** |
| 2 | 2025-10-30 06:42 | 06:47 | USDJPY | +0,40 | **conférence de presse Ueda (BoJ, ~06:30 UTC)** |
| 3 | 2025-11-28 09:11 | 09:16 | GBPUSD | +0,43 | **panne CME Globex (data center CyrusOne), lendemain de Thanksgiving (férié pré-déclaré)** |
| 4 | 2025-11-28 11:41 | 11:45 | USDJPY | +0,47 | **même panne CME** : spread USDJPY ≈ 4× ref sans interruption de 11:37 à 11:58 ; la « normalisation » = une seule minute (11:44, s = 0,005) |
| 5 | 2025-12-10 19:40 | 19:44 | USDJPY | +2,36 | **conférence de presse Powell (FOMC, décision 19:00, presser 19:30 UTC)** |
| 6 | 2025-12-19 06:41 | 06:43 | USDJPY | +2,84 | **conférence de presse Ueda après la hausse de taux BoJ du 19/12** |
| 7 | 2026-01-14 12:04 | 12:08 | USDJPY | −0,69 | période de « jawboning » du MoF japonais (Katayama) vers 158 ; cause précise non vérifiée |
| 8 | 2026-01-27 09:52 | 09:58 | USDJPY | +3,89 | chute de 90 pips en 1 min (18,1 ATR), spread 5× : climat de « rate check »/menace d'intervention fin janvier 2026 ; cause exacte non vérifiée |

- 4 trades sur 8 (#1, #2, #5, #6) tombent pendant une **conférence de presse de banque centrale programmée** :
  la minute du choc est « hors ronde », mais l'événement est une nouvelle programmée. Le filtre horloge ±2 min ne
  les exclut pas, contrairement à ce que supposait l'hypothèse (« hors minute ronde = rarement une nouvelle »).
  Ces 4 trades = 6,55 R sur 10,64 R (62 %).
- 2 trades (#3, #4) = un seul épisode de marché anormal (panne CME, jour férié US) ; 0,90 R.
- 2 trades (#7, #8) = épisodes d'intervention / interventions verbales japonaises ; #8 seul = 3,89 R (37 % du total V2).
- Concentration chiffrée (V2) : 5 meilleurs jours = 103 % du R total (critère 12 : < 40 %) ; sans les 5 meilleurs
  trades : +0,04 R sur 3 trades ; sans USDJPY : 1 trade. V1 : 5 meilleurs jours = 106 %, sans eux −0,08 R.
- Conclusion : ce n'est pas un « retour de liquidité » générique mais **le retracement de chocs USDJPY sur
  4–5 événements macro japonais/US identifiables**. Artefact de quelques événements, pas un indice d'avantage récurrent.

## Corrélation entre paires
7/8 trades sur USDJPY, 0 sur EURUSD. Vue par épisode = 8 épisodes (pas de doublon simultané), mais l'échantillon
est en pratique celui d'une seule paire et d'un seul thème (yen 2025-26 : BoJ, MoF).

## Coûts
V2 : +1,27 R à +0,6 pip, +1,24 R à +1,0 pip (stop 1,5 ATR M5 large en pips lors des chocs). V5 (règle principale) :
+0,11 R à +0,6 pip, t = 0,68. Les coûts ne sont pas le problème ; la taille d'échantillon l'est.

## Force statistique
- V2 : n = 8, t = 2,45, IC jour [0,47 ; 2,60] sur 7 jours. Avec 8 variantes et 8 trades, un t de 2,4 sur la
  meilleure n'a rien d'exceptionnel ; un bootstrap sur 7 jours n'est pas fiable.
- Règle principale pré-déclarée V5 : n = 18, +0,18 R, t = 1,10, IC jour [−0,12 ; 0,58], sans les 5 meilleurs
  trades −0,11 R, sans les 5 meilleurs jours −0,05 R. Le seul test pré-déclaré n'est PAS significatif.
- Critères échoués (train.json) : 1 (n ≥ 80), 2 (principale t ≥ 2), 9 (C3 : n(A2) = 8 < 30), 12 (concentration).
  Un seul échec suffit.
- Les contrôles favorables (C1 écart +1,35 R, placebo p95 dépassé, C2 hors-ronde > ronde) sont calculés sur
  8 trades dominés par 3 événements : ils ne prouvent rien. C2 : n = 39 < 50 → mécanisme NON confirmé.

## Paramètres trop précis (voisins)
V1/V3 (cible 50 %) +0,51 / ≈ +0,17 R ; V2/V4 (sans cible) plus élevés surtout parce que le trade #8 (+3,89 R)
continue à revenir après la cible. L'écart V2 vs V1 tient à 2–3 trades. V5–V8 (18 trades) : t de 1,10 à 1,71.

## Revue adversariale (forex_agent/meta/adversarial.py) sur un échantillon de trades
- Meilleure raison d'être faux : les gains viennent de retracements d'excès **pendant des conférences de presse
  BoJ/Fed et des menaces d'intervention japonaises** ; régimes d'information, pas de liquidité.
- Contexte contradictoire : sur 3 417 chocs « même mouvement, spread normal » (C1), −0,02 R ; l'avantage n'existe
  que dans 8 cas extrêmes.
- Risque caché : une vraie intervention (sept. 2022, avril-mai 2024) ne revient pas en 15 min → perte ≥ 1 R avec
  glissement ; un stop de 1,5 ATR M5 calculé avant le choc est minuscule face à un mouvement de 18 ATR.
- Condition d'invalidation : ≥ 80 trades hors événements datés, sur plusieurs paires — non atteinte.

## Piste éventuelle pour le Researcher (hypothèse DIFFÉRENTE, pas un relâchement)
Question distincte, à formuler et pré-critiquer comme NOUVELLE hypothèse si le Researcher le juge utile :
« surréaction pendant les conférences de presse des banques centrales (FOMC/BoJ/BCE/BoE), fenêtre +5 à +60 min
après la décision, sens contraire au premier mouvement » — calendrier pré-déclaré, toutes paires concernées.
Réserves : ≈ 30 événements/an (échantillon structurellement petit), proximité avec H5 ; un historique long
(2019→) est nécessaire pour espérer n ≥ 80. Les 8 trades E002 ne peuvent pas servir de preuve.

## Verdict imposé : REJECT
Train échoué (règle utilisateur : échec au Train = REJECT immédiat, ni validation ni OOS). Critères 1, 2, 9, 12
non remplis : n = 8 (V1–V4) et 18 (V5–V8) contre 80 requis ; règle principale V5 +0,18 R, t = 1,10 ; 5 meilleurs
jours = 103 % du R de V2 ; 6/8 trades sur des événements datés (conférences Fed/BoJ, panne CME). Conformité du
protocole et absence de look-ahead : OK. Pas de RETEST : aucun seuil ne peut être relâché (protocole).
