# 📊 VIEWs Analytiques - Documentation

## Vue d'ensemble

Les VIEWs SQL fournissent des données de match et des analyses sportives:

## Buts : `v_goals`

Cette vue retourne une ligne par but canonique. `team_id` et `team_name`
désignent l'équipe créditée du but ; `own_goal` indique s'il s'agit d'un but
contre son camp. `phase_play` contient le libellé de phase du fournisseur,
`possession_id` l'identifiant de possession collective et `type` le libellé
du type de jeu (par exemple `Fast play` ou `Structured play`).

La vue inclut également `goal_id`, `game_id`, `game_name` et `round` pour
identifier et filtrer les buts. Les valeurs de phase ou de type restent
`NULL` lorsque le fournisseur ne fournit pas la référence correspondante.
Le champ `goals.shot` est joint à l'événement `Shot` correspondant dans
`events` par `game_id` et `entity.sequence_id`. `phase_play` est extrait du
payload de cet événement Shot (et non du payload Goal). La vue expose son identifiant,
son issue, son xG, sa partie du corps, ses coordonnées de départ et d'arrivée,
ainsi que l'entité Shot complète dans `shot_event`. La jointure externe conserve
les buts qui n'ont pas d'événement Shot associé.

```sql
SELECT game_name, round, team_name, own_goal, phase_play, possession_id, type,
       shot_outcome, shot_xg, shot_body_part, shot_start_x, shot_start_y,
       shot_end_x, shot_end_y
FROM v_goals
ORDER BY round, game_name, goal_id;
```

## Distances par état de jeu

Les vues `v_team_distance_game_state` et `v_player_distance_game_state`
exposent, respectivement par match/équipe et par match/joueur, les distances
parcourues ballon en jeu et hors jeu. Les colonnes `in_play_distance_m` et
`out_of_play_distance_m` sont exprimées en mètres. Les vues contiennent aussi
les identifiants et noms du match, de l'équipe et, pour la vue joueur, du
joueur, ainsi que le côté domicile/extérieur.

Elles exposent également les cinq zones de vitesse pour chacun des deux états
avec les colonnes `in_play_{walking,jogging,moderated_intensity,high_intensity,sprint}_m`
et `out_of_play_{walking,jogging,moderated_intensity,high_intensity,sprint}_m`.
Les colonnes `in_play_high_intensity_distance_m` et
`out_of_play_high_intensity_distance_m` donnent aussi la somme calculée
**High intensity + Sprint**, respectivement ballon en jeu et hors jeu.

```sql
SELECT game_name, team_name, team_side,
       in_play_distance_m, out_of_play_distance_m
FROM v_team_distance_game_state
ORDER BY game_date, game_name, team_side;
```

```sql
SELECT game_name, player_name, team_name,
       in_play_distance_m, out_of_play_distance_m
FROM v_player_distance_game_state
ORDER BY game_date, game_name, player_name;
```

## Vitesse maximale par joueur et match : `v_player_match_peak_speed`

Cette vue contient une ligne par joueur présent dans `player_fitness_runs` pour
un match. `peak_speed` est le maximum des vitesses de pointe enregistrées pour
les courses de ce joueur dans ce match. La valeur est `NULL` si aucune course
ne possède de `peak_speed`.

| Colonne | Description |
|---------|-------------|
| `game_id` | Identifiant du match |
| `game_name` | Nom du match |
| `game_round` | Nom du tour, ou numéro si le nom n'est pas renseigné |
| `player_id` | Identifiant du joueur |
| `player_name` | Nom du joueur |
| `peak_speed` | Plus grande vitesse de pointe du joueur pendant le match |

```sql
SELECT game_name, game_round, player_name, peak_speed
FROM v_player_match_peak_speed
ORDER BY game_name, peak_speed DESC;
```

## Écarts de distance équipe/adversaire : `v_team_distance_opponent_deltas`

Cette vue contient une ligne par équipe et par match (donc deux lignes par
match lorsque les données des deux équipes sont disponibles). Chaque delta
est calculé comme **distance de l'équipe de la ligne moins distance de son
adversaire** : une valeur positive indique que l'équipe de la ligne a parcouru
une distance supérieure. L'autre ligne du match expose l'écart inverse.

