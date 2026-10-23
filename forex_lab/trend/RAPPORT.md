# Test D01 — suivi de tendance 12 mois : ÉCHEC (24/10/2026)

Protocole pré-enregistré : `PROTOCOLE.md` (commit 0bc5f88, avant téléchargement des données). Résultats : `resultats.json`.

| Mesure (version officielle, 2 positions, frais standard) | Résultat | Critère |
|---|---|---|
| Développement 1972-02 → 2023-08 (619 mois) | +0,015 %/mois, Sharpe 0,03, t 0,19, perte max −42 % | C1 Sharpe ≥ 0,3 et t ≥ 2 : **non** |
| 2010 → 2023-08 | Sharpe −0,09 | C2 > 0 : **non** |
| Frais de stress | Sharpe −0,09 | C3 > 0 : **non** |
| Sous-périodes positives | 2 sur 3 (avant 2000 ≈ 0 ; 2000-2009 Sharpe 0,17) | C4 : oui |
| Sans aucun frais (information) | Sharpe 0,14, t 1,0 | — |
| Récent sept. 2024 → oct. 2026 (indicatif) | Sharpe −0,17 | — |

Informations (ne décident pas) : 3 paires sans limite Sharpe 0,06 ; durées 1/3/6 mois Sharpe 0,09 / 0,16 / 0,17 ;
par paire : EURUSD −0,12, GBPUSD 0,01, USDJPY 0,33 (2002-2023). Le choix de l'USDJPY seul serait une sélection après coup.

Vérification indépendante (`verif.py`, autre code, données FRED et BCE) : Sharpe brut 2000-2023 par paire identiques
(EURUSD −0,01 / −0,07 BCE ; GBPUSD 0,10 ; USDJPY 0,44 / 0,42 BCE).

Lecture : l'avantage publié du suivi de tendance vient de la diversification sur des dizaines de marchés ; sur nos
trois paires seules, il est trop faible pour couvrir des frais de courtier de détail. Pas de robot MT5 (étape 2 annulée).
