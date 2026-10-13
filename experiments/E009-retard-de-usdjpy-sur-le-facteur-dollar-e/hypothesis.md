# E009 — Retard de USDJPY sur le facteur dollar EURUSD/GBPUSD (rattrapage ≤ 2 h)
Auteur : RESEARCHER · cycle 7 · 2026-10-13

## Mécanisme supposé
EURUSD et GBPUSD sont dominés par le flux « dollar » ; USDJPY a une autre base de participants (carry, hedgeurs
japonais, flux de taux US) et se réajuste plus lentement quand un choc dollar commun survient. Si, sur 30 min, le
facteur dollar (moyenne de −Δ EURUSD et −Δ GBPUSD) bouge nettement alors que USDJPY n'a pas suivi (ou a bougé à
l'inverse), on suppose que USDJPY rattrape partiellement dans les 2 heures (price discovery décalée entre paires,
arbitrage triangulaire/couverture inter-paires par les dealers).

## Raison économique / microstructure
Découverte du prix asynchrone entre paires : les dealers couvrent leur inventaire USD sur la paire la plus liquide
(EURUSD) puis propagent vers les autres (littérature lead-lag inter-paires, Evans-Lyons ; Cai et al.). Aucun lien avec
E001 (EURUSD vs GBPUSD, écart EURGBP) : ici on trade USDJPY seul contre un facteur composite. Le risque connu est que
le décalage soit trop court (< 5 min) pour être capturé avec des coûts d'un spread réel.

## Conditions (règles objectives, sans donnée future)
- Fuseau Europe/London (DST via zoneinfo) ; mid = (bid+ask)/2 ; barres M5 (dernier mid de chaque 5 min).
- Rendements log sur 30 min (6 barres) : usd = −(r_EURUSD + r_GBPUSD)/2 ; écart g = r_USDJPY − usd.
- z = g / écart-type glissant de g (2000 barres M5 précédentes, strictement passé, décalé de 1 barre).
- Signal : |z| ≥ 2,0 à la clôture d'une barre M5 entre 08:00 et 15:00 Londres. Trade sur USDJPY : si z > 0
  (USDJPY a trop monté vs facteur) VENTE ; si z < 0 ACHAT. Entrée à l'open M1 suivant (bid/ask réels).
- Sortie : close M1 à +2 h, ou 17:00 Londres si plus tôt (toujours < 21:00 UTC) ; stop catastrophe 3 ATR M5(14) ;
  pas de TP ; cooldown 2 h entre deux signaux ; max 2 trades/jour ; une seule position.
- Variantes (≤ 4) : A (principale : seuil 2,0, sortie 2 h) ; B sortie 1 h ; C sortie 4 h (plafond) ; D seuil 2,5
  (≈ 100 trades, rapportée seulement). Seuil 2,0 fixé par le comptage du signal, sans R.

## Comptage préalable (sans R, Train sept. 2025 → fév. 2026)
|z| ≥ 1,5 : 279 ; ≥ 2,0 : 175 ; ≥ 2,5 : 102 ; ≥ 3,0 : 63 (un par fenêtre de 2 h). Seuil 2,0 retenu (≥ 150, marge
~15 %). Si le comptage final après filtres de données < 150 : INCONCLUSIVE, aucun seuil abaissé.

## Pourquoi cet horizon
Rattrapage inter-paires attendu en minutes à quelques heures ; 2 h laisse la propagation s'achever sans reprendre
le biais de journée ; 5 min trop court (coût), 4 h testé seulement en C.

## Critères falsifiables (écrits avant de regarder les R)
Train sept. 2025 → fév. 2026, variante A, coûts bid/ask réels, mesures en R :
1. ≥ 150 trades ; moyenne ≥ +0,05 R ; t-stat par jour ≥ 2,0.
2. IC 95 % bootstrap par jour : borne basse > 0.
3. Placebo : (a) sens inverse (continuation du retard) doit être < 0 ; (b) facteur dollar construit avec un décalage
   de 1 jour (signal factice) : la vraie moyenne doit être au-dessus du 90e centile ; (c) mêmes règles avec heures
   d'entrée décalées ±1..6 h.
4. Coûts +0,5 pip : moyenne ≥ 0.
5. Sans les 5 meilleurs jours : moyenne > 0 ; ≥ 4 mois sur 6 positifs ; pas de concentration > 25 % du total sur un mois.
6. Validation (mars → août 2026) : même signe, ≥ 50 % de l'effet Train. OOS vierge seulement si oos-gate = OUVERT.
Échec d'un critère 1–5 = REJECT immédiat, sans micro-réglage.

## Risques d'échec
Rattrapage déjà absorbé en < 5 min (invisible en M5, coût > gain) ; 08:00–15:00 inclut les annonces US (13:30) où
USDJPY réagit aux taux, pas au dollar global (divergence légitime, pas retard) ; effet = biais USD constant ou
mouvement du yen (risk-off) ; échantillon juste au-dessus de 150 ; fade/réversion globalement négatif (E003, V4-H5).

## Non-doublon
dupcheck : aucun doublon. Distinct de E001 (paire GBP/EUR), E007/E008 (momentum/fade journalier d'une paire seule),
E005 (saisonnalité). Déclencheur : écart inter-paires USDJPY vs facteur dollar, jamais testé.
