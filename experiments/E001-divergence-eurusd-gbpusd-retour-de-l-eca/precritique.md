# E001 — critique AVANT test
Auteur : CRITIC · cycle 1 · 2026-10-02

## Meilleure raison pour laquelle l'hypothèse est fausse
**Le retour attendu est plus petit que le coût, et les gros écarts EUR/GBP sont surtout de l'information.**
- Ordre de grandeur : stop = 1,5 ATR M5 ≈ 3–6 pips sur EURUSD/GBPUSD en séance de Londres. Un retour de 1–2 pips
  (chiffre donné par le RESEARCHER) = +0,2 à +0,5 R brut ; le spread aller-retour réel (≈ 0,2 pip EURUSD, 0,5–0,9
  pip GBPUSD sur Dukascopy) coûte déjà ≈ 0,05–0,25 R. La marge est mince avant même le moindre bruit.
- Précédent direct : V4-H5 « displacement M5 en retour » ≈ −0,03 R, tué par le coût. Si la divergence n'ajoute pas
  nettement plus que ce retour sur une seule paire, E001 finira au même endroit.
- |z| ≥ 2,5 avec dollar calme = mouvement d'EURGBP ≈ 2,5 σ en 15 min. En séance de Londres, ce sont typiquement des
  publications UK / zone euro (CPI UK, PMI, BoE, BCE, discours) ou des titres politiques : impact **permanent**, pas
  temporaire. Le filtre spread ≤ 2× médiane ne les élimine pas (les spreads EURUSD/GBPUSD se normalisent en 1–3 min
  après une publication). Le mécanisme « flux non informatif » est plausible, mais la population sélectionnée par le
  seuil est probablement dominée par l'information → prédiction alternative : continuation ou zéro, pas retour.

