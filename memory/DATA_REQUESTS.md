# Demandes de données M1 (Dukascopy)

## 2026-10-02 — OOS vierge sept. 2023 → août 2024 (cycle 1)

Rôle : échantillon hors-échantillon VIERGE pour les hypothèses du cycle 1 et suivants
(sept. 2024 → août 2026 est contaminé, déjà utilisé). À NE JAMAIS OUVRIR avant le
verrouillage (PROTOCOL_LOCKED) d'un protocole qui le désigne comme OOS.

| Période | Tag | Branche attendue | Dossier bootstrap | Run GitHub |
|---|---|---|---|---|
| 2023-09-01 → 2024-02-29 | 2023sep-2024feb | data-2023sep-2024feb | data/m1_oos2324_a | 37002044362 (1er dispatch, créé 11:37:42Z) |
| 2024-03-01 → 2024-08-31 | 2024mar-aug | data-2024mar-aug | data/m1_oos2324_b | 37002046304 (2e dispatch, créé 11:37:44Z) |

- Déclenchement : 2026-10-02 11:37:41 UTC, workflow « Export données M1 » (export-data.yml, ref main, attempt 1), HTTP 204 ×2.
- Correspondance run ↔ période déduite de l'ordre des dispatchs (non vérifiée dans les logs).
- Durée attendue : ≈ 5 à 9 h. Ensuite `bash orchestrator/bootstrap.sh` devra préparer
  data/m1_oos2324_a et data/m1_oos2324_b depuis les branches ci-dessus.
- Vérifier la fin : `git -C /home/claude/mar ls-remote origin | grep data-2023sep-2024feb\|data-2024mar-aug`.
