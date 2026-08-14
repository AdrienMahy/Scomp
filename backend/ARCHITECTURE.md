# 🏗️ Architecture Globale - Scomp

## 📊 Vue d'ensemble (High Level)

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER APPLICATION                         │
│                      (Scraper / Web UI)                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FILTER SYSTEM (Notre création)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │   Values     │→ │  Filter Cfg  │→ │  GraphQL Payload│     │
│  │   (simples)  │  │  (Magic ✨)   │  │   (complexe)    │     │
│  └──────────────┘  └──────────────┘  └──────────────────┘     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   API CLIENT (SportsDynamics)                    │
│         Envoie requêtes GraphQL vers l'API externe              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SPORTSDYNAMICS API                             │
│    (Externe - Retourne données JSON avec structure GraphQL)     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flux des Données - Détail

### Étape 1: Tu fournis des VALEURS SIMPLES

```python
# Dans ton scraper (simple à comprendre)
filter_values = {
    "available": True,                          # Booléen
    "competition_id": "comp-123",               # Chaîne
    "round": ["Round 1", "Round 2"],            # Liste
    "season": ["2024", "2025"]                  # Liste
}
```

### Étape 2: Le système TRANSFORME

```python
# Chargement de la configuration prédéfinie
config = get_filter_config()

# Transformation magique ✨
payload = config.build_payload_from_values("get_games", filter_values)
```

### Étape 3: Résultat = FORMAT GRAPHQL COMPLEXE

```json
{
  "available": {
    "equals": true
  },
  "competition": {
    "id": {
      "equals": "comp-123"
    }
  },
  "round": {
    "name": {
      "in": ["Round 1", "Round 2"]
    }
  },
  "season": {
    "season": {
      "in": ["2024", "2025"]
    }
  }
}
```

### Étape 4: Envoi à l'API

```python
# L'API client utilise le payload
query = """
query GetGames($filters: GameFilters, $limit: Int) {
    games(filters: $filters, limit: $limit) {
        id name startsAt homeTeam { id }
    }
}
"""

result = client.query(query, {
    "filters": payload,        # ← Notre payload transformé
    "limit": 100
})
```

---

## 📁 Structure des Fichiers

```
backend/src/config/
├── predefined_filters.json
│   ├── Définit QUELS filtres sont disponibles pour CHAQUE query
│   ├── Pour chaque filtre:
│   │   ├── label (affichage)
│   │   ├── type (boolean, string, array)
│   │   ├── required (obligatoire ?)
│   │   ├── operator (equals, in, gte, lte)
│   │   └── graphql_path (chemin imbriqué: "competition.id", "round.name")
│   │
│   └── Structure:
│       {
│         "queries": {
│           "get_games": {
│             "filters": {
│               "available": {...},
│               "competition_id": {...},
│               "round": {...},
│               "season": {...}
│             }
│           }
│         }
│       }
│
├── filter_config.py (LA CLASSE MAGIQUE)
│   ├── Charge predefined_filters.json
│   ├── Méthode clé: build_payload_from_values()
│   │   ├── Prend: query_name + values dict
│   │   ├── Pour chaque value:
│   │   │   ├── Cherche la définition dans predefined_filters.json
│   │   │   ├── Récupère le graphql_path et l'operator
│   │   │   ├── Construit la structure imbriquée
│   │   │   └── Ajoute au payload
│   │   └── Retourne: payload complet GraphQL
│   │
│   └── Autres méthodes:
│       ├── get_predefined_filters(query_name)
│       ├── validate_required_filters(query_name, values)
│       ├── get_required_filters(query_name)
│       └── _set_nested_value() [Interne - transforme "a.b.c" en {"a":{"b":{"c":value}}}]
│
└── graphql_filters.json
    └── Vide pour l'instant (à remplir après tests API)
```

---

## 🔀 Diagramme du FLOW COMPLET