## Doublon / déjà testé ?
- `python3 -m orchestrator dupcheck "divergence EURUSD GBPUSD retour"` → aucun doublon.
- ≠ V4-H3 (heure fixe 16:00) : déclencheur d'état, pas d'horaire. OK.
- **Proche de V4-H5 retour** (même type de trade : fade d'un mouvement M5–M15 sur une paire, sortie au temps). La
  nouveauté réelle est UNIQUEMENT la condition relative (l'autre paire n'a pas suivi, dollar calme). Ce n'est pas un
  recyclage déguisé **à condition** que le contrôle « même mouvement sans divergence » soit décisif (tests 1–2).
  Si E001 ne bat pas ce contrôle, il est archivé comme une variante de H5, pas comme « presque positif ».
- ≠ sweep (V4-H1) : aucun niveau de liquidité. OK.
- Pas un micro-réglage V2. Famille nouvelle (relations entre paires). → pas de doublon.

## Risques méthodologiques prévisibles (look-ahead, fuite, trop de variantes, échantillon, coûts, corrélation USD)
1. **Look-ahead dans σx, σu (« 20 jours ouvrés précédents »)** : calcul sur les jours J−20…J−1 uniquement, fenêtre
   07:00–16:30 **Europe/London** de CHAQUE jour (DST : la fenêtre UTC bouge d'1 h fin mars / fin octobre ; Train et
   Validation contiennent chacun un changement d'heure). Interdit : `rolling` incluant le jour courant, normalisation
   sur toute la période, z-score global. Test unitaire exigé : modifier les prix du jour J ne change pas σ(J). Idem
   pour la **médiane de spread 20 j**. Premier mois : pas de σ avant 20 jours complets → pas de signal (pas de
   `min_periods` réduit).
2. **ATR M5 (sélection de jambe et stop)** : M5 **clôturées** uniquement (`m5["atr"]`, déjà `shift(1)` dans
   `engine.build_ctx`), jamais `atr_now` d'une bougie en cours. À la minute t multiple de 5, vérifier l'alignement
   d'index (barres étiquetées par leur ouverture).
3. **Horodatage d'entrée** : rE, rG utilisent la clôture de la M1 t, connue à t+1 → entrée à l'ouverture M1 t+1
   (`simulate` prend la première minute ≥ heure donnée : lui passer t+1, pas t). `signals_frame` entre à la clôture
   M5, pas à t+1 M1 : ne pas mélanger les deux conventions.
4. **Sortie anticipée |z| ≤ 0,5 non supportée par `research/v4/sim.py`** (`hold` est un scalaire, aucune sortie
   conditionnelle). Le Quant doit soit (a) précalculer l'heure de sortie anticipée de chaque trade avec des données
   ≤ minute courante puis simuler trade par trade, soit (b) supprimer la règle. Choix figé dans protocol.md. Piège :
   recalculer z avec la clôture de la minute de sortie elle-même puis sortir à cette même clôture (il faut sortir à
   l'ouverture suivante).
5. **Sélection des seuils / variantes** : la liste proposée (|z| 2,5/3,0 × fenêtre 15/30 × sortie 20/30 × 1 ou 2
   jambes) fait **16 combinaisons**, pas « ≤ 6 ». Plafond CLAUDE.md : **8**. Grille ≤ 8 figée avant lecture des
   données ; TOUTES les variantes rapportées. |u| ≤ 1 σu, spread ≤ 2×, stop 1,5 ATR, cooldown 30 min : fixes.
6. **Nombre de signaux attendu** : ≈ 114 scans/jour (07:00–16:30, pas de 5 min) ; |z| ≥ 2,5 sur rendements à queues
   épaisses ≈ 1,5–3 % des scans, très groupés (fenêtres 15 min chevauchantes) ; × ≈ 0,68 (dollar calme) × ≈ 0,9
   (spread) ; cooldown 30 min → **≈ 0,5–1,5 signal/jour, soit ≈ 60–190 trades sur le Train** (≈ 125 jours). Le seuil
   de 100 trades du critère 1 est limite ; la variante |z| ≥ 3,0 donnera probablement < 60 trades → inutilisable
   (t ≥ 2 exigerait ≈ +0,25 R/trade avec σ ≈ 1 R). Recommandation : compter les signaux sur le Train AVANT tout calcul
   de R (comptage seul) et retirer les variantes < 100 trades avant de regarder leur performance.
7. **Corrélation EURUSD-GBPUSD ≈ 0,6 et signal commun** : un signal porte par construction sur les deux paires ; la
   variante deux jambes = un seul pari EURGBP compté deux fois. Le t-stat par trade est surestimé → **vue par jour
   obligatoire** (Europe/London) ; la variante deux jambes est évaluée comme UN trade (somme des deux demi-R).
8. **Coûts sur deux paires** : la variante deux jambes paie deux spreads (dont GBPUSD, le plus large) ;
   `robustness.costs` ajoute le coût par ligne → correct seulement si chaque jambe est une ligne avec son propre
   `stop` (à préciser). Le spread de clôture M1 sous-estime le coût réel autour de 07:00 et des publications →
   coût +0,6 pip obligatoire.
9. **Choix de la jambe « fautive »** : GBPUSD a une ATR plus grande ; le critère peut favoriser une paire de façon
   systématique. Publier la répartition EURUSD / GBPUSD des trades.
10. **OOS** : l'OOS 2024-2025 est consommé par H3 (`memory/PROJECT_STATE.md`). E001 ne doit pas lire
    `data/m1_locked*` ; un nouvel OOS jamais lu (ex. 2023-2024) doit être téléchargé avant l'étape OOS. Sans lui,
    verdict maximal = « validation passée, OOS en attente ».

## Tests obligatoires à inclure dans le protocole (placebo, coûts, vue par jour, concentration…)
Calculés avec `research/common/robustness.py`, tz = `Europe/London`, rapportés pour TOUTES les variantes.
1. **Contrôle « même mouvement sans divergence » (décisif)** : même jambe, mêmes heures, même cooldown, même
   mouvement 15 min de la jambe en ATR (appariement par quantile, ± 10 %), mais |z| < 1 (l'autre paire a suivi).
   Même sens (fade), même stop, même sortie. E001 doit battre ce contrôle d'au moins **+0,05 R/trade** ET l'IC 95 %
   par jour (bootstrap) de la différence doit exclure 0 sur le Train. Sinon REJECT (= H5 retour).
2. **Contrôle « jambe inverse »** : sur les mêmes signaux, trader la jambe qui a le MOINS bougé, dans le sens de la
   convergence. Le mécanisme prédit fautive > inverse ; si inverse ≥ fautive, le mécanisme annoncé est faux même si
   le total est positif.
3. **Placebos** : (a) signal décalé de 60 min (z, u calculés à t−60, entrée à t+1) → |espérance| < 0,03 R exigée,
   sinon artefact ; (b) sens aléatoire aux mêmes heures d'entrée (1000 tirages, graine fixe) → E001 doit dépasser le
   95e centile.
4. **Coûts 0 / 0,2 / 0,4 / 0,6 / 1,0 pip** par trade (par jambe pour la variante deux jambes) : espérance > 0 exigée
   à **+0,6 pip** (remplace le +0,5 du RESEARCHER ; c'est le palier où H3 a échoué).
5. **Vue par jour, IC 95 %** (`day_view`, tz Europe/London) : borne basse > 0 sur le Train ; signe positif par jour
   en Validation. Plus `one_per_day`.
6. **Concentration** (`concentration`) : top 5 jours < 40 % du R total ; sans meilleur trimestre et sans meilleure
   paire, espérance toujours > 0 ; répartition des trades par paire publiée.
7. **Jours de nouvelles** (liste fixée AVANT les résultats depuis un calendrier public : BoE, BCE, CPI UK, CPI zone
   euro, NFP) : résultat avec et sans ces jours, à titre de diagnostic (aucun filtre ajouté après coup). Si tout le
   R vient de ces jours ou si l'exclusion change le signe → fragile.
8. **Variantes ≤ 8** figées dans protocol.md et commitées avant lecture (vérifié par `git log` à l'audit) ; voisins
   rapportés (|z| 2,5 vs 3,0 ; 20 vs 30 min) : un résultat présent à un seul point de grille = suspect.
9. **Test de non-look-ahead** (perturbation du futur) sur σx, σu, médiane de spread et ATR, fourni dans
   `experiments/E001-*/code/`.

## Verdict : GO
Falsifiable, non doublon (si le contrôle 1 est décisif), testable avec M1 bid/ask EURUSD + GBPUSD et le moteur V4
(moyennant le code de sortie anticipée ou son retrait). Pronostic du CRITIC : probabilité élevée d'échec sur les
coûts ou sur le contrôle « sans divergence ».
