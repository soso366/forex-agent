# E007 — Momentum inter-sessions : matin Londres vers après-midi New York (4 h)
Auteur : RESEARCHER · cycle 6 · 2026-10-13

## Mécanisme supposé
Le flux directionnel du matin européen (fonds, trésoreries, réactions aux données européennes) est absorbé
progressivement : quand New York ouvre, les teneurs de marché américains et les gérants qui n'étaient pas présents
rejoignent le mouvement (diffusion de l'information entre sessions, rééquilibrage tardif). Équivalent FX du
« intraday momentum » de Gao-Han-Li-Zhou (rendement d'une première fenêtre prédit celui d'une fenêtre ultérieure).
Le sens du matin Londres prolonge donc sur la fenêtre London/NY.

## Raison économique / microstructure / comportementale
Information diffusée lentement entre fuseaux horaires + sous-réaction initiale. Pas un signal de cassure de prix
(aucun niveau, aucun seuil de prix) : c'est le signe d'un rendement de session, déjà complet avant l'entrée.
Biais attendu faible (≈ 1 pip) : le test est de savoir s'il passe le spread.

## Conditions (règles objectives, sans donnée future)
- Paires : EURUSD, GBPUSD, USDJPY (rapportées par paire ET poolées par jour).
- Fuseau : Europe/London (heures locales, DST géré par zoneinfo). Prix = mid (bid+ask)/2 pour le signal.
- Signal : S = mid(13:00) − mid(08:00) (heure de Londres). Sens = signe de S. Aucun filtre de taille (règle principale A) ;
  jours sans 08:00 ou 13:00 disponibles ignorés.
- Entrée à l'open M1 de 13:00 (ask si achat, bid si vente) ; sortie au close M1 de 17:00 Londres (4 h) ; au plus 1 trade
  par paire et par jour ouvré ; sortie forcée avant 21:00 UTC (toujours vrai ici). Stop catastrophe 3 ATR M5(14), pas de TP.
- Variantes (≤ 4, fixées maintenant) : A (règle ci-dessus) ; B : |S| ≥ médiane de |S| sur les 20 jours précédents ;
  C : sortie à 15:00 (2 h) ; D : signal 07:00→13:00. Aucune autre.
- R = pips nets / (1 ATR M5(14) à l'entrée × 3) ; rapporter aussi en pips.

## Pourquoi cet horizon
Fenêtre de recouvrement Londres/NY (13:00–17:00) = liquidité maximale et arrivée des flux US ; 4 h est la limite.
Un horizon de 5–30 min est celui où la continuation a été trouvée négative (V4-H2, H5) : ici on teste un autre horizon
et un signal de session, pas de micro-structure de prix.

## Comptage préalable (sans R)
Jours avec ADR20 disponible ≈ 111 par paire sur le Train → ≈ 333 trades poolés (règle A). Seuil de 150 satisfait ; B ≈ 50 % (≈ 165).

## Critères falsifiables (écrits avant de regarder)
Train sept. 2025 → fév. 2026, règle A poolée, coûts bid/ask réels :
1. ≥ 300 trades ; moyenne ≥ +0,05 R ; t-stat clusterisé par jour ≥ 2,0.
2. IC 95 % bootstrap par jour : borne basse > 0.
3. Placebo : mêmes règles avec fenêtres décalées de ±1..8 h (signal et exécution) ; le vrai horaire dans le top 10 % ;
   et le sens inversé (fade) doit perdre.
4. Coûts +0,5 pip : moyenne ≥ 0.
5. Sans les 5 meilleurs jours : moyenne > 0 ; ≥ 2 paires sur 3 positives ; ≥ 4 mois sur 6 positifs.
6. Validation (mars → août 2026) : même signe, ≥ 50 % de l'effet Train. OOS seulement si oos-gate = OUVERT.
Échec d'un critère 1–5 = REJECT immédiat.

## Risques d'échec
Tendance USD de la période imitant le signal (placebo + vue par jour) ; continuation déjà trouvée négative à court
horizon (possible que le même retour à la moyenne domine à 4 h) ; événements US 13:30 (NFP, CPI) dominent la variance ;
effet documenté surtout en actions/futures, pas en FX spot.

## Non-doublon
Pas ORB (V4-H2), pas displacement M5 (V4-H5), pas saisonnalité horaire sans signal (E005), pas E006 (retour de dérive
asiatique, sens opposé, autre fenêtre). dupcheck : aucun doublon.
