# Strategy Discovery — rapport de sélection (23/10/2026)

Méthode : grille de preuves fixée AVANT la recherche (`GRILLE.md`), 13 fiches (`registre.yaml`), score calculé par
`score.py` (`CLASSEMENT.md`). Sources : revues académiques, documents de travail, notes de praticiens, GitHub.
Doublons des registres d'échecs écartés (5 fiches). **Aucun backtest lancé.**

## Conclusion
**Aucune stratégie intrajournalière (≤ 4 h) n'a de preuve suffisante.** Les meilleures candidates intrajournalières
(fix de fin de mois, journées FOMC) ont un score faible (6 à 9 sur 21) : pas de test hors échantillon, pas de coûts,
données anciennes. La seule preuve **solide** (D01, suivi de tendance 12 mois) est mensuelle, donc incompatible avec la
règle actuelle « ≤ 4 h, rien la nuit » — et son auteur signale lui-même un net affaiblissement depuis 2010.

## Les cinq premières (par score de preuve)

### 1. D01 — Suivi de tendance 12 mois — 15/21 (solide, malgré −3 pour déclin)
- Sources : Moskowitz-Ooi-Pedersen (JFE 2012) ; Hurst-Ooi-Pedersen (JPM 2017, un siècle de données) ; AQR « Trends Everywhere » (2018, hors échantillon sur nouveaux actifs) ; AQR « You Can't Always Trend When You Want » (2019).
- Résultats publiés : rentable sur plus de 100 ans et 67 marchés dont les devises du G10, après frais estimés ; Sharpe de l'indice SG Trend ≈ 0,05 sur 2010-2018 (contre 0,28 depuis 2000).
- Conditions exactes : fin de mois, signe du rendement 12 mois → achat / vente, taille inverse de la volatilité, tenu 1 mois.
- Limites : mensuel (nuits et week-ends), avantage tiré de la diversification sur des dizaines de marchés, ≈ 12 trades par an et par paire.

### 2. D02 — Portage (carry) G10 — 10/21 (faible)
- Source : Hsu-Taylor-Wang (JIMF 2024).
- Résultats : **pas rentable hors échantillon** 1983-2015 après correction du data snooping, sauf 2001-2005.
- Conditions : mensuel, acheter taux élevés / vendre taux bas.
- Limites : preuve hors échantillon négative ; krachs.

### 3. D07 — Momentum transversal des devises — 10/21 (faible)
- Sources : Menkhoff-Sarno-Schmeling-Schrimpf (JFE 2012) ; CEPR DP15653 « Currency Anomalies » (baisse après publication).
- Résultats : jusqu'à ≈ 10 %/an avant coûts sur 1976-2010, fortement réduits par les coûts.
- Conditions : mensuel, ≈ 40 devises classées sur 1-12 mois.
- Limites : impossible avec nos 3 paires ; déclin après publication.

### 4. D03 — Dollar avant les changements de taux de la Fed — 9/21 (faible)
- Source : Karnaukh (2018, SSRN).
- Résultats : 1994-2014, 57 trades, +25 pb/trade, Sharpe 0,93 (t 2,8) ; après coûts +15 pb, Sharpe 0,57.
- Conditions : 3 jours avant le FOMC, changement attendu (fed funds futures du mois suivant) ≥ +12,5 pb → acheter USD, ≤ −12,5 pb → vendre ; de 14:00 NY deux jours avant à 14:00 le jour J ; panier EUR, GBP, CHF, JPY.
- Limites : pas de hors échantillon, s'arrête en 2014, 3 trades/an, positions de 2 jours, données fed funds futures gratuites incertaines.

### 5. D04 — Vente du dollar les jours FOMC — 9/21 (faible)
- Source : Mueller-Tahbaz-Salehi-Vedolin (Journal of Finance 2017).
- Résultats : rendement excédentaire significatif les jours FOMC sur ≈ 20 ans, plus fort pour les devises à taux élevé et en période de baisse ; **coûts non déduits**.
- Conditions : vendre USD le jour d'une annonce FOMC programmée ; adaptable en intrajournalier (annonce ≈ 18-19 h UTC, avant notre clôture 21 h).
- Limites : ≈ 8 trades/an, pas de coûts, données anciennes, horaires précis à fixer.

## Écartées
- Doublons d'échecs : règles techniques simples (F01/F02), saisonnalité horaire (F03), fix de Tokyo (V3-H1), momentum intrajournalier (V3-H2), cassure d'ouverture (V3-H3).
- Score très faible : fix de fin de mois (D05, 7), Sheth-Teeple fix WM (D06, 6, « à titre d'illustration »), dérive post-annonce (D08, 4).

## Décision demandée à l'utilisateur (aucun test lancé)
1. Garder la règle ≤ 4 h → aucune candidate ne mérite une campagne ; au mieux un **test exploratoire pré-enregistré** de D04 (journées FOMC, 2020-2026, ≈ 50 occasions — trop peu pour conclure seul).
2. Assouplir la règle (positions de plusieurs jours / semaines) → D01 devient la seule candidate solide, à tester sur l'historique antérieur à 2024 avant d'ouvrir la période vierge.
