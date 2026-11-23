# Réglage des pools PostgreSQL en production

Ce runbook décrit le déploiement d'une configuration de pools limitée pour
**PROD uniquement**. Il concerne l'API, le worker Celery TacticalData et le
worker Celery PhysicalData. Ne pas appliquer ces valeurs à DEV sans les
redimensionner selon sa configuration.

## Contexte et hypothèses

- PostgreSQL est configuré avec `max_connections = 50` sur le serveur observé.
- TacticalData et PhysicalData peuvent partager cette limite si leurs bases
  résident sur la même instance PostgreSQL.
- Chaque worker Celery démarre avec `--concurrency=1`.
- L'API peut utiliser les deux bases. Celery Beat publie des tâches et n'a pas
  besoin d'un pool applicatif permanent.
- Les fichiers `config/docker-compose.yml` et `config/.env` sont propres au
  serveur et ignorés par Git. Toujours modifier la copie PROD, pas celle de DEV.

La configuration actuellement suivie dans le dépôt ne représente pas encore
les deux workers de PROD. Vérifier les noms de services et leurs commandes sur
le serveur avant d'appliquer les étapes ci-dessous.

## Budget de connexions proposé

`pool_size` est le nombre maximal de connexions conservées dans le pool d'un
processus. `max_overflow` autorise des connexions supplémentaires pendant les
pics ; elles sont fermées lorsqu'elles sont rendues au pool.

| Service PROD | Base | `pool_size` | `max_overflow` | Maximum simultané |
|---|---|---:|---:|---:|
| API | TacticalData | 4 | 2 | 6 |
| API | PhysicalData | 2 | 1 | 3 |
| Worker TacticalData (`concurrency=1`) | TacticalData | 4 | 1 | 5 |
| Worker PhysicalData (`concurrency=1`) | PhysicalData | 2 | 1 | 3 |
| **Total Scomp si même instance PostgreSQL** | | | | **17** |

Ce plafond laisse une marge de 33 connexions pour PostgreSQL, les outils
d'administration et les autres applications. Les connexions applicatives
conservées au repos par ces pools sont plafonnées à 12. Si les deux bases sont
sur des serveurs distincts, le maximum est de 11 sur TacticalData et 6 sur
PhysicalData.

Ne pas augmenter la concurrence Celery sans recalculer ce budget. Une hausse
de `concurrency` permet plus de tâches simultanées et peut donc accroître la
demande de connexions.

## 1. Déployer d'abord le support applicatif

Le backend lit désormais les options suivantes depuis l'environnement,
séparément pour chaque moteur :

- `TACTICAL_DB_POOL_SIZE`
- `TACTICAL_DB_MAX_OVERFLOW`
- `TACTICAL_DB_APPLICATION_NAME`
- `TACTICAL_DB_IDLE_SESSION_TIMEOUT_MS`
- `PHYSICAL_DB_POOL_SIZE`
- `PHYSICAL_DB_MAX_OVERFLOW`
- `PHYSICAL_DB_APPLICATION_NAME`
- `PHYSICAL_DB_IDLE_SESSION_TIMEOUT_MS`

Les deux moteurs activent `pool_pre_ping=True`. Les tailles de pool ne sont
appliquées qu'aux URL PostgreSQL, et les options `connect_args` PostgreSQL ne
sont ajoutées qu'à ces URL ; le pool SQLite de développement conserve ses
réglages par défaut. Les deux workers de `config/docker-compose.yml` définissent
déjà leurs budgets de connexion et leur délai d'inactivité ; adapter ces valeurs
dans la configuration PROD réelle si nécessaire.

Le nom d'application permet d'identifier le service dans `pg_stat_activity`.
L'option PostgreSQL `idle_session_timeout` est réglée par connexion et non
globalement sur le serveur. Valeur initiale recommandée : `1800000` ms
(30 minutes). Après expiration d'une connexion restée inactive, `pool_pre_ping`
la détecte au prochain emprunt et SQLAlchemy en ouvre une nouvelle.

`pool_recycle=1800` peut compléter ce réglage : il renouvelle une connexion
ancienne lorsqu'elle est reprise par le pool, mais ne ferme pas à lui seul une
connexion qui reste inutilisée. Ne pas modifier le `idle_session_timeout`
global du serveur, qui pourrait affecter les autres applications.

Ne pas définir de `idle_in_transaction_session_timeout` dans cette première
étape. C'est un réglage distinct qui peut interrompre une transaction laissée
ouverte ; ne l'ajouter qu'après avoir confirmé que l'application n'en dépend
pas.

## 2. Régler la configuration Compose de PROD

Sur le serveur PROD, depuis la racine du dépôt :

1. Vérifier le fichier Compose réellement utilisé et les noms de services :

   ```bash
   docker compose -f config/docker-compose.yml config --services
   docker compose -f config/docker-compose.yml ps
   ```

