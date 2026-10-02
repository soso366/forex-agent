# H3 — fade du fix de Londres : ARCHIVÉE (FAIL hors-échantillon)

Règle (figée) : 16:00 Europe/London (DST automatique). Si |mouvement des 30 min précédentes| ≥ 0,5 ATR M5 →
position opposée à 16:01, stop 1,5 ATR, sortie au bout de 30 min. EURUSD, GBPUSD, USDJPY.

| Période | Trades | R/trade | PF |
|---|---|---|---|
| Train sept. 2025 → fév. 2026 | 288 | +0,119 | 1,35 |
| Validation mars → août 2026 | 294 | +0,135 | 1,47 |
| **OOS verrouillé sept. 2024 → août 2025** | **577** | **−0,108** | **0,74** |

OOS lu une seule fois le 2 octobre 2026 avec les critères verrouillés (commit 2e4ae39) : 0 condition sur 7 remplie.
Vue par jour : IC 95 % de l'espérance quotidienne [−0,45 ; −0,05] R. 3 paires négatives, 1 trimestre positif sur 4,
placebo 13:00 et 14:00 meilleurs que 16:00, négatif à tous les niveaux de coût.

Décision : archivée, aucun réglage de rattrapage (exigence utilisateur). Ne pas retester sous forme de variante
(autre seuil k, autre stop, autre durée, filtre de jour) : ce serait de la sélection après coup.
Détails : `research/v4/out/oos_check.json`, `research/v4/rapport_v4.html`.