Les deltas couvrent la distance totale et les cinq zones de vitesse
(walking, jogging, moderated intensity, high intensity et sprint), en match
complet, MT1 et MT2. La vue inclut aussi High intensity + Sprint, en match
complet et pour chaque mi-temps. Les valeurs sont arrondies à deux décimales.

```sql
SELECT
    game_name,
    team_name,
    opponent_team_name,
    delta_vs_opponent_total_distance_m,
    delta_vs_opponent_mt1_total_distance_m,
    delta_vs_opponent_mt2_total_distance_m,
    delta_vs_opponent_high_intensity_distance_m
FROM v_team_distance_opponent_deltas
ORDER BY game_date, game_name, team_side;
```

## Informations de match : `v_game_information`

Cette vue contient deux lignes par match, une pour chacune des équipes. La
colonne `team_name` correspond à l'équipe de la ligne ; les équipes domicile
et extérieur et le score complet sont répétés sur les deux lignes.

| Colonne | Description |
|---------|-------------|
| `id` | Identifiant du match |
| `name` | Nom du match |
| `round` | Nom du tour, ou numéro si le nom n'est pas renseigné |
| `team_name` | Équipe représentée par la ligne |
| `home_team_name` | Équipe à domicile |
| `away_team_name` | Équipe à l'extérieur |
| `score` | Score domicile - extérieur ; `NULL` tant que les deux scores ne sont pas disponibles |
| `game_date` | Date prévue du match (`starts_at`) |

### Exemple

```sql
SELECT id, name, round, team_name,
       home_team_name, away_team_name, score, game_date
FROM v_game_information
ORDER BY game_date, name, team_name;
```

---

## Distances TacticalData : structure et vues mises à jour

Les tables `team_distance_covered` et `player_distance_covered` utilisent deux
nœuds JSONB :

- `match_data` : totaux du match, zones de vitesse globales et résumé de MT1/MT2.
- `intervals` : distance totale et distances par zone pour chaque bucket de
  cinq minutes.

Pour les joueurs, `match_data` contient aussi `minutes_played` et
`distance_per_min_played_m`. MT1 additionne les buckets de `0_5` à `45+` ;
MT2 additionne ceux de `45_50` à `90+`. Les buckets au-delà de `90+` sont
conservés dans `intervals` mais ne sont pas ajoutés à ces périodes.

La migration reprend les anciennes distances totales et marges globales. Les
anciennes tables ne conservaient pas le croisement zone × intervalle : ces
valeurs apparaîtront après un nouveau scraping des matchs. Les statistiques
MT1/MT2 par zone seront donc nulles pour les lignes historiques jusqu'à leur
rechargement.

Les distances équipe sont réparties en trois vues :

- `v_team_distance_absolute` expose les mesures par match et équipe, dont les
  distances totales et les cinq zones de vitesse de MT1 et MT2 : walking,
  jogging, moderated intensity, high intensity et sprint.
- `v_team_distance_reference` contient une seule ligne par équipe et saison :
  `season_id`, les identifiants/noms de l'équipe, et uniquement les maxima et
  moyennes de saison. Ces références couvrent la distance totale et les cinq
  zones de vitesse en match complet, MT1 et MT2 ; aucune donnée propre à un
  match n'est exposée dans cette vue. Elles incluent également le maximum et
  la moyenne de `high_intensity_distance_m` (High intensity + Sprint) et de
  `high_intensity_ratio_percent`, calculés match par match avant agrégation.
- `v_team_distance_deltas` reste au niveau match/équipe, mais n'expose que les
  identifiants du match/de l'équipe et les deltas. Elle fournit les deltas à la
  moyenne pour le total et les cinq zones de vitesse en match complet, MT1 et
  MT2. Elle expose également le delta High intensity + Sprint pour le match
  complet. Les champs `delta_period_*_m` calculent MT1 moins MT2 pour le total,
  les cinq zones de vitesse et High intensity + Sprint.

`v_team_distance_summary` reste disponible comme vue de compatibilité et expose
le même résultat réduit que `v_team_distance_deltas`.
Les vues joueur suivent la même séparation :

