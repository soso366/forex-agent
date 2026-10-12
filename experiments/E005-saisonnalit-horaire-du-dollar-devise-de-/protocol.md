# E005 — protocole (VERROUILLÉ au commit, ne plus modifier)
Auteur : QUANT · 2026-10-12 · hypothèse : `hypothesis.md` ; corrections de `precritique.md` appliquées ci-dessous.

## Définitions uniques
- **R = pips nets / ATR M5(14) à l'entrée** (ATR calculé sur barres M5 mid terminées au plus tard au début de la minute d'entrée ; 1 ATR = 1 R). Le **stop catastrophe = 3 ATR** (= -3 R, jamais un « 1 R »). Pas de take-profit. Sortie au temps. Le R inclut le spread bid/ask réel (achat ask / vente bid, sortie côté opposé). Les pips nets moyens sont rapportés ET exigés (le R seul est trop indulgent).
- Heures **ancrées sur Europe/London via zoneinfo** (jamais +1 h fixe). Entrée = open de la minute M1 de l'heure locale ; sortie = close de la dernière minute de la durée (≤ 4 h, toujours avant 21:00 UTC ; fenêtres A et B finissent avant 19:00 UTC).
- Un trade par paire et par jour ouvré (lun–ven). Exclus d'avance : 24, 25, 26, 31 déc., 1er janv. ; jours où la minute d'entrée manque (> 1 min d'écart) ou la fenêtre a < 90 % de minutes présentes.
- **Unité d'analyse = le jour** (somme des R des paires = panier USD). Trades par paire = annexe.
- Directions. **A** (règle principale) : 08:00 London → +4 h ; EURUSD, GBPUSD VENTE, USDJPY ACHAT. **B** (contrepartie ; 14:00–18:00 London = 09:00–13:00 New York, recouvre les annonces US ; rapportée, NE conditionne PAS le verdict) : directions inverses de A.

## Variantes (8 exactement, aucune autre ; rapportées, jamais sélectionnées)
1 A (4 h) · 2 B (4 h) · 3 A+B (union des trades) · 4 A-2h · 5 B-2h · 6 A-3h · 7 B-3h · 8 A|Bveille (A seulement si le dernier trade B de la même paire, ≤ 4 jours calendaires avant, avait R > 0 ; sinon pas de trade).
Voisins de A (rapportés, non retenus) : départ 07:30, 08:30 ; durée 3 h, 5 h.
**Seule la variante A est jugée.** Une autre variante meilleure n'est pas un résultat (8 variantes ⇒ seuil t = 2,5).

## Données
- Train : sept. 2025 → fév. 2026 (2025-09-02 → 2026-02-27, `data/m1_2025`), 124 jours × 3 paires = 372 signaux A (compte avant tout R : `results/signal_counts.json`, commité).
- Validation : mars → août 2026 (`data/m1`, 2026-03-02 → 2026-08-31).
- OOS vierge sept. 2023 → août 2024 : non touché ; `oos-gate` doit répondre OUVERT (Train ET Validation réussis). Ce script ne lit jamais l'OOS.

## Critères Train (A, 3 paires, TOUS requis, sinon REJECT immédiat, pas d'inversion de signe, pas de nouvelles heures)
1. n ≥ 300 trades ; moyenne ≥ +0,05 R ; moyenne ≥ +0,3 pip net ; t-stat par jour (somme R quotidienne) ≥ 2,5.
2. IC 95 % bootstrap par jour : borne basse > 0.
3. Placebo : (a) 10 horaires placebo (débuts 00,01,02,03,04 et 12,13,14,15,16 h London, durée 4 h, mêmes directions que A, non chevauchants, finissant avant 20:00 UTC) : le vrai horaire doit avoir la meilleure moyenne R (rang 1/11) ; (b) différence vrai − moyenne des placebos (contrôle de dérive USD), IC 95 % bootstrap par jour apparié : borne basse > 0 ; (c) permutation de signe aléatoire par jour (5000 tirages, même heure) : p ≤ 0,05. (Les décalages ±1..3 h chevauchent A et les 28 horaires prévus dépassent la plage 21:00 UTC : remplacés par ces 10, décision écrite avant tout calcul.)
4. Coûts : à +0,5 pip supplémentaire (aller-retour), moyenne R > 0 (+0,2 et +1,0 rapportés).
5. Sans les 5 meilleurs jours : moyenne > 0 ; sans les 5 pires jours : moyenne > 0 ; ≥ 2 paires sur 3 à moyenne > 0 ; ≥ 4 mois sur 6 positifs. Rapportés : par trimestre, jours d'annonces (NFP + FOMC), par jour de semaine.
6. Poolé sans USDJPY (signe ad hoc) : moyenne ≥ 0 (rapporté avec le poolé).
Rapportés (non décisifs) : IC bootstrap par blocs de semaine, une paire par jour, voisins, variantes.

## Critères Validation (A seule, uniquement si Train réussi)
Moyenne R > 0 ET ≥ 50 % de la moyenne Train ET moyenne à +0,5 pip > 0. Tous les autres éléments du rapport sont fournis (`full_report`) mais non décisifs.

## Critères OOS (une seule lecture, seulement si oos-gate = OUVERT)
PASS : moyenne R > 0, t par jour ≥ 1,65, moyenne à +0,5 pip > 0, ≥ 50 % de l'effet Train. FAIL : moyenne ≤ 0 ou coût +0,5 pip ≤ 0. INCONCLUSIVE : le reste (ex. signe correct, t < 1,65).

## Tests de robustesse obligatoires (tous implémentés dans `code/run.py`)
Placebo horaire + permutation de jours + contrôle de dérive ; coûts +0,2/+0,5/+1,0 pip ; vue par jour + IC 95 % (jour et semaine) ; une paire par jour ; concentration (5 meilleurs / 5 pires jours, paire, mois, trimestre, jours d'annonces) ; avec ET sans USDJPY ; test synthétique (`code/test_synthetic.py` : DST dont jours de changement d'heure, effet connu, ATR sans fuite, placebo valides, coûts) = PASS.
