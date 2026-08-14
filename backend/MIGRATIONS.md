# Database Migrations with Alembic

Alembic manages database schema changes for the Scomp database.

## Quick Start

### For Development

**Run pending migrations:**
```bash
cd backend
DATABASE_URL="postgresql://scrapper:scomp_dev_password@postgres:5432/scomp_dev" \
  python3 -m alembic upgrade head
```

**Check current migration status:**
```bash
DATABASE_URL="postgresql://scrapper:scomp_dev_password@postgres:5432/scomp_dev" \
  python3 -m alembic current
```

### For Docker

**Within container:**
```bash
docker-compose exec api bash -c \
  "cd /app/backend && python3 -m alembic upgrade head"
```

**Automatic migration on startup:**
- Set `RUN_MIGRATIONS=true` in docker-compose to auto-run migrations
- Or set in .env file

## Creating New Migrations

After modifying ORM models in `src/models/`:

1. **Auto-generate migration:**
   ```bash
   DATABASE_URL="postgresql://scrapper:scomp_dev_password@postgres:5432/scomp_dev" \
     python3 -m alembic revision --autogenerate -m "Add new_column to games table"
   ```

2. **Review the generated migration:**
   ```bash
   cat alembic/versions/[timestamp]_add_new_column_to_games_table.py
   ```

3. **Test the migration locally:**
   ```bash
   DATABASE_URL="postgresql://scrapper:scomp_dev_password@postgres:5432/scomp_dev" \
     python3 -m alembic upgrade head
   ```

4. **Commit to git:**
   ```bash
   git add alembic/versions/[timestamp]_*.py
   git commit -m "Add migration: Add new_column to games table"
   ```

## Migration Files

Located in `alembic/versions/`, each file contains:

```python
def upgrade() -> None:
    # Schema changes (DDL) to apply
    op.add_column('table_name', sa.Column('new_column', sa.String(255)))

def downgrade() -> None:
    # Revert the upgrade()
    op.drop_column('table_name', 'new_column')
```

## Workflow

1. **Modify ORM model** in `src/models/`
2. **Auto-generate migration** (Alembic detects changes)
3. **Review migration file** (manual adjustments if needed)
4. **Test upgrade/downgrade** locally
5. **Commit migration** to git
6. **Run on production** with `alembic upgrade head`

## Configuration

**alembic.ini:**
- Script location: `alembic/`
- Versions stored in: `alembic/versions/`
- Database URL read from: `DATABASE_URL` environment variable

**alembic/env.py:**
- Auto-detects schema from `src/models/Base.metadata`
- Supports both online (with connection) and offline modes
- Autogenerate enabled in online mode

## Important Notes

- **Never** manually edit the database schema directly
- **Always** create a migration for schema changes
- **Test** migrations locally before production
- **Keep downgrade()** methods accurate for emergency rollbacks
- **Commit migrations** to git as part of code review

## Troubleshooting

**Migration doesn't detect changes:**
- Ensure ORM model is imported in `alembic/env.py`
- Check that `target_metadata = Base.metadata` is set
- Run: `python3 -m alembic current` to verify current version

**Can't connect to database:**
- Verify `DATABASE_URL` is set correctly
- For Docker: ensure postgres service is healthy
- Check credentials in environment variables

**Need to rollback a migration:**
```bash
DATABASE_URL="postgresql://..." python3 -m alembic downgrade -1
```

**Reset to baseline (development only):**
```bash
# Delete all migration history and stamp to initial
docker-compose exec postgres psql -U scrapper -d scomp_dev -c \
  "DROP TABLE IF EXISTS alembic_version;"
DATABASE_URL="..." python3 -m alembic stamp 5fc50b649d06
```

## Current Status

- **Initial migration:** `5fc50b649d06` (baseline from initial_schema)
- **Schema version:** Captured complete schema with all tables:
  - competitions
  - seasons
  - teams
  - games
  - game_status (incremental tracking)
  - game_summary (denormalized view)
  - squads
  - players

## Next Steps

1. Run migrations in Dockerfile on startup
2. Set up monitoring for migration status
3. Create production migration procedures
4. Document schema changes in CHANGELOG
