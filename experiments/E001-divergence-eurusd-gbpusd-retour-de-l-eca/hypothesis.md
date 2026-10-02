# E001 — Divergence EURUSD-GBPUSD : retour de l'ecart EURGBP implicite
Auteur : RESEARCHER · cycle 1 · 2026-10-02 11:37 UTC
Famille : relations entre paires (valeur relative intrajournalière). Aucun rapport avec une heure fixe.

## Mécanisme supposé
EURUSD et GBPUSD partagent la jambe USD et sont fortement corrélés à court terme. Quand l'une des deux paires
s'écarte brutalement de l'autre (gros ordre client non informatif sur UNE jambe, ex. un gérant qui achète des EUR
contre USD), l'EURGBP implicite (= EURUSD / GBPUSD) bouge sans que le dollar ait bougé. Les teneurs de marché
EURGBP et les arbitragistes de triangle vendent alors ce mouvement implicite : la jambe qui a « trop » bougé
revient partiellement vers l'autre dans les 10–30 minutes. On joue ce retour sur la jambe qui s'est écartée.

## Raison économique / microstructure / comportementale
- Impact de prix d'un flux non informatif = en grande partie temporaire (littérature order flow FX, Evans & Lyons ;
  décomposition impact permanent / temporaire). Sur une seule jambe, ce flux n'est pas confirmé par l'autre paire.
- L'EURGBP est un croisé structurellement en range à l'échelle intrajournalière (deux économies très liées) :
  le marché ne « croit » pas spontanément à un écart EUR/GBP de grande taille sans nouvelle.
- La condition « dollar calme » sépare l'écart idiosyncratique (candidat au retour) des chocs USD où les deux
  paires réagissent avec des bêtas différents (pas un vrai écart).
- Point honnête : une forte corrélation n'implique pas un retour ; c'est précisément ce qui est testé.

## Conditions (règles objectives, calculables sans regarder le futur)
Données : M1 bid/ask, prix milieu = (bid close + ask close)/2. Horodatage en UTC dans les fichiers ; fenêtre de
trading définie en **Europe/London** (heure d'été gérée automatiquement).
- Paires : signal calculé sur EURUSD + GBPUSD ; trade sur l'une des deux (USDJPY non concernée).
- Heures : déclencheurs évalués aux minutes de scan (multiples de 5) entre **07:00 et 16:30 Europe/London**
  (liquidité EUR et GBP maximale). Pas de trade le vendredi après 16:30 ni le dimanche soir.
- Calculs à la minute t (uniquement des minutes ≤ t) :
  - rE = log-rendement mid EURUSD sur 15 min, rG = idem GBPUSD.
  - Écart implicite x = rE − rG ; composante dollar u = (rE + rG) / 2.
  - σx et σu = écart-type des x et u sur 15 min non chevauchants, 07:00–16:30 Europe/London, sur les
    **20 jours ouvrés précédents** (jour courant exclu).
  - z = x / σx.
- Déclencheur : |z| ≥ 2,5 **et** |u| ≤ 1,0 σu (dollar calme) **et** spread courant des deux paires ≤ 2 × leur
  spread médian des 20 jours précédents (évite les moments de nouvelle / liquidité dégradée).
- Jambe tradée : celle dont le mouvement 15 min en unités de sa propre ATR M5 (ATR 14 sur M5 clôturées) est le plus
  grand en valeur absolue. Sens : opposé à son mouvement (si EURUSD a monté plus que GBPUSD et que c'est EURUSD qui a
  le plus bougé → vente EURUSD ; si c'est GBPUSD qui a le plus baissé → achat GBPUSD).
- Entrée : ouverture de la minute t+1 (ask pour un achat, bid pour une vente).
- Stop : 1,5 ATR M5 de la paire tradée, jamais élargi.
- Sortie : au temps, **20 minutes** après l'entrée ; sortie anticipée si |z| recalculé repasse ≤ 0,5 (écart refermé).
- Une seule position par signal ; pas de nouveau signal sur la même paire pendant 30 min.
- Variantes proposées (≤ 6, à figer par le QUANT avant les données) : seuil |z| 2,5 / 3,0 ; fenêtre 15 / 30 min ;
  sortie 20 / 30 min ; une jambe vs les deux jambes à demi-risque (vente de l'une + achat de l'autre = USD neutre,
  compatible avec la règle « pas deux positions même devise même sens »).

## Pourquoi 5–30 minutes
L'impact temporaire d'un flux sur une jambe se résorbe en minutes à dizaines de minutes (temps pour que les
arbitragistes et les teneurs EURGBP réagissent) ; au-delà, l'écart restant est plutôt de l'information (nouvelle
UK/zone euro) et devient persistant. 15 min de mesure + 20 min de détention est donc le bon ordre de grandeur.

## Critères falsifiables (ce qui prouverait que c'est FAUX)
À verrouiller dans protocol.md avant toute lecture de la validation :
1. Train : espérance ≤ +0,05 R/trade après spread réel, ou t < 2, ou moins de 100 trades → REJECT.
2. Validation : signe négatif ou espérance < +0,03 R → REJECT.
3. **Contrôle « paire seule »** : même jambe, même taille de mouvement 15 min (en ATR), même heures, mais SANS la
   condition de divergence (l'autre paire a bougé pareil). Si E001 ne bat pas ce contrôle d'au moins +0,05 R,
   l'effet n'est qu'un retour à la moyenne d'une paire seule (famille H5 « displacement en retour », déjà
   rejetée) → REJECT.
4. **Placebo temporel** : signal décalé de 60 min (z calculé une heure avant) → doit donner ≈ 0 ; sinon artefact.
5. Coûts +0,5 pip par trade : espérance doit rester > 0, sinon avantage non exploitable → REJECT.
6. Concentration : plus de 40 % du total R sur 5 jours, ou une seule paire tradée portant tout le résultat → REJECT.

## Risques d'échec
- Les gros écarts EUR/GBP viennent surtout de **nouvelles UK / zone euro** (données, BoE, BCE, politique) : ils
  sont informatifs et persistants. Sans calendrier automatique, le filtre « dollar calme + spread normal » ne les
  élimine qu'en partie. C'est le risque principal.
- Coûts : le retour attendu est petit (≈ 1–2 pips) ; un seul spread le mange vite. La variante deux jambes double
  le coût.
- Choix de la jambe « fautive » par ATR peut être bruité (les deux ont un peu bougé).
- Fréquence incertaine : |z| ≥ 2,5 avec dollar calme pourrait donner trop peu de trades (< 100 sur 6 mois).
- Régime : en période de forte thématique GBP (BoE surprise, politique UK), l'EURGBP tend au lieu de revenir.

## Non-doublon
Vérifié contre memory/EXPERIMENTS.md et memory/REJECTED_HYPOTHESES.md (dupcheck : « divergence EURUSD GBPUSD »,
« EURGBP implicite », « SMT », « relations paires » → aucun doublon).
- Rien à voir avec un fixing ou une heure fixe (≠ H3, ≠ fix de Tokyo) : le déclencheur est un état relatif entre
  deux paires, à n'importe quelle minute de la journée de Londres.
- ≠ displacement en retour (H5) : H5 regardait UNE paire seule ; ici la condition décisive est la divergence
  entre deux paires à dollar constant, et le critère 3 exige de battre explicitement le contrôle « paire seule ».
- ≠ SMT divergence ICT (playbook, jamais testée, prévue comme confirmation de sweep) : pas de sweep, pas de
  niveau de liquidité, mesure statistique normalisée.
- ≠ filtrage par cellules de contexte : la règle est fixée a priori par un mécanisme, pas apprise sur des cellules.
