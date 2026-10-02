# Registre des expériences (consulter AVANT toute nouvelle expérience)

Format : ID · titre · période(s) · variantes · résultat clé · verdict · où sont les détails.

| ID | Expérience | Données | Variantes | Résultat clé | Verdict | Détails |
|---|---|---|---|---|---|---|
| X-01 | Backtest V2 complet | mars → août 2026 | 1 | 148 trades, −1,97 €, −0,047 R/trade | pas d'avantage | `main`, results |
| X-02 | Parameter Lab blocs A–D | IS mars–mai, VAL juin–juil., OOS août 2026 | 213 | 2 réglages retenus (horaires 06–16, er_trend 0,25) | rejetés à l'OOS | `lab/rapport.html` |
| X-03 | OOS 2e période du lab | sept. 2025 → fév. 2026 | 2 configs | −2,8 R vs −3,1 R | aucun gain | `lab/results/final.json` |
| X-04 | Analyse des échecs V2 (miroir, géométrie, persistance) | 12 mois | — | sens sans info ; cibles atteintes 4–12 % ; cellules non persistantes | diagnostic | `research/v4/out/failures.txt` |
| V4-H1 | Sweep & reclaim Asie / PDH-PDL | Train V4 | 8 | toutes ≤ +0,06 R, la plupart négatives | REJECT | `research/v4/out/train.json` |
| V4-H2 | Opening range breakout Londres / NY | Train V4 | 8 | −0,26 à 0 R | REJECT | idem |
| V4-H3 = E000 | Fade du fix de Londres 16:00 | Train +0,12 R (288) · Valid +0,135 R (294) · **OOS sept. 2024 → août 2025 : 577 trades, −0,108 R, PF 0,74** | 8 | 0/7 critères OOS ; IC 95 % jour < 0 ; placebos 13:00/14:00 meilleurs | **REJECT / ARCHIVED** | `research/v4/archive/H3`, `experiments/E000-*` |
| V4-H4 | Fix de Tokyo USDJPY | Train V4 | 8 | +0,16 R mais t < 1 | REJECT (surveillance) | `train.json` |
| V4-H5 | Displacement M5 continuation / retour | Train V4 | 8 | continuation −0,14 à −0,19 R (t −4 à −6) ; retour ≈ −0,03 | REJECT | `train.json` |
| V4-R | Router matrix (stratégie × régime × séance × vol × paire) | 12 mois | — | V2 : 131 cellules UNKNOWN ; H3 : sous-cellules non persistantes | pas de filtrage par contexte | `research/v4/out/router.txt` |
| M-01 | Audit du journal V2 (meta-skill) | 12 mois | — | 22 % des perdants ont d'abord été à +0,5 R ; 40 % des sorties de gestion suivies d'un mouvement favorable ≥ 0,5 R | observations (à tester) | `lab/journal_audit_v2/` |
| E001 | Divergence EURUSD-GBPUSD (retour de l'écart EURGBP implicite) | Train sept. 2025 → fév. 2026 | 8 | V1 : 78 trades, +0,085 R, t 0,87, IC 95 % jour contient 0, négatif sans top 5 ; V5/V6 = bruit (27 trades, 1 trade BoE) | **REJECT** (Train) — OOS 2023-24 non ouvert | `experiments/E001-*` |
| E002 | Choc de spread hors heure ronde (retour après normalisation) | — | — | pré-critique GO (contrôles : artefact de cotation, spread normal) | protocole au cycle 2 | `experiments/E002-*` |
