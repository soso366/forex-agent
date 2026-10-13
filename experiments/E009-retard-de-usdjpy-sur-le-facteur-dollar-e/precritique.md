# E009 — critique AVANT test
Auteur : CRITIC · cycle 7 · 2026-10-13

## Meilleure raison pour laquelle l'hypothèse est fausse
**Le « retard » n'existe pas : g = r_USDJPY − usd est presque entièrement le mouvement propre de USDJPY (yen, taux US), et le rattrapage inter-paires se fait en secondes, pas en 2 h.**
- Le facteur dollar est pris avec un coefficient fixe de 1. USDJPY n'a pas la même sensibilité au dollar que EURUSD/GBPUSD (corrélation souvent faible, instable, signe variable en risk-off). g est donc dominé par r_USDJPY. Le trade revient à « fader un mouvement de 30 min de USDJPY seul, au-delà de 2 σ ». C'est de la famille V4-H5 retour (≈ −0,03 R, tué par le coût), E008 (+0,016 R, t 0,14) et E003 : prior très bas.
- L'arbitrage triangulaire (EURUSD, USDJPY, EURJPY) corrige les écarts en secondes. Rien dans le mécanisme ne justifie 2 h.
- Alternative plus probable : un |z| ≥ 2 sur 30 min est de l'information (taux US, BoJ, risk-off), donc permanent. Même schéma que E001 (écarts inter-paires portés par les jours d'annonces).

