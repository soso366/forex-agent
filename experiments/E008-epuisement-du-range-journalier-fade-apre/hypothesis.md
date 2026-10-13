# E008 — Épuisement du range journalier : fade après 13:00 Londres (4 h)
Auteur : RESEARCHER · cycle 6 · 2026-10-13

## Mécanisme supposé
Quand, depuis minuit (Londres), la paire a déjà parcouru ≥ 30 % de son range journalier moyen (ADR 20 jours) dans un
seul sens, la demande directionnelle de la journée (flux d'ordres de couverture, stops, clients de banques) est en
grande partie servie. Les teneurs de marché, longs d'inventaire accumulé contre ce flux, le réduisent pendant la
fenêtre de forte liquidité 13:00–17:00 (inventory-control, Stoll / Evans-Lyons) ; sans nouveau flux, le prix revient partiellement.

## Raison économique / microstructure / comportementale
Gestion d'inventaire des dealers + ancrage des participants sur le range habituel (le range moyen sert de repère de
« mouvement complet »). Hypothèse de réversion partielle, pas de retournement de tendance.

## Conditions (règles objectives, sans donnée future)
- Paires : EURUSD, GBPUSD, USDJPY (par paire + poolé par jour).
- Fuseau : Europe/London, DST via zoneinfo ; mid = (bid+ask)/2.
- ADR20 = moyenne des (high−low) mid des 20 jours précédents (jour calendaire Londres), strictement passé.
- Signal à 13:00 : M = (mid(13:00) − mid(00:00)) / ADR20. Si |M| ≥ 0,30 : trade CONTRE le sens de M.
- Entrée à l'open M1 de 13:00 (ask si achat, bid si vente) ; sortie au close M1 de 17:00 Londres ; stop catastrophe
  3 ATR M5(14) ; pas de TP ; max 1 trade/paire/jour ; fermé avant 21:00 UTC.
- Variantes (≤ 4) : A (seuil 0,30) ; B seuil 0,40 (≈ 133 trades, rapportée seulement) ; C sortie 15:00 ; D fenêtre
  d'entrée 12:00. Seuil 0,30 fixé par la distribution de |M| (comptage, sans R).

## Pourquoi cet horizon
Réversion d'inventaire sur plusieurs heures, pendant la plus forte liquidité ; 4 h = plafond. Hors fix 16:00 : la
sortie 17:00 inclut le fix, mais le signal ne dépend pas de lui (H3/E000 rejetée comme fade ponctuel du fix ; ici le déclencheur est l'amplitude de la journée).

## Comptage préalable (sans R)
|M| ≥ 0,30 : 171 jours-paires sur le Train (≥ 150 requis, marge faible) ; ≥ 0,40 : 133 ; ≥ 0,50 : 105. Si le comptage
final < 150 après filtres de données, la règle bascule explicitement à INCONCLUSIVE, pas à un seuil abaissé.

## Critères falsifiables (écrits avant de regarder)
Train sept. 2025 → fév. 2026, règle A, coûts bid/ask réels :
1. ≥ 150 trades ; moyenne ≥ +0,05 R ; t-stat par jour ≥ 2,0 (cluster USD).
2. IC 95 % bootstrap par jour : borne basse > 0.
3. Placebo : mêmes règles avec heure de signal/entrée décalée de ±1..6 h ; le vrai horaire dans le top 10 % ; et le
   sens inverse (continuation) doit perdre.
4. Coûts +0,5 pip : moyenne ≥ 0.
5. Sans les 5 meilleurs jours : moyenne > 0 ; ≥ 2 paires sur 3 positives ; ≥ 4 mois sur 6 positifs.
6. Validation (mars → août 2026) : même signe, ≥ 50 % de l'effet Train. OOS seulement si oos-gate = OUVERT.
Échec d'un critère 1–5 = REJECT immédiat.

## Risques d'échec
Jours de tendance forte (annonces US 13:30) = pertes grandes et corrélées entre paires (USD commun) ; échantillon
juste au-dessus de 150 ; signal opposé à E007 sur les jours extrêmes (si E007 gagne, E008 perd, ce qui est une cohérence
utile) ; fade de mouvement = famille globalement négative (E003, V4-H5).

## Non-doublon
Pas E006 (dérive asiatique 00–07, sortie 07:05), pas H3/E000 (fix), pas E003 (niveaux), pas V4-H1 (sweep). Déclencheur
= amplitude de mouvement relative à l'ADR depuis minuit, jamais testé. dupcheck : aucun doublon.
