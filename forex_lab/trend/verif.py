# Vérification indépendante (code séparé, vectorisé) — rendement brut par paire, signal 12 mois.
import sys, numpy as np, pandas as pd
D = sys.argv[1]
def fred(c):
    d = pd.read_csv(f"{D}/{c}.csv"); s = pd.to_numeric(d.iloc[:,1], errors="coerce"); s.index = pd.to_datetime(d.iloc[:,0]); return s.dropna()
def ecb(c):
    d = pd.read_csv(f"{D}/ECB_{c}.csv", usecols=["TIME_PERIOD","OBS_VALUE"]); s = pd.Series(d.OBS_VALUE.values, index=pd.to_datetime(d.TIME_PERIOD)); return s.dropna()
def rate(c):
    s = fred(c); s.index = s.index.to_period("M"); return s/100
us, ez, gb, jp = rate("TB3MS"), rate("IR3TIB01EZM156N"), rate("IR3TIB01GBM156N"), rate("IR3TIB01JPM156N")
src = {"FRED": {"EURUSD": fred("DEXUSEU"), "GBPUSD": fred("DEXUSUK"), "USDJPY": fred("DEXJPUS")}}
u, g, j = ecb("USD"), ecb("GBP"), ecb("JPY")   # devises par 1 EUR
src["BCE"] = {"EURUSD": u, "GBPUSD": (u / g).dropna(), "USDJPY": (j / u).dropna()}
carry = {"EURUSD": (ez, us), "GBPUSD": (gb, us), "USDJPY": (us, jp)}
for name, px in src.items():
    for p, s in px.items():
        m = s.resample("ME").last(); m.index = m.index.to_period("M")
        sig = np.sign(m.pct_change(12))
        b, q = carry[p]; idx = m.index
        c = (b.reindex(idx).ffill() - q.reindex(idx).ffill()) / 12
        ret = (m.shift(-1) / m - 1) + c          # rendement du mois suivant, avec portage
        r = (sig * ret).shift(1).dropna()         # attribué au mois de détention
        r = r[(r.index >= pd.Period("2000-01","M")) & (r.index <= pd.Period("2023-08","M"))]
        print(name, p, len(r), "Sharpe brut 2000-2023/08 :", round(r.mean()/r.std()*np.sqrt(12), 2))