## Doublon / déjà testé ?
- `dupcheck` : aucun doublon exact. Mais proche de **E001** (divergence inter-paires, mêmes jambes EURUSD/GBPUSD, rejeté sur annonces : t 0,87) : seule la jambe tradée change. Aucun fait nouveau (pas de calendrier). Proche de **E008/V4-H5** (fade d'un mouvement de paire seule). Proche de **E007** par le risque de biais USD constant. Non rejeté comme doublon, mais classé « variante de famille déjà négative » : la charge de la preuve est sur E009.

## Risques méthodologiques prévisibles
1. **Normalisation sans effet d'heure (look-ahead absent, biais présent)** : l'écart-type sur 2000 barres M5 (≈ 7 jours, nuits asiatiques incluses, faible vol) sous-estime la vol de 08:00–15:00. Le seuil |z| ≥ 2 se déclenchera surtout à l'ouverture de Londres et à 13:30. Les 175 signaux ne sont pas un « événement rare » mais un effet d'horaire.
2. **Alignement des barres M5** : `resample` par défaut étiquette à gauche (open). Un rendement « à la clôture de la barre » doit utiliser une barre terminée, entrée à l'open M1 de la minute suivante (cf. E001 point 3). Test exigé : modifier les prix après t ne change pas z(t). σ strictement passé, `shift(1)` vérifié par test unitaire. Warm-up de 2000 barres : utiliser août 2025 (OOS 2024-25 déjà consommé, autorisé) ; **jamais** sept. 2023 → août 2024.
3. **Fenêtre 13:30 / annonces US** : 08:30 New York = 13:30 Londres sauf 3 semaines par an où les décalages DST US/UK diffèrent (fin oct. → 2 nov. 2025 dans le Train : 08:30 ET = 12:30 Londres). Une fenêtre « 13:30 Londres » fixe est donc fausse ces semaines-là. Le NFP (1er vendredi), CPI, FOMC minutes, jobless claims tombent tous dans la plage 08:00–15:00 et dans la fenêtre de détention (jusqu'à 17:00). USDJPY réagit aux taux US : divergence légitime, pas retard.
4. **Comptage « 175 »** : fait avec « un par fenêtre de 2 h » mais avant les filtres exacts (08:00–15:00, max 2 trades/jour, une position, cooldown, stop catastrophe, trous de données). Le nombre final peut tomber sous 150, donc INCONCLUSIVE par construction. À recompter avec les règles finales, avant tout R.
5. **Définition du R** : « stop 3 ATR M5(14) » avec détention 2 h : la taille de R (en pips) et le poids du coût en R ne sont pas fixés. Le seuil +0,05 R peut valoir 0,3 pip ou 1 pip selon l'ATR. Convertir en pips et publier.
6. **Placebo 3(a) vide** : le sens inverse est mécaniquement −(brut) moins 2 × coût ; il est négatif dès que A est positif. Ce n'est pas un contrôle. Les placebos 3(b) « décalage 1 jour » et 3(c) « heures ±1..6 h » n'ont pas de règle de décision chiffrée (rang minimal, nombre de tirages).
7. **Biais USD constant** (leçon E007) : sur Train, USDJPY a une dérive ; si les achats dominent, la moyenne peut n'être que la dérive.
8. **Corrélation entre signaux** : un choc dollar produit des signaux consécutifs le même jour ; n_effectif ≈ nombre de jours, pas de trades. Le t doit être calculé par jour (déjà prévu), IC avec bootstrap par blocs de jours.
9. **Multiplicité** : 4 variantes, 8 hypothèses déjà échouées sur le même Train. Seule A décide ; B/C/D sont informatives et ne peuvent pas sauver A.

## Tests que le protocole DOIT contenir
Au-delà des critères 1-6 de l'hypothèse (conservés, non modifiés) :
1. **Placebo « USDJPY seul »** : même règle avec z calculé sur r_USDJPY seul (sans facteur dollar). Si sa moyenne ≥ celle de A − 0,03 R, ou si A ne la bat pas, le mécanisme de retard est faux : REJECT (ça devient V4-H5/E008).
2. **Placebo facteur permuté** : usd issu d'un autre jour, même heure, ≥ 500 permutations, vraie moyenne ≥ 95e centile (au lieu de 90e) ; z recalculé avec la même procédure.
3. **Placebo d'horaires** : mêmes règles avec heures d'entrée décalées de ±1..6 h (12 décalages, hors 0) ; la vraie moyenne doit être le rang 1 sur 13 ; sinon REJECT.
4. **Sens inverse** : à rapporter (informatif), pas un critère.
5. **Contrôle d'horaire/vol** : répartition des signaux par heure Londres ; si une heure (ou la tranche 13:00–14:00) porte > 35 % des trades, rapporter séparément et recalculer avec σ conditionnel à l'heure (diagnostic, pas sélection).
6. **Annonces** : séparer les trades dont la fenêtre [t−30 min ; t+2 h] contient 12:30 ou 13:30 Londres (heures UTC 12:30/13:30 calculées explicitement à cause du DST) des autres. Si l'effet positif est entièrement dans le sous-ensemble « annonce » et le complémentaire ≤ 0, REJECT (même verdict que E001). Pas de calendrier : approximation mécanique documentée.
7. **Direction** : achats vs ventes séparément ; moyenne ajustée de la dérive (retrancher la moyenne non conditionnelle de USDJPY sur les mêmes heures d'entrée/sortie). Si moyenne ajustée < 0,03 R → REJECT.
8. Coûts : +0,2, +0,5 (critère), +1,0 pip ; spread réel entrée/sortie USDJPY en pips.
9. Concentration : sans les 5 meilleurs jours, par mois (6), par semaine d'événement (NFP), part du top 10 % des trades.
10. Tests unitaires anti-look-ahead (point 2 ci-dessus) et table de signaux (date, z, heure, sens) écrite avant tout R.

## Conditions chiffrées pour le Quant
- Recompter les signaux avec les règles exactes ; N final ≥ 150 sinon INCONCLUSIVE (aucun seuil abaissé, aucun z modifié).
- Protocole + code + signal_counts commités AVANT tout calcul de R.
- Critères 1-5 inchangés ; ajouter : placebo « USDJPY seul » battu, placebo permuté ≥ 95e centile, rang 1/13 sur les décalages horaires, moyenne ajustée de la dérive ≥ 0,03 R, complément « hors annonces » > 0.
- Pas de Validation ni d'OOS si un critère Train échoue. OOS vierge 2023-24 interdit tant que `oos-gate` ≠ OUVERT.
- Prior de succès estimé faible (< 10 %) : ne pas allonger la liste de variantes en cas d'échec.

## Verdict
**GO sous conditions** (falsifiable, calculable sans donnée future, non doublon strict). Les conditions ci-dessus font partie du protocole ; sans elles, le test ne distingue pas un retard inter-paires d'un fade de USDJPY seul ou d'un effet d'annonces.
