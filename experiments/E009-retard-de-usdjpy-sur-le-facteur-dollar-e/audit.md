# E009 - audit du Train (CRITIC)
Verdict : **OK pour REJECT** (rejet du Train confirme ; pas de RETEST).

## Verifications
- Protocole : un seul commit (71b2d41, 19:58) avant les resultats ; le commit ce404a0 ne touche ni protocol.md ni code/ (git diff vide). signal_counts commite avant le run (A=160 >= 150, pas INCONCLUSIVE).
- Look-ahead : sigma = rolling(2000).std().shift(1) (e009.py l.71), entree a la cloture L+5 min, ATR de la barre L, direction fade = -sign(z). Pas de fuite relevee.
- Donnees : SRC train = m1_2025 seul (e009.py l.41) ; trades du 2025-09-10 au 2026-02-27 ; validation.json et oos.json = "skipped". OOS non lu.
- Chiffres recalcules depuis trades_train.csv : n=160, moyenne -0,04594 R, somme -7,35 R, 103 jours, moyenne jour -0,0686, t jour -0,837. Exacts. (t par trade = -0,59.)
- Rejet justifie : 12 des 13 criteres echouent ; moyenne < +0,05, IC jour [-0,225 ; +0,098] contient 0, permute p=0,66 (q95=+0,113), placebo horaire rang 4/13, cout +0,5 pip -0,072 R, hors annonces -0,097 R.

## Remarques (sans effet sur le verdict)
- Incoherence mineure : without_top5_days n=153 (train.json racine) vs n=152 (full_report). Moyenne < 0 dans les deux cas ; a corriger si le code est reutilise.
- 5_no_month_gt_25pct=false parce que max_share=None quand le total est negatif : echec "par defaut", sans importance ici, redondant avec la moyenne.
- Sens inverse (continuation) +0,031 R, t=0,34, -0,002 R par jour : bruit, ne pas le promouvoir (regle 7). Sous-groupes (semaines NFP -0,446 R t=-3,2 ; ventes -0,14 R) = observations, pas des regles.
- Placebo USDJPY seul (-0,043) ~ regle (-0,046) : le facteur dollar n'apporte rien.
