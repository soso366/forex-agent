# E005 — critique AVANT test
Auteur : CRITIC · 2026-10-12

## Meilleure raison pour laquelle l'hypothèse est fausse
Effet publié sur 2005-2010 (Breedon & Ranaldo), de l'ordre de 0,5-1 pip, soit le niveau du spread (0,3-0,6 pip) ; la volatilité d'une fenêtre de 4 h est de 15-30 pips, donc 6 mois (~125 jours) ne peuvent détecter qu'un biais bien supérieur à 1 pip. Le signal réel du Train risque d'être la dérive de l'USD sur sept. 2025 → fév. 2026, pas un flux horaire.

## Doublon / déjà testé ?
Pas de doublon : `memory/EXPERIMENTS.md` et `REJECTED_HYPOTHESES.md` ne contiennent aucun biais directionnel horodaté. Proche mais distinct de E000/H3 (fade du fix 16:00 : signal de prix) et du filtre d'horaires V2 (X-02 : filtre, pas signal). La clause « autres fixings à heure fixe en fade » ne couvre pas E005 (pas de fade, pas de seuil de prix). Attention : si le résultat est négatif, ne pas inverser le signe après coup (c'est une autre hypothèse).

## Risques méthodologiques prévisibles
1. **Corrélation USD** : en fenêtre A, EURUSD vente + GBPUSD vente + USDJPY achat = 3 fois le même pari « USD monte ». Les ~750 trades du Train valent ~125 observations indépendantes. Le critère « ≥ 300 trades » est trompeur ; seul le t-stat par jour compte (déjà prévu). Le résultat doit être donné aussi par jour (panier USD, 1 observation/jour/fenêtre).
2. **Incohérence mécanisme / fenêtre B** : le texte parle de l'après-midi de New York, mais 14:00-18:00 Europe/London = 09:00-13:00 à New York (matin US, recouvrement Londres, et publications 13:30 UTC incluses, comme NFP/CPI). Soit la fenêtre B ne teste pas le mécanisme, soit elle teste un effet « annonces US ». Une vraie fenêtre « après-midi NY » (≥ 14:00 NY ≈ 19:00 London) dépasse 21:00 UTC en partie, donc est interdite. À clarifier : B reste une variante rapportée, mais le critère principal ne doit pas dépendre d'elle.
3. **DST** : l'ancrage Europe/London est bien explicite, mais les États-Unis changent d'heure à d'autres dates (UK 26 oct. 2025, US 2 nov. 2025 ; mars 2026 pour la Validation) : pendant ~1 à 3 semaines le décalage Londres/NY vaut 1 h de moins. Le code doit convertir via `zoneinfo`, jamais `+1 h` fixe, et un test doit vérifier 08:00 London = 07:00 UTC en été et 08:00 UTC en hiver, ainsi que le jour du changement d'heure.
4. **USDJPY ad hoc** : le signe « symétrique » n'est pas dans l'article (JPY se déprécie pendant les heures de Tokyo, hors fenêtre). Il est choisi sans fondement ; inclus dans le poolé, il peut diluer ou gonfler. Exiger le résultat poolé avec ET sans USDJPY, rapporté dès le départ.
5. **Définition de R incohérente** : « R = pips / stop 1 ATR M5 » mais « stop catastrophe 3 ATR M5 ». Une unité de R de 3-4 pips pour une sortie à 4 h rend 0,05 R ≈ 0,2 pip (seuil trop bas, moyenne ≥ 0,05 R presque triviale en coûts nuls). Figer : R = 1 ATR M5(14) à l'entrée (calculé sans la barre d'entrée) ; critère principal aussi en pips nets.
6. **Variantes** : la liste est ambiguë (« les 2 autres sont des variantes de sortie 3 h » vs durée 2 h). Compte attendu ≤ 8 : A, B, A+B, A-2h, B-2h, A-3h, B-3h, A|B(veille). À figer par écrit avant le Train. La variante « filtrée par B de la veille » dépend de la fenêtre précédente (lundi : vendredi ?) ; définir les jours sans veille (week-end, jours fériés).
7. **Placebo** : l'horaire « ±1..14 h » inclut des décalages de ±1 à ±3 h qui chevauchent la vraie fenêtre de 4 h (corrélation mécanique) ; et « top 10 % de 28 » = rang ≤ 2, très sévère mais valide. Le critère « le signe inversé doit perdre » est redondant (moyenne positive ⇒ inverse négatif) et ne prouve rien : le vrai placebo est la comparaison aux autres horaires. Les placebos 14-28 doivent être hors tunnel 21:00 UTC (exclure ou borner).
8. **Événements** : les fenêtres contiennent Fed/BoE/NFP/CPI ; un biais de 0,5 pip est écrasé par un seul jour de 80 pips. Vérifier « sans les 5 meilleurs jours » ET « sans les 5 pires » (si le signe tient seulement avec l'une des deux, c'est du bruit).
9. **Données** : jours à données incomplètes, ouverture de lundi, 24-26 déc., 1er janv. : liste d'exclusion écrite avant ; spread à 08:00 London souvent plus large qu'à 10:00 (utiliser bid/ask réels, pas un spread moyen).

## Tests obligatoires à inclure dans le protocole
- Unité d'analyse = jour (panier USD) ; t-stat et IC 95 % bootstrap par jour (bloc par semaine si autocorrélation) ; trades par paire en annexe.
- Placebo horaire (28 horaires décalés, durée identique, DST géré) ET placebo par permutation de jours (même heure, jours mélangés, ou signe aléatoire par jour) pour séparer la dérive USD du Train.
- Contrôle de dérive : résultat de la fenêtre A dé-trendé (soustraire la moyenne de la dérive jour 24 h de la même paire, ou comparer à une position « hors fenêtre » de même durée).
- Coûts : +0,2, +0,5, +1,0 pip ; critère principal à +0,5 pip.
- Concentration : sans 5 meilleurs / 5 pires jours, par paire, par mois, par trimestre ; part des gains venant des jours à annonce (calendrier fixe NFP/FOMC/BoE).
- Ajustement multiplicité : 8 variantes ⇒ seuil de t-stat relevé (≥ 2,5 pour la meilleure variante, ou Bonferroni), sinon la meilleure variante ne vaut pas validation.
- Voisins : départ ±30 min et durée ±1 h de la règle A (rapportés, pas retenus).
- Règle d'arrêt : Train raté ⇒ REJECT immédiat, pas d'inversion de signe, pas de nouvelles heures.
- Protocole figé et commité (`protocol.md`) avant tout calcul Train ; aucun accès à l'OOS 2023-24 sans `oos-gate`.

## Verdict : GO
Falsifiable, calculable sans donnée future, fuseau explicite, pas de doublon. GO conditionnel à la correction des points 2, 5, 6 dans `protocol.md` avant le Train (fenêtre B/mécanisme, définition de R, liste exacte des variantes) et à l'ajout des tests ci-dessus. Prior faible : effet probablement arbitré depuis 2010.
