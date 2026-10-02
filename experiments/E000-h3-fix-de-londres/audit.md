# E000 — audit des résultats
Auteur : CRITIC (cycle 1) — audit du test hors-échantillon (OOS) sept. 2024 → août 2025 de H3 (fade du fix de Londres,
variante `mode=fade · k=0.5 · days=tous`, stop 1,5 ATR, 30 min, EURUSD/GBPUSD/USDJPY).

| Échantillon | n | Espérance (R/trade) | t | PF |
|---|---|---|---|---|
| Train (sept. 2025 → fév. 2026) | 288 | +0,119 | 2,22 | 1,35 |
| Validation (mars → août 2026) | 294 | +0,135 | 2,51 | 1,47 |
| **OOS verrouillé (sept. 2024 → août 2025)** | **577** | **−0,108** | **−3,09** | **0,74** |

Les 7 conditions de `oos_check.py` sont fausses (`a` à `g`) → FAIL mécanique. Le critère simple de `PROTOCOLE.md`
(« espérance > 0 et PF > 1 sur 2025 ») échoue aussi.

## Overfitting / sélection après coup
- **Chronologie des verrous (git log)** : critères OOS commités en e0bb22b (2026-10-01 11:15), e4de8f1 (11:20),
  2e4ae39 (11:31). Données OOS locales créées APRÈS : `data/m1_locked_2024/*.csv` le 2026-10-02 01:57,
  `data/m1_locked/*.csv` le 2026-10-02 04:01, ~1 min avant c57b82f (04:02:39, verdict FAIL). Le dossier `data/m1_2025`
  (2026-10-01 07:53, avant les critères) contient en fait sept. 2025 → fév. 2026 (= train ; 1re ligne 2025-09-01,
  dernière 2026-02-27) : nom trompeur, pas de fuite OOS. → **Aucune sélection après coup sur l'OOS.**
- **Sélection en train** : 40 variantes (5 hypothèses × 8) → ≈ 2 faux positifs attendus à 5 % ; le max de 40 t sous
  l'hypothèse nulle est typiquement ≈ 2,2–2,5. La variante retenue avait **t = 2,22** en train : le niveau attendu du
  meilleur de 40 tirages de bruit. Le train ne prouvait rien.
