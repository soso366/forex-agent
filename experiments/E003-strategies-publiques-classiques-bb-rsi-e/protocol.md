# E003 — protocole (VERROUILLÉ au commit, ne plus modifier)
Auteur : QUANT · cycle 3 · 2026-10-10 · écrit AVANT tout calcul de résultat (aucun R calculé avant ce commit).

## Règle commune (fixe pour les 3 hypothèses)
- Données M1 bid/ask Dukascopy, UTC. Bougies M5 sur le mid : `research/v4/data.bars(m1, "5min")` (étiquette = début).
- Indicateurs sur la clôture M5 : EMA (ewm span, adjust=False), RSI de Wilder (ewm alpha=1/n), Bollinger = SMA20 ± 2 écarts-types
  (ddof=0), ATR(14) = `research/v4/data.atr` sur la bougie du signal (close, donc connue). ADX(14) de Wilder.
  Pente H1 : signe de EMA50(H1).diff(3), lue sur la dernière bougie H1 **clôturée** avant la fin de la bougie M5.
- Fenêtre : bougie M5 dont la clôture tombe dans [07:00, 20:00[ UTC, lundi–vendredi (sauf P1 « 24h » : toutes heures).
- Entrée : ouverture de la première minute ≥ clôture M5 (ASK achat, BID vente) via `research/v4/sim.simulate` (inchangé) :
  stop/cible côté sortie, stop prioritaire dans la même minute, glissement si l'ouverture saute le stop, sortie au temps à 30 min.
- Une position à la fois par paire (`research/v4/engine.non_overlap`, 30 min). R = PnL / distance de stop. Spread réel inclus.

## Hypothèses et variantes (4 par hypothèse, 12 au total)
**P1 — Bollinger + RSI (retour à la moyenne)** : clôture < bande basse ET RSI14 < 30 → achat ; clôture > bande haute ET
RSI14 > 70 → vente. Stop 1,5 ATR. Signal suivant seulement après retour du prix à l'intérieur des bandes (pas de rafale).
| id | sortie | heures |
|---|---|---|
| P1a | cible = SMA20 du signal (distance |SMA20 − clôture| ; signal ignoré si < 2 spreads) | 07–20 UTC |
| P1b | cible = SMA20 | 24 h |
| P1c | temps seul (30 min) | 07–20 UTC |
| P1d | temps seul | 24 h |

**P2 — croisement EMA 9/21 dans le sens H1** : EMA9 passe au-dessus d'EMA21 (clôture M5) et pente H1 > 0 → achat ;
en dessous et pente < 0 → vente. Stop 1 ATR.
| id | cible | filtre |
|---|---|---|
| P2a | 1,5 R | aucun |
| P2b | 1,5 R | ADX14 ≥ 25 |
| P2c | temps seul | aucun |
| P2d | temps seul | ADX14 ≥ 25 |

**P3 — RSI(2) de Connors** : RSI2 < seuil bas ET clôture > EMA200(M5) → achat ; RSI2 > seuil haut ET clôture < EMA200 → vente.
Sortie au temps (30 min).
| id | seuils | stop |
|---|---|---|
| P3a | 10 / 90 | 1 ATR |
| P3b | 10 / 90 | 2 ATR |
| P3c | 5 / 95 | 1 ATR |
| P3d | 5 / 95 | 2 ATR |

Voisins = variantes qui diffèrent d'UNE dimension (2 voisins chacune).

## Données
- Train : 2025-09-01 → 2026-02-28 (`data/m1_2025`) ; T1 = sept.–nov., T2 = déc.–fév.
- Validation A : 2026-03-01 → 2026-08-31 (`data/m1`) · Validation B : 2024-09-01 → 2025-08-31 (`data/m1_locked_2024` +
  `data/m1_locked`, contaminées par H3 mais jamais utilisées pour ces règles). Historique d'indicateurs : jours précédents permis.
- OOS vierge sept. 2023 → août 2024 : **non ouvert** ; seulement via `orchestrator oos-gate E003` si une hypothèse passe Train ET
  Validation ; lu une seule fois.

## Sélection (Train uniquement, par hypothèse)
Éligible : n ≥ 60. Score prudent = min(espérance de v, de ses 2 voisins). Sélection = score prudent max (égalité → plus petit id).

## Critères Train → validation (tous requis, par hypothèse)
1. espérance > 0 et t ≥ 2,0 ; 2. n ≥ 60 ; 3. T1 et T2 positifs ; 4. au moins un voisin positif ;
5. espérance > 0 sans les 5 meilleurs trades ; 6. PF ≥ 1,10 ; 7. au moins 2 paires sur 3 positives ;
8. espérance > 0 avec +0,5 pip de coût ; 9. espérance > quantile 95 % du **placebo sens aléatoire** (mêmes signaux, mêmes
stops/cibles, sens tiré au hasard, 200 tirages, graine 3).

## Critères validation (variante sélectionnée seulement)
A et B : espérance > 0 et PF > 1 chacune ; au moins 3 trimestres sur 4 non négatifs sur B ; espérance > 0 avec +0,5 pip sur A ∪ B.
Sinon REJECT sans ré-ajustement.

## Tests de robustesse rapportés (toutes variantes)
`research/common/robustness.full_report` : coûts 0 / 0,2 / 0,4 / 0,6 / 1,0 pip, vue par jour (IC 95 %), une paire par jour,
concentration. Placebo sens aléatoire (critère 9). Test anti-look-ahead : signaux identiques si les données après la bougie
du signal sont supprimées (échantillon de 300 signaux).

## Partie « mise » (descriptive, demandée par l'utilisateur ; ne change rien au Risk Manager)
Trades de la variante sélectionnée de chaque hypothèse, sur les 24 mois (B, Train, A dans l'ordre), rejoués sur un compte de 50 € :
- levier 30:1, lot min et pas 0,01 ; marge d'un 0,01 lot en € (≈ 29–38 €) → une seule position ouverte à la fois, toutes paires ;
- conversion en € au mid du moment (EURUSD, USDJPY) ; perte au stop par 0,01 lot = distance × 1 000 × conversion ;
- taille = plus grand multiple de 0,01 dont la perte au stop ≤ risque × équité ; si 0,01 lot dépasse le risque → trade **non pris** ;
- risques testés : 1 % et 2 % ; coûts : spread Dukascopy, et +0,5 pip (compte standard) ;
- variante « forcer 0,01 lot » : risque réel moyen rapporté ;
- arrêt si l'équité < marge d'un 0,01 lot ; drawdown max ; déclenchement du kill switch 20 % (informatif, pas d'arrêt) ;
- Monte-Carlo 1 000 séquences (tirage avec remise des trades pris, graine 5) : P(−50 %), P(drawdown ≥ 20 %), médiane finale.
