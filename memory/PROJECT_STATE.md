# État du projet (mis à jour par le Manager à chaque cycle)

Dernière mise à jour : 2026-10-20 (cycle 21)
Dernier cycle : cycle 21 (2026-10-20) : 0 hypothèse (14e cycle consécutif, même blocage). Précédent : cycle 20 (2026-10-20) : 0 hypothèse (13e cycle consécutif, même blocage). Précédent : cycle 19 (2026-10-19) : 0 hypothèse (12e cycle consécutif, même blocage). Précédent : cycle 18 (2026-10-19) : 0 hypothèse (11e cycle consécutif, même blocage). Précédent : cycle 17 (2026-10-18) : 0 hypothèse (10e cycle consécutif, même blocage). Précédent : cycle 16 (2026-10-18) : 0 hypothèse (9e cycle consécutif, même blocage). Précédent : cycle 15 (2026-10-17) : 0 hypothèse (8e cycle consécutif, même blocage). Précédent : cycle 14 (2026-10-17) : 0 hypothèse (7e cycle consécutif, même blocage). Précédent : cycle 13 (2026-10-16) : 0 hypothèse (6e cycle consécutif, même blocage). Précédent : cycle 12 : 0 hypothèse. Précédent : cycle 11 (2026-10-15) : 0 hypothèse (4e cycle consécutif, même blocage). Précédent : cycle 10 (2026-10-15) : 0 hypothèse (3e cycle consécutif, même blocage données). Précédent : cycle 9 (2026-10-14) : 0 hypothèse (Researcher confirme l'épuisement ; recommande de ne pas relancer de cycle sans nouvelles données). Précédent : cycle 8 (2026-10-14, GitHub Actions) : aucune hypothèse proposée (espace testable épuisé avec bid/ask M1 seul). Aucun OOS consommé. Besoin : calendrier économique / historique / volume.
Contrôle : voir `orchestrator/control.yaml` (RUNNING / PAUSED)
Moteur d'autonomie : tâche planifiée Claude externe DÉSACTIVÉE (aucun accès au dépôt privé). Remplaçant prêt : GitHub Actions `agents-cycle.yml` (en attente d'un secret API et de l'accord pour main). Les cycles tournent pour l'instant en session interactive.

## Publication (2 octobre 2026)
- Historique Git RÉÉCRIT pour retirer `knowledge/sources` (contenus de tiers) : tous les identifiants de commit
  antérieurs au 2 oct. 2026 21:00 ont changé ; ceux cités dans la mémoire ou les status.json sont ANCIENS (retrouver
  le commit par son message).
- Données Dukascopy déplacées dans le dépôt PRIVÉ `soso366/forex-data` (mêmes branches `data-*`). `bootstrap.sh` et
  `export-data.yml` utilisent ce dépôt. Moindre privilège : `DATA_REPO_TOKEN` = jeton fin LECTURE SEULE (Contents: Read)
  limité à forex-data, utilisé par `agents-cycle` / `bootstrap.sh`. La publication de nouvelles données (`export-data.yml`)
  utilise un secret séparé `DATA_WRITE_TOKEN`, NON créé tant qu'aucune nouvelle donnée n'est nécessaire.
- Audit de publication du 9 oct. 2026 : aucun secret ni donnée personnelle dans l'historique ; forex-data privé ;
  6 branches `data-*` identiques (mêmes SHA) dans forex-data avant suppression de forex-agent.

## Où en est-on
- **Baseline officielle = V2** (branche `main`) : 6 stratégies, Router par régime, Risk Manager. Pas d'avantage démontré.
- **Meta-skills** ajoutées sur `main` (informatives, rejeu identique 148 trades / −1,97 €).
- **Recherche V4** (branche `research-v4`) : 5 hypothèses testées, une seule candidate (H3, fix de Londres).
- **H3 / E000 : TERMINÉE — FAIL OOS, REJECT / ARCHIVED** (sept. 2024 → août 2025 : 577 trades, −0,108 R/trade, PF 0,74,
  3 paires négatives, 1 trimestre positif / 4, IC 95 % journalier entièrement négatif, placebos 13:00/14:00 > 16:00).
  Ne JAMAIS la resélectionner, la retester, l'optimiser ni la recycler.
- **Aucune stratégie validée pour le paper trading.**
- **Cycle 1** : E001 (divergence EURUSD-GBPUSD) REJECT au Train.
- **Cycle 2** : E002 (choc de spread) REJECT au Train (8 trades, portés par quelques événements). Aucune donnée de validation ni OOS consommée.
- **Cycle 3** (GitHub Actions, 11 oct.) : E003 (nombres ronds, retournement au premier contact) → pré-critique GO, protocole + code VERROUILLÉS (commit 7b277ef). Train NON lancé : la session GitHub Actions n'avait pas le secret `DATA_REPO_TOKEN` → aucune donnée (dossier `data/` absent). À corriger par l'utilisateur.
- **OOS vierge en préparation** : sept. 2023 → août 2024 (voir memory/DATA_REQUESTS.md). Les 24 mois sept. 2024 → août 2026
  sont CONTAMINÉS : utilisables en Train / Validation, jamais comme OOS.

## Contraintes permanentes
intraday 5 min – 4 h, fermé avant 21:00 UTC (depuis le 12/10/2026) · scan 5 min · EURUSD/GBPUSD/USDJPY · 150 € (depuis le 11/10/2026) · paper · max 2 positions · risque 1 %/trade, 2 % total,
perte jour 3 %, drawdown 20 % = kill switch, 3 pertes = pause 60 min, pas de martingale, stop obligatoire jamais élargi,
min R:R 1,5 (baseline), pas deux positions avec la même devise dans le même sens.

## Données disponibles (Dukascopy M1 bid/ask)
| Période | Dossier local | Branche (dépôt privé soso366/forex-data) | Rôle |
|---|---|---|---|
| sept. 2025 → fév. 2026 | `data/m1_2025` | `data-2025sep-2026feb` | Train V4 |
| mars → août 2026 | `data/m1` | `data-2026mar-aug` | Validation V4 |
| mars → août 2025 | `data/m1_locked` | `data-2025mar-aug` | OOS H3 consommé → validation seulement |
| sept. 2024 → fév. 2025 | `data/m1_locked_2024` | `data-2024sep-2025feb` | OOS H3 consommé → validation seulement |
| sept. 2023 → fév. 2024 | `data/m1_oos2324_a` | `data-2023sep-2024feb` | **OOS vierge** (en téléchargement) |
| mars → août 2024 | `data/m1_oos2324_b` | `data-2024mar-aug` | **OOS vierge** (en téléchargement) |
Les CSV ne sont pas dans git (trop gros) : les cloner depuis la branche `data-*` et `gunzip`.
Ne jamais ouvrir l'OOS vierge 2023-2024 avant qu'un protocole soit verrouillé (commit) pour l'expérience concernée.

## Chiffres de référence
- V2, 12 mois (305 trades) : −0,033 R/trade, PF 0,90. Sens du signal sans information (test du miroir).
- Coût moyen : spread ≈ 0,3–0,6 pip ; entrées aléatoires stop 1 ATR M5 ≈ −0,07 R/trade.
- Amplitude typique en 30 min ≈ 2,3 ATR M5 (07–20 UTC).
