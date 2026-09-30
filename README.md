# Agent de trading Forex autonome — V1 (paper trading)

> **Déploiement cloud sans code : voir [DEPLOIEMENT.md](DEPLOIEMENT.md).**

Capital de référence 50 €, un cycle complet toutes les 5 minutes, scalping / intraday
(30 minutes maximum par position), 2 positions simultanées maximum, Risk Manager strict.
**Aucun argent réel, aucun ordre envoyé à un broker.**

## Démarrer

```bash
pip install -r requirements.txt          # pandas, numpy, PyYAML (versions figées) ; LLM : requirements-llm.txt
python -m unittest discover -s tests     # 46 tests : risque, broker, look-ahead, structure, liquidité, horaires, news, LLM, Dukascopy, pipeline cloud, cycle
python -m forex_agent replay --days 5 --fresh   # rejoue 5 jours de cycles (données synthétiques)
python -m forex_agent report             # bilan du journal
```

Faire tourner l'agent en continu (au choix) :

```bash
python -m forex_agent loop               # boucle intégrée : 10:00:15, 10:05:15, 10:10:15…
# ou cron : voir deploy/cron.example     # ou systemd : deploy/forex-agent.service
```

## Le cycle (forex_agent/cycle.py)

```
SCHEDULER (5 min)
 → rejeu M1 depuis le dernier cycle : SL / TP / fermeture à 30 min   (broker/paper.py)
 → marché H1, M15, M5, M1 pour chaque paire                            (data/providers.py)
 → contexte + régime : TREND_UP/DOWN, RANGE, CHOP, DEAD, VOLATILE      (analysis/market.py)
 → gestion des positions : HOLD / MOVE STOP / TAKE PROFIT / CLOSE      (positions.py)
 → régime → stratégies autorisées → setups notés sur 8                 (brain/router.py, strategies/)
 → (optionnel) Claude relit les candidats, borné                       (brain/llm.py)
 → Risk Manager : taille, risque, exposition, corrélation, marge       (risk/manager.py)
 → exécution paper → journal SQLite + JSONL                            (journal.py)
```

## Fichiers à connaître

| Fichier | Rôle |
|---|---|
| `config/settings.yaml` | tous les paramètres (capital, paires, timeframes, risque, 30 min, sessions…) |
| `prompts/agent_system.md` | prompt permanent de l'agent (empreinte notée à chaque cycle) |
| `knowledge/playbook.md` | règles exactes de chaque stratégie, avec leur source ; documents dans `knowledge/sources/` |
| `data/journal.sqlite` | compte, trades, événements de position, cycles, snapshots par paire, idées |
| `data/cycles.jsonl` | le même journal, une ligne lisible par cycle |
| `data/KILL_SWITCH` | si ce fichier existe : plus aucune nouvelle position (créé auto à −20 %) |

## Rejeu sur vraies données Dukascopy (V2 inchangée)

```bash
python -m forex_agent data-download      # EURUSD, GBPUSD, USDJPY — 6 derniers mois civils complets, BID + ASK M1
python -m forex_agent data-validate      # relit les CSV exactement comme le rejeu
python -m forex_agent backtest           # rejoue TOUTE la période, journal séparé, rapport complet
```

- Période par défaut fixée avant tout résultat : les 6 derniers mois complets (`--start/--end` pour élargir).
- Téléchargement reprenable : relancer la même commande ne récupère que les fichiers manquants (cache `data/dukascopy_raw/`).
- Minutes sans cotation (volume 0 des deux côtés) retirées ; minutes incohérentes comptées et exclues, jamais corrigées ;
  arrêt si > 1 % de bougies incohérentes (format mal lu). Rapport qualité : `data/m1/quality_report.json`.
- Résultats : `data/backtest/report.md`, `data/backtest/trades.csv`, `data/backtest/journal.sqlite`.
- Le backtest n'utilise pas le journal paper (`data/journal.sqlite`) et ne modifie aucun paramètre.

## Sources de données (`data.provider`)

- `synthetic` : marché simulé à régimes, pour tester la mécanique. **Ses résultats ne disent rien de la rentabilité.**
- `csv` : M1 bid/ask historiques (ex. Dukascopy) dans `data/m1/<SYMBOL>.csv`, colonnes
  `time,bid_open,bid_high,bid_low,bid_close,ask_open,ask_high,ask_low,ask_close` (UTC, ouverture de bougie).
- `oanda` : prix temps réel en lecture seule (compte démo, `OANDA_TOKEN`). Non testé ici faute de réseau.

## Ajouter une stratégie

identifier → formaliser dans `knowledge/playbook.md` → coder `forex_agent/strategies/<nom>.py`
(fonction `scan(ctx, direction, cfg)`, conditions essentielles + optionnelles) → l'ajouter à `REGIME_MATRIX` → rejouer → changer son statut.
