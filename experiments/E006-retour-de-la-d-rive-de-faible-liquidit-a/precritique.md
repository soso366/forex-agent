# E006 — critique AVANT test
Auteur : CRITIC

## Meilleure raison pour laquelle l'hypothèse est fausse
Une dérive 00–07 UTC de |z| ≥ 1 est le plus souvent de l'information réelle (Japon, Chine, Australie, données de la nuit) ou le début de la tendance londonienne. Le retour se fait alors à contre-courant d'un flux de continuation. Le mécanisme « carnet mince = impact temporaire » n'est pas observable ici : pas de profondeur et pas de volume (cf. E004). Le spread moyen sert seulement de proxy. Hold de 4 h = bruit élevé pour un effet attendu de l'ordre de 0,05 R.

## Doublon / déjà testé ?
- Pas un doublon strict. dupcheck de l'auteur : aucun. V4-H1 testait un signal de cassure-échec de niveau à 5–30 min. Ici : dérive totale à heure fixe, horizon 2–4 h. La condition « autre horizon que 5–30 min » de REJECTED_HYPOTHESES est donc formellement remplie.
- Voisinage proche : V4-H1 (extrêmes d'Asie), V4-H5 « retour » (≈ −0,03 R) et la famille « fade à heure fixe » (H3 : jamais retester). E006 ne doit pas se réduire à un fade d'heure fixe : la comparaison au placebo 12:05 est donc décisive.
- Risque de doublon de fait : si le gain, éventuel, vient seulement des trades où le prix revient dans le range asiatique (sweep), le résultat est V4-H1 à 4 h. Il faut le mesurer (voir tests).

## Risques méthodologiques prévisibles
- Falsifiabilité : OK, critères chiffrés écrits avant. Fuseau : UTC fixe, pas de DST pour la mesure. Mais l'ouverture de Londres bouge de 1 h en UTC entre été et hiver (07:00 UTC = 08:00 londonien en hiver, 07:00 en été). Le Train sept.–fév. est surtout en heure d'hiver et la Validation mars–août surtout en heure d'été. Un changement de signe entre les deux périodes peut venir du DST, pas du bruit. À rapporter par sous-période UTC+0 / UTC+1.
- Look-ahead : aucun apparent si ATR(14) est calculé jusqu'à la barre M5 de 07:00 incluse et clôturée, et si l'entrée à 07:05 utilise l'ask/bid de l'open M1 de 07:05. Interdire l'usage du close M5 de 07:05. « ATR journalier moyen des 20 jours passés » n'est pas défini (ATR D1 ? range moyen ?) et doit l'être, sans inclure le jour courant.
- Taille d'échantillon : 6 mois ≈ 125 jours × 2 paires = 250 paires-jours. Avec |z| ≥ 1 sur une marche aléatoire normalisée, environ 30 % des jours déclenchent, soit ~75 trades, bien moins que les 150 exigés au critère 1. Le filtre de range réduit encore. Le critère 1 sera probablement raté mécaniquement. Le protocole doit compter les trades avant d'ouvrir les résultats. Si le nombre attendu est < 150, REJECT « échantillon insuffisant » (pas un échec de l'idée) plutôt qu'un élargissement du seuil après coup.
- R non défini : le stop « 3 ATR M5 » (~10–15 pips) est étroit pour un hold de 4 h, il peut être touché souvent, alors que le risque de 1 R doit être défini comme cette distance. Le protocole doit fixer R = distance du stop, et rapporter la part de sorties par stop.
- Variantes : 2×2 (seuil × durée) + spread + USDJPY = 6, plus « deux autres interdites » (formulation floue). Rester ≤ 8 et nommer chaque variante. La règle principale est fixée à z ≥ 1,0 / 4 h ; ne pas la remplacer au vu des résultats.
- Chevauchement et corrélation : un trade par paire par jour, entrée 07:05 et sortie 11:05, pas de chevauchement intra-paire. Mais EURUSD et GBPUSD sont ouverts en même temps et sont fortement corrélés (USD commun). Le plafond de 2 positions les autorise, mais ce sont ~1 pari indépendant par jour. Les t-stats doivent être calculées par jour (moyenne des paires), comme prévu. Les trades EURUSD+GBPUSD de même sens doivent être déclarés comme un seul événement.
- Coûts : entrée à 07:05 = spread de début de Londres, plus large que la moyenne de la journée. Utiliser le spread réel bid/ask de la barre ; pas de spread moyen.
- Non-indépendance temporelle : la dérive 00–07 et les 20 jours de filtre se recouvrent ; pas de problème de fuite, mais les dépendances en série réduisent le nombre effectif de jours.

## Tests obligatoires à inclure dans le protocole (placebo, coûts, vue par jour, concentration…)
1. Placebo temporel : même règle avec dérive 07→12 UTC et entrée 12:05, et aussi 2 à 3 autres fenêtres (ex. 12→16, 20→00 hors zone interdite) ; le vrai doit être meilleur que tous. Placebo permuté : signe de D mélangé entre jours (≥ 1000 permutations), p-valeur rapportée.
2. Placebo « continuation » : le même déclencheur à contre-sens (suivre la dérive). S'il est symétriquement négatif, l'effet est un coût de spread, pas un retour.
3. Test sweep : séparer les trades où le prix retouche le range asiatique avant 11:05 de ceux qui ne le font pas. Si l'avantage n'existe que dans les premiers, verdict « doublon V4-H1 ».
4. Coûts +0,2 / +0,5 / +1,0 pip. Un résultat > 0 à +0,5 pip est requis (déjà au critère 5).
5. Vue par jour (jours uniques) : t-stat, IC 95 % bootstrap, sans les 5 meilleurs jours, ≥ 4 mois sur 6 positifs ; concentration par paire, par mois, par jour de semaine (lundi = gap de week-end, à isoler) et par jour d'annonce majeure (NFP, FOMC) : vérifier que l'effet n'est pas porté par quelques jours, comme E001/E002.
6. Gradient en |z| et voisins : z ∈ {0,8 ; 1,0 ; 1,25 ; 1,5} et durée 2 / 3 / 4 h, en simple diagnostic ; un effet qui n'existe que sur un point précis est rejeté.
7. Scission DST (UTC+0 / UTC+1) et USDJPY séparé, rapportés dans tous les cas.
8. Compte de trades attendus et de jours à |z| ≥ 1 publié dans protocol.md avant la lecture des résultats. Protocole commité avant le Train. Aucune ouverture OOS sans oos-gate OUVERT.

## Verdict : GO
GO sous conditions : (a) définir R, l'ATR journalier du filtre et le calcul exact du z avant le run ; (b) tests 1 à 8 ci-dessus ; (c) si le nombre de trades attendus au Train est < 150, le dire dans le protocole et conclure « échantillon insuffisant » sans abaisser le seuil z après coup ; (d) pas de re-réglage en cas d'échec (règle 7 de CLAUDE.md).
