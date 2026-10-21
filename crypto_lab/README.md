# Strategy Research Lab — robot crypto (simulation uniquement)

Branche `research-crypto`, séparée du robot Forex (`main`, `multi-agent-research`). Aucun ordre réel, aucune clé d'exchange.

- `candidates.yaml` : les 10 candidats GitHub analysés (commit épinglé, licence, verdict TEST / RÉFÉRENCE / ÉCARTÉ).
- `CRITERES.md` : critères de validation écrits avant tout résultat (ne jamais les modifier après coup).
- `fetch_data.py` : bougies publiques Binance (data.binance.vision) au format Freqtrade.
- `pick_exchange.py` : liste des marchés accessible sans clé (exigée par Freqtrade même en backtest).
- `run_batch.py` : télécharge les stratégies au commit épinglé, crée les variantes 30/45/60 min, backtest, verdict.
- `results/lot_N.md` : tableau des résultats ; `results/lot_N.json` : détail (par bloc, par paire).

Lancement : tout changement poussé dans `crypto_lab/` sur cette branche relance le lot 1 ; sinon
Actions → « Crypto Lab — backtests » → Run workflow (numéro du lot). Les stratégies externes (GPL-3.0) ne sont
jamais copiées dans ce dépôt : elles sont téléchargées au moment du test.
