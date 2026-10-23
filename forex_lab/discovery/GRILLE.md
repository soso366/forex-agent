# Strategy Discovery — grille d'évaluation des preuves (fixée le 23/10/2026, AVANT la recherche)

But : classer les **preuves** qu'une stratégie Forex documentée gagne de l'argent, avant d'écrire la moindre ligne de
backtest. Une stratégie n'est jamais classée sur la base de résultats optimisés ou promotionnels.

## Élimination immédiate (aucun score)
- **Doublon d'un échec** : même mécanisme qu'une ligne de `forex_lab/ECHECS.md`, de `forex_lab/candidates.yaml`
  (verdict ELIMINE) ou de `memory/REJECTED_HYPOTHESES.md`, sans « fait nouveau » documenté. Contrôle automatique par mots-clés
  + contrôle manuel (`doublon_de` renseigné dans la fiche).
- **Promotionnel** : vente d'EA / de signaux / de formation, résultats sans méthode vérifiable, « myfxbook » non audité.
- **Aucune règle reproductible** : impossible d'écrire les règles d'entrée et de sortie sans deviner.
- **Seulement des résultats optimisés** sur la période affichée (aucune période hors échantillon).

## Score de preuve (0 à 3 par critère, total sur 21)
| Critère | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| S — source | blog, forum, vidéo | publication technique / note de praticien avec méthode | document de travail académique, ou étude de praticien reconnue avec données publiques | revue à comité de lecture |
| H — hors échantillon | aucun | découpage IS/OOS par l'auteur | walk-forward / OOS long chez l'auteur | performance **après publication** mesurée (par l'auteur ou des tiers) |
| C — coûts | ignorés | mentionnés sans chiffrer | coûts estimés (spread moyen) | coûts réalistes (bid/ask réels ou spreads de broker) et résultat net publié |
| R — récence | preuves s'arrêtant avant 2010 | jusqu'à 2010-2014 | jusqu'à 2015-2019 | couvrant 2020 ou après |
| I — réplication indépendante | aucune | une réplication partielle | une réplication complète | plusieurs, dont après publication |
| F — force statistique | non chiffrée | t < 2 ou < 5 ans | t ≥ 2 sur ≥ 5 ans | t ≥ 3 ou ≥ 20 ans et plusieurs marchés |
| P — précision des règles | vagues | partielles | complètes avec paramètres | code public ou règles complètes + données |

**Seuils** : ≥ 15 = preuve solide ; 11-14 = preuve moyenne ; ≤ 10 = preuve faible (ne pas backtester en priorité).
**Pénalités** : −3 si l'auteur signale lui-même une disparition / un affaiblissement récent de l'effet ; −2 si les résultats
ne portent pas sur nos paires (EUR/USD, GBP/USD, USD/JPY) ni sur un panier qui les contient.

## Compatibilité avec le projet (indicateurs, ne change PAS le score)
- `horizon` : intrajournalier ≤ 4 h (règle actuelle du projet) / journalier / hebdomadaire / mensuel.
- `paires` : utilisable avec EUR/USD, GBP/USD, USD/JPY seules ?
- `donnees` : données gratuites suffisantes (Dukascopy, calendriers publics de la Fed / BCE / BLS, CFTC) ?
- `cout_sensibilite` : gain brut publié par trade comparé à notre coût réaliste (≈ 1 à 1,5 pip aller-retour).
Une stratégie à preuve solide mais incompatible avec la règle « ≤ 4 h » est présentée comme telle : c'est à
l'utilisateur de décider s'il assouplit la règle.