2. Sauvegarder `config/docker-compose.yml` dans un emplacement de sauvegarde
   local non partagé. Ne pas copier `config/.env` dans un rapport ou un ticket.

3. Dans les sections `environment` des services PROD, définir les valeurs
   suivantes. Garder les URL et secrets de base dans le mécanisme de
   configuration déjà utilisé par PROD ; ne pas les ajouter au dépôt.

   **Service API :**

   ```yaml
   TACTICAL_DB_POOL_SIZE: "4"
   TACTICAL_DB_MAX_OVERFLOW: "2"
   TACTICAL_DB_APPLICATION_NAME: "scomp-api-tactical"
   TACTICAL_DB_IDLE_SESSION_TIMEOUT_MS: "1800000"
   PHYSICAL_DB_POOL_SIZE: "2"
   PHYSICAL_DB_MAX_OVERFLOW: "1"
   PHYSICAL_DB_APPLICATION_NAME: "scomp-api-physical"
   PHYSICAL_DB_IDLE_SESSION_TIMEOUT_MS: "1800000"
   ```

   **Worker TacticalData** (conserver sa file TacticalData) :

   ```yaml
   TACTICAL_DB_POOL_SIZE: "4"
   TACTICAL_DB_MAX_OVERFLOW: "1"
   TACTICAL_DB_APPLICATION_NAME: "scomp-worker-tactical"
   TACTICAL_DB_IDLE_SESSION_TIMEOUT_MS: "1800000"
   ```

   **Worker PhysicalData** :

   ```yaml
   PHYSICAL_DB_POOL_SIZE: "2"
   PHYSICAL_DB_MAX_OVERFLOW: "1"
   PHYSICAL_DB_APPLICATION_NAME: "scomp-worker-physical"
   PHYSICAL_DB_IDLE_SESSION_TIMEOUT_MS: "1800000"
   ```

   Les workers spécialisés doivent consommer les files auxquelles les tâches
   sont routées dans `backend/src/tasks/celery_config.py` :

   - TacticalData : `sportsdynamics`
   - PhysicalData : `statsport`

   Vérifier que leurs commandes Celery utilisent bien `-Q sportsdynamics` et
   `-Q statsport` respectivement. Garder `--concurrency=1` pour le premier
   déploiement.

4. Valider le Compose sans afficher sa configuration interpolée (qui pourrait
   contenir des valeurs sensibles) :

   ```bash
   docker compose -f config/docker-compose.yml config --quiet
   ```

## 3. Déployer avec interruption contrôlée

Le déploiement redémarre les processus applicatifs et coupe leurs connexions
courantes. Il ne nécessite aucune migration de schéma PostgreSQL.

1. Planifier le redémarrage pendant une période de faible activité et vérifier
   qu'aucune collecte importante n'est en cours.
2. Reconstruire et redémarrer uniquement l'API et les deux services worker
   PROD, avec leurs vrais noms récupérés via `config --services` :

   ```bash
   docker compose -f config/docker-compose.yml up -d --build \
     <service-api> <service-worker-tactical> <service-worker-physical>
   ```

3. Vérifier leur état et consulter les journaux des services redémarrés :

   ```bash
   docker compose -f config/docker-compose.yml ps
   docker compose -f config/docker-compose.yml logs --since=10m \
     <service-api> <service-worker-tactical> <service-worker-physical>
   ```

Ne pas exécuter `down -v` : cela pourrait supprimer des volumes de données.

## 4. Vérifier les connexions après déploiement

Exécuter cette requête avec un compte autorisé à lire `pg_stat_activity` :

```sql
SELECT
    datname,
    application_name,
    state,
    count(*) AS connections,
    max(now() - state_change) FILTER (WHERE state = 'idle') AS oldest_idle
FROM pg_stat_activity
WHERE application_name LIKE 'scomp-%'
GROUP BY datname, application_name, state
ORDER BY datname, application_name, state;
```

Vérifier que :

- les noms d'application distinguent l'API et chaque worker ;
- le nombre de connexions reste dans le budget ci-dessus en fonctionnement
  normal et pendant une collecte ;
- les connexions inactives sont fermées après le délai configuré (prévoir une
  petite marge de vérification au-delà de 30 minutes) ;
- une tâche et une requête API peuvent encore utiliser la base après
  expiration d'une connexion inactive ;
- aucune connexion Scomp ne reste en `idle in transaction`.

Si un worker a besoin de davantage de connexions ou attend le pool sous charge,
augmenter uniquement son budget après avoir mesuré l'utilisation, puis
recalculer le total de tous les processus sur l'instance PostgreSQL.

## Retour arrière

Si l'application échoue à se connecter ou si des collectes échouent :

1. restaurer l'image applicative précédente ;
2. restaurer la sauvegarde de `config/docker-compose.yml` ;
3. redémarrer les mêmes services PROD ;
4. vérifier l'état des files Celery et des tâches avant de relancer une
   collecte interrompue.

Comme ce réglage ne modifie pas le schéma, aucun downgrade Alembic n'est requis.
