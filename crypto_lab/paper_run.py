"""Paper trading « en avant » (gratuit) de la stratégie retenue au lot 1.

Chaque jour : télécharge les bougies 5m publiques de Binance depuis le début du paper trading, rejoue la stratégie
(même moteur Freqtrade, même code, mêmes frais) uniquement sur des données postérieures au départ, et met à jour
le journal. Aucune clé, aucun ordre réel. Les résultats passés ne changent pas : le moteur est déterministe.
"""
import json
import shutil
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
import run_batch as rb  # noqa: E402

CFG = yaml.safe_load((LAB / "paper.yaml").read_text())
UD = Path("user_data")
API = "https://data-api.binance.vision/api/v3/klines"


def klines(symbol, tf, start_ms, end_ms):
    out, cur = [], start_ms
    while cur < end_ms:
        url = f"{API}?symbol={symbol}&interval={tf}&startTime={cur}&endTime={end_ms}&limit=1000"
        for i in range(4):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    batch = json.loads(r.read())
                break
            except Exception:
                time.sleep(2 + 3 * i)
        else:
            raise RuntimeError(f"bougies indisponibles : {symbol}")
        if not batch:
            break
        out += batch
        cur = batch[-1][0] + 1
        if len(batch) < 1000:
            break
    return out


def main():
    start = datetime.fromisoformat(CFG["depart"]).replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if now <= start:
        print("paper trading pas encore commencé")
        return
    warm = start - timedelta(days=3)                       # bougies de préchauffage des indicateurs
    end_ms = int(now.timestamp() * 1000)
    ddir = UD / "data" / json.loads(Path("exchange_choice.json").read_text())["name"]
    ddir.mkdir(parents=True, exist_ok=True)
    last_closed = None
    for pair in CFG["paires"]:
        rows = [[k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])]
                for k in klines(pair.replace("/", ""), "5m", int(warm.timestamp() * 1000), end_ms) if k[6] < end_ms]
        (ddir / f"{pair.replace('/', '_')}-5m.json").write_text(json.dumps(rows))
        if rows:
            last_closed = max(last_closed or 0, rows[-1][0])
    # stratégie au commit épinglé + variante plafond
    cand = yaml.safe_load((LAB / "candidates.yaml").read_text())
    c = next(x for x in cand["candidates"] if x["id"] == CFG["candidat"])
    repo = rb.fetch_repo(c["repo"], cand["repos"][c["repo"]], Path("ext"))
    src = repo / c["file"]
    sdir = UD / "strategies"
    sdir.mkdir(parents=True, exist_ok=True)
    code = src.read_text()
    for a, b in rb.PORT:
        code = code.replace(a, b)
    (sdir / src.name).write_text(code)
    name = f"{c['name']}_cap{CFG['plafond_min']}"
    (sdir / f"{name}.py").write_text(rb.WRAPPER.format(mod=src.stem, cls=c["name"], cap=CFG["plafond_min"]))
    ex = json.loads(Path("exchange_choice.json").read_text())
    rb.write_config(dict(ex, pair_whitelist=CFG["paires"]))
    res_dir = UD / "backtest_results"
    shutil.rmtree(res_dir, ignore_errors=True)
    res_dir.mkdir(parents=True)
    r = rb.sh(["freqtrade", "backtesting", "-c", "config_lab.json", "--userdir", str(UD), "--timerange",
               start.strftime("%Y%m%d") + "-", "--fee", str(rb.FEE), "--timeframe", "5m", "--export", "trades",
               "--cache", "none", "--strategy-list", name], log="paper_backtest.log")
    trades = []
    if r.returncode == 0:
        from freqtrade.data.btanalysis import load_backtest_data
        try:
            df = load_backtest_data(res_dir, strategy=name)
            trades = [{"paire": p, "ouverture": str(o)[:16], "fermeture": str(cl)[:16], "duree_min": int(d),
                       "resultat_pct": round(100 * float(pr), 2), "resultat_usdt": round(float(pa), 2),
                       "sortie": str(er)}
                      for p, o, cl, d, pr, pa, er in zip(df["pair"], df["open_date"], df["close_date"],
                                                         df["trade_duration"], df["profit_ratio"], df["profit_abs"],
                                                         df["exit_reason"])]
        except ValueError:
            trades = []  # aucun trade encore
    elif "No trades" not in (r.stdout + r.stderr):
        raise SystemExit("backtest du paper trading en échec (voir paper_backtest.log)")
    finis = [t for t in trades if t["sortie"] != "force_exit"]
    en_cours = [t for t in trades if t["sortie"] == "force_exit"]
    pnl = sum(t["resultat_usdt"] for t in finis)
    pnl_slip = pnl - rb.STAKE * rb.SLIP_RT * len(finis)
    jours = max((now - start).total_seconds() / 86400, 1e-9)
    gains = [t for t in finis if t["resultat_usdt"] > 0]
    etat = {
        "mis_a_jour_utc": now.strftime("%Y-%m-%d %H:%M"),
        "derniere_bougie_utc": datetime.fromtimestamp(last_closed / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M") if last_closed else None,
        "depart": CFG["depart"], "jours": round(jours, 1), "strategie": name, "paires": CFG["paires"],
        "capital_depart": rb.WALLET, "capital_actuel": round(rb.WALLET + pnl, 2),
        "capital_avec_glissement": round(rb.WALLET + pnl_slip, 2),
        "trades_termines": len(finis), "trades_en_cours": len(en_cours),
        "taux_gain_pct": round(100 * len(gains) / len(finis), 1) if finis else None,
        # même convention que les backtests : frais + glissement 0,05 %/ordre
        "gain_moyen_pct": round(sum(t["resultat_pct"] for t in finis) / len(finis) - 100 * rb.SLIP_RT, 3) if finis else None,
        "trades_par_jour": round(len(finis) / jours, 2),
        "attendu_backtest": CFG["attendu"],
    }
    pdir = LAB / "paper"
    pdir.mkdir(exist_ok=True)
    (pdir / "etat.json").write_text(json.dumps(etat, indent=1, ensure_ascii=False))
    (pdir / "trades.json").write_text(json.dumps(trades, indent=1, ensure_ascii=False))
    a = CFG["attendu"]
    lines = [f"# Paper trading — {name}", "",
             f"Départ : {CFG['depart']} · mis à jour : {etat['mis_a_jour_utc']} UTC (dernière bougie {etat['derniere_bougie_utc']}) · {etat['jours']} jours",
             "", "Simulation uniquement, aucun ordre réel. Capital 150 USDT, 2 positions max, mise 50 USDT, frais 0,10 %/ordre.", "",
             "| | Paper trading | Attendu (backtest) |", "|---|---|---|",
             f"| Capital | {etat['capital_actuel']} USDT (avec glissement : {etat['capital_avec_glissement']}) | — |",
             f"| Trades terminés | {len(finis)} ({etat['trades_par_jour']} / jour) | ≈ {a['trades_par_jour']} / jour |",
             f"| Taux de gain | {etat['taux_gain_pct'] if finis else '—'} % | ≈ {a['taux_gain_pct']} % |",
             f"| Gain moyen par trade | {etat['gain_moyen_pct'] if finis else '—'} % | ≈ {a['gain_moyen_pct']} % |",
             f"| Positions ouvertes | {len(en_cours)} | — |", "",
             "## Journal", "", "| Paire | Ouverture (UTC) | Fermeture (UTC) | Durée | Résultat | USDT | Sortie |", "|---|---|---|---|---|---|---|"]
    for t in sorted(trades, key=lambda x: x["ouverture"], reverse=True):
        sortie = "en cours" if t["sortie"] == "force_exit" else t["sortie"]
        lines.append(f"| {t['paire']} | {t['ouverture']} | {t['fermeture'] if sortie != 'en cours' else '—'} | {t['duree_min']} min | "
                     f"{t['resultat_pct']} % | {t['resultat_usdt']} | {sortie} |")
    if not trades:
        lines.append("| — | aucun trade pour l'instant | | | | | |")
    (pdir / "JOURNAL.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:14]))


if __name__ == "__main__":
    main()