```
┌─────────────────────────────────────────────────────────────────┐
│ TOI: Le développeur                                              │
│                                                                  │
│  1. Je fournis des valeurs simples                             │
│     values = {"available": True, "competition_id": "comp-123"} │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ FILTER_CONFIG (filter_config.py)                               │
│                                                                  │
│  2. Je charge la config                                         │
│     config = get_filter_config()                               │
│                                                                  │
│  3. Je lis predefined_filters.json                             │
│     {                                                            │
│       "get_games": {                                            │
│         "filters": {                                            │
│           "available": {"type":"bool", "op":"equals", ...},    │
│           "competition_id": {"type":"str", "path":"comp.id"...}│
│         }                                                        │
│       }                                                          │
│     }                                                            │
│                                                                  │
│  4. Je transforme les valeurs                                   │
│     payload = build_payload_from_values("get_games", values)   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼ TRANSFORMATION MAGIQUE
                       │
│  5. Résultat transformé:                                        │
│     {                                                            │
│       "available": {"equals": true},                            │
│       "competition": {"id": {"equals": "comp-123"}}             │
│     }                                                            │
│                                                                  │
│  (Note: "competition.id" devient {"competition":{"id":{...}}}) │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ API CLIENT (sportsdynamics.py)                                  │
│                                                                  │
│  6. Je construis la requête GraphQL                             │
│     query GetGames($filters: GameFilters, $limit: Int) {       │
│       games(filters: $filters, limit: $limit) { ... }          │
│     }                                                            │
│                                                                  │
│  7. Je passe le payload                                         │
│     client.query(query, {                                       │
│       "filters": payload,    ← Payload transformé             │
│       "limit": 100                                              │
│     })                                                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ API SportsDynamics (EXTERNE)                                    │
│                                                                  │
│  8. L'API reçoit la requête                                    │
│     {                                                            │
│       "query": "query GetGames {...}",                          │
│       "variables": {                                            │
│         "filters": {...},    ← Notre payload GraphQL           │
│         "limit": 100                                            │
│       }                                                          │
│     }                                                            │
│                                                                  │
│  9. L'API retourne les données                                 │
│     {                                                            │
│       "data": {                                                 │
│         "games": [                                              │
│           {"id": "g1", "name": "Game 1", ...},                │
│           {"id": "g2", "name": "Game 2", ...}                 │
│         ]                                                        │
│       }                                                          │
│     }                                                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ TOI: De retour avec les données                                 │
│                                                                  │
│  10. Tu reçois les résultats                                   │
│      games = result["games"]                                   │
│                                                                  │
│  11. Tu les traites (sauvegarde BD, transformation, etc.)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧠 La MAGIE: Comment ça transforme les valeurs?

### Exemple concret:

**Input (ce que tu donnes):**
```python
{
    "available": True,
    "competition_id": "comp-123",
    "round": ["Round 1", "Round 2"]
}
```

**Lookup dans predefined_filters.json:**
```json
"available": {
    "type": "boolean",
    "operator": "equals",
    "graphql_path": "available"
},
"competition_id": {
    "type": "string",
    "operator": "equals",
    "graphql_path": "competition.id"
},
"round": {
    "type": "array",
    "operator": "in",
    "graphql_path": "round.name"
}
```

**Processus de transformation:**

```
1. "available" → True
   Lookup: graphql_path="available", operator="equals"
   Résultat: {"available": {"equals": true}}

2. "competition_id" → "comp-123"
   Lookup: graphql_path="competition.id", operator="equals"
   Path "competition.id" = imbriqué
   Résultat: {"competition": {"id": {"equals": "comp-123"}}}

3. "round" → ["Round 1", "Round 2"]
   Lookup: graphql_path="round.name", operator="in"
   Path "round.name" = imbriqué + array
   Résultat: {"round": {"name": {"in": ["Round 1", "Round 2"]}}}
```

**Output (ce que tu obtiens):**
```json
{
    "available": {"equals": true},
    "competition": {"id": {"equals": "comp-123"}},
    "round": {"name": {"in": ["Round 1", "Round 2"]}}
}
```

### Comment marche `_set_nested_value()`?

```python
def _set_nested_value(obj, path, operator, value):
    """
    Transforme "competition.id" en structure imbriquée
    """
    parts = path.split(".")  # ["competition", "id"]
    current = obj
    
    # Crée la structure imbriquée
    for part in parts[:-1]:  # ["competition"]
        if part not in current:
            current[part] = {}
        current = current[part]
    
    # Ajoute la valeur avec l'operator
    final_key = parts[-1]  # "id"
    current[final_key] = {operator: value}
    # current devient: {"id": {"equals": value}}
