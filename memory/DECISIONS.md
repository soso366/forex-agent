# Décisions verrouillées (ne pas rouvrir sans fait nouveau)

| Date | Décision | Raison / preuve |
|---|---|---|
| 2026-09 | Paper trading uniquement, aucun broker réel | exigence utilisateur |
| 2026-09 | Durée max 30 min, scan 5 min, 3 paires, 50 €, max 2 positions | exigence utilisateur (durée et capital remplacés le 2026-10-11) |
| 2026-09 | Risque 1 %/trade inchangé ; jamais augmenté pour améliorer un résultat | exigence utilisateur |
| 2026-09 | Données Dukascopy M1 bid+ask réelles pour toute mesure | spread réel ; données synthétiques abandonnées |
| 2026-09-30 | Parameter Lab : 213 variantes ; seuls « horaires 06–16 UTC » et « er_trend_min 0,25 » passaient | OOS sept. 2025 → fév. 2026 : −2,8 R vs −3,1 R (V2) = aucun gain → **non adoptés** |
| 2026-10-01 | Pas de micro-réglage de la V2 | l'OOS a montré que les gains du lab étaient du bruit |
| 2026-10-01 | Router V4 : on n'utilise que les dimensions de contexte dont la persistance Train→Validation est démontrée ; sinon UNKNOWN = NO TRADE | cellules V2 : corrélation de rang P1→P2 entre −0,36 et +0,03 |
| 2026-10-01 | H3 figée ; critères OOS verrouillés (commit 2e4ae39) | protocole pré-enregistré |
| 2026-10-01 | Si H3 FAIL/INCONCLUSIVE : archiver, ne pas la sauver, nouvelle famille d'hypothèses | exigence utilisateur |
| 2026-10-01 | Meta-skills = informatives seulement ; aucune décision de trading modifiée | rejeu identique 148 trades |
| 2026-10-01 | Système multi-agents sur `multi-agent-research` ; merge vers `main` uniquement avec accord | limites d'autorité |
| 2026-10-02 | H3 / E000 : FAIL OOS → REJECT / ARCHIVED définitif | 577 trades, −0,108 R, PF 0,74 ; verdict utilisateur « ne plus retester » |
| 2026-10-02 | Sept. 2024 → août 2026 = données contaminées (Train / Validation uniquement) ; nouvel OOS vierge = sept. 2023 → août 2024 | exigence utilisateur |
| 2026-10-02 | E001 REJECT au Train | audit du Critic |
| 2026-10-02 | E002 REJECT au Train ; OOS vierge 2023-2024 toujours non lu (verrou oos-gate) | audit du Critic |
| 2026-10-02 | Tâche planifiée Claude externe désactivée (pas d'accès au dépôt privé) ; automatisation à porter sur GitHub Actions | piste automatisation séparée |
| 2026-10-11 | **Recherche : durée max 60 min** (au lieu de 30) et **capital de référence 150 €** (au lieu de 50) ; risque 1 %/trade, 2 positions max et toutes les protections inchangés. La baseline V2 et `config/settings.yaml` (protégés) ne sont pas modifiés. E001, E002 et H3 restent rejetées : ne pas les retester sous prétexte du nouvel horizon. | décision explicite de l'utilisateur : à 30 min le spread pèse trop face à l'amplitude typique (cibles hors de portée, 58 % des trades sortis au temps) |
