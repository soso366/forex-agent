"""Comptes consultés (25/10/2026), recopiés tels que publiés. Aucune donnée inventée.

Niveaux de confiance :
  A = historique trade par trade exporté et analysé ; B = page publique MQL5 lue en détail ;
  C = ligne de liste MQL5 (paires et type de compte non vérifiés) ; D = liste cTrader / Myfxbook (rendement et ancienneté seulement) ;
  H = performance HYPOTHÉTIQUE (Collective2 l'indique pour toutes ses stratégies).
"""

# C — lignes des listes MQL5 (semaines ≥ 52 et PF ≥ 1,25), pages lues : MT4 4-6, MT5 5-6.
# (nom, id, croissance %, drawdown %, semaines, trades, PF)
MQL5_LIST = [
    ("GrattMarMic", 2393538, 242, 13, 64, 3143, 2.40), ("Hari Ke 7", 2371938, 217, 15, 58, 364, 2.48),
    ("NS eP v3 49109488", 1412455, 176, 35, 244, 2085, 1.92), ("Pension", 2369942, 178, 26, 55, 4398, 1.41),
    ("SEA South East EA", 1496203, 114, 54, 239, 2531, 2.54), ("Commodity Accumulation Plan", 2270674, 389, 20, 506, 8499, 1.53),
    ("Bonus 2026", 2332586, 246, 34, 56, 162, 2.81), ("ScalpingAlgo", 2371939, 174, 24, 60, 443, 3.20),
    ("VNB SS650 Ver3 Safe Mode", 2326210, 174, 26, 74, 241, 2.95), ("MG", 1949522, 247, 37, 237, 2783, 2.40),
    ("Nanacuanglory GBP Hedgefund24", 2233959, 404, 36, 137, 1476, 1.46), ("Black Mountain HR", 1861383, 162, 36, 193, 2460, 2.26),
    ("EURUSD121", 2341798, 475, 38, 86, 1174, 2.07), ("Balanced Blend Of EAs", 1724716, 406, 36, 290, 8700, 1.97),
    ("Five Strategy", 2333519, 160, 16, 62, 776, 1.28), ("Gentleman", 2317915, 160, 39, 69, 479, 1.40),
    ("Wong1", 2301965, 243, 48, 81, 2590, 1.64), ("EA Happy Japanese Market FM", 2295123, 387, 23, 113, 258, 2.47),
    ("Barbarkill", 2281956, 163, 43, 143, 1034, 1.65), ("Bunker Scrooge", 2254589, 289, 36, 111, 502, 2.71),
    ("Diver", 2385070, 156, 32, 108, 153, 3.41), ("Digital Pride medium risk", 2326563, 151, 40, 99, 337, 1.67),
    ("Boring Pips MEDIUM RISK", 1801317, 993, 54, 211, 1207, 1.36), ("Blcx138", 2307358, 147, 39, 83, 658, 1.54),
    ("Vionix", 2340796, 148, 36, 52, 175, 2.69), ("Algo Mind Moderate", 2306648, 144, 16, 77, 659, 1.49),
    ("STNDLAG", 2286538, 145, 34, 186, 12119, 1.35), ("Family Safe Trading 1", 1905292, 238, 49, 205, 14405, 1.30),
    ("Dudu Jolin", 2351357, 142, 15, 96, 1065, 1.47), ("Wisdom Trading", 2361095, 390, 29, 120, 741, 1.44),
    ("Cradle", 1750952, 142, 31, 232, 5150, 2.56), ("DARK HOLE AZ v1 EU", 2311566, 172, 46, 90, 2559, 1.98),
    ("PAI Unique Mode No Limits with AI Filter", 1919885, 348, 18, 377, 6757, 1.50), ("MinorForce MT4", 2193150, 195, 48, 143, 2035, 1.67),
    ("Steady Day Trading", 2377645, 235, 49, 81, 673, 1.33), ("Blue Agressive CFDs Fiat FIC04", 2031876, 319, 14, 203, 4283, 1.43),
    ("No 11 ACY Index 3773", 2318345, 131, 40, 68, 1897, 2.15), ("Bull Zone", 2195079, 472, 52, 193, 6102, 1.32),
    ("Premium Investment 1", 938930, 2026, 51, 298, 2007, 4.93), ("Forex Winner", 2197653, 246, 50, 178, 2388, 2.19),
    ("Stone Bridge", 1436314, 133, 43, 241, 2693, 1.54), ("Steady Long term", 2373736, 121, 16, 168, 1979, 1.58),
    ("Gold Digger TrailStop", 2324426, 425, 45, 64, 120, 4.92), ("NebulaEA", 2332163, 269, 8, 64, 954, 2.41),
    ("EU Zone Arsenal", 2385553, 122, 9, 98, 933, 1.72), ("Litchfield VHR", 2261554, 116, 40, 110, 2115, 2.22),
    ("Web57", 1847469, 110, 22, 194, 5844, 1.42), ("QuantumStar", 2332164, 234, 9, 75, 732, 2.08),
    ("R Factor Neural Network 2", 1911819, 107, 25, 204, 1120, 1.43), ("FX2 Leo2026", 2387965, 108, 23, 63, 377, 1.86),
    ("Interstellar", 2303521, 465, 53, 229, 4028, 1.78), ("Irenyun", 2334125, 257, 51, 60, 3907, 1.30),
    ("Vtradeforyousafe", 2319321, 108, 41, 81, 1745, 1.26), ("Excellent", 2238626, 103, 37, 155, 5544, 1.43),
    ("Pippy McUSAFace", 2031936, 253, 35, 165, 2783, 2.33), ("Temanggung", 1771343, 141, 25, 201, 704, 3.02),
    ("Michael wu", 2230586, 119, 37, 127, 422, 2.23), ("PeacockFeather GBPUSD", 2286356, 244, 28, 89, 444, 2.56),
    ("KISS", 2327061, 114, 37, 58, 1115, 1.56), ("Safe Gold Trading", 2247437, 151, 47, 135, 1085, 1.27),
    ("Rbb robo 11", 2298464, 250, 51, 106, 243, 2.58), ("Night Hawk", 539949, 1067, 55, 405, 4428, 1.82),
    ("MOMANTIC PRO 30000", 2350881, 332, 29, 90, 3338, 1.86), ("SAFEPIPS", 2337747, 142, 34, 58, 184, 3.17),
    ("Rbb robo 5", 2298456, 258, 51, 106, 248, 2.60), ("GPI IP1", 2093286, 114, 30, 156, 7684, 1.48),
    ("Dudu Aircraft Carrier", 2197770, 2002, 57, 144, 2009, 1.39), ("Dunia Maya MT4", 2333730, 109, 30, 60, 518, 1.89),
    ("Visent01", 2237832, 107, 42, 173, 5164, 1.36), ("UnicornFx GSS 60", 2236796, 103, 41, 148, 4815, 1.59),
    ("HassTrader Relax", 2292609, 103, 18, 86, 918, 1.76), ("I288 The present for mother", 2362229, 272, 35, 258, 12661, 1.36),
    ("MaiCapitalAnts", 2361967, 690, 51, 111, 1427, 1.31), ("Prado Pro USDJPY", 2310627, 137, 25, 74, 102, 1.53),
    ("Manual Fix Risk Trades", 2278523, 123, 33, 95, 394, 1.32), ("OneShot Only Strategy", 2378888, 100, 25, 74, 626, 1.33),
    ("Copy Athx ST", 2311870, 272, 30, 79, 2790, 1.56), ("Bitcoin Scalper BTC", 2294444, 96, 17, 90, 249, 1.38),
    ("Jefe De Oro", 2392010, 265, 34, 104, 938, 1.25), ("ConnectGain BR Moderado", 2376652, 95, 14, 55, 1355, 1.55),
    ("Nord Way", 2304149, 153, 49, 224, 1909, 1.31), ("US 500 Growth", 2287270, 327, 52, 100, 831, 2.18),
    ("Alazaizeh Investment", 2263922, 228, 36, 147, 3746, 1.55), ("Copy RangelFX", 2326342, 89, 32, 62, 1465, 1.47),
    ("Golden Stability Growth", 2270349, 272, 42, 105, 1579, 1.30), ("A D U L T FRX", 2379785, 184, 50, 86, 352, 1.74),
    ("Harmonizer Mid Risk PAMM", 2388397, 191, 21, 100, 1135, 1.97), ("Eternal Engine Low", 2220467, 223, 31, 174, 4140, 1.52),
    ("Apex EA Selective", 2256697, 73, 19, 110, 298, 1.35), ("Couple", 2312683, 72, 25, 74, 431, 1.57),
    ("One Man Army Double Shot", 2338672, 192, 15, 55, 542, 2.13), ("HYPER GROWTH X", 2355321, 70, 24, 126, 274, 1.80),
    ("US500 AndyCFD", 2364634, 71, 17, 73, 4434, 1.69), ("TradeXpert Vantage 6320", 2389970, 471, 51, 55, 2269, 1.26),
    ("Quantum King", 2333407, 397, 29, 61, 560, 2.29), ("QuantFleet USDJPY MT5", 2302040, 69, 18, 80, 1205, 1.31),
]

