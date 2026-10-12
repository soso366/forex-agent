# E006 — Retour de la dérive de faible liquidité asiatique à l'ouverture de Londres
Auteur : RESEARCHER · cycle 5 · 2026-10-12

## Mécanisme supposé
Entre ~00:00 et 07:00 UTC, le carnet est mince (hors yen) : un petit flux unidirectionnel déplace le prix sans contrepartie informée.
À l'arrivée des teneurs de marché et des clients londoniens, la liquidité revient et une part de ce déplacement « sans information »
est reprise (rééquilibrage d'inventaire). Prédiction : l'excès de dérive asiatique se retourne partiellement pendant la matinée européenne.

## Raison économique / microstructure / comportementale
Impact de prix temporaire élevé quand la profondeur est faible, qui se résorbe quand la profondeur augmente. Indice testable avec nos colonnes :
le déplacement est ANORMAL surtout s'il s'est fait avec un spread large (liquidité faible) -> variante de conditionnement.

## Conditions (règles objectives, sans donnée future)
- Paires : EURUSD, GBPUSD (principal) ; USDJPY rapporté à part (le yen est liquide à Tokyo, effet attendu faible).
- Fuseau : UTC pour la dérive (00:00–07:00 UTC fixe) ; entrée à 07:00 Europe/London... pour éviter le DST, on fixe l'entrée à l'open M1 de 07:05 UTC.
- Dérive D = mid(07:00 UTC) − mid(00:00 UTC) ; normalisée z = D / (ATR M5(14) × √84) mesuré à 07:00 (84 = nombre de barres M5 de 7 h). Seul l'ATR passé est utilisé.
- Déclencheur : |z| ≥ 1,0 (règle principale, fixée avant). Pas de trade si le range 00–07 UTC est < 0,5 ATR journalier moyen des 20 jours passés.
- Entrée : sens opposé à D, à l'open M1 07:05 UTC (ask si achat, bid si vente). Sortie : close M1 à 11:05 UTC (4 h) ; stop catastrophe 3 ATR M5. Un trade par paire par jour.
- Variantes (≤ 8) : seuil z ∈ {1,0 ; 1,5} × durée {2 h ; 4 h} ; conditionnement spread moyen 00–07 UTC > médiane glissante 20 jours (oui/non) pour la règle principale ; USDJPY seul ; deux autres interdites. Total ≤ 8.

## Pourquoi cet horizon
Le retour de liquidité se fait sur la matinée européenne (1–4 h) ; en dessous de 5 min c'est du bruit de spread, au-delà la journée apporte d'autres nouvelles.

## Critères falsifiables (écrits avant de regarder)
Train (sept. 2025 → fév. 2026), règle principale, coûts réels inclus :
1. ≥ 150 trades (paires EURUSD+GBPUSD) ; moyenne ≥ +0,05 R ; t-stat par jour ≥ 2,0 (jours uniques, paires corrélées moyennées).
2. IC 95 % bootstrap par jour : borne basse > 0.
3. Placebo : mêmes règles avec la dérive 07→12 UTC et trade à 12:05 (autre heure, même |z|), et dérive signée aléatoire permutée : le vrai doit les dominer.
4. Gradient : le |z| ≥ 1,5 doit donner une moyenne ≥ celle de |z| ∈ [1,0 ; 1,5[ (monotonie). Sinon c'est du bruit.
5. Coûts +0,5 pip : moyenne ≥ 0 ; sans les 5 meilleurs jours > 0 ; ≥ 4 mois sur 6 positifs.
6. Validation (mars → août 2026) : même signe, ≥ 50 % de l'effet ; sinon REJECT. OOS vierge seulement si oos-gate = OUVERT.
Échec d'un critère 1–5 au Train = REJECT immédiat.

## Risques d'échec
Les dérives asiatiques sont souvent de vraie information (données Japon/Chine/Australie) et se prolongent à Londres (continuation = famille négative mais ici c'est le retour qui est testé) ; peu de jours à |z| ≥ 1 ; l'ouverture de Londres elle-même provoque des mouvements (sweeps, cf. V4-H1 rejeté) : si le résultat n'est que le sweep de l'Asie, c'est un doublon de fait -> à signaler par le Critic.

## Non-doublon
V4-H1 (sweep & reclaim des extrêmes Asie/PDH-PDL, signal de cassure-échec de niveau) ne conditionne pas sur la dérive normalisée ni sur l'horizon 4 h ; la règle ici est une mean-reversion de la dérive totale à heure fixe, justifiée par la profondeur de carnet. E000/E003 : autres déclencheurs. dupcheck : aucun doublon.
