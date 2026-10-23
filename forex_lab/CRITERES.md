# Critères — Forex Strategy Research Lab, lot 1 (écrits le 23/10/2026, AVANT tout résultat)

## Conditions identiques pour toutes les candidates
- Données : Dukascopy M1 bid + ask réelles, sept. 2024 → août 2026 (4 blocs de 6 mois : B1 sept. 24-févr. 25, B2 mars-août 25,
  B3 sept. 25-févr. 26, B4 mars-août 26). La période vierge sept. 2023 → août 2024 n'est PAS utilisée ici : elle reste réservée
  au test final d'une candidate qui passerait ces critères (et l'historique 2020-2023 en téléchargement servira de confirmation).
- Achat au prix ask, vente au prix bid : le spread réel est inclus dans chaque trade. Stress : +0,5 pip de coût par trade.
- Indicateurs calculés sur les bougies bid (comme MetaTrader), signal lu à la clôture, exécution à l'ouverture suivante.
- Stops, objectifs et sorties à heure fixe vérifiés minute par minute ; si stop et objectif tombent dans la même minute : stop d'abord.
- Une position à la fois par stratégie et par paire. Résultats en pips (les règles d'origine n'ont pas toutes de stop, donc pas de R).
- Règles et paramètres d'origine, sans aucune optimisation. Deux versions : « exact » (règles d'origine) et « projet »
  (sortie au plus tard après 4 h, entrées 00:00-20:00 UTC en semaine, tout fermé à 21:00 UTC).

## Une configuration (candidate × version) est ROBUSTE seulement si TOUT est vrai
1. ≥ 80 trades au total.
2. Gain moyen par trade positif sur au moins 3 des 4 blocs.
3. Profit factor global ≥ 1,15.
4. Statistique t du gain moyen par trade ≥ 2,5 (seuil relevé car ≈ 16 configurations sont testées) ET t ≥ 2,0 sur les résultats
   regroupés par jour (les paires et les trades d'un même jour ne sont pas indépendants).
5. Toujours positive avec +0,5 pip de coût par trade.
6. Pas plus de 60 % du gain venant d'une seule paire (stratégies multi-paires).
Sinon : ÉCHEC (négative) ou FRAGILE (positive mais incomplète). Toute ÉCHEC entre dans le registre `ECHECS.md`.

## Ce qui se passe ensuite
Une configuration ROBUSTE en version « projet » passe au test final : période vierge 2023-2024 puis historique 2020-2023,
mêmes critères, sans aucun changement de règle. Puis paper trading. Jamais d'argent réel sans l'accord de l'utilisateur.
