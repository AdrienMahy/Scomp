# 📊 Views Test Summary - Distance Analytics

**Date:** 2026-08-18  
**Status:** ✅ All 3 views successfully created and tested

---

## 🎯 Les 3 Vues Créées

### 1️⃣ `v_team_speed_zones_by_interval`
**Affiche:** Distance par speed_zone, par time_interval, pour chaque équipe par match

```
Test Game: Dunkerque vs Grenoble Foot 38

Résultats (60 rows affichés):
- Équipe: Dunkerque / Grenoble Foot 38
- Speed Zones: walking, jogging, moderated_intensity, high_intensity, sprint
- Time Intervals: 0_5, 5_10, 10_15, ... 90+
- Estimated Distance par combination

Exemple:
  Grenoble     | 0_5 min  | walking    | 2,072.75 m (estimation)
  Grenoble     | 0_5 min  | jogging    | 3,362.40 m (estimation)
  Grenoble     | 0_5 min  | sprint     | 120.41 m (estimation)
  ...
```

**Cas d'usage:**
- Analyser l'intensité d'une équipe par période
- Comparer l'évolution de l'intensité (1ère mi-temps vs 2e mi-temps)
- Identifier les ralentissements/accélérations

---

### 2️⃣ `v_player_speed_zones_by_interval`
**Affiche:** Distance par speed_zone, par time_interval, pour chaque JOUEUR par match

```
Test Results: 50 rows

Colonnes retournées:
- game_name, team_name, player_name
- speed_zone, time_interval
- estimated_distance_m (par speed_zone dans l'intervalle)
- minutes_played, distance_per_min_played_m

Exemple:
  Dunkerque | Player X | 0_5 min | high_intensity | 15.75 m (est.) | 101.3 min | 124.10 dist/min
  Dunkerque | Player X | 0_5 min | walking        | 67.32 m (est.) | 101.3 min | 124.10 dist/min
  Dunkerque | Player X | 5_10 min| high_intensity | 18.92 m (est.) | 101.3 min | 124.10 dist/min
  ...
```

