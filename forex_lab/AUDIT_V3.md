# Audit du backtester Forex (`forex_lab/engine.py`) — phase V3, 23/10/2026

Verdict : **fiable après corrections**. Quatre manques ont été corrigés avant tout nouveau test ; aucune erreur de calcul
n'a été trouvée dans les prix d'exécution, l'ordre des événements ou l'absence de look-ahead.

## 1. Points contrôlés

| Point | Constat avant audit | Action | Preuve |
|---|---|---|---|
| Spread | Réel : achat à l'ask, vente au bid, minute par minute (Dukascopy). Médiane 0,3 pip EURUSD, 0,6-0,9 GBPUSD, 0,3-0,7 USDJPY ; 1,5-3 pips à 22:00 UTC | conservé | tests `test_spread_cost_flat_market`, `test_sell_prices_and_spread` |
| Commission | **Absente** : les spreads Dukascopy sont des spreads « bruts » d'ECN, sans la commission que facture un broker ECN | **ajoutée** : 3 $ par lot et par côté (≈ 0,6 pip aller-retour EURUSD/GBPUSD, ≈ 0,9 pip USDJPY) | `test_costs_commission_and_slippage` |
| Glissement | Absent (seulement un stress +0,5 pip à posteriori) | **ajouté** : 0,1 pip par ordre au marché (entrée, stop, sortie à l'heure / sur signal) ; pas sur l'objectif (ordre limite). Stress +0,5 pip conservé | idem |
| Stop sur gap | Rempli au prix d'ouverture si l'ouverture est déjà au-delà du stop (pas au prix du stop) | conservé | `test_stop_gap_fills_at_open_not_at_stop` |
| Stop et objectif dans la même minute | Stop retenu (hypothèse prudente) | conservé + **compteur** des cas ambigus | `test_stop_first_when_both_hit_same_minute` |
| Trailing stop | Mis à jour sur la clôture de la minute, après le contrôle du stop (pas d'optimisme intra-minute) | conservé | revue du code |
| Look-ahead | Signal lu à la clôture de la bougie, exécution à l'ouverture de la suivante ; indicateurs causaux | conservé + **test de troncature** : les signaux passés ne changent pas quand on ajoute des données futures (7 stratégies) | `test_signal_entry_next_bar_open_and_no_lookahead`, `test_signals_have_no_lookahead` |
| Horaires / heure d'été | Horodatage UTC ; règles « New York » converties avec l'heure d'été ; fermeture projet à 21:00 UTC | conservé | `test_new_york_schedule_follows_dst`, `test_flat_hour_projet` |
| 2 positions max | **Non appliqué** entre paires (une position par paire seulement) | **ajouté** : simulateur de portefeuille chronologique, 1 position par paire et 2 au total | `test_portfolio_max_two_positions` |
| Fin des données | Position encore ouverte **ignorée** (léger biais) | **corrigé** : clôturée au dernier prix (« fin ») | `test_end_of_data_position_is_closed_not_dropped` |
| Week-end / trous | Pas d'entrée si la première minute disponible est à plus de 3 h du signal ; sortie au premier prix disponible après un trou | conservé | revue du code |

## 2. Intégrité des données (sept. 2024 → août 2026, 3 paires) — `python -m forex_lab.data_check`
0 doublon, ordre chronologique respecté, 0 bougie OHLC incohérente, 0 ask < bid, 0 prix nul ; ≈ 184 000 minutes par paire
et par semestre ; trous > 30 min en semaine uniquement à Noël et au 1er janvier ; 1 à 18 sauts > 50 pips par semestre
(annonces, interventions sur le yen : réels, conservés). Les minutes sans aucune cotation ont été retirées à la préparation.

## 3. Comparaison de transactions
- **Simulateur de référence indépendant** (`forex_lab/reference.py`, code différent, calcul vectorisé) :
  **1 200 transactions réelles comparées une à une** (entrée, stop, objectif, sortie à l'heure, 3 paires, sept. 2025 →
  févr. 2026) : **0 écart** (même minute de sortie, même prix, même motif). Test automatique sur données synthétiques.
- **Placebo** : entrées au hasard → ≈ 0 pip avant coûts (t ≈ −0,5) ; la perte nette égale exactement le spread payé.
- **MetaTrader 5** : pas de comparaison directe possible ici (MT5 ne tourne pas dans l'environnement de calcul et la
  plateforme est un logiciel Windows). Comparaison possible plus tard, sans coût, si l'utilisateur exporte depuis son MT5 le
  rapport du testeur de stratégie de l'EA d'exemple « MACD Sample » (EURUSD H1) : les règles sont déjà codées (F01).
  Les écarts attendus viennent des données (ticks du broker ≠ Dukascopy) et de la lecture de la bougie en cours par l'EA.

## 4. Effet des corrections sur le lot 1 (mêmes règles, coûts réalistes + 2 positions max)
Toutes les configurations restent en ÉCHEC ; la seule positive (F01 exact, +2,0 pips/trade) devient −0,9 pip/trade.
Les coûts réalistes retirent ≈ 0,8 à 1,0 pip par trade. Détail : `results/lot_1_v3.md`.

## 5. Bugs trouvés et corrigés pendant la phase V3 (tests ajoutés)
- **Ordres enchaînés dans la même minute** : la limite « une position par paire » refusait l'ordre qui s'ouvre à la minute
  exacte où le précédent se ferme. Cela coupait de moitié les stratégies à horaires fixes (F03, version papier du fix de
  Tokyo). Corrigé (ordres programmés « chain ») ; les signaux sur bougie restent refusés dans la minute de sortie, comme un EA
  MetaTrader. F03 relancée : 2 068 trades, −3,0 pips/trade, toujours ÉCHEC. Test : `test_scheduled_reversal_in_same_minute_is_kept`.
- **Fenêtres de la version papier du fix de Tokyo** : dates décalées d'un jour. Corrigé avant toute conclusion. Test :
  `test_tokyo_paper_windows`.
Total : 15 tests automatiques, exécutés sur GitHub à chaque modification (`.github/workflows/forex-lab-tests.yml`).

## 6. Limites qui restent
- Données Dukascopy ≠ prix d'un broker de détail (spreads souvent plus larges) : d'où la commission et le stress.
- Pas de file d'attente, ni de refus d'ordre, ni de swap (sans objet : aucune position la nuit en version projet).
- Les minutes n'ont qu'un OHLC : l'ordre réel des ticks dans une minute est inconnu (stop retenu en cas de doute).
