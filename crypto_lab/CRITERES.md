# Critères de validation — robot crypto (écrits AVANT tout résultat, ne jamais les modifier après coup)

Date : 22/10/2026. Décision de l'utilisateur : robot crypto d'abord, simulation uniquement, capital de référence 150 €.

## Conditions de test (identiques pour toutes les stratégies)
- Marché : spot Binance, achat seul, paires BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT, XRP/USDT (liste fixée à l'avance).
- Données : bougies publiques Binance (data.binance.vision), 5m et 1h, déc. 2022 → sept. 2026.
- Capital 150 USDT, 2 positions maximum, mise fixe 50 USDT par position (≈ 1 % du capital perdu pour un recul de 3 %).
- Frais : 0,10 % par ordre (taux Binance standard). Test de sensibilité : +0,05 % de glissement par ordre (soit 0,30 % aller-retour).
- Durée : version d'origine (référence) et plafonds **30, 45 et 60 minutes** (sortie forcée au plafond ; sortie plus tôt autorisée par ROI, stop ou signal).
- Code des stratégies : téléchargé au commit épinglé (`candidates.yaml`), logique inchangée. Seule adaptation permise : le plafond de durée.

## Périodes
Les stratégies testées ont été publiées avant 2023 : toute la période est hors échantillon pour leur logique.
Les paramètres ont pu être retouchés plus tard par les auteurs ; on exige donc la régularité sur trois blocs :
- P1 : janv. 2023 → juin 2024
- P2 : juil. 2024 → juin 2025
- P3 : juil. 2025 → sept. 2026 (bloc le plus récent)

## Une configuration (stratégie × plafond) est ROBUSTE seulement si TOUT est vrai
1. ≥ 100 trades sur chaque bloc.
2. Résultat net positif sur **chacun** des 3 blocs, frais + glissement inclus (0,30 % aller-retour).
3. Profit factor global ≥ 1,15 avec glissement.
4. Statistique t du gain moyen par trade ≥ 2,0 sur l'ensemble (avec glissement).
5. Pas plus de 50 % du gain total venant d'une seule paire, ni d'un seul mois.
6. Drawdown maximal ≤ 20 % du capital (30 USDT).

Sinon : ÉCHEC (perdante) ou FRAGILE (positive mais pas sur tous les critères). Aucune stratégie n'est retenue par défaut.
Une stratégie ROBUSTE passe ensuite au paper trading, jamais directement à l'argent réel.

## Test de confirmation (écrit le 22/10/2026 APRÈS le lot 1, AVANT tout test sur ces nouvelles paires)
Au lot 1, seule CombinedBinHAndClucV5 est positive (FRAGILE : trop peu de trades par bloc). Le plafond de 45 min
y donne le meilleur profit factor : le choisir est une sélection après coup, donc il doit être confirmé ailleurs.

- Nouvelles paires, jamais testées : ADA, DOGE, LTC, LINK, AVAX, TRX, DOT, BCH, ATOM, ETC (/USDT). Mêmes périodes,
  mêmes frais, même mise, même code (aucun réglage modifié).
- **Confirmé** seulement si la version « plafond 45 min » de V5 sur ces 10 paires : est positive sur chacun des 3 blocs
  avec glissement, a un profit factor ≥ 1,15 et t ≥ 2. Les autres plafonds sont rapportés pour information.
- Stress supplémentaire : glissement 0,10 % par ordre (0,40 % aller-retour, frais compris) — doit rester positif au total.
- Audit de biais : `freqtrade lookahead-analysis` sur chaque stratégie testée ; tout biais détecté = REJET.
