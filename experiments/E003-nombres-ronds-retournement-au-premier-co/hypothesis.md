# E003 — Nombres ronds : retournement au premier contact (ordres take-profit groupés)
Auteur : RESEARCHER · cycle 3 · 2026-10-11 18:30 UTC
Famille : microstructure / flux d'ordres (regroupement des ordres en attente sur des niveaux de prix exogènes).

## Mécanisme supposé
Les clients des banques et des brokers placent leurs ordres de prise de bénéfice (take-profit) et leurs ordres
limites **sur des nombres ronds** (EURUSD 1,1700 / 1,1750 ; USDJPY 150,00 / 150,50). Ces ordres forment un « mur »
d'offres (au-dessus du prix) ou de demandes (au-dessous). Quand le prix arrive pour la première fois depuis un
moment sur un tel niveau, ce mur absorbe le flux directionnel et le prix a plus de chances de **repartir en sens
inverse** dans les minutes suivantes qu'à un niveau quelconque. On vend au premier contact d'un nombre rond par
le bas, on achète au premier contact par le haut, seulement si le niveau n'a pas été franchi dans la minute.

Un seul mécanisme : regroupement des ordres limites / take-profit AUX nombres ronds (offre/demande passive concentrée).

## Raison économique / microstructure / comportementale
- **Données d'ordres réelles** : C. Osler (Journal of Finance 2003, « Currency orders and exchange-rate
  dynamics » ; FRBNY Economic Policy Review 2000 ; JIMF 2005 « Stop-loss orders and price cascades ») a étudié le
  carnet d'ordres clients d'une grande banque : les take-profit se concentrent **exactement** sur les niveaux
  finissant par 00, puis 50 ; les stop-loss se concentrent **juste au-delà**. Conséquences prédites et observées :
  (1) les tendances intrajournalières s'interrompent / se retournent plus souvent aux nombres ronds ; (2) après
  franchissement, le mouvement s'accélère (cascade de stops). E003 teste uniquement (1).
- **Comportemental** : biais cognitif de préférence pour les chiffres ronds (« price clustering », Goodhart &
  Curcio 1991 ; Sopranzetti & Datar 2002 sur les cotations FX). Le niveau est choisi par des humains et des
  algorithmes qui les imitent, pas déduit de l'historique de prix → il est **exogène** et connu à l'avance.
- Contrairement aux niveaux techniques (plus haut de la veille, range asiatique, swings) déjà rejetés, la
  position du niveau ne dépend d'aucune donnée de prix : cela permet un **placebo propre** (mêmes règles sur des
  niveaux non ronds décalés), qui est le test central du mécanisme.

## Conditions (règles objectives, calculables sans regarder le futur)
Fuseau : **UTC**. Données : Dukascopy M1 bid/ask. ATR = ATR 14 sur barres M5 mid **clôturées** avant la minute t.
- Paires : EURUSD, GBPUSD, USDJPY (chacune indépendamment ; 1 pip = 0,0001 / 0,0001 / 0,01).
- Niveaux ronds L : multiples de **50 pips** (EURUSD/GBPUSD : x,xx00 et x,xx50 ; USDJPY : xxx,00 et xxx,50).
- Heures autorisées : minute de contact entre **07:00 et 19:30 UTC**, lundi → vendredi ; sortie forcée au plus
  tard 20:00 UTC (avant le rollover). Aucune exclusion de calendrier (pas de données de calendrier requises).
