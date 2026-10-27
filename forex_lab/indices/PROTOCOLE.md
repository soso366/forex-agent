# Test I01 — « zone de bruit » (momentum intrajournalier) sur le S&P 500 — protocole pré-enregistré le 27/10/2026

Décision de l'utilisateur (27/10/2026) : tester cette stratégie, vue dans une vidéo TikTok (@thequantbuilder) et tirée d'une
étude universitaire. Nouveau marché (indice S&P 500 en CFD) pour CE test seulement. Simulation uniquement, aucun argent réel,
0 € de dépense. Règles projet conservées : trades dans la journée, tout fermé à 16:00 New York (20:00/21:00 UTC), 1 position.

## Source (règles recopiées, aucun réglage modifié)
Zarattini, Aziz, Barbon, « Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY) »,
Swiss Finance Institute RP 24-97 (SSRN mai 2024 ; version du 03/02/2025). Résultat publié 2007 → 2024/04, net de frais :
19,6 %/an, Sharpe 1,33 (taille dynamique) ; 9,7 %/an, Sharpe 1,24, perte max 12 % (taille fixe 100 %).

## Données
Dukascopy, CFD USA500IDXUSD, bougies 1 minute BID et ASK, 01/01/2016 → 23/10/2026 (gratuites, téléchargées dans GitHub
Actions, jamais publiées). Échelle des prix : facteur choisi automatiquement pour que le prix médian soit entre 500 et 20 000.
Séance : bougies ouvrant de 09:30 à 15:59 heure de New York (changements d'heure gérés). Prix de signal = milieu (bid+ask)/2.
Volume : volume Dukascopy (si tout est nul un jour, VWAP remplacé par la moyenne simple des prix — à signaler).

## Règles (étude, version finale « bande courante + VWAP »)
- σ(HH:MM) = moyenne sur les 14 séances précédentes de |Close(HH:MM) / Open(09:30) − 1|.
- Bande haute = max(Open 09:30, Close veille 16:00) × (1 + σ) ; bande basse = min(Open, Close veille) × (1 − σ).
- Contrôles uniquement à HH:00 et HH:30, de 10:00 à 15:30 (prix = clôture de la minute précédente).
- Achat si prix > bande haute ; vente si prix < bande basse.
- Sortie d'un achat si prix < max(bande haute, VWAP) ; d'une vente si prix > min(bande basse, VWAP) ; si le prix est
  au-delà de la bande opposée, retournement immédiat. VWAP depuis 09:30, séance seulement.
- Pas de nouvelle entrée dans le même sens au contrôle où une position vient d'être coupée (précision de copie, l'étude ne le dit pas).
- Exécution à l'ouverture de la minute suivante : achat au prix ASK, vente au prix BID. Clôture forcée à 16:00 (dernière minute).
- Jours sans les 14 séances précédentes complètes, ou sans bougie à un contrôle : pas de trade.

## Taille des positions
- **Officielle (projet, prudente)** : 100 % du capital, sans levier (version « 100 % » de l'étude).
- Information : taille dynamique de l'étude, min(4, 2 % / volatilité journalière sur 14 jours).

## Frais
- Standard : écart bid/ask réel de Dukascopy + 0,1 point de glissement par ordre. Pas de commission (CFD).
- Stress : + 0,5 point de plus par ordre.
- Pas de frais de financement (aucune position gardée la nuit).

## Périodes
- **Reproduction** : janv. 2016 → avril 2024 (période de l'étude) — vérifie que notre copie et ce marché donnent un résultat comparable.
- **Après publication** : mai 2024 → oct. 2026 — **décisive** (l'effet existe-t-il encore une fois public ?).
  Sous-périodes : mai-déc. 2024, 2025, janv.-oct. 2026.

## Critères (version officielle, frais standard) — tous obligatoires
- C0 : reproduction, Sharpe ≥ 0,8 (sinon notre copie ou ce marché ne ressemblent pas à l'étude : résultat NON CONCLUANT).
- C1 : après publication, rendement net > 0 et Sharpe ≥ 0,75.
- C2 : après publication, frais de stress, rendement net > 0.
- C3 : après publication, perte maximale ≤ 15 % du capital.
- C4 : au moins 2 des 3 sous-périodes après publication positives.
PASSE → étape suivante : simulation en direct (paper trading) gratuite, puis discussion avec l'utilisateur. Jamais d'argent réel
sans son accord. Sinon ÉCHEC, ajouté à ECHECS.md. Aucune variante (durée de 14 jours, multiplicateur, horaires) ne sera
choisie d'après ces résultats.
