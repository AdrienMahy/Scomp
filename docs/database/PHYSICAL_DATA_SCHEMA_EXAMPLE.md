# PhysicalData - Exemple SQL simplifie

Ce schema correspond au dataset reel STATSport exporte dans `start/STATSport/physical_data_dataset_2026-09-22.json`.
Les tables sont dans la base `PhysicalData`, donc aucun prefixe n'est necessaire.

```sql
CREATE TABLE squads (
    id UUID PRIMARY KEY,
    external_id UUID NOT NULL UNIQUE,
    name TEXT,
    raw_data JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE players (
    id UUID PRIMARY KEY,
    identity_key TEXT NOT NULL UNIQUE,
    display_name TEXT,
    first_name TEXT,
    last_name TEXT,
    primary_position TEXT,
    secondary_position TEXT,
    active_squad_name TEXT,
    player_details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    activity_id UUID NOT NULL UNIQUE,
    activity_name TEXT,
    share_date TIMESTAMPTZ NOT NULL,
    squad_id UUID NOT NULL REFERENCES squads(id),
    session_date TIMESTAMPTZ NOT NULL,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    session_type TEXT,
    raw_data JSONB NOT NULL,
    response_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE session_players (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES players(id),
    source_id UUID NOT NULL,
    raw_data_id UUID,
    player_details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, player_id),
    UNIQUE (session_id, source_id)
);

CREATE TABLE drill_metadata (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    signature TEXT NOT NULL,
    drill_name TEXT,
    primary_label TEXT,
    secondary_label TEXT,
    tertiary_label TEXT,
    session_type TEXT,
    UNIQUE (session_id, signature)
);

CREATE TABLE drills (
    id UUID PRIMARY KEY,
    session_player_id UUID NOT NULL REFERENCES session_players(id) ON DELETE CASCADE,
    drill_metadata_id UUID NOT NULL REFERENCES drill_metadata(id),
    source_id UUID NOT NULL,
    session_player_data_id UUID,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    free_text TEXT,
    metrics JSONB NOT NULL DEFAULT '{}',
    raw_data JSONB NOT NULL,
    UNIQUE (session_player_id, source_id)
);

CREATE TABLE api_snapshots (
    id UUID PRIMARY KEY,
    endpoint TEXT NOT NULL,
    request_payload JSONB,
    response_payload JSONB NOT NULL,
    http_status INTEGER NOT NULL,
    api_version TEXT NOT NULL,
    response_hash TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## Exemple de KPI

```sql
INSERT INTO drills (id, session_player_id, drill_metadata_id, source_id, metrics, raw_data)
VALUES (
    '50000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    '40000000-0000-0000-0000-000000000001',
    '50000000-0000-0000-0000-000000000002',
    '{
      "distance": {"distanceTotal": 9075.19, "distanceZ6Abs": 136.14},
      "speed": {"maxSpeed": 8.93, "sprints": 5},
      "heart_rate": {"maxHeartrate": 80.0}
    }',
    '{"drillName":"MATCH"}'
);
```

## Requetes

```sql
-- Distance et vitesse d'un joueur
SELECT
    p.display_name,
    s.share_date,
    d.metrics #>> '{distance,distanceTotal}' AS distance_total,
    d.metrics #>> '{speed,maxSpeed}' AS max_speed
FROM drills d
JOIN session_players sp ON sp.id = d.session_player_id
JOIN players p ON p.id = sp.player_id
JOIN sessions s ON s.id = sp.session_id;

-- Activites modifiees depuis le dernier import
SELECT id, activity_id, share_date, response_hash
FROM sessions
WHERE share_date > :last_import_share_date
ORDER BY share_date DESC;

-- KPI d'une categorie sans catalogue de metriques
SELECT
    p.display_name,
    d.metrics -> 'distance' AS distance_metrics,
    d.metrics -> 'speed' AS speed_metrics
FROM drills d
JOIN session_players sp ON sp.id = d.session_player_id
JOIN players p ON p.id = sp.player_id;
```

## Joueurs et nouvelles sessions

Le registre `players` est mis a jour par `identity_key` :

```sql
INSERT INTO players (id, identity_key, display_name, player_details)
VALUES (:id, :identity_key, :display_name, :details)
ON CONFLICT (identity_key) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    player_details = EXCLUDED.player_details,
    updated_at = now();
```

`session_players` est ensuite ajoute pour chaque nouvelle session. Ainsi, un joueur existant n'est pas duplique, mais sa participation a chaque activite est conservee.

Limite actuelle : l'API observee ne fournit pas `customPlayerId`. Tant qu'un identifiant joueur STATSport stable n'est pas disponible, `identity_key` repose sur les details d'identite et doit etre surveille pour les homonymes.
