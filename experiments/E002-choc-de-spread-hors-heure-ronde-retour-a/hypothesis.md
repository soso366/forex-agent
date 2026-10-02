# E002 — Choc de spread hors heure ronde : retour apres normalisation de la liquidite
Auteur : RESEARCHER · cycle 1 · 2026-10-02 11:37 UTC
Famille : microstructure / liquidité (impact de prix temporaire lors d'un retrait de liquidité).

## Mécanisme supposé
Quand les fournisseurs de liquidité retirent leurs prix (le spread s'écarte brutalement) et qu'un ordre au marché
traverse ce carnet aminci, le prix bouge beaucoup plus que ce que justifie l'information : c'est un impact
**temporaire** dû au manque de liquidité. Dès que les fournisseurs reviennent (le spread redevient normal), le
prix revient partiellement. Hors des heures de publications programmées (minutes rondes), un tel choc est
rarement une nouvelle : on joue le retour, en entrant seulement APRÈS la normalisation du spread.

## Raison économique / microstructure / comportementale
- Décomposition classique impact permanent (information) / impact temporaire (liquidité) : plus la liquidité est
  mince au moment du flux, plus la part temporaire est grande.
- Les « flash moves » FX hors nouvelles (retraits d'algorithmes, last look, ordre stop massif dans un carnet vide)
  reviennent typiquement en minutes (ex. épisodes JPY de janvier 2019, à une autre échelle).
- Les publications macro tombent presque toutes à des minutes rondes (:00, :15, :30, :45) ; là, l'écartement du
  spread accompagne une information → impact permanent. Ce découpage par l'horloge est donc un **test du
  mécanisme**, pas un filtre optimisé : on prédit à l'avance que les chocs aux minutes rondes ne reviennent pas.
- Entrer après la normalisation évite de payer le spread élargi (sinon l'avantage serait mangé par le coût).

## Conditions (règles objectives, calculables sans regarder le futur)
Tout en **UTC** (les publications et le rollover sont exclus par fenêtres explicites ci-dessous).
- Paires : EURUSD, GBPUSD, USDJPY (chacune indépendamment).
- Spread de la minute t : s_t = max(ask open − bid open, ask close − bid close).
- Référence : ref_t = médiane des spreads de la même paire sur le **même créneau de 30 min de la journée (UTC)**
  sur les **20 jours ouvrés précédents** (jour courant exclu) → tient compte de la saisonnalité du spread.
- Heures autorisées : **06:00–20:00 UTC**, lundi à vendredi ; exclus : 20:30–22:30 UTC (rollover, spread élargi
  mécaniquement) et lundi avant 07:00 UTC.
- Déclencheur (minute de choc t) :
  1. s_t ≥ **3 × ref_t** ;
  2. mouvement mid entre la clôture de t−3 et la clôture de t : |Δ| ≥ **1,0 ATR M5** (ATR 14 sur M5 clôturées) ;
  3. **minute hors heure ronde** : la minute de choc n'est pas à ±2 min de :00, :15, :30, :45 (soit 40 minutes
     autorisées sur 60). Les chocs exclus sont gardés dans un échantillon de contrôle séparé (voir critères).
- Normalisation : première minute m dans (t, t+5] où s_m ≤ **1,5 × ref_m**. Si aucune → pas de trade.
  Si le prix a déjà retracé plus de 50 % de Δ à la clôture de m → pas de trade (le retour est déjà fait).
- Entrée : ouverture de m+1, dans le sens opposé à Δ (ask pour un achat, bid pour une vente).
- Stop : 1,5 ATR M5, jamais élargi.
- Sortie : au temps **15 minutes** après l'entrée ; ou cible = retour de 50 % de Δ (mesuré depuis l'extrême du choc).
- Un seul trade par paire par épisode ; pas de nouveau trade sur la paire pendant 30 min.
- Variantes proposées (≤ 6, à figer par le QUANT avant les données) : seuil spread 3× / 2,5× ; sortie 15 / 30 min ;
  avec / sans cible 50 %.

## Pourquoi 5–30 minutes
Le retour de la liquidité et la résorption de l'impact temporaire se font en minutes ; au-delà de 30 min, le prix
est dominé par d'autres flux et l'effet se dilue. Sortie au temps 15 min (variante 30) colle au mécanisme.

## Critères falsifiables (ce qui prouverait que c'est FAUX)
À verrouiller dans protocol.md avant toute lecture de la validation :
1. Train : espérance ≤ +0,05 R/trade après spread réel, ou t < 2, ou moins de 80 trades (3 paires) → REJECT
   (si < 80 trades au seuil 3×, la variante 2,5× pré-déclarée sert de règle principale ; pas d'autre relâchement).
2. Validation : signe négatif ou espérance < +0,03 R → REJECT.
3. **Contrôle « même mouvement, spread normal »** : chocs de prix identiques (|Δ| ≥ 1 ATR en 3 min, mêmes heures,
   même minute hors ronde) mais spread < 1,5 × ref. C'est l'équivalent du « displacement en retour » (H5, ≈ −0,03 R).
   Si E002 ne bat pas ce contrôle d'au moins +0,08 R → la condition de liquidité n'apporte rien → REJECT.
4. **Test du mécanisme** (décisif si l'échantillon de contrôle a ≥ 50 trades) : la même règle appliquée aux
   chocs AUX minutes rondes doit faire moins bien (écart ≥ +0,05 R en faveur des minutes hors rondes) ; sinon le
   mécanisme « liquidité ≠ information » n'est pas soutenu → REJECT même si E002 est positif.
5. Coûts +0,5 pip par trade : espérance doit rester > 0 → sinon REJECT.
6. Concentration : plus de 40 % du total R sur 5 jours ou sur un seul épisode de marché → REJECT.
7. Contrôle de données : les chocs de spread isolés sur une seule minute sans mouvement des minutes voisines
   (probables erreurs de flux Dukascopy) doivent être inspectés ; si le résultat vient d'eux → REJECT.

## Risques d'échec
- **Spécificité Dukascopy** : les spreads mesurés sont ceux d'un seul fournisseur ; un « choc » peut être propre
  à son flux et ne pas exister chez un autre broker (paper live différent).
- Résolution M1 : on ne voit pas l'intra-minute ; la normalisation peut survenir en milieu de minute et
  l'entrée à m+1 arriver trop tard (retour déjà fait).
- Nouvelles non programmées (déclarations de banquiers centraux, gros titres) tombent aussi hors minutes rondes :
  elles sont informatives et persistantes → pertes.
- Rareté : un choc 3× avec 1 ATR de mouvement peut être peu fréquent ; risque d'échantillon trop petit.
- Proximité avec H5 (displacement en retour, rejeté) : le critère 3 est là pour l'éliminer si la condition de
  spread n'ajoute rien.

## Non-doublon
Vérifié contre memory/EXPERIMENTS.md et memory/REJECTED_HYPOTHESES.md (dupcheck : « spread choc »,
« spread liquidite retour » → aucun doublon).
- ≠ H3 / fix de Tokyo : aucune heure fixe de déclenchement ; au contraire les minutes rondes (où tombent fixings et
  publications) sont EXCLUES et servent de contrôle.
- ≠ H5 displacement en retour : H5 conditionnait sur la taille d'une bougie seule ; ici la condition décisive est
  l'état de liquidité (spread anormal puis normalisé) mesuré en bid/ask, et le critère 3 impose de battre
  explicitement l'équivalent de H5.
- ≠ ORB / sweep & reclaim / cellules de contexte / micro-réglage V2 : aucun niveau de prix, aucun apprentissage de
  cellules, règle fixée a priori par un mécanisme.
