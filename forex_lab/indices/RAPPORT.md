# Test I01 — zone de bruit S&P 500 (28/10/2026)

Protocole : `PROTOCOLE.md` (pré-enregistré, commit 9a155d2). Résultats : `resultats.json` (données 01/12/2015 → 23/10/2026,
2 809 séances, écart bid/ask médian 0,50 point).

| Version officielle (sans levier) | Reproduction 2016 → 2024/04 | Après publication 2024/05 → 2026/10 |
|---|---|---|
| Frais réels | +2,2 %/an, Sharpe 0,36, perte max −17 % | **−6,8 %/an, Sharpe −1,15, perte max −16 %** |
| Sans aucun frais (information) | +6,4 %/an, Sharpe 1,0 | **−4,7 %/an, Sharpe −0,78** |
| Frais de stress | — | −9,7 %/an |
| Indice acheté et gardé | +13,6 %/an | +17,7 %/an |

Sous-périodes après publication : mai-déc. 2024 −7,3 % ; 2025 −5,2 % ; 2026 −4,8 %. Version à levier de l'étude : −43 %.

Verdict selon le protocole : **NON CONCLUANT** (C0 : la copie nette n'atteint pas Sharpe 0,8 ; sans frais elle atteint 1,0,
proche de l'étude — l'écart vient surtout du coût du CFD, ≈ 0,035 % par trade contre un gain moyen publié ≈ 0,036 %).
Tous les critères après publication échouent, y compris sans frais : l'effet n'apparaît plus depuis la publication.
Réserve sur les données : le rendement « indice » de 2020 (+43 %) est anormal (réel ≈ +16 %) — probablement des jours
manquants exclus du calcul ; cela ne touche pas la conclusion après publication.
Décision : abandon. Pas de simulation en direct, pas de robot.
