# E000 — H3 fix de Londres (expérience historique, recherche V4)
Hypothèse, protocole, code et résultats : `research/v4/` (branche research-v4), `research/v4/PROTOCOLE.md`,
critères OOS verrouillés dans `research/v4/oos_check.py` (commit 2e4ae39). FIGÉE : aucun fichier ne doit changer.
Règle : 16:00 Europe/London (DST auto) ; si |mouvement 30 min| ≥ 0,5 ATR M5 → position opposée à 16:01, stop 1,5 ATR,
sortie au bout de 30 min ; 3 paires.