```

---

## 📋 Résumé: Les 3 niveaux

### Niveau 1: CONFIGURATION (prédéfinie)
**Fichier:** `predefined_filters.json`
```
Définit pour CHAQUE query:
- Quels filtres sont disponibles?
- Quel type? (boolean, string, array)
- Quel opérateur GraphQL? (equals, in, gte, lte)
- Quel chemin GraphQL? (imbriqué avec points)
```

### Niveau 2: TRANSFORMATION (la magie)
**Classe:** `FilterConfig.build_payload_from_values()`
```
Prend: values simples + query_name
Fait: lookup + transformation + construction imbriquée
Retourne: payload GraphQL complexe prêt à l'emploi
```

### Niveau 3: UTILISATION (ton code)
**Dans ton scraper:**
```python
config.build_payload_from_values("get_games", simple_values)
↓
payload = {...complexe...}
↓
client.query(query, {"filters": payload})
↓
Données retournées ✅
```

---

## 🎯 Cas d'usage: Add a new filter

**Tu veux ajouter un filtre `team_id`?**

1. **Édite** `predefined_filters.json`:
```json
"team_id": {
    "label": "Team ID",
    "type": "string",
    "required": false,
    "operator": "equals",
    "graphql_path": "team.id"
}
```

2. **Utilise-le** immédiatement:
```python
values = {
    "available": True,
    "team_id": "team-456"
}
payload = config.build_payload_from_values("get_games", values)
# Automatiquement: {"available": {...}, "team": {"id": {"equals": "team-456"}}}
```

**Pas besoin de modifier le code!** 🎉

---

## 🔗 Interactions entre les fichiers

```
┌─────────────────────────────────────────────────────────────────┐
│ TES SCRIPTS (tests/)                                            │
│  test_get_games_filters.py                                      │
│  test_predefined_filters.py                                     │
└────────┬────────────────────────────────────────────────────────┘
         │ import
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ FILTER_CONFIG (backend/src/config/filter_config.py)            │
│  - Charge predefined_filters.json au __init__                  │
│  - Expose: build_payload_from_values()                          │
│  - Utilise: _set_nested_value() [helper]                        │
└────────┬────────────────────────────────────────────────────────┘
         │ lit
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ PREDEFINED_FILTERS.JSON (backend/src/config/)                  │
│  - Définition de tous les filtres                              │
│  - Quels filtres pour quelle query?                            │
│  - Operator, type, graphql_path pour chaque filtre             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TON SCRAPER (backend/src/scraper/sportsdynamics_scraper.py)     │
└────────┬────────────────────────────────────────────────────────┘
         │ import & utilise
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ API_CLIENT (backend/src/api/sportsdynamics.py)                  │
│  - Méthode: query(graphql_query, variables)                    │
│  - Variables contient le payload transformé                    │
└────────┬────────────────────────────────────────────────────────┘
         │ envoie
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ SPORTSDYNAMICS API (EXTERNE)                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Avantages de cette architecture

| Aspect | Avantage |
|--------|----------|
| **Séparation des préoccupations** | Config ≠ Logique ≠ Utilisation |
| **Facilité de maintenance** | Changer un filtre = éditer JSON |
| **Réutilisabilité** | Même code pour toutes les queries |
| **Type-safe** | Chaque filtre a un type défini |
| **Scalabilité** | Ajouter 10 filtres sans toucher au code |
| **Testabilité** | Chaque layer peut être testé indépendamment |
| **Documentation** | JSON self-documenting |

---

## 🚀 Workflow complet au lancement

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. APP STARTUP                                                  │
│    - Importe FilterConfig                                       │
│    - Charge predefined_filters.json en mémoire                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. USER REQUEST                                                 │
│    - Utilisateur demande: "Récupère les jeux de Round 1"       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. BUILD VALUES                                                 │
│    values = {"round": ["Round 1"], "available": True}          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. TRANSFORM                                                    │
│    payload = config.build_payload_from_values("get_games",...)│
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. SEND TO API                                                  │
│    client.query(graphql_query, {"filters": payload})           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. API RESPONSE                                                 │
│    {"data": {"games": [...]}}                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. PROCESS RESULTS                                              │
│    - Parse response                                             │
│    - Transform to ORM models                                    │
│    - Save to database                                           │
│    - Return to user                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📞 Questions fréquentes

**Q: Pourquoi pas juste envoyer les valeurs directement à l'API?**
R: L'API attend un format GraphQL très spécifique (imbriqué, avec opérateurs). Notre système abstraite cette complexité.

**Q: Mais les performances?**
R: La transformation se fait en mémoire (pas de réseau). Tellement rapide que c'est négligeable.

**Q: Comment ça scale avec 100 filtres?**
R: Parfaitement! Ajoute juste 100 entrées dans predefined_filters.json. Le code reste identique.

**Q: Et si la structure GraphQL change?**
R: Tu édites juste predefined_filters.json. Zéro changement au code!

---

C'est plus clair maintenant? Des questions sur une partie spécifique? 🚀
