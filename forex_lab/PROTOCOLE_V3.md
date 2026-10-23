# Protocole V3 — trois hypothèses documentées (écrit le 23/10/2026, AVANT tout calcul sur ces hypothèses)

Moteur audité (`AUDIT_V3.md`). Coûts : spread bid/ask réel + commission 3 $/lot/côté + 0,1 pip de glissement par ordre au
marché. 2 positions simultanées maximum (toutes paires). Signaux sur bougies M5 bid (ou horaires fixes), exécution à
l'ouverture de la minute suivante. Aucune position entre 21:00 et 00:00 UTC (règle du projet) sauf dans la version
« exacte » d'une source quand elle l'exige (rapportée pour information, jamais retenue pour le projet).

## Découpage des données (jamais d'optimisation sur la validation)
- **Optimisation (IS)** : sept. 2024 → août 2025. Seule période où l'on compare des paramètres.
- **Validation (VAL)** : sept. 2025 → août 2026. Lue UNE fois, pour la seule configuration choisie sur IS.
- **Confirmation finale** (plus tard, si VAL réussie) : historique 2020-2023 (en téléchargement, jamais lu) puis période
  vierge sept. 2023 → août 2024. Mêmes règles, aucun changement.

## Règle de choix sur IS (fixée à l'avance)
Configuration retenue = meilleure statistique t journalière sur IS parmi celles qui ont ≥ 60 trades. Si cette t est < 1,5,
l'hypothèse s'arrête là (ÉCHEC à l'optimisation, la validation n'est pas consommée).

## Critères de réussite en VAL (configuration unique)
1. ≥ 60 trades ; 2. gain moyen net > 0 sur chaque semestre de VAL ; 3. profit factor ≥ 1,10 ; 4. t journalière ≥ 1,65
(test unilatéral 5 %) ; 5. toujours positive avec +0,5 pip de coût par trade ; 6. positive avec une commission de 5 $/lot/côté.
Réussite = « recherche supplémentaire » (confirmation 2020-2023 + période vierge), PAS passage en démo.
Passage en démo seulement si la confirmation finale passe aussi.

## H1 — Fix de Tokyo USD/JPY
- **Sources** : Krohn, Mueller & Whelan, *Foreign Exchange Fixings and Returns Around the Clock* (Journal of Finance ;
  données 1999-2019) : le dollar monte avant le fix de Tokyo (9:55 heure de Tokyo = 00:55 UTC, pas d'heure d'été au Japon)
  puis rebaisse ; JPY : avant −1,61 bp (t −5,9), après +3,15 bp (t 8,2), renversement 4,76 bp/jour (t 10,1), 57 % de jours
  positifs ; ≈ 75 % de l'effet disparaît les jours fériés japonais (pas de fix) ; **effet nettement plus faible en 2014-2019**.
  Ito & Yamada (NBER w22820) : déséquilibre d'ordres prévisible au fix, effets de calendrier (jours « gotobi »).
  Projet : V4-H4 (2024-2025, horizon ≤ 30 min) positive dans les deux moitiés mais t < 1.
- **Limites des preuves** : résultats bruts (sans coûts) ; effet en baisse ; amplitude ≈ 3 bp ≈ 4-5 pips, du même ordre que les coûts.
- **Version exacte (papier)** : acheter USDJPY à 17:00 New York, retourner à 9:55 Tokyo (vendre), racheter à 02:00 New York.
  Rapportée pour information (positions de nuit, interdite par le projet).
- **Version projet** : vendre USDJPY à 00:55 UTC + d minutes, sortie après h heures (≤ 4 h).
  Grille IS : d ∈ {1, 5, 15} min ; h ∈ {2, 3, 4} h ; jours ∈ {tous, gotobi} (5, 10, 15, 20, 25, 30 et dernier jour ouvré ;
  si week-end → jour ouvré précédent). 18 configurations. Jours fériés japonais : non exclus (pas de calendrier gratuit
  fiable ; limite connue, l'effet y est plus faible donc cela pénalise la stratégie).

## H2 — Momentum intrajournalier filtré par la volatilité
- **Sources** : Gao, Han, Li & Zhou, *Market Intraday Momentum* (Journal of Financial Economics 2018) : la première
  demi-heure prédit la dernière, effet plus fort les jours de forte volatilité (actions américaines) ; Elaut, Frömmel &
  Lampaert (2018) : même effet sur le RUB/USD ; marchés à terme chinois : effet plus fort quand la volatilité de la
  1re demi-heure est élevée. **Aucune preuve publiée sur EUR/USD, GBP/USD, USD/JPY.**
- **Lien avec les échecs** : E007 (momentum Londres 08:00→13:00, tenue jusqu'à 17:00, sans filtre) est rejetée.
  Le filtre de volatilité est la seule nouveauté ; il est documenté dans la source, pas inventé après coup.
- **Règle** (heure de Londres, heure d'été gérée) : signal = sens du rendement de la fenêtre S ; position dans ce sens
  pendant la fenêtre T ; seulement si la volatilité réalisée (somme des carrés des rendements M5) de S est au-dessus du
  quantile q de ses 60 jours ouvrés précédents (calcul causal).
  Grille IS : S ∈ {08:00-08:30 ; 17:00 New York de la veille → 08:30 (avec la nuit, comme Gao et al.)} ;
  T ∈ {15:30-16:00 (dernière demi-heure de Londres) ; 08:30-12:30 (reste de séance, 4 h)} ; q ∈ {aucun filtre, 50 %, 67 %}.
  12 configurations × EURUSD, GBPUSD, USDJPY.

## H3 — Cassure de session (range asiatique → Londres)
- **Sources** : script open source TradingView « London BreakOut Classic » (range 00:00-07:00 UTC, entrée sur clôture
  hors du range, stop au milieu du range, objectif 1:1, une fois par jour) ; Backtrex (range 00:00-06:00 UTC, entrée
  07:00-10:00 UTC, stop 35 pips, objectif 70 pips) ; opening range breakout de T. Crabel.
- **Preuves contraires connues** : Backtrex EURUSD H1 2016-2026 : PF 0,87, −28 % ; GBPUSD M15 : −60 % ; l'auteur TradingView
  le juge peu concluant ; projet : V4-H2 (opening range breakout, ≤ 30 min) rejetée. Testée ici à la demande, en M5, avec
  sortie jusqu'à 4 h.
- **Règle** : range = plus haut / plus bas bid des bougies M5 entre 00:00 UTC et la fin du range ; signal = première bougie M5
  qui clôture au-dessus (achat) ou en dessous (vente) du range dans la fenêtre d'entrée ; une entrée par paire et par jour ;
  sortie : stop, objectif = k × risque, ou 4 h, ou 21:00 UTC.
  Grille IS : fin du range ∈ {06:00, 07:00} ; fenêtre d'entrée ∈ {jusqu'à 10:00, jusqu'à 12:00} ;
  stop ∈ {milieu du range, autre bord du range} ; k ∈ {1, 2}. 16 configurations × EURUSD, GBPUSD, USDJPY.

## Sensibilité (rapportée pour la configuration choisie, sur IS et VAL)
Commission 0 / 3 / 5 $ ; glissement 0,1 / 0,3 pip ; coût additionnel +0,5 / +1,0 pip ; résultats de toutes les
configurations voisines de la grille (stabilité des paramètres). Toute hypothèse en échec va dans `ECHECS.md` et dans le
registre des agents.
