# E003 — critique AVANT test
Auteur : CRITIC · cycle 3 · 2026-10-10

## Meilleure raison pour laquelle c'est faux
Ces règles sont publiques depuis des décennies et copiées par des milliers de bots : tout avantage simple sur M5 a été
arbitré. Le projet a déjà mesuré que le sens des signaux techniques à 30 min ne porte pas d'information (test du miroir
V2) et qu'une entrée aléatoire avec stop 1 ATR coûte ≈ −0,07 R/trade en spread. Il faut donc battre ce plancher, pas zéro.

## Doublon ?
Aucun doublon formel. P1 est proche de V4-H5 « retour » et P2 de la continuation : contrôle imposé = comparer à une
**entrée placebo** (mêmes heures, mêmes paires, même stop, sens aléatoire) — si la stratégie ne bat pas le placebo,
elle n'a pas d'information.

## Risques méthodologiques
1. Look-ahead : EMA/RSI/BB/ATR calculés sur les clôtures M5 ≤ bougie du signal ; pente EMA50 H1 lue sur la dernière H1
   **close** ; entrée à la minute suivante. Test automatique obligatoire (signal identique si on tronque le futur).
2. Trop de variantes : 3 familles × 4 = 12. Un seul t ≥ 2 attendu par hasard sur ~12 → critères multiples + voisin.
3. Corrélation USD : vue par jour obligatoire.
4. Coûts : spread Dukascopy très serré (0,2–0,6 pip) ; un petit compte paie ≈ 1 pip et plus. Stress +0,5 et +1 pip décisif.
5. Partie « mise » : le risque 2 % ne crée pas d'espérance ; il multiplie celle qui existe. Ne pas présenter un meilleur
   résultat à 2 % comme une amélioration si l'espérance en R est négative.

## Verdict : GO (prior défavorable assumé ; résultat utile à l'utilisateur dans les deux sens)
