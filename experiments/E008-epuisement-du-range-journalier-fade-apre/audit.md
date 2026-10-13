# Audit E008 (Train échoué) — verdict : REJECT (confirmé)
- Protocole, code et signal_counts commités en e56a109 avant tout R ; protocole non modifié depuis (1 seul commit). Seuil 0,30 fixé sur comptage sans R.
- Code relu (e008.py) : ADR20 sur jours strictement antérieurs (jour courant jamais lu), M avec l'open de la barre d'entrée, ATR M5 de la barre terminée à signal-5 min, sortie < 21:00 UTC (assert), tests synthétiques fournis. Pas de look-ahead ni bug fabriquant l'échec.
- Chiffres cohérents : n=164 (≥150), +0,016 R, t=0,14, IC95 par jour [-0,244 ; +0,295] (92 jours), -0,020 R à +0,5 pip, 64 % de stops. Sens inverse -0,154 R (t=-1,34). Variantes B (-0,097), C (-0,046) : aucune ne sauve A (et ne le peut pas).
- validation.json et oos.json = {"skipped": "Train échoué"} : non lus, OOS vierge intact.
- Remarque : 64 % de stops avec stop 3 ATR M5 (étroit pour 4 h) = R dominé par le stop ; ne change pas le verdict (coût +0,5 pip déjà négatif).
Archiver. Pas de RETEST.
