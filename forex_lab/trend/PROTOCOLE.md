# Test D01 — suivi de tendance 12 mois (protocole pré-enregistré le 24/10/2026, AVANT tout téléchargement des données)

Décision de l'utilisateur (24/10/2026) : accepter, pour ce test seulement, des positions tenues plusieurs semaines
(la règle « ≤ 4 h, fermé avant 21:00 UTC » ne s'applique pas à D01). Simulation uniquement, aucun argent réel.
Les autres règles restent : 3 paires (EUR/USD, GBP/USD, USD/JPY), **2 positions simultanées maximum**, 0 € de dépense.

## Source (règles publiées, non modifiées)
Moskowitz, Ooi, Pedersen (2012) « Time Series Momentum », JFE ; Hurst, Ooi, Pedersen (2017). Signal = signe du rendement
des 12 derniers mois, position tenue 1 mois.

## Données (gratuites, Réserve fédérale de St. Louis — FRED)
- Cours journaliers de midi à New York : DEXUSEU (USD par EUR, depuis 1999), DEXUSUK (USD par GBP), DEXJPUS (JPY par USD).
- Taux à 3 mois, mensuels, pour le portage (intérêts reçus ou payés en gardant la position) : TB3MS (USA),
  IR3TIB01EZM156N (zone euro), IR3TIB01GBM156N (Royaume-Uni), IR3TIB01JPM156N (Japon). Valeur manquante = dernière connue.
- Prix de fin de mois = dernière cotation disponible du mois.

## Règles (figées)
1. Fin du mois m : r12 = P(m) / P(m−12) − 1 sur la paire telle que cotée (EURUSD, GBPUSD, USDJPY).
2. Sens = signe de r12 (achat si > 0, vente si < 0).
3. Limite de 2 positions (version officielle) : on garde les 2 paires au signal le plus fort,
   |r12| / volatilité annualisée des rendements journaliers des 12 derniers mois.
4. Position tenue tout le mois m+1, taille égale (chaque position = la moitié du capital, levier 1 au total).
5. Rendement d'une position achetée sur XXX/USD = variation du cours + (taux XXX − taux USD) / 12 ;
   sur USD/JPY = variation du cours + (taux USD − taux JPY) / 12 ; vente = l'opposé.

## Frais (prudents, comme chez un courtier de détail)
- Standard : 1,5 pip par aller-retour à chaque ouverture / fermeture (changement de sens ou de paire),
  + 1 % par an de marge du courtier sur les swaps pour chaque position tenue.
- Stress : 3 pips par aller-retour + 2 % par an.

## Périodes
- **Développement** : de la première position possible à août 2023 (mois de détention).
- Sous-périodes : avant 2000, 2000-2009, 2010 → août 2023.
- **Période vierge sept. 2023 → août 2024 : aucun rendement calculé ni affiché** (ses prix servent seulement de point de
  départ du calcul sur 12 mois pour les signaux suivants).
- Récent : sept. 2024 → dernier mois disponible, affiché à titre indicatif (trop court pour décider).

## Critères de réussite (tous obligatoires, version officielle 2 positions, frais standard)
- C1 : développement, Sharpe annualisé net ≥ 0,3 et t ≥ 2 (rendements mensuels).
- C2 : 2010 → août 2023, rendement moyen net > 0 (l'effet est réputé affaibli depuis 2010).
- C3 : avec les frais de stress, développement rendement moyen net > 0.
- C4 : rendement net positif sur au moins 2 des 3 sous-périodes.
PASSE → étape 2 (robot MT5 sur compte démo). Sinon ÉCHEC, ajouté à ECHECS.md.

## Informations (ne décident pas, aucun choix de réglage à partir d'elles)
Version 3 paires sans limite ; durées 1, 3 et 6 mois ; détail par paire ; part du portage dans le résultat.
Contrôle : un second calcul écrit séparément doit retrouver les mêmes chiffres.
