"""Recreate v_player_distance_summary aligned with current schema (total distance + minutes played only)

Revision ID: 060
Revises: 059_create_v_team_distance_summary
Create Date: 2026-09-18 00:00:00.000000

Purpose:
    - v_player_distance_summary was recorded as created by migration 058, but is
      missing from the live database (dropped outside of Alembic at some point).
    - Recreate it with a minimal, current-schema-aligned structure: only
      total_distance_m and minutes_played (no speed zones, no calculated fields,
      no raw JSONB passthrough).
"""

from alembic import op


revision = '060'
down_revision = '059_create_v_team_distance_summary'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_player_distance_summary CASCADE")

    op.execute("""
    CREATE VIEW v_player_distance_summary AS
    SELECT
        pdc.game_id,
        pdc.player_id,
        pdc.team_id,
        g.name as game_name,
        p.name as player_name,
        t.name as team_name,
        ROUND((pdc.metrics->>'total_distance_m')::NUMERIC, 2) as total_distance_m,
        ROUND((pdc.metrics->>'minutes_played')::NUMERIC, 2) as minutes_played
    FROM player_distance_covered pdc
    LEFT JOIN games g ON pdc.game_id = g.id
    LEFT JOIN players p ON pdc.player_id = p.id
    LEFT JOIN teams t ON pdc.team_id = t.id
    ORDER BY g.name, p.name
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_player_distance_summary CASCADE")