- `v_player_distance_absolute` expose les mesures par match/joueur, les cinq
  zones de vitesse en match complet, MT1 et MT2, ainsi que High intensity +
  Sprint et son ratio en match complet.
- `v_player_distance_reference` contient une seule ligne par joueur et
  `season_id`, sans partition par équipe. Elle ne conserve que les maxima et
  moyennes de saison pour le total et les cinq zones en match complet, MT1 et
  MT2, plus High intensity + Sprint et son ratio en match complet.
- `v_player_distance_deltas` reste au niveau match/joueur, mais n'expose que
  les identifiants et les deltas. Elle fournit les deltas à la moyenne pour le
  total et les cinq zones en match complet, MT1 et MT2, ainsi que High intensity
  + Sprint en match complet. Les champs `delta_period_*_m` calculent MT1 moins
  MT2 pour le total, les cinq zones et High intensity + Sprint.

Les références sont regroupées par joueur et saison, sans équipe, afin de
rester continues en cas de changement d'équipe. `v_player_distance_summary`
reste disponible comme alias de compatibilité de la vue des deltas.
Ces vues de distance sont gérées par les migrations Alembic ; le script SQL
complémentaire `backend/views.sql` ne crée ni ne remplace `v_player_distance_summary`.
`v_player_distance_relative` fournit toujours les distances du match complet
par minute jouée pour le total, High intensity et Sprint. Une durée jouée nulle
produit une valeur relative `NULL`. Les ratios MT1/MT2 ne sont pas inclus, car
la durée de jeu propre à chaque période n'est pas disponible dans ces données.
`v_player_distance_by_speed_zone` et `v_player_distance_by_zone_interval`
utilisent également les nouveaux nœuds JSONB.

### Exemple : références saisonnières équipe

```sql
SELECT
    season_id,
    team_id,
    team_name,
    season_max_total_distance_m,
    season_avg_total_distance_m,
    season_max_high_intensity_distance_m,
    season_avg_high_intensity_distance_m,
    season_max_high_intensity_ratio_percent,
    season_avg_high_intensity_ratio_percent,
    season_max_walking_m,
    season_avg_walking_m,
    season_max_mt1_moderated_intensity_m,
    season_avg_mt1_moderated_intensity_m,
    season_max_mt2_sprint_m,
    season_avg_mt2_sprint_m
FROM v_team_distance_reference
ORDER BY season_id, team_name;
```

### Exemple : écarts des distances équipe à la moyenne saisonnière

```sql
SELECT
    game_date,
    game_round_name,
    game_name,
    team_id,
    team_name,
    delta_total_distance_m,
    delta_walking_m,
    delta_jogging_m,
    delta_moderated_intensity_m,
    delta_high_intensity_m,
    delta_sprint_m,
    delta_high_intensity_distance_m,
    delta_mt1_total_distance_m,
    delta_mt1_walking_m,
    delta_mt1_jogging_m,
    delta_mt1_moderated_intensity_m,
    delta_mt1_high_intensity_m,
    delta_mt1_sprint_m,
    delta_mt2_total_distance_m,
    delta_mt2_walking_m,
    delta_mt2_jogging_m,
    delta_mt2_moderated_intensity_m,
    delta_mt2_high_intensity_m,
    delta_mt2_sprint_m,
    delta_period_total_distance_m,
    delta_period_walking_m,
    delta_period_jogging_m,
    delta_period_moderated_intensity_m,
    delta_period_high_intensity_m,
    delta_period_sprint_m
FROM v_team_distance_deltas
WHERE season_id = '2026'
ORDER BY game_round_name::integer, team_name, game_name;
```

### Exemple : valeurs absolues joueur par match

```sql
SELECT
    game_round_name,
    game_name,
    player_id,
    player_name,
    team_name,
    total_distance_m,
    walking_m,
    jogging_m,
    moderated_intensity_m,
    high_intensity_m,
    sprint_m,
    high_intensity_distance_m,
    high_intensity_ratio_percent,
    mt1_total_distance_m,
    mt1_walking_m,
    mt1_jogging_m,
    mt1_moderated_intensity_m,
    mt1_high_intensity_m,
    mt1_sprint_m,
    mt2_total_distance_m,
    mt2_walking_m,
    mt2_jogging_m,
    mt2_moderated_intensity_m,
    mt2_high_intensity_m,
    mt2_sprint_m
FROM v_player_distance_absolute
WHERE season_id = '2026'
ORDER BY game_round_name::integer, player_name, game_name;
```

