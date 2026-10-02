# Faire tourner les agents automatiquement (GitHub Actions)

Le Manager et ses agents peuvent tourner **tout seuls, sur les serveurs de GitHub**, toutes les 6 heures.
Vous n'avez rien à lancer sur votre ordinateur. Tout est prêt dans le fichier
`.github/workflows/agents-cycle.yml`. Il manque seulement **deux choses que vous seul pouvez faire**.

## 1. Ajouter la clé Anthropic (une seule fois)

1. Allez sur **console.anthropic.com** → menu **API Keys** → **Create Key**. Copiez la clé (elle commence par `sk-ant-`).
2. Allez sur **GitHub** → dépôt **soso366/forex-agent** → onglet **Settings** (Paramètres)
   → à gauche **Secrets and variables** → **Actions** → bouton vert **New repository secret**.
3. Name (nom) : `ANTHROPIC_API_KEY` — Secret (valeur) : collez la clé. Cliquez **Add secret**.

Alternative (si vous avez un abonnement Claude Pro/Max) : un secret nommé `CLAUDE_CODE_OAUTH_TOKEN`
à la place. Un seul des deux suffit. Si aucun n'est présent, le cycle s'arrête avec un message clair.

## 2. Donner votre accord pour copier UN fichier sur `main`

GitHub n'exécute les tâches automatiques (toutes les 6 h) **que si le fichier est sur la branche principale `main`**.
Le bouton de lancement manuel n'apparaît lui aussi qu'à cette condition.

- On copie **uniquement** `.github/workflows/agents-cycle.yml` sur `main`.
- **Aucun code de trading**, aucune stratégie, aucun réglage de risque ne change sur `main`.
- Les agents continuent de travailler uniquement sur la branche `multi-agent-research` ; ils ne poussent jamais sur `main`.

Dites simplement à Claude : « J'accepte de copier le workflow agents-cycle sur main ».

## 3. Vérifier que ça marche

GitHub → dépôt → onglet **Actions** → à gauche **« Agents — cycle Manager »** → bouton **Run workflow** → **Run workflow**.
Après quelques minutes, cliquez sur l'exécution : un résumé indique si le cycle a tourné, s'il est en pause,
ou s'il manque la clé. Le rapport du cycle apparaît dans `reports/` sur la branche `multi-agent-research`.

## 4. Arrêter

- **Pause** : dans le fichier `orchestrator/control.yaml` (branche `multi-agent-research`), remplacez
  `mode: RUNNING` par `mode: PAUSED` (bouton crayon sur GitHub). Les cycles suivants ne feront rien.
- **Arrêt complet** : onglet **Actions** → « Agents — cycle Manager » → menu **…** → **Disable workflow**.

## Coût

Chaque cycle utilise l'API Claude, **facturée sur votre compte Anthropic** (avec `ANTHROPIC_API_KEY`).
Un cycle complet peut consommer beaucoup d'appels (jusqu'à 200 tours, plusieurs agents). Fixez une limite de
dépense dans console.anthropic.com → **Billing / Limits**. Les minutes GitHub Actions sont gratuites dans les
limites de votre offre GitHub. Pour réduire le coût : mettez en pause, ou demandez à espacer les cycles.

## Sécurité

- Un seul cycle à la fois. Avant et après chaque cycle, les garde-fous vérifient que la baseline, le Risk Manager
  et les protocoles verrouillés n'ont pas été touchés ; sinon rien n'est publié.
- En cas d'échec, le verrou de cycle est libéré automatiquement pour ne pas bloquer le cycle suivant.
- Argent réel, broker live, hausse du risque, merge vers `main` : toujours interdits sans votre accord.
