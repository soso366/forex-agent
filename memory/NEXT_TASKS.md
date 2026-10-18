# Prochaines tâches (file d'attente — source exécutable : `python -m orchestrator plan`)

## Piste RECHERCHE
0. **[BLOQUANT — utilisateur]** Le cycle GitHub Actions n'a pas accès aux données : secret `DATA_REPO_TOKEN` absent ou non transmis à l'étape Claude du workflow (bootstrap : « indisponibles »). Sans lui, aucun backtest.
0b. **[Quant — E003]** Dès que les données sont là : `bash orchestrator/bootstrap.sh`, `run.py count` → commit `results/signal_counts.json`, puis `run.py train` → Critic → décision. Le Critic doit aussi relire les 2 choix signalés par le Quant (IC 95 % jour rendu éliminatoire ; comptage des signaux dans un fichier séparé).
1. **[Researcher]** 1 hypothèse nouvelle possible (cycle 3 : une seule, E003). Piste suggérée par le Critic (à évaluer, pas imposée) : surréaction
   pendant les conférences de presse des banques centrales (Fed, BoJ, BCE, BoE), calendrier déclaré à l'avance ; ≈ 30
   événements/an → il faudrait de l'historique depuis ~2019 (nouvelle demande de données, distincte de l'OOS vierge).
2. **OOS vierge sept. 2023 → août 2024** : téléchargé ou en cours, mais NON LU. Verrou : `python -m orchestrator oos-gate E###`
   (ouvert seulement après Train ET Validation réussis).
3. **INTERDIT** : H3/E000, E001, E002 (et toute variante d'E003 hors protocole) sous quelque forme que ce soit.

## Piste AUTOMATISATION (indépendante)
4. Le workflow `.github/workflows/agents-cycle.yml` est prêt (voir `orchestrator/AUTOMATION.md`). Bloqué par :
   (a) secret `ANTHROPIC_API_KEY` ou `CLAUDE_CODE_OAUTH_TOKEN` à ajouter par l'utilisateur ;
   (b) accord utilisateur pour copier CE SEUL fichier sur `main` (GitHub n'exécute les tâches planifiées que depuis main).
5. Tâche planifiée Claude externe « Forex — cycle Manager » : DÉSACTIVÉE (pas d'accès au dépôt privé).

## Mise à jour cycle 4
- E003 REJECT (Train) ; E004 archivée (volume absent des CSV). Les données sont présentes en session depuis ce cycle (data/m1_2025, m1, m1_locked*). OOS vierge 2023-24 absent.
- Pour rouvrir E004 : script hors fichiers protégés extrayant le volume M1 (bid/ask) des .bi5 Train ; ≤ 8 variantes ; conditions de experiments/E004-*/precritique.md.
- Le Researcher doit privilégier des hypothèses testables avec les colonnes déjà présentes (bid/ask OHLC) ou la piste conférences banques centrales (nécessite historique).

## Mise à jour cycle 5
- E005 et E006 REJECT au Train. Researcher : éviter les filtres empilés (tester d'abord la distribution du signal pour garantir ≥150 trades) ; piste conférences banques centrales toujours bloquée par l'historique.

## Mise à jour cycle 6
- E007 et E008 REJECT au Train (intraday 4 h, 13→17 Londres). Les familles « momentum/fade de mouvement journalier » sont épuisées sur ce Train ; biais USD constant à connaître pour toute hypothèse 13-17 h.
- Researcher : explorer des familles différentes (événements calendrier avec historique long, structure inter-marchés) ; toujours compter les signaux avant R.

## Mise à jour cycle 7
- E009 REJECT au Train (inter-paires USDJPY vs facteur dollar : pas de mécanisme, équivalent à un fade d'USDJPY seul). Le Researcher n'a trouvé qu'une hypothèse : l'espace testable avec bid/ask M1 seul s'épuise. Envisager avec l'utilisateur : nouvelles données (calendrier économique, historique long, volume) pour de nouvelles familles.

## Mise à jour cycle 8
- Researcher : 0 hypothèse (fin de mois = ~18 trades au Train ; volatilité = retombe sur cassure rejetée ; macro/conférences = besoin calendrier + historique ; volume absent). BLOQUANT utilisateur : fournir calendrier économique daté + historique 3–5 ans, et/ou autoriser l'extraction du volume M1 des .bi5 (rouvre E004). Sans cela, les cycles suivants n'ont rien à tester.

## Mise à jour cycle 9
- Researcher : 0 hypothèse (vendredi après-midi ~78 signaux, fin de mois ~18 : insuffisant). Recommandation : ne pas relancer de cycle avant décision utilisateur (calendrier économique + historique 3-5 ans, ou extraction du volume M1).

## Mise à jour cycle 10
- Researcher : 0 hypothèse (3e cycle consécutif). Même blocage : calendrier économique daté + historique 3–5 ans, ou autorisation d'extraire le volume M1 des .bi5 (rouvre E004). Ne pas relancer de cycle avant décision utilisateur.

## Mise à jour cycle 11
- Researcher : 0 hypothèse (4e cycle consécutif). Même blocage utilisateur : calendrier économique + historique 3–5 ans, ou autorisation d'extraire le volume M1. Suspendre les cycles planifiés jusque-là.

## Mise à jour cycle 12
- Researcher : 0 hypothèse (5e cycle consécutif). Même blocage utilisateur ; suspendre les cycles planifiés tant que ni calendrier+historique ni extraction du volume M1 ne sont fournis.

## Mise à jour cycle 13
- Researcher : 0 hypothèse (6e cycle consécutif). Même blocage utilisateur ; suspendre les cycles planifiés (passer control.yaml en PAUSED) jusqu'à calendrier+historique ou autorisation d'extraction du volume M1.

## Mise à jour cycle 14
- Researcher : 0 hypothèse (7e cycle consécutif). Même blocage utilisateur ; passer control.yaml en PAUSED jusqu a calendrier+historique ou autorisation du volume M1.

## Mise à jour cycle 15
- Researcher : 0 hypothèse (8e cycle consécutif). Même blocage utilisateur ; passer control.yaml en PAUSED jusqu'à calendrier+historique ou autorisation du volume M1.

## Mise à jour cycle 16
- Researcher : 0 hypothèse (9e cycle consécutif). Même blocage utilisateur ; passer control.yaml en PAUSED jusqu'à calendrier+historique ou autorisation du volume M1.

## Mise à jour cycle 17
- Researcher : 0 hypothèse (10e cycle consécutif). Même blocage utilisateur ; passer control.yaml en PAUSED jusqu'à calendrier+historique ou autorisation du volume M1.