### Exemple : deltas joueur par match

```sql
SELECT
    game_round_name,
    game_name,
    player_id,
    player_name,
    team_name,
    delta_total_distance_m,
    delta_walking_m,
    delta_jogging_m,
    delta_moderated_intensity_m,
    delta_high_intensity_m,
    delta_sprint_m,
    delta_high_intensity_distance_m,
    delta_mt1_total_distance_m,
    delta_mt1_walking_m,
    delta_mt1_jogging_m,
    delta_mt1_moderated_intensity_m,
    delta_mt1_high_intensity_m,
    delta_mt1_sprint_m,
    delta_mt2_total_distance_m,
    delta_mt2_walking_m,
    delta_mt2_jogging_m,
    delta_mt2_moderated_intensity_m,
    delta_mt2_high_intensity_m,
    delta_mt2_sprint_m,
    delta_period_total_distance_m,
    delta_period_walking_m,
    delta_period_jogging_m,
    delta_period_moderated_intensity_m,
    delta_period_high_intensity_m,
    delta_period_sprint_m
FROM v_player_distance_deltas
WHERE season_id = '2026'
ORDER BY game_round_name::integer, player_name, game_name;
```

### Exemple : références saisonnières joueur

```sql
SELECT
    season_id,
    player_id,
    player_name,
    season_max_total_distance_m,
    season_avg_total_distance_m,
    season_max_high_intensity_distance_m,
    season_avg_high_intensity_distance_m,
    season_max_high_intensity_ratio_percent,
    season_avg_high_intensity_ratio_percent,
    season_max_mt1_walking_m,
    season_avg_mt1_walking_m,
    season_max_mt2_moderated_intensity_m,
    season_avg_mt2_moderated_intensity_m
FROM v_player_distance_reference
ORDER BY season_id, player_name;
```

### Exemple : distances joueur par minute jouée

```sql
SELECT
    game_round_name,
    game_name,
    player_name,
    team_name,
    minutes_played,
    total_distance_per_min_played_m,
    high_intensity_per_min_played_m,
    sprint_per_min_played_m
FROM v_player_distance_relative
WHERE season_id = '2026'
ORDER BY game_round_name::integer, player_name, game_name;
```

---

## 1️⃣ `v_team_speed_zones_by_interval`

**Objectif:** Analyser les distances parcourues par équipe par zone de vitesse et intervalle de temps

### Colonnes
- `game_id` - ID du match
- `game_name` - Nom du match
- `played_at` - Date/heure du match
- `competition_name` - Compétition
- `team_id` - ID de l'équipe
- `team_name` - Nom de l'équipe
- `speed_zone` - Zone de vitesse (walking, jogging, moderated_intensity, high_intensity, sprint)
- `time_interval` - Intervalle de temps (0_5, 5_10, 10_15, etc.)
- `estimated_distance_m` - Distance estimée en mètres
- `total_distance_interval_m` - Distance totale de l'intervalle

### Exemple
```
Grenoble Foot 38 | J1 | high_intensity | 0_5 | 234.5m
Grenoble Foot 38 | J1 | sprint        | 5_10 | 89.2m
```

### Use Cases
✅ Analyser l'effort physique par équipe  
✅ Comparer les performances entre zones de vitesse  
✅ Identifier les équipes qui sprintent plus

---

## 2️⃣ `v_player_speed_zones_by_interval`

**Objectif:** Analyser les distances parcourues par joueur par zone de vitesse et intervalle de temps

### Colonnes
- `game_id` - ID du match
- `game_name` - Nom du match
- `played_at` - Date/heure du match
- `competition_name` - Compétition
- `team_id` - ID de l'équipe
- `team_name` - Nom de l'équipe
- `player_id` - ID du joueur
- `player_name` - Nom du joueur (avec fallback)
- `speed_zone` - Zone de vitesse (walking, jogging, moderated_intensity, high_intensity, sprint)
- `time_interval` - Intervalle de temps (0_5, 5_10, 10_15, etc.)
- `estimated_distance_m` - Distance estimée en mètres
- `total_distance_interval_m` - Distance totale de l'intervalle
- `minutes_played` - Minutes jouées
- `distance_per_min_played_m` - Distance par minute

