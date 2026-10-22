"""Choisit une configuration d'exchange dont la liste des marchés est accessible depuis le serveur GitHub (sans clé).

Freqtrade charge la liste des marchés au démarrage, même en backtest. L'API principale de Binance refuse les serveurs
américains de GitHub : on essaie d'abord le miroir public de données de Binance, puis Kraken en secours.
Écrit exchange_choice.json (bloc « exchange » de la config Freqtrade).
"""
import json
import sys

import ccxt

PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
MIRROR = "https://data-api.binance.vision/api/v3"
TRIES = [
    ("binance", {"urls": {"api": {"public": MIRROR}}, "options": {"fetchMarkets": {"types": ["spot"]}}}),
    ("binance", {"urls": {"api": {"public": MIRROR}}, "options": {"fetchMarkets": ["spot"]}}),
    ("binance", {}),
    ("kraken", {}),
]

for name, extra in TRIES:
    try:
        ex = getattr(ccxt, name)(extra)
        mk = ex.load_markets()
        ok = [p for p in PAIRS if p in mk]
        if len(ok) < 2:
            raise RuntimeError(f"paires absentes : {ok}")
        choice = {"name": name, "key": "", "secret": "", "pair_whitelist": ok, "pair_blacklist": [],
                  "ccxt_config": extra, "ccxt_async_config": extra}
        json.dump(choice, open("exchange_choice.json", "w"), indent=1)
        json.dump(sorted(k for k, v in mk.items() if v.get("spot") and v.get("active", True)), open("markets.json", "w"))
        print(f"exchange retenu : {name} {extra or ''} — paires {ok}")
        sys.exit(0)
    except Exception as e:  # on passe à l'essai suivant
        print(f"échec {name} {extra}: {str(e)[:200]}")
print("aucun exchange accessible")
sys.exit(1)
