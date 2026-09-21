# 📊 VIEWs Analytiques - Documentation

## Vue d'ensemble

Trois VIEWs SQL ont été créées pour fournir des analyses sportives complètes:

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

- `backend/views.sql` - Définitions complètes des VIEWs
- `db_schema.mermaid` - Diagramme ER des tables (mise à jour)
- `DB_SCHEMA.md` - Documentation détaillée des tables