**Cas d'usage:**
- Analyser la performance individuelle d'un joueur
- Détecter la fatigue (baisse d'intensité sur 2e mi-temps)
- Comparer l'intensité entre joueurs
- Analyser les substitutions (pourquoi remplacer?)

---

### 3️⃣ `v_team_changes`
**Affiche:** Évolution des métriques de performance d'une équipe entre les matchs

```
Test Results: 2 rows (1 par équipe)

Colonnes retournées:
- team_name, game_name, played_at
- team_side (HOME/AWAY), result (WIN/LOSS/DRAW)
- goals_for, goals_against
- total_distance_m, walking_m, jogging_m, ...
- distance_change_m (vs match précédent)
- goals_scored, cards_received, substitutions_made
- match_number_from_latest

Exemple (Match: Dunkerque vs Grenoble):
  Team: USL Dunkerque
  - Result: WIN (4-2)
  - Total Distance: 114,415 m
  - Distance Change: N/A (no previous match)
  - Goals Scored: 4, Cards: 2, Subs: 4

  Team: Grenoble Foot 38
  - Result: LOSS (2-4)
  - Total Distance: 117,451 m
  - Distance Change: N/A (no previous match)
  - Goals Scored: 2, Cards: 3, Subs: 4
```

**Cas d'usage:**
- Tracker l'évolution d'une équipe à travers la saison
- Identifier les patterns de performance
- Analyser l'impact de tactiques sur la distance
- Corrélation: distance ↔ résultat

---

## 📊 Query Examples

### Exemple 1: Distance par zone pour une équipe dans un match
```sql
SELECT
    time_interval,
    speed_zone,
    estimated_distance_m
FROM v_team_speed_zones_by_interval
WHERE game_id = 'c1d63cc5-0585-4a32-b61a-77ce8df0c691'
  AND team_name = 'USL Dunkerque'
ORDER BY time_interval, 
         CASE speed_zone 
           WHEN 'sprint' THEN 1
           WHEN 'high_intensity' THEN 2
           WHEN 'moderated_intensity' THEN 3
           WHEN 'jogging' THEN 4
           WHEN 'walking' THEN 5 
         END;
```

### Exemple 2: Intensité des joueurs dans les dernières 10 minutes
```sql
SELECT
    player_name,
    time_interval,
    distance_per_min_played_m,
    estimated_distance_m
FROM v_player_speed_zones_by_interval
WHERE game_id = 'c1d63cc5-0585-4a32-b61a-77ce8df0c691'
  AND time_interval IN ('80_85', '85_90', '90+')
  AND speed_zone IN ('sprint', 'high_intensity')
ORDER BY distance_per_min_played_m DESC;
```

### Exemple 3: Fatigue (1ère vs 2e mi-temps)
```sql
SELECT
    player_name,
    SUM(CASE WHEN time_interval IN ('0_5','5_10','10_15','15_20','20_25','25_30','30_35','35_40','40_45')
            THEN estimated_distance_m ELSE 0 END) as first_half_m,
    SUM(CASE WHEN time_interval IN ('45_50','50_55','55_60','60_65','65_70','70_75','75_80','80_85','85_90','90+')
            THEN estimated_distance_m ELSE 0 END) as second_half_m
FROM v_player_speed_zones_by_interval
WHERE game_id = 'c1d63cc5-0585-4a32-b61a-77ce8df0c691'
  AND speed_zone IN ('sprint', 'high_intensity')
GROUP BY player_name
HAVING SUM(CASE WHEN time_interval IN ('0_5','5_10','10_15','15_20','20_25','25_30','30_35','35_40','40_45')
         THEN estimated_distance_m ELSE 0 END) > 0;
```

### Exemple 4: Comparaison avant/après pour une équipe
```sql
SELECT
    team_name,
    played_at,
    result,
    total_distance_m,
    distance_change_m,
    CASE 
        WHEN distance_change_m IS NULL THEN 'N/A'
        WHEN distance_change_m > 0 THEN 'Distance ↑ (amélioration)'
        WHEN distance_change_m < 0 THEN 'Distance ↓ (fatigue?)'
        ELSE 'Distance = (stable)'
    END as distance_trend
FROM v_team_changes
WHERE team_name = 'USL Dunkerque'
ORDER BY played_at DESC
LIMIT 10;
```

---

## 📈 Résultats du Test

### Statistics
- ✅ **v_team_speed_zones_by_interval**: 60+ rows (limité par LIMIT 60)
- ✅ **v_player_speed_zones_by_interval**: 50 rows (limité par LIMIT 50)
- ✅ **v_team_changes**: 2 rows (1 par équipe)
- ✅ **Total**: Toutes les vues retournent des données correctement

### Data Quality
- ✅ Speed zones: walking, jogging, moderated_intensity, high_intensity, sprint
- ✅ Time intervals: 0_5, 5_10, ..., 90+ (20 intervalles)
- ✅ Teams: USL Dunkerque (HOME, WIN 4-2), Grenoble Foot 38 (AWAY, LOSS 2-4)
- ✅ Players: 31 joueurs inclus
- ✅ Distances: Calculées correctement avec estimations

---

## ⚠️ Notes Importantes

### Estimation de Distance
Les vues utilisent une **distribution uniforme** pour estimer la distance par speed_zone sur chaque time_interval.

**Formule:**
```
estimated_distance_m = (distance_interval_total * speed_zone_distance / total_distance_match)
```

**Limitation:** Cette estimation assume que chaque speed_zone est uniformément distribuée dans le temps. En réalité, il pourrait y avoir de la variation (un joueur peut accélérer à certains moments).

### Cas d'usage recommandé
✅ Bonnes pour:
- Tendances générales
- Comparaisons relatives (équipes, joueurs)
- Analyse de fatigue
- Pattern recognition

❌ Non recommandées pour:
- Précision absolue à la seconde près
- Analyse frame-by-frame (utiliser raw JSON)
- Événements spécifiques précis

---

## 🚀 Prochaines Étapes

1. **API Endpoints**: Créer des routes FastAPI qui exposent ces vues
2. **Frontend Visualization**: 
   - Graphiques d'intensité par intervalle
   - Heatmaps de distance
   - Comparaisons entre joueurs/équipes
3. **Advanced Analytics**:
   - Clustering de patterns de fatigue
   - Prédiction de performance
   - Corrélation distance ↔ résultat

---

## 📁 Fichiers

- **backend/views.sql**: Définition des 3 vues
- **test_views.py**: Script de test
- **DATABASE_SCHEMA.md**: Documentation des structures

