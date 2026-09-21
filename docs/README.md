# 📚 Scomp Documentation

Complete documentation for the Scomp sports data scraping and analytics platform.

---

## 📂 Structure

### 🏗️ **Architecture/** - System Design & Backend

**Overview of the backend architecture, components, and design patterns**

- **[BACKEND_ANALYSIS.md](architecture/BACKEND_ANALYSIS.md)** (8,698 LOC)
  - Complete backend breakdown: 64 Python files, 13 modules
  - ORM models (20+ tables), API endpoints (25+), ETL processors (6)
  - Deep dive into each component with code examples
  - **Start here** to understand the complete system 🎯

- **[WORKFLOW_PIPELINE.md](architecture/WORKFLOW_PIPELINE.md)**
  - 4 visual diagrams of the data pipeline:
    - End-to-end workflow (API → DB → Frontend)
    - ETL phases (Extract → Transform → Load)
    - File-by-file flow (6 JSON files → 6 processors)
    - Performance timeline (~13s per competition)
  - **Visual reference** for the scraping pipeline 📊

---

### 🗄️ **Database/** - Schema, Migrations & Analytics

**Database design, models, and analytical views**

- **[DB_SCHEMA.md](database/DB_SCHEMA.md)**
  - 27 tables documented with relationships
  - Primary keys, foreign keys, indexes
  - Column descriptions and data types
  - **Reference guide** for the complete schema 📋

- **[db_schema.mermaid](database/db_schema.mermaid)**
  - Visual ER diagram of the database
  - Shows all relationships and table connections
  - **Visual schema reference** 📈

- **[VIEWS_DOCUMENTATION.md](database/VIEWS_DOCUMENTATION.md)**
  - 3 analytical SQL VIEWs documented:
    - `v_team_matches_summary` - Team match results & events
    - `v_team_speed_zones_by_interval` - Team distance by speed zone
    - `v_player_speed_zones_by_interval` - Player distance analytics
  - Example queries and performance characteristics
  - **Reference** for analytics queries 🔍

- **[init-db.sql](database/init-db.sql)**
  - Database initialization script
  - Creates all tables, indexes, and views
  - Run once on fresh PostgreSQL instance 🛠️

---

### 🌐 **API/** - Endpoints & Request/Response

**API specifications and endpoint documentation**

- **[VIEWS_SUMMARY.md](api/VIEWS_SUMMARY.md)**
  - Quick reference for analytical VIEWs
  - Usage patterns and common queries
  - **Quick reference** for API data structures 📱

---

### 🔄 **Pipeline/** - ETL & Scraping Flow

**Data pipeline execution and ETL processes**

- **[SCRAPE_FLOW_DIAGRAM.md](pipeline/SCRAPE_FLOW_DIAGRAM.md)**
  - Detailed scraping pipeline diagram
  - Step-by-step flow with timings
  - Error handling and validation
  - **Detailed reference** for scraping process 🔄

---

## 🎯 Quick Navigation

**By Role:**

- **🧑‍💻 Backend Developer**
  - Start: [BACKEND_ANALYSIS.md](architecture/BACKEND_ANALYSIS.md)
  - Then: [WORKFLOW_PIPELINE.md](architecture/WORKFLOW_PIPELINE.md)
  - Reference: [DB_SCHEMA.md](database/DB_SCHEMA.md)

- **📊 Data Analyst**
  - Start: [VIEWS_DOCUMENTATION.md](database/VIEWS_DOCUMENTATION.md)
  - Reference: [DB_SCHEMA.md](database/DB_SCHEMA.md)
  - Quick: [VIEWS_SUMMARY.md](api/VIEWS_SUMMARY.md)

- **🚀 DevOps/Infrastructure**
  - Start: [WORKFLOW_PIPELINE.md](architecture/WORKFLOW_PIPELINE.md)
  - Setup: [init-db.sql](database/init-db.sql)
  - Reference: [db_schema.mermaid](database/db_schema.mermaid)

- **🎨 Frontend Developer**
  - Start: [BACKEND_ANALYSIS.md](architecture/BACKEND_ANALYSIS.md) → API section
  - Reference: [VIEWS_SUMMARY.md](api/VIEWS_SUMMARY.md)

**By Task:**

- **Understanding the System**: [BACKEND_ANALYSIS.md](architecture/BACKEND_ANALYSIS.md)
- **Visualizing Data Flow**: [WORKFLOW_PIPELINE.md](architecture/WORKFLOW_PIPELINE.md)
- **Database Queries**: [VIEWS_DOCUMENTATION.md](database/VIEWS_DOCUMENTATION.md)
- **Setting up DB**: [init-db.sql](database/init-db.sql)
- **API Integration**: [VIEWS_SUMMARY.md](api/VIEWS_SUMMARY.md)

---

## 📊 Key Statistics

```
Backend:        8,698 LOC | 64 files | 13 modules
Database:       27 tables | 3 VIEWs | 100+ indexes
API:            25+ endpoints
Pipeline:       ~13s per competition
Fitness Data:   3,082 runs per game tracked
```

---

## 🗂️ File Organization

```
docs/
├── README.md                          ← You are here
├── architecture/                      ← Backend & System Design
│   ├── BACKEND_ANALYSIS.md
│   └── WORKFLOW_PIPELINE.md
├── database/                          ← Schema & Analytics
│   ├── DB_SCHEMA.md
│   ├── db_schema.mermaid
│   ├── VIEWS_DOCUMENTATION.md
│   └── init-db.sql
├── api/                               ← Endpoints & Data
│   └── VIEWS_SUMMARY.md
└── pipeline/                          ← ETL & Scraping
    └── SCRAPE_FLOW_DIAGRAM.md
```

---

## 🔗 Related Files

**In root directory:**
- `docker-compose.yml` - Infrastructure setup
- `.instructions.md` - Project customization
- `Makefile` - Common development commands

**In backend:**
- `backend/README.md` - Backend specific setup
- `backend/VISION_GLOBALE.md` - Architecture philosophy
- `backend/ARCHITECTURE.md` - Filter system deep dive

**In frontend:**
- `frontend/README.md` - Frontend setup

---

## ✅ Documentation Status

- ✅ **Complete**: Backend analysis, DB schema, API docs, Pipeline flow
- ⏳ **In Progress**: Frontend component documentation
- ❌ **Not Started**: Deployment guides, troubleshooting

---

## 💡 Tips

1. **First time here?** Start with [BACKEND_ANALYSIS.md](architecture/BACKEND_ANALYSIS.md)
2. **Visual learner?** Check [WORKFLOW_PIPELINE.md](architecture/WORKFLOW_PIPELINE.md) and [db_schema.mermaid](database/db_schema.mermaid)
3. **Need API info?** See [VIEWS_SUMMARY.md](api/VIEWS_SUMMARY.md)
4. **Database questions?** Reference [VIEWS_DOCUMENTATION.md](database/VIEWS_DOCUMENTATION.md)
5. **Setting up?** Run [init-db.sql](database/init-db.sql) for fresh DB

---

**Last Updated**: August 25, 2026 | **Version**: 1.0
