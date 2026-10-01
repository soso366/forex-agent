# META-SKILLS de l'agent Forex

Ce sont des outils de contrôle de la réflexion, **pas des stratégies de trading**. Ils ne changent automatiquement
aucune règle, aucune taille de position, aucune stratégie. Toute erreur dans ces modules est ignorée par le cycle :
elle ne peut ni bloquer ni modifier une décision. Vérifié : rejeu mars → août 2026 identique au trade près
(148 trades, −1,97 €) avec et sans les meta-skills.

## 1. Revue adversariale (`forex_agent/meta/adversarial.py`)
Pour chaque candidat qualifié, le critique répond à quatre questions, à partir des données uniquement :

| Question | Ce qui est vérifié |
|---|---|
| Meilleure raison d'être faux | l'objection la plus grave parmi celles ci-dessous |
| Contexte contradictoire | tendance H1/M15 opposée · niveau opposé avant 1 R · achat en premium / vente en discount · annonce proche · fin de fenêtre de trading · confirmations optionnelles absentes |
| Risques cachés | verdict de la stratégie en recherche V4 (`knowledge/strategy_evidence.yaml`) · cible > amplitude typique de 30 min (≈ 2,3 ATR M5, mesuré) · volatilité anormale · spread > 10 % du risque · espérance négative dans le journal paper |
| Invalidation observable | clôture M5 au-delà du stop · clôture M15 au-delà du niveau protégé · bascule du régime |

Sortie : journal du cycle (`market_snapshots.meta.adversarial_review`) et JSON transmis au LLM s'il est activé.
**Ne bloque rien.**

## 2. Audit d'exposition / corrélation (`forex_agent/meta/exposure.py`)
Avant une deuxième position simultanée : exposition nette par devise (en € de risque), devises communes et sens,
corrélation des rendements M5 sur 5 jours et corrélation des P&L (corrélation × sens des deux positions),
annonces des 2 prochaines heures sur les devises exposées, risque brut et risque effectif
(√(r₁² + r₂² + 2ρ r₁ r₂)). **Le Risk Manager garde le dernier mot** : sa règle existante « même devise, même sens »
reste la seule qui bloque. Remarque : nos 3 paires contiennent toutes l'USD ; en 12 mois de backtest V2,
aucune position simultanée n'a été ouverte.

## 3. Audit du journal (`forex_agent/meta/journal_audit.py`, commande `journal-audit`)
Produit automatiquement à la fin de chaque backtest (fichiers `journal_audit.md` / `.json` dans les résultats),
ou à la demande sur le journal paper. Mesure : espérance, win rate, gain / perte moyens et PF par stratégie,
paire, heure, séance, jour de semaine et type de sortie ; durée des gagnants / perdants ; MFE / MAE ;
gagnants devenus perdants ; sorties de gestion suivies d'un mouvement favorable (prix réels après la sortie) ;
séries de pertes ; contextes perdants répétés ; corrélations cachées entre trades.

**Règle absolue : une observation ne devient JAMAIS une règle automatiquement.**
Observation → hypothèse → backtest → validation → OOS → éventuellement intégration.
Moins de 30 trades : « échantillon insuffisant, ne rien conclure ».

## 4. Auto-critique (processus, pour toute hypothèse importante)
Gabarit à remplir avant d'intégrer quoi que ce soit :

- **RESEARCHER** — l'argument en faveur : mécanisme de marché, source, pourquoi à 5–30 min.
- **CRITIC** — tentative de réfutation : placebo (même règle ailleurs / à d'autres heures), sens inverse (test du
  miroir), coûts réalistes, concentration (quelques jours, une paire, un trimestre), nombre de variantes testées,
  fuite d'information entre périodes.
- **DATA** — tranche, selon des critères écrits et commités **avant** de regarder le test final.
- Verdict : REJECT / RETEST / KEEP FOR VALIDATION, puis PASS / FAIL / INCONCLUSIVE sur l'OOS.

Ne jamais défendre une ancienne idée uniquement parce qu'on l'a proposée. Exemple appliqué : H3 (fix de Londres),
critères PASS verrouillés le 1er octobre 2026 avant lecture des données 2024-2025.
