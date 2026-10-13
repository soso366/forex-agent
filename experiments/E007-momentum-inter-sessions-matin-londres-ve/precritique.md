# E007 — Précritique (CRITIC, cycle 6)
Verdict : GO SOUS CONDITIONS

- Doublon : non (dupcheck vide ; REJECTED : ORB V4-H2, E005 fenêtres horaires, H3). Proche d'E005 (mêmes heures 13-17) : le placebo horaire doit inclure E005.
- Incohérence R/stop : R = 1 ATR M5 x3 (~4-5 pip) alors que la sortie dure 4 h. Le stop catastrophe sera touché très souvent, donc le résultat mesuré sera celui du stop, pas du momentum. À fixer AVANT : stop plus large (ex. 3 ATR H1) ou pas de stop, et R défini sur une base stable ; sinon t-stat non interprétable.
- Puissance : 333 trades poolés mais EURUSD/GBPUSD/USDJPY partagent l'USD, donc n effectif ~111 jours ; t clusterisé par jour obligatoire (déjà prévu). Placebo « top 10 % » parmi 17 fenêtres = rang 1 ou 2 seulement : à garder tel quel. Ajouter test par signe USD (USDJPY inversé) et jours NFP/CPI exclus en sensibilité.
- DST : Europe/London bien, mais l'ouverture NY (heure US) décale de 1 h pendant ~1-2 semaines (fin oct/début nov, mars) par rapport à Londres ; vérifier que les résultats tiennent hors de ces semaines. La mention « ADR20 disponible » n'est pas dans les conditions : retirer ou la définir (jours précédents seulement).
- Pas de look-ahead dans le signal (08:00→13:00, entrée 13:00 open) si l'entrée est bien au bar suivant la clôture 13:00 ; coûts +0,5 pip et variantes (4 ≤ 8) OK.
