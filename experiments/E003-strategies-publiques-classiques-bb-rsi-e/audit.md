# E003 — audit APRÈS test
Auteur : CRITIC · cycle 3 · 2026-10-10

## Conformité au protocole
- Protocole verrouillé au commit 89b27a4 avant tout calcul ; résultats Train au commit suivant. Aucune variante ajoutée.
- Anti-look-ahead : 80 signaux par hypothèse recalculés sur des données tronquées à la clôture du signal → 0 écart (P1, P2, P3).
- Validation et OOS : **non exécutés** (règle d'arrêt : aucune hypothèse ne passe le Train). OOS 2023-2024 jamais ouvert.
- Correction de bug (code de recherche, partie « mise » seulement) : la première version arrêtait le compte dès qu'un trade GBPUSD
  manquait de marge (≈ 38 €) alors que EURUSD/USDJPY restaient possibles. Corrigé : trade sauté si marge insuffisante pour SA
  paire ; compte arrêté seulement sous la marge minimale de toutes les paires (≈ 29 €). Conforme à l'intention du protocole.

## Résultats Train (sept. 2025 → fév. 2026)
| Hyp. | Meilleure variante | n | Espérance | t | +0,5 pip | Verdict |
|---|---|---|---|---|---|---|
| P1 BB+RSI | P1a | 937 | −0,009 R | −0,27 | −0,080 R | 3/9 critères |
| P2 EMA 9/21 | P2c | 1 190 | −0,001 R | −0,02 | −0,113 R | 4/9 critères |
| P3 RSI2 Connors | P3b | 2 522 | −0,030 R | −1,91 | −0,086 R | 1/9 critère |
Les 12 variantes : de −0,107 à +0,038 R (P2d, 155 trades, t 0,31). 4 variantes significativement négatives (t ≤ −2,7).

## Point honnête en faveur de P1 / P2
P1a et P2c battent le placebo « sens aléatoire » (≈ −0,075 / −0,086 R) : leur sens porte un peu d'information, juste assez pour
compenser le spread Dukascopy (≈ 0 R). Pas assez pour payer un spread de petit courtier (+0,5 pip → −0,08 à −0,11 R).
P3 ne bat même pas le placebo.

## Partie « mise » (50 €, 24 mois, descriptif)
- Tous les scénarios finissent **en perte** (28,5 € à 42,9 €). La plupart s'arrêtent sous ≈ 29 € (plus assez de marge à 30:1).
- À 1 % de risque, 60 à 93 % des signaux sont **impossibles** : même 0,01 lot dépasse 0,50 € de risque.
- À 2 %, presque tous les signaux deviennent possibles, mais le compte s'arrête plus tôt ; Monte-Carlo : probabilité de perdre
  la moitié du compte 44–53 % (contre 4–40 % à 1 %), drawdown de 20 % quasi certain (≥ 99 %).
- Le risque plus élevé ne crée aucun avantage : il accélère l'effet d'une espérance négative.

## Verdict : REJECT (P1, P2, P3)
