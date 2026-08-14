# 🧪 Tests & Exploration

This directory contains all test and exploration scripts for the Scomp project.

## 📂 Structure

```
tests/
├── test_api.py                      # API connectivity test
├── test_api_discovery.py            # API discovery & structure documentation
├── test_basic.py                    # Basic API query test
├── test_debug.py                    # Debug API requests & responses
├── test_all_queries.py              # Test all query endpoints
├── test_filter_config.py            # Test filter configuration system
├── test_filter_usage_example.py     # Examples of filter usage in scraper
├── test_get_games_filters.py        # Test get_games specific filters
├── test_predefined_filters.py       # Test predefined filter system
└── outputs/                         # Generated test outputs
```

## 🚀 Running Tests

All tests require the virtual environment to be activated:

```bash
cd /Users/adrienmahy/Documents/GitHub/ISB/Services/Scomp
source venv/bin/activate
```

### API Discovery & Connection Tests

**1. Discover API structure:**
```bash
python3 tests/test_api_discovery.py
# Output: tests/outputs/loaded_configuration.json, graphql_queries.json
```

**2. Test basic connectivity:**
```bash
python3 tests/test_basic.py
# Steps: Load creds → Load query → Build payload → Set headers → Send request
```

**3. Debug full request/response:**
```bash
python3 tests/test_debug.py
# Output: Full unmasked request/response with actual API key
```

**4. Test all endpoints:**
```bash
python3 tests/test_all_queries.py
# Tests: getCompetitions, getSeasons, getGames, getClubs
```

### Filter Configuration Tests

**5. Test filter configuration system:**
```bash
python3 tests/test_filter_config.py
# Demonstrates loading filters from graphql_filters.json
```

**6. Test predefined filters:**
```bash
python3 tests/test_predefined_filters.py
# Shows building GraphQL payloads from simple values
```

**7. Test get_games specific filters:**
```bash
python3 tests/test_get_games_filters.py
# Tests: available, competition_id, round, season
```

**8. Filter usage examples:**
```bash
python3 tests/test_filter_usage_example.py
# Complete workflow examples for using filters in scraper
```

## 📊 Current Filter Configuration

### get_games Query

**Available Filters:**
- `available` (boolean) → `available`
- `competition_id` (string) → `competition.id`
- `round` (array) → `round.name` (using `in` operator)
- `season` (array) → `season.season` (using `in` operator)

**Example Usage:**
```python
from src.config.filter_config import get_filter_config

config = get_filter_config()

values = {
    "available": True,
    "competition_id": "comp-123",
    "round": ["Round 1", "Round 2"],
    "season": ["2024"]
}

payload = config.build_payload_from_values("get_games", values)
# Result: GraphQL-formatted filters ready for API
```

## 📝 Test Files Summary

| File | Purpose | Status |
|------|---------|--------|
| test_api.py | Direct API connectivity | ✅ Working |
| test_api_discovery.py | Document API structure | ✅ Complete |
| test_basic.py | Step-by-step API test | ⚠️ 403 Forbidden (permissions) |
| test_debug.py | Full request/response debug | ⚠️ 403 Forbidden (permissions) |
| test_all_queries.py | Test all endpoints | ⚠️ 403 Forbidden (permissions) |
| test_filter_config.py | Filter system validation | ✅ Working |
| test_filter_usage_example.py | Filter usage patterns | ✅ Working |
| test_get_games_filters.py | get_games filters | ✅ Working |
| test_predefined_filters.py | Predefined filter system | ✅ Working |

## ⚠️ Current Issues

- **API Access**: All queries return 403 Forbidden (apiCode 5003)
- **Root Cause**: API key lacks read permissions for game/competition data
- **Status**: Awaiting credential update or permissions grant from SportsDynamics

## 📁 Outputs

Test results and discoveries are saved in `outputs/`:
- `loaded_configuration.json` - All 5 providers and their configurations
- `graphql_queries.json` - All available GraphQL query templates

## 🔄 Workflow

1. **Discover** → Run `test_api_discovery.py` to understand API structure
2. **Connect** → Run `test_basic.py` to verify connectivity
3. **Debug** → Run `test_debug.py` if issues occur
4. **Configure** → Update `backend/src/config/predefined_filters.json` with working filters
5. **Test** → Run `test_get_games_filters.py` to verify filter configuration
6. **Integrate** → Use filters in scraper via `build_payload_from_values()`

## 🎯 Next Steps

1. ✅ Filter system configured for get_games
2. ⏳ Resolve API permissions (waiting for credentials update)
3. ⏳ Initialize Alembic migrations for database schema
4. ⏳ Test live scraping with real API data
5. ⏳ Frontend development

---

**Last Updated**: 2026-08-12
**Working Directory**: `/Users/adrienmahy/Documents/GitHub/ISB/Services/Scomp`
