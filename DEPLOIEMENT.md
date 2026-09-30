# Déployer dans le cloud — guide sans code

Objectif de cette étape : obtenir le **premier vrai backtest** de la V2 (inchangée) sur les données
Dukascopy des 6 derniers mois civils complets, sans rien lancer sur ton ordinateur.
Mode **paper uniquement** : aucun broker, aucun argent réel.

Le cloud utilisé est **GitHub Actions** : gratuit, accès à Internet, et un simple bouton pour tout relancer.

---

## Ce que tu as à faire (≈ 10 minutes, une seule fois)

1. **Créer un compte GitHub** (gratuit) sur github.com, si tu n'en as pas.
2. **Créer un dépôt vide et privé** : bouton « New repository », nom `forex-agent`, cocher **Private**,
   ne rien ajouter d'autre (pas de README), puis « Create repository ».
3. **Connecter GitHub à Claude** (paramètres de l'app Claude → Connecteurs → GitHub) et autoriser
   l'accès au dépôt `forex-agent`.
4. **Me donner le nom du dépôt**, par exemple `ton-pseudo/forex-agent`.

C'est tout. Ensuite, je m'occupe de la partie technique :

- j'envoie le projet dans ton dépôt ;
- cet envoi **déclenche automatiquement** le téléchargement Dukascopy, la validation et le backtest ;
- quand c'est fini (environ 1 à 2 heures), je récupère `report.md`, `trades.csv` et `quality_report.json`
  et je te les donne ici.

---

## Où voir les choses toi-même (facultatif)

- **Avancement** : onglet **Actions** du dépôt → « Backtest V2 (Dukascopy) ». Le journal s'affiche en direct,
  jour simulé par jour simulé.
- **Résultats** : branche **results**, dossier **latest/** : `report.md`, `trades.csv`, `quality_report.json`,
  `pipeline.log` (tout le journal d'exécution), `STATUS.txt` (OK ou ÉCHEC, et à quelle étape).
  Chaque lancement est aussi archivé dans `runs/<date>/`.
- **Relancer** : onglet Actions → « Backtest V2 (Dukascopy) » → bouton **Run workflow**.
  Les champs début / fin peuvent rester vides (= 6 derniers mois complets).

---

## Si quelque chose s'interrompt

Rien n'est perdu :
- les fichiers Dukascopy déjà téléchargés sont gardés ; un nouveau lancement ne récupère que ce qui manque ;
- un backtest coupé en route **reprend là où il s'était arrêté**, à condition que le code, les paramètres
  et les données soient strictement identiques (sinon il recommence proprement depuis le début) ;
- un échec n'est jamais masqué : `STATUS.txt` indique l'étape en cause, `pipeline.log` donne le détail.

Il suffit de relancer avec **Run workflow**.

---

## Ce qui tourne exactement

Une seule commande : `python -m forex_agent pipeline`
1. téléchargement Dukascopy M1 BID + ASK (EURUSD, GBPUSD, USDJPY), 3 essais si le réseau coupe ;
2. validation des données (rapport `quality_report.json`) ;
3. backtest de la V2 : 6 stratégies, 50 € simulés, 2 positions max, 30 min max, risque identique,
   paramètres identiques ;
4. copie des résultats dans `results/`.

Avant ça, les 48 tests automatiques sont relancés : si le code a été abîmé, rien ne tourne.

**Coût** : gratuit. Un dépôt privé dispose de 2 000 minutes de calcul par mois ; un backtest en prend
environ 60 à 120.

**Limite connue** : Dukascopy peut ralentir ou refuser certains serveurs cloud. Dans ce cas, le
pipeline réessaie puis s'arrête avec un message clair ; on choisira alors une autre solution.

---

## Plus tard seulement : le scheduler 24/7

À ne faire **qu'après validation des résultats**. GitHub Actions ne convient pas pour tourner en continu.
Il faudra alors :
- un petit serveur toujours allumé (quelques euros par mois), avec Docker ;
- un **compte démo OANDA** gratuit, pour lire les prix en temps réel (lecture seule, aucun ordre) ;
- la commande `docker compose --profile later up -d scheduler` (fichiers déjà prêts : `Dockerfile`,
  `docker-compose.yml`, `.env.example`).

Par sécurité, le scheduler **refuse de démarrer** sur le marché simulé : sans vrais prix, il ne tourne pas.