### Exemple
```
Yadaly Diaby | Grenoble | high_intensity | 0_5  | 156.3m | 45 min
Yadaly Diaby | Grenoble | sprint         | 10_15| 34.8m  | 45 min
```

### Use Cases
✅ Évaluer les performances individuelles des joueurs  
✅ Identifier les joueurs fatigués (moins de distance)  
✅ Comparer l'intensité entre joueurs  
✅ Analyser les efforts pendant différentes phases du match

---

## 3️⃣ `v_team_matches_summary`

**Objectif:** Résumé complet des résultats de match pour chaque équipe avec statistiques d'événements

### Colonnes
- `team_id` - ID de l'équipe
- `team_name` - Nom de l'équipe
- `game_id` - ID du match
- `game_name` - Nom du match
- `round` - Journée/Round du championnat
- `played_at` - Date du match
- `competition_name` - Compétition
- `team_side` - Position (HOME ou AWAY)
- `goals_for` - Buts marqués
- `goals_against` - Buts encaissés
- `result` - Résultat (WIN, LOSS, DRAW)
- `goals_scored` - Nombre total de buts marqués (count from game_goals)
- `yellow_cards` - Cartons jaunes
- `red_cards` - Cartons rouges
- `substitutions` - Nombre de remplacements

### Exemple
```
Grenoble Foot 38 | J1 | Dunkerque vs Grenoble | 2-4 | LOSS | 0 YC | 4 RC | 4 SUB
Grenoble Foot 38 | J2 | Grenoble vs Metz      | ?-? | DRAW | 0 YC | 0 RC | 0 SUB
```

### Use Cases
✅ Suivi de la saison match par match  
✅ Analyse des performances d'équipe  
✅ Historique des cartons et remplacements  
✅ Résumé rapide des résultats par journée

---

## 📈 Requêtes Utiles

### Tous les matchs d'une équipe
```sql
SELECT * FROM v_team_matches_summary
WHERE team_name = 'Grenoble Foot 38'
ORDER BY round::integer;
```

### Analyse de distance pour un joueur
```sql
SELECT player_name, speed_zone, SUM(estimated_distance_m) as total_distance
FROM v_player_speed_zones_by_interval
WHERE game_name LIKE '%Grenoble%' AND player_name = 'Yadaly Diaby'
GROUP BY player_name, speed_zone;
```

### Comparaison d'intensité par équipe
```sql
SELECT team_name, speed_zone, SUM(estimated_distance_m) as total_distance
FROM v_team_speed_zones_by_interval
WHERE game_name = 'Dunkerque vs Grenoble Foot 38'
GROUP BY team_name, speed_zone
ORDER BY team_name, speed_zone;
```

### Filtrer sur les premières journées
```sql
SELECT * FROM v_team_matches_summary
WHERE round::integer IN (1, 2, 3)
ORDER BY round, team_name;
```

---

## ⚠️ Limitations Actuelles

| Source | Status | Count |
|--------|--------|-------|
| Player distances | ✅ Complète | 306 games × 31 players max |
| Team distances | ✅ Complète | 306 games × 2 teams |
| Scores (goals_for/against) | ⚠️ Partielle | 18 games seulement |
| Yellow cards | ⚠️ Minimal | 1 game (Dunkerque vs Grenoble) |
| Red cards | ⚠️ Minimal | 1 game (Dunkerque vs Grenoble) |
| Substitutions | ⚠️ Minimal | 1 game (Dunkerque vs Grenoble) |

---

## 📂 Fichiers Associés

- `backend/views.sql` - Définitions complémentaires des VIEWs analytiques ; les vues de distance joueur/équipe sont gérées par Alembic
- `db_schema.mermaid` - Diagramme ER des tables (mise à jour)
- `DB_SCHEMA.md` - Documentation détaillée des tables