# D — cTrader Copy (page /copy/symbols/eurusd) : nom, symbole principal, ROI %, ancienneté. Aucun lien, drawdown ni nombre de trades publié.
CTRADER = [
    ("Camel", "XAUUSD", 944, "2 mois"), ("HoloForex", "XAUUSD", 36607, "5 mois"), ("The Power of Discipline", "XAUUSD", 119463, "7 mois"),
    ("WriggleX5", "XAUUSD", 14915, "7 mois"), ("iloveyou", "XAUUSD", 10286, "11 mois"), ("JET", "XAUUSD", 570, "3 mois"),
    ("The Moon", "XAUUSD", 20619, "3 mois"), ("ProMax", "XAUUSD", 9024, "7 mois"), ("GOLD ORBIT", "XAUUSD", 1040, "6 mois"),
    ("GOLD PLUTO", "XAUUSD", 649, "6 mois"), ("GOLD MARS", "XAUUSD", 466, "6 mois"), ("iloveyou golobal", "XAUUSD", 12486, "3 mois"),
    ("BlackSignal", "XAUUSD", 374, "7 mois"), ("Empire Trades", "EURUSD", 717, "3 ans"), ("PainGain cTrader", "AUDCAD", 1322, "3 ans"),
    ("DAX Daytrading Plus IR", "DE40", 666, "1 an"), ("ElWCap26", "DE40", -98, "1 jour"), ("Defensive AI", "GBPUSD", 78, "7 mois"),
    ("SMART TRADER OM", "XAUUSD", 422, "1 an"), ("Rostova", "XAUUSD", 53, "1 an"),
]

