# PhysicalData - Relations STATSport

Le JSON de reference est `start/STATSport/physical_data_dataset_2026-09-22.json`.
Les noms de tables n'ont pas de prefixe : elles appartiennent deja a la base `PhysicalData`.

```mermaid
erDiagram
    squads ||--o{ sessions : "identifie l'equipe"
    sessions ||--o{ session_players : contient
    players ||--o{ session_players : participe
    sessions ||--o{ drill_metadata : definit
    session_players ||--o{ drills : realise
    drill_metadata ||--o{ drills : categorise
    sessions ||--o{ api_snapshots : "est tracee par"

    squads { uuid id PK; uuid external_id UK; text name }
    players { uuid id PK; text identity_key UK; text display_name; jsonb player_details }
    sessions { uuid id PK; uuid activity_id UK; timestamptz share_date; uuid squad_id FK; jsonb raw_data }
    session_players { uuid id PK; uuid session_id FK; uuid player_id FK; uuid source_id; uuid raw_data_id }
    drill_metadata { uuid id PK; uuid session_id FK; text signature; text drill_name }
    drills { uuid id PK; uuid session_player_id FK; uuid drill_metadata_id FK; uuid source_id; jsonb metrics; jsonb raw_data }
    api_snapshots { uuid id PK; text endpoint; jsonb response_payload; text response_hash }
```

## Modele

- `squads` remplace `clubs`. STATSport fournit `sessionDetails.squadId`, qui identifie l'equipe ayant realise l'activite. Le nom n'est pas fourni dans la reponse actuelle et reste nullable.
- `sessions` represente une activite STATSport. `activity_id` vient du champ racine `id`; `share_date` vient du champ racine `shareDate` et sert a detecter une modification de l'activite.
- `players` est le registre dedoublonne. `session_players` conserve l'identifiant de participation `source_id` et le `raw_data_id` propres a une session.
- `drill_metadata` dedoublonne la definition d'un drill dans une session.
- `drills` represente un drill pour un joueur et contient les KPI dans `metrics`.
- `api_snapshots` conserve la reponse brute pour audit et rejeu.

## KPI JSONB

Un drill contient par exemple :

```json
{
  "metrics": {
    "distance": {
      "distanceTotal": 9075.19,
      "distanceZ1Abs": 3850.18,
      "distanceZ6Abs": 136.14
    },
    "speed": {
      "maxSpeed": 8.93,
      "sprints": 5
    },
    "heart_rate": {
      "maxHeartrate": 80.0
    }
  }
}
```

Ce choix evite une table catalogue `metrics`, une cle `metric_id` et une jointure pour chaque KPI. Les categories sont stables, les codes STATSport restent flexibles.

## Identite joueur

Dans le dataset observe, `customPlayerId` n'est pas fourni. `sessionPlayers[].id` est conserve comme `session_players.source_id`, car il identifie la participation STATSport et ne doit pas etre presume identifiant global du joueur.

`players.identity_key` est calcule a partir de `customPlayerId`, nom, prenom et date de naissance. Si STATSport fournit plus tard un identifiant joueur stable, il devra devenir la cle d'identite prioritaire.

Cette precaution dedoublonne 53 participations en 49 joueurs dans l'export actuel, sans fusionner automatiquement deux personnes qui porteraient le meme nom.

## Mise a jour d'une activite

```text
1. rechercher sessions.activity_id
2. comparer share_date et response_hash
3. si aucun changement : ne rien recharger
4. si share_date change : remplacer les enfants de la session dans une transaction
5. mettre a jour players et conserver les nouvelles participations
```

## Volumes du dataset actuel

| Table | Lignes |
|---|---:|
| `squads` | 3 |
| `players` | 49 |
| `sessions` | 6 |
| `session_players` | 53 |
| `drill_metadata` | 35 |
| `drills` | 301 |
| `api_snapshots` | 1 |