- **Validation non vierge** : `PROTOCOLE.md` (« Remarque d'honnêteté ») reconnaît que sept. 2025 → août 2026 a servi au
  Parameter Lab et que l'analyse des échecs V2 a « regardé les 12 mois ». L'idée même de « fade à 16:00 » a pu être
  inspirée par la période de validation : test semi-in-sample.
- **Traçabilité** : protocole (d92c027, 10:41:31) et résultats train + sélection (fd42436, 10:44:35) commités à 3 min
  d'écart : impossible de prouver que le protocole précède les premiers essais locaux. `status.json` date
  PROTOCOL_LOCKED 09:40 UTC et TRAIN_DONE 10:20 UTC alors que les commits sont à 08:41 et 08:44 UTC : horodatages
  incohérents (expérience « legacy »).

## Fuite de données / look-ahead
- `research/v4/hypotheses.py` l.114-135 : signal sur la bougie M5 15:55–16:00 Londres (`_local(..., "Europe/London")`,
  DST auto), entrée 16:00 + 1 min ; mouvement = `c[i] − o[i−5]` (30 min passées seulement).
- `research/v4/engine.py` l.36 : `m5["atr"] = atr(m5).shift(1)` → ATR connu avant la bougie.
- `oos.json → check_time` : 334 trades à 15:01 UTC (BST), 243 à 16:01 UTC (GMT), `all_at_1601_london = true`.
- Aucune fuite ni look-ahead trouvé.

## Dépendance (quelques trades/jours, une paire, une période)
- Échec non concentré : sans 5 meilleurs jours −0,154 R ; sans meilleur trimestre (Q3) −0,178 ; sans meilleure paire
  (EURUSD) −0,153 ; sans fins de mois −0,124.
- Trimestres : Q1 −0,029 ; **Q2 −0,197 (t −3,02)** ; Q3 +0,103 (t 1,31) ; **Q4 −0,288 (t −4,78)** → 1/4 positif.
  Mois : 9/12 négatifs ; janv. 2025 −0,406 R ; juin–août 2025 tous ≤ −0,24 R.
- Paires : EURUSD −0,015 (t −0,23), GBPUSD −0,186 (t −3,09), USDJPY −0,117 (t −2,07) → 0/3 positives.
- Saisonnalité exclue : été 2026 (V2) +0,210 R contre été 2025 (Q4 OOS) −0,288 R.

## Corrélation entre paires
- 2,31 paires par jour de fix ; corrélation des R le même jour : EURUSD-GBPUSD **0,63**, EURUSD-USDJPY 0,32,
  GBPUSD-USDJPY 0,28 (USD commun).
- Vue par jour (250 jours) : −0,248 R/jour, **IC 95 % [−0,447 ; −0,052]** ; 109 jours gagnants / 141 perdants.
- Une seule paire par jour : −0,010 R (t −0,17) ≈ 0. Le négatif global est amplifié par l'empilement de paires
  corrélées (surtout GBPUSD/USDJPY), mais il n'y a aucun avantage positif dans aucune vue.

## Coûts
- Négatif dès le coût additionnel nul (−0,108 R ; −1,25 pip/trade). +0,6 pip : −0,162 R (t −4,63) ; +1 pip : −0,198 R.
- Avantage de validation déjà mince : `critic_h3.txt`, +0,5 pip par côté → +0,008 R sur train+validation
  (avantage brut ≈ 1 pip aller-retour).
- Spread médian (quality_report) EURUSD/GBPUSD/USDJPY : train 0,4/0,6/0,3 ; OOS 2025 0,5/0,8/0,6 ; OOS 2024 0,3/0,9/0,7.
  +0,2 à +0,4 pip sur les deux paires les plus perdantes. À ≈ 0,09 R par pip, cela explique ≈ 0,03 R sur un écart de
  0,24 R : facteur réel mais minoritaire.

## Force statistique
- Écart validation → OOS = 0,243 R. Erreurs-types : 0,135/2,51 ≈ 0,054 ; 0,108/3,09 ≈ 0,035 → σ(différence) ≈ 0,064 →
  **z ≈ 3,8** (trades indépendants), ≈ 3,1 après inflation ≈ ×1,5 de la variance due à la corrélation intra-jour.
  Le bruit pur autour d'une même vraie espérance est improbable (p < 0,01).
- Mais +0,135 n'était pas une estimation sans biais : sélection parmi 40 variantes + période déjà regardée →
  espérance réelle a priori ≈ 0. L'écart à expliquer est donc surtout 0 → −0,108.
- Le bootstrap IC90 [+0,068 ; +0,192], P(≤0) = 0 de `critic_h3` était par trade (n = 592, train+validation mélangés),
  sans regroupement par jour : il surestimait la confiance.

## Paramètres trop précis (voisins)
- Voisins tous positifs en train+validation (k 0,25 → 1,0 : +0,090 à +0,155 ; stop 1–3 ATR ; durée 10–25 min), mais
  ils partagent les mêmes jours et mouvements : très corrélés, ce ne sont pas des tests indépendants.
- Fragilité déjà visible : durée 10 min T1 −0,019 ; entrée +3 min V1 −0,039 ; fin de mois V1 −0,093 ; USDJPY V1 −0,039 ;
  TREND_DOWN V2 −0,223 ; jeudi T1 −0,177 / T2 −0,178 puis V1 +0,248. Les sous-groupes changeaient de signe d'un
  trimestre à l'autre.

## Revue adversariale (forex_agent/meta/adversarial.py) sur un échantillon de trades
Question : pourquoi la validation était-elle trompeuse ? Les 4 rubriques de la meta-skill sont appliquées au niveau
de la stratégie (l'OOS n'exporte pas de trades individuels).
- **Meilleure raison d'être faux** : le signal n'est pas propre au fix. Placebos OOS : 10:00 −0,131 ; 12:00 −0,134 ;
  15:00 −0,107 ; 17:00 −0,081 ; 18:00 −0,124, contre **16:00 −0,108** (`placebo_equivalence_16h = true`). Le « fade d'un
  mouvement ≥ 0,5 ATR en 30 min » est un retour à la moyenne générique dont le signe dépend de la période :
  - en train, le fond était négatif à beaucoup d'heures (placebo 09:30 −0,154, 12:30 −0,169) et 16:00 ressortait :
    compatible avec l'heure chanceuse parmi ~20 testées ;
  - en OOS, 16:00 retombe au niveau du fond, et ce sont 13:00 (+0,097) et 14:00 (+0,090) qui « ressortent ».
- **Contexte contradictoire** : OOS à forte tendance USD (élection US nov. 2024, janv. 2025 −0,406 R, glissade USD
  de l'été 2025 de −0,24 à −0,31 R/mois) : les mouvements avant 16:00 se prolongent au lieu de revenir. Seul trimestre
  positif : mars–mai 2025 (+0,103), pendant le choc de volatilité des tarifs, où les excès se retournaient.
- **Risque caché** : corrélation USD (0,63) qui multiplie la même erreur par 2,3 positions/jour ; avantage brut ≈ 1 pip,
  détruit par +0,2–0,4 pip de spread.
- **Condition d'invalidation** (pré-enregistrée) : espérance ≤ 0 et PF ≤ 1 en OOS → atteinte (−0,108, PF 0,74),
  IC 95 % par jour entièrement < 0.

**Diagnostic de l'écart +0,135 → −0,108 :**
1. **Sélection** (cause principale) : t train 2,22 = max attendu de 40 variantes ; validation contaminée par l'analyse
   préalable des mêmes 12 mois.
2. **Changement de régime du fond** (cause secondaire réelle) : en OOS toutes les heures de fade valent ≈ −0,1 R et
   16:00 n'en diffère pas. L'effet « fix » n'a pas disparu : il n'a jamais été démontré.
3. **Bruit** : insuffisant seul (z ≈ 3,1–3,8) mais il amplifie (1) : 294 trades sur ≈ 130 jours corrélés,
   IC 95 % par trade ≈ [+0,03 ; +0,24], plus large par jour.
4. **Coûts** : contribution mineure (≈ 0,03 R), concentrée sur GBPUSD/USDJPY.

## Verdict imposé : OK | RETEST | REJECT
**REJECT.**
- Échec pré-enregistré sans ambiguïté : 0/7 conditions ; IC 95 % par jour [−0,447 ; −0,052] ; 1/4 trimestre ;
  0/3 paires ; 16:00 équivalent aux placebos ; négatif même sans coût additionnel.
- Test valide : pas de fuite, pas de look-ahead, critères (2e4ae39) commités avant la création des données verrouillées
  et avant c57b82f.
- **RETEST interdit** : toute variante dérivée (k, heure 13:00/14:00, une paire/jour, filtre de régime, EURUSD seul)
  serait une sélection sur un OOS désormais brûlé. À inscrire dans `memory/REJECTED_HYPOTHESES.md` : « fade d'un
  mouvement 30 min ≥ k ATR à heure fixe (fix de Londres 16:00), rejeté en OOS 2024-25 ».
- Leçons de protocole : (1) l'heure cible doit battre nettement les placebos dès le train, en vue par jour ;
  (2) une période déjà vue par une autre analyse ne compte pas comme validation ; (3) bootstrap et IC par jour,
  jamais par trade.