# D — Myfxbook /systems (page lisible sans liens) : nom, gain %, drawdown %.
MYFXBOOK = [
    ("GOLDEN WINNER PRO", 1341653.10, 7.89), ("AGI EA V.1.1_REAL ACCOUNT 1", 511093.69, 5.74), ("IL BOSS DEL TRADING SCALPER", 303704.95, 22.60),
    ("swqi-2025", 299519.41, 46.20), ("Dr Javi 9", 175235.84, 44.84), ("Mt4-70034869", 136374.02, 49.77),
    ("100K Cent Scalper XAU", 81362.08, 43.87), ("CR7EA-VIP SAFE SETTING", 79623.34, 0.25), ("VanSocial", 65966.65, 11.59),
    ("CR7EA VIP SAFE SETTING", 65662.11, 1.28), ("CheckMate", 65349.51, 24.71), ("AutoX", 52773.90, 39.50),
    ("makariostrading(.)com", 43507.57, 1.14), ("IC Markets Live", 30275.67, 9.16), ("AutoX Pro", 28295.63, 6.24),
]

# H — Collective2 leaderboard : toutes les performances sont HYPOTHÉTIQUES selon le site.
# (nom, id, instruments, trades, ancienneté, rendement annuel %, drawdown max %)
COLLECTIVE2 = [
    ("Easy Value", 132169961, "Actions", 16, "5 ans", 22.5, 31.8), ("ares", 131145247, "Futures", 2, "6 ans", 32.4, 14.1),
    ("SQT Stocks Long Short Portfolio", 152043424, "Actions", 1, "1 an", 27.3, 7.6), ("Quant AI SP500", 152974419, "Actions", 1, "1 an", 50.4, 7.5),
    ("SQT Stocks Long Portfolio 2x", 153081578, "Actions", 1, "1 an", 50.9, 19.2), ("Sparc", 152701320, "Actions, Futures", 4, "1 an", 63.0, 22.4),
    ("Orange Cat Management", 152221526, "Actions, Options", 1, "1 an", 23.8, 5.7), ("Calicut Commodities", 146455121, "Actions, Futures", 10, "2 ans", 57.5, 29.7),
    ("AELong", 144585915, "Actions", 5, "3 ans", 24.4, 16.2), ("Adaptive Investments", 148705494, "Actions", 7, "2 ans", 80.0, 33.1),
    ("ETF Timer", 30415311, "Actions", 19, "18 ans", 15.7, 43.9), ("WS Value Investing", 144168570, "Actions", 21, "3 ans", 31.1, 35.5),
    ("EDGE - T4", 146649042, "Actions", 2, "2 ans", 22.7, 13.4), ("The Dragon's Prodigy", 152169281, "Actions, Options, Futures", 4, "1 an", 45.8, 11.2),
    ("Fearless Value", 114146885, "Actions, Options", 41, "9 ans", 50.4, 65.2), ("UnicornIndex", 129575948, "Actions", 47, "6 ans", 39.3, 77.8),
    ("SmartFutures", 132148218, "Futures", 9, "5 ans", 24.4, 25.9), ("AIB STOCKS and FUT", 150377786, "Futures", 24, "1 an", 120.3, 46.0),
    ("FOREX VIX-3", 134962085, "Forex (panier, EUR/USD inclus)", 275, "5 ans", 14.9, 23.8), ("Long Horizon", 143011111, "Actions", 20, "3 ans", 38.2, 44.7),
    ("extreme-os", 13202557, "Actions", 28, "21 ans", 21.6, 61.1), ("Evolutionary Trading", 146261882, "Actions", 7, "2 ans", 27.7, 23.4),
    ("ares P2", 149476882, "Futures", 2, "2 ans", 16.1, 13.0), ("Sage Volatility Margin", 102427283, "Actions, Options", 17, "10 ans", 20.6, 34.9),
    ("DT LS Mix", 150759166, "Futures", 15, "1 an", 23.4, 26.4), ("OPN Ind 8868", 151325077, "Actions, Futures", 2, "1 an", 22.4, 12.1),
    ("BRIX Opportunity", 140808945, "Actions", 11, "4 ans", 23.4, 25.2), ("Growth Investment Stateg", 150004796, "Actions", 22, "1 an", 106.3, 49.4),
    ("EP-Space", 149244504, "Actions", 23, "2 ans", 56.7, 52.0), ("AI INVESTOR AGGRESSIVE", 152305234, "Futures", 5, "1 an", 35.8, 15.2),
    ("Solid Companies", 148311109, "Actions", 18, "2 ans", 36.2, 34.8), ("AI INVESTOR ACCELERATED", 152305186, "Futures", 2, "1 an", 29.4, 11.7),
    ("US Alpha Equity Focus", 141710744, "Actions, Options", 44, "4 ans", 89.6, 37.0), ("US Stock Momentum", 151894080, "Actions, Options", 18, "1 an", 80.4, 39.2),
    ("LS ACTIVE 2 HALF", 151330723, "Futures", 2, "1 an", 61.1, 17.4),
]
