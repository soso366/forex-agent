# E005 — Saisonnalité horaire du dollar (devise de base se déprécie pendant ses heures locales)
Auteur : RESEARCHER · cycle 5 · 2026-10-12

## Mécanisme supposé
Breedon & Ranaldo (2013) : la devise étrangère se déprécie face à l'USD pendant les heures locales de son
marché et s'apprécie pendant les heures de New York. Les flux commerciaux/de couverture (importateurs, exportateurs,
trésoreries) sont récurrents, quasi insensibles au prix et concentrés dans les heures de bureau de chaque zone :
les importateurs européens achètent des USD le matin européen ; les exportateurs américains rapatrient du EUR/GBP/JPY l'après-midi US.
Pression de flux non informée, donc pas arbitrée entièrement (le coût d'inventaire des teneurs de marché la rend rémunératrice).

## Raison économique / microstructure / comportementale
Flux non spéculatifs, prévisibles par l'heure, sans lien avec l'information. Biais attendu minuscule (≈ 0,5–1 pip par fenêtre) :
la seule question est s'il survit au spread (~0,3–0,6 pip).

## Conditions (règles objectives, sans donnée future)
- Paires : EURUSD, GBPUSD, USDJPY (résultats rapportés par paire ET poolés par jour).
- Fuseau : tout en UTC, heures fixes d'été/hiver converties avec Europe/London (le signal est ancré sur l'ouverture locale, pas sur l'UTC brut).
- Fenêtre unique A (règle principale, fixée avant les données) :
  - EURUSD, GBPUSD : VENTE à 08:00 Europe/London (ouverture Londres), sortie 12:00 Europe/London (4 h).
  - USDJPY : ACHAT 08:00–12:00 Europe/London (hypothèse de symétrie de la devise étrangère ; la fenêtre Tokyo est hors zone utile et exclue). Rapporté à part ; non requis pour le critère « 2 paires sur 3 » si le signe est ambigu, mais compté dans le poolé.
- Fenêtre B (contrepartie US) : EURUSD/GBPUSD ACHAT à 14:00 Europe/London, sortie 18:00 Europe/London ; USDJPY VENTE.
- Entrée au open M1 suivant l'heure (ask si achat, bid si vente), sortie au close M1 (bid/ask opposé). Stop catastrophe 3 ATR M5(14), pas de take-profit. Un trade par paire par jour ouvré.
- Variantes (≤ 8) : A, B, A+B ; durée 2 h au lieu de 4 h pour A et B ; A filtré aux jours où la fenêtre précédente (B de la veille) était dans le même sens ; les 2 autres sont des variantes de sortie fixes 3 h. Aucune autre.

## Pourquoi cet horizon
4 h max = longueur de la fenêtre de flux ; au-delà on retombe dans la dérive journalière non spécifique. Pas d'actif porté la nuit.

## Critères falsifiables (écrits avant de regarder)
Train (sept. 2025 → fév. 2026), règle A+B poolée, coûts bid/ask réels inclus, R = pips / stop 1 ATR M5 équivalent (rapporter aussi en pips) :
1. ≥ 300 trades, moyenne ≥ +0,05 R, t-stat par jour ≥ 2,0 (clusterisé par jour, paires corrélées via USD).
2. IC 95 % bootstrap par jour : borne basse > 0.
3. Placebo : 28 horaires décalés de ±1..14 h (même durée) ; le vrai horaire doit être dans le top 10 % ET le signe inversé doit perdre.
4. Coûts +0,5 pip : moyenne reste ≥ 0.
5. Sans les 5 meilleurs jours : moyenne > 0. Au moins 2 paires sur 3 positives ; ≥ 4 mois sur 6 positifs.
6. Validation (mars → août 2026) : même signe et ≥ 50 % de l'effet Train ; sinon REJECT. OOS vierge seulement si oos-gate = OUVERT.
Échec d'un critère 1–5 au Train = REJECT immédiat.

## Risques d'échec
Effet documenté sur 2005-2010 et possiblement arbitré depuis ; bruit énorme (vol journalière ≫ biais) ; DST décale les flux ; dérive USD de la période (tendance) peut imiter le signal : le placebo décalé et la vue par jour sont là pour cela.

## Non-doublon
Pas une cassure ni un fade d'événement ponctuel (E000/E003/E002) : biais de flux récurrent horodaté, sans déclencheur de prix. Le « micro-réglage des horaires V2 » rejeté concernait un filtre d'une stratégie à signal ; ici l'heure EST le signal. dupcheck : aucun doublon.