- Déclencheur VENTE (niveau L au-dessus du prix ; symétrique pour l'ACHAT avec bid low ≤ L + 0,5 pip) :
  1. **Contact** à la minute t : ask high_t ≥ L − 0,5 pip (l'offre a touché le mur d'ordres posé à L).
  2. **Premier contact** : aucun contact de ce même niveau (ask high ≥ L − 0,5 pip ou bid low ≤ L + 0,5 pip)
     dans les **120 minutes** précédentes.
  3. **Arrivée** (et non oscillation autour du niveau) : mid à la clôture de t−15 au moins **0,75 ATR** sous L.
  4. **Non franchi dans la minute** : mid close_t < L et mid high_t < L + 0,3 ATR (sinon c'est le cas
     « franchissement / cascade », non traité ici).
- Entrée : **ouverture de t+1, au marché** (bid pour une vente, ask pour un achat) — pas d'hypothèse de remplissage
  à cours limité, donc pas de biais de remplissage favorable.
- Stop : **1,0 ATR** depuis le prix d'entrée, jamais élargi.
- Sortie : cible **1,0 R** ou **sortie au temps 20 min** (le premier atteint ; si stop et cible dans la même
  minute M1 → compter le stop).
- Au plus un trade par paire et par niveau par jour ; une seule position ouverte par paire.
- Placebo (obligatoire, mêmes règles, calculé en même temps) : grilles de niveaux **non ronds** décalées de
  **+17 pips** et **+33 pips** (même espacement de 50 pips ; on évite +25 qui est un « quart » semi-rond).
- Variantes proposées (≤ 6, à figer par le QUANT avant les données) : A principale (00+50, stop 1 ATR, cible 1 R,
  20 min) · B niveaux 00 seulement · C sortie 10 min · D sortie 30 min · E sans cible (sortie au temps seule) ·
  F stop 0,75 ATR. Chaque variante est toujours comparée à ses deux placebos.

## Estimation du nombre de trades au Train (sept. 2025 → fév. 2026, ≈ 125 jours ouvrés)
Ordre de grandeur (à vérifier par le QUANT, pas mesuré ici) : amplitude journalière ≈ 60–80 pips (EURUSD),
80–110 (GBPUSD), 90–130 (USDJPY) → environ 1 à 2 niveaux de 50 pips atteints par jour et par paire ; après les
filtres « premier contact », « arrivée » et heures 07–19:30 UTC, on attend ≈ 0,5 à 1 trade / jour / paire, soit
**≈ 190 à 370 trades au Train** pour la règle A (≈ 90 à 180 pour la variante B, niveaux 00 seuls).
Le seuil de 80 trades est donc atteignable avec une marge confortable ; s'il ne l'est pas pour A, c'est un REJECT
(pas de relâchement des filtres).

## Pourquoi 5–30 minutes
L'absorption par un mur d'ordres est un phénomène de court terme : soit le stock d'ordres au niveau est consommé
et le prix passe (cascade, en minutes), soit il tient et le flux s'épuise ; dans les deux cas l'issue se joue
dans les 5 à 20 minutes suivant le contact. Au-delà de 30 min, l'information macro et les autres flux dominent.
Sortie au temps 20 min (variantes 10 / 30) et cible 1 R (≈ 1 ATR M5, atteignable en 20 min : amplitude typique
30 min ≈ 2,3 ATR) collent au mécanisme et aux leçons du projet (pas de cible structurelle lointaine).

## Critères falsifiables (ce qui prouverait que c'est FAUX)
À verrouiller par le QUANT dans protocol.md avant toute lecture de la validation :
1. **Train** : moins de 80 trades (3 paires), ou espérance ≤ +0,05 R/trade après spread réel, ou t < 2 calculé
   **par jour** (somme des R du jour, les 3 paires partagent l'USD) → REJECT immédiat, pas de validation ni d'OOS.
2. **Test du mécanisme — placebo (décisif)** : la règle sur niveaux ronds doit battre **chacune** des deux grilles
   placebo (+17 et +33 pips) d'au moins **+0,06 R/trade**. Si un placebo fait aussi bien ou mieux → l'effet est un
   simple « retour après approche » sans rapport avec les nombres ronds → REJECT même si E003 est positif.
3. **Gradient prédit par Osler** : les niveaux 00 ne doivent pas faire moins bien que les niveaux 50 de plus de
   0,10 R (les take-profit sont plus concentrés sur 00). Un gradient inversé net → mécanisme non soutenu → REJECT.
4. **Coûts** : avec +0,5 pip de coût par trade, l'espérance doit rester > 0 ; rapporter aussi +0,2 et +1 pip.
5. **Concentration** : > 40 % du total R sur 5 jours, ou une seule paire > 70 % du total R, ou un seul trimestre
   portant tout le résultat → REJECT.
6. **Validation** (mars → août 2026) : espérance < +0,03 R ou signe négatif, ou placebo ≥ règle → REJECT.
7. Diagnostic (non décisionnel, à rapporter) : après un franchissement net (clôture M1 ≥ 0,3 ATR au-delà de L),
   le mouvement des 5 min suivantes (prédiction (2) d'Osler, cascade). Il ne doit PAS devenir une règle de
   continuation (famille rejetée) sans nouvelle hypothèse.

## Risques d'échec
- **Effet ancien et arbitré** : les données d'Osler datent de 1999–2000 ; le marché est aujourd'hui dominé par des
  algorithmes qui connaissent ces regroupements (ordres placés « juste avant » le rond → le mur se déplace de
  quelques pips, ce qui peut diluer l'effet au niveau exact).
- **Taille de l'effet** : Osler mesure un écart de probabilité de quelques points de pourcentage ; après un coût
  de ≈ 0,07 R par trade (entrées aléatoires), l'avantage net peut être nul.
- **Cascades** : quand le niveau cède, les stops groupés juste au-delà provoquent un mouvement rapide contre nous ;
  la perte moyenne peut dépasser 1 R en cas de saut (glissement) → à mesurer sur le prix réel de la minute.
- **Proximité avec les fades déjà rejetés** (sweep & reclaim, RangeFade, displacement en retour) : le critère 2
  (placebo de niveaux) est précisément là pour éliminer E003 si la nature « ronde » du niveau n'apporte rien.
- **Spécificité Dukascopy** : les cotations sont celles d'un seul fournisseur ; les niveaux ronds sont universels,
  mais le contact exact à ±0,5 pip peut différer d'un broker à l'autre (tester la sensibilité à ±1 pip en
  diagnostic seulement, sans en faire une variante sélectionnée).
- **Régime de marché** : en tendance forte (ex. USDJPY lors d'interventions), les ronds sont franchis en série ;
  l'effet peut n'exister qu'en marché calme, ce qui ne serait pas exploitable sans filtre de contexte (rejeté).

## Données nécessaires
Aucune donnée nouvelle : uniquement Dukascopy M1 bid/ask déjà prévues (Train sept. 2025 → fév. 2026, Validation
mars → août 2026). Pas de calendrier économique. L'OOS vierge sept. 2023 → août 2024 reste fermé jusqu'à
`python -m orchestrator oos-gate E003` = OUVERT.

## Non-doublon
Vérifié contre memory/EXPERIMENTS.md et memory/REJECTED_HYPOTHESES.md (dupcheck : « nombre rond », « round
number », « niveau psychologique », « niveau rond retournement », « take profit clustering » → aucun doublon).
- ≠ V4-H1 sweep & reclaim Asie / PDH-PDL : niveaux dérivés de l'historique de prix et exigeant un franchissement
  puis un retour ; ici niveau **exogène** fixe et **aucun franchissement** (on refuse justement les minutes qui
  franchissent).
- ≠ RangeFade_v2 / cellules de contexte : aucun régime ni range requis, aucune cellule apprise.
- ≠ V4-H5 displacement en retour : pas de condition sur la taille de bougie ; le placebo de niveaux (critère 2)
  impose de battre un « retour après approche » générique.
- ≠ H3 / fix de Tokyo / E002 : aucune heure fixe, aucun fixing, aucune condition de spread.
- ≠ E001 : une seule paire à la fois, aucune relation entre paires.
- ≠ ORB / continuation : E003 est un retournement ; la cascade après franchissement n'est qu'un diagnostic.
