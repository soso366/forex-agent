"""Conventions Forex : pips, conversions de devises vers la devise du compte."""
from __future__ import annotations


def split(symbol: str) -> tuple[str, str]:
    return symbol[:3], symbol[3:6]


def pip_size(symbol: str) -> float:
    return 0.01 if split(symbol)[1] == "JPY" else 0.0001


def to_pips(symbol: str, price_distance: float) -> float:
    return price_distance / pip_size(symbol)


def ccy_to_account(ccy: str, mids: dict[str, float], account: str = "EUR") -> float:
    """Combien vaut 1 unité de `ccy` en devise du compte, à partir des prix mid disponibles."""
    if ccy == account:
        return 1.0
    if account + ccy in mids:
        return 1.0 / mids[account + ccy]
    if ccy + account in mids:
        return mids[ccy + account]
    # passage par l'USD
    if ccy != "USD" and account != "USD":
        usd_to_acc = ccy_to_account("USD", mids, account)
        if "USD" + ccy in mids:
            return usd_to_acc / mids["USD" + ccy]
        if ccy + "USD" in mids:
            return usd_to_acc * mids[ccy + "USD"]
    raise KeyError(f"Impossible de convertir {ccy} en {account} avec {sorted(mids)}")


def conversion_symbols(symbols: list[str], account: str = "EUR") -> list[str]:
    """Paires supplémentaires à coter pour convertir les PnL (ex. EURUSD pour USDJPY)."""
    needed = set()
    for s in symbols:
        for c in split(s):
            if c != account:
                needed.add(f"{account}USD" if account != "USD" else None)
    needed.discard(None)
    return sorted(needed - set(symbols))


def pnl_account(symbol: str, sign: int, entry: float, exit_: float, units: float,
                mids: dict[str, float], account: str = "EUR") -> float:
    quote = split(symbol)[1]
    return sign * (exit_ - entry) * units * ccy_to_account(quote, mids, account)


def margin_account(symbol: str, units: float, leverage: float,
                   mids: dict[str, float], account: str = "EUR") -> float:
    base = split(symbol)[0]
    return units * ccy_to_account(base, mids, account) / leverage


def quote_mids(provider, cfg: dict, now) -> dict[str, float]:
    """Prix mid de toutes les paires tradées + paires de conversion, à l'instant `now`."""
    acc = cfg["account"]["currency"]
    out = {}
    for s in list(cfg["symbols"]) + conversion_symbols(cfg["symbols"], acc):
        bid, ask = provider.quote(s, now)
        out[s] = (bid + ask) / 2
    return out
