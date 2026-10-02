# E002 — critique AVANT test
Auteur : CRITIC · cycle 1 · 2026-10-02

## Meilleure raison pour laquelle l'hypothèse est fausse
**Le « mouvement » Δ mesuré sur le mid pendant un spread élargi est en grande partie un artefact de cotation, pas un
prix traité.** Quand un fournisseur retire un côté (ex. l'ask saute de 6 pips, le bid ne bouge pas), le mid bouge de
3 pips sans qu'aucun ordre ne soit passé. À la normalisation, le mid « revient » mécaniquement : le retour est déjà
dans la cotation de la minute m, donc rien n'est capturable à l'ouverture de m+1. Conséquences :
- le déclencheur (s_t ≥ 3×ref ET |Δ_mid| ≥ 1 ATR) sélectionne justement ces artefacts (un spread qui triple déplace
  le mid d'environ un spread de référence ; en période calme, 1 ATR M5 EURUSD ≈ 2–3 pips, atteignable par le seul
  écartement) ;
- les vrais chocs traités qui restent sont, hors minutes rondes, souvent des **nouvelles non programmées** (titres,
  déclarations) → impact permanent → stop 1,5 ATR touché ;
- le filtre « déjà retracé > 50 % à la clôture de m » enlève les artefacts purs mais aussi les cas où le retour a
  bien eu lieu : ce qui reste est biaisé vers les chocs qui NE reviennent PAS. Le mécanisme peut être vrai et
  l'exécution M1 quand même nulle.

## Doublon / déjà testé ?
**Pas un doublon, mais proximité forte avec V4-H5 « displacement M5 en retour » (≈ −0,03 R, REJECT).**
La condition d'état de liquidité (spread anormal puis normalisé, mesuré en bid/ask) est un « fait nouveau » au sens
de `memory/REJECTED_HYPOTHESES.md` : H5 n'utilisait pas le spread. E002 n'est un recyclage déguisé de H5 que si
la condition de spread n'apporte rien → c'est ce que tranche le critère 3 (contrôle « même mouvement, spread
normal », écart ≥ +0,08 R). Ce critère est **non négociable et décisif** : si E002 ne bat pas son contrôle, il est
archivé avec H5. Différent de H3/H4 (aucune heure fixe), H1/H2 (aucun niveau), cellules de contexte (aucun
apprentissage).

## Risques méthodologiques prévisibles (look-ahead, fuite, trop de variantes, échantillon, coûts, corrélation USD)
1. **Le spread Dukascopy M1 est une mesure grossière de la liquidité.** s_t = max(spread d'ouverture, spread de
   clôture) ne voit pas le pic intra-minute (ask_high − bid_low n'est pas un spread). Un retrait de 20 s au milieu
   de la minute est invisible ; un tick aberrant à la clôture crée un faux choc. Dukascopy est un seul flux : un choc
   chez lui peut ne pas exister chez le broker paper. Le critère 7 (chocs isolés d'une minute) doit être **chiffré**
   (part des trades et du R), pas seulement « inspecté ».
2. **Look-ahead — points à vérifier dans le code du Quant :**
   - ATR M5 : `research/v4/data.py::bars()` étiquette les M5 par leur **début** (`label="left"`). `m5["atr_now"]`
     à l'étiquette 10:05 contient les minutes 10:05–10:09 ; pour un choc à 10:07, un `reindex(..., ffill)` sur
     l'étiquette = **fuite**. Utiliser la dernière M5 dont la fin ≤ clôture de t (décaler l'index de +5 min comme
     pour `er` dans `engine.build_ctx`, ou `m5["atr"]` qui est déjà `shift(1)`).
   - ref_t : médiane des 20 jours ouvrés **précédents**, jour courant exclu (ni la minute t ni le créneau du jour t).
   - Normalisation décidée à la **clôture** de m, entrée à l'**ouverture de m+1** → exécutable sans look-ahead.
     L'extrême du choc (base de la cible 50 %) et le filtre « > 50 % retracé » n'utilisent que les minutes ≤ m.
   - Minutes manquantes (fréquentes autour d'un choc) : « t−3 » et « (t, t+5] » en **horodatage**, pas en position
     d'index. `sim.simulate` tolère `max_gap_min=5` minutes entre l'heure prévue et la première cotation : pour E002
     imposer `max_gap_min=1` (sinon l'entrée glisse de plusieurs minutes).
3. **Granularité minute.** Entrée à m+1 = 1 à 2 min après le pic ; l'essentiel d'un impact temporaire FX se résorbe
   souvent en secondes. Le test ne mesure qu'un retour **résiduel** : un résultat nul réfute l'exploitabilité à
   5–30 min (la seule question du projet), pas le mécanisme intra-minute.
4. **Rareté → nombre de signaux.** 3 conditions conjointes + normalisation ≤ 5 min + filtre 50 % : probablement
   quelques dizaines de trades par paire sur 6 mois. Le seuil de 80 trades et le repli unique sur 2,5× sont
   corrects ; **le Quant compte les signaux (sans regarder les R) avant de figer la règle principale** et l'écrit
   dans protocol.md. Aucun autre relâchement (pas de 2×, pas d'ATR 0,8, pas de normalisation à 10 min).
5. **Concentration sur quelques jours / épisodes.** Les chocs se regroupent (jours de stress, fériés partiels,
   flash-crashes) et un même épisode déclenche souvent les 3 paires dans la même minute (USD commun) → 3 trades
   corrélés comptés comme indépendants ; le t par trade est surestimé.
6. **Rollover / jours spéciaux.** La fenêtre 06:00–20:00 UTC rend l'exclusion 20:30–22:30 redondante (sans danger ;
   rollover 21:00 UTC été / 22:00 UTC hiver, hors fenêtre dans les deux cas). Risque réel : **jours fériés**
   (Noël, 1er janvier, Good Friday, Thanksgiving) — liquidité mince toute la journée alors que ref_t vient de jours
   normaux → faux chocs en série. Liste pré-déclarée, résultat montré avec et sans.
7. **Hors minute ronde ≠ sans nouvelle.** Discours, titres, ordres de banque centrale tombent n'importe quand.
   Le découpage ±2 min est raisonnable ; ne pas le retoucher après coup.
8. **Coûts réels pendant un choc.** Entrée à un spread jusqu'à 1,5×ref (donc +50 % du spread habituel) ; stop
   pouvant être touché pendant une seconde vague d'écartement (le glissement à l'ouverture est déjà modélisé dans
   `sim.py`). Chez un broker de détail, last look / rejets en période de stress → coût réel > Dukascopy. +0,6 pip
   est le niveau réaliste minimum.
9. **Variantes.** 3 axes binaires = 8 combinaisons = plafond du projet. Rien de plus (pas d'autre stop, d'autre
   fenêtre horaire, ni de sélection de paire après coup).

## Tests obligatoires à inclure dans le protocole (placebo, coûts, vue par jour, concentration…)
1. **Contrôle « même mouvement, spread normal »** (critère 3) : même code, même Δ, mêmes heures, même minute hors
   ronde, entrée à la minute de même rang, spread < 1,5×ref. Écart E002 − contrôle ≥ +0,08 R, avec IC 95 % par jour
   de l'écart. Sinon REJECT (= H5).
2. **Contrôle minutes rondes** (critère 4) : même règle sur les chocs à ±2 min de :00/:15/:30/:45 ; écart ≥ +0,05 R
   en faveur du hors-rond si n ≥ 50 ; si n < 50, le dire et ne pas déclarer le mécanisme confirmé.
3. **Contrôle « artefact de cotation »** (imposé) : recalculer Δ sur le **côté traitable** (bid pour une baisse,
   ask pour une hausse) au lieu du mid et rejouer la règle principale. Si l'avantage disparaît → artefact → REJECT.
4. **Placebo temporel** : même règle, entrée à des minutes tirées au hasard (graine fixe) dans la même heure UTC des
   mêmes jours, sens opposé au mouvement des 3 dernières minutes ; ≥ 200 tirages ; E002 au-delà du 95e centile.
5. **Coûts** : `robustness.costs` à 0 / 0,2 / 0,4 / 0,6 / 1,0 pip par trade ; espérance > 0 à +0,5 pip
   (critère 5), affichée à +0,6 et +1,0.
6. **Vue par jour** : `robustness.day_view` (IC 95 % bootstrap) + `one_per_day` + vue **par épisode** (chocs
   simultanés à ±2 min sur plusieurs paires = 1 épisode, R moyenné).
7. **Concentration** : `robustness.concentration` (> 40 % du R sur 5 jours → REJECT, critère 6 ; sans meilleure
   paire, sans meilleur trimestre, sans fin de mois) + liste des 10 plus gros trades avec date et contexte.
8. **Contrôle données** (critère 7 chiffré) : part des trades et du R venant de chocs d'une seule minute sans
   mouvement voisin ; résultat recalculé sans eux.
9. **Jours fériés / lundi** : résultat avec et sans la liste pré-déclarée.
10. **Nombre de signaux** par paire et par variante compté avant lecture des R, écrit dans protocol.md.
11. **≤ 8 variantes** figées et commitées dans protocol.md avant toute lecture ; t ≥ 2 exigé sur la règle
    principale pré-déclarée, pas sur la meilleure des 8.

## Verdict : GO
Falsifiable, calculable sans données futures (sous réserve des points de look-ahead ci-dessus), fuseau UTC
explicite, testable avec Dukascopy M1 bid/ask, non doublon de H5 tant que le critère 3 reste décisif.
Objection principale : le Δ mid pendant un spread élargi peut être un artefact de cotation → test 3 imposé.

Verdict : GO
