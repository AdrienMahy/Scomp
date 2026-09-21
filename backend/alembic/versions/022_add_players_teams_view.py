"""Create VIEW v_players_teams_full - Players joined with Teams with all JSON extracted

Revision ID: 022_add_players_teams_view
Revises: 021_add_events_full_view
Create Date: 2026-09-07 17:00:00.000000

This migration creates a comprehensive VIEW that joins Players with Teams,
extracting all JSON/JSONB columns for easier querying and analysis.

Player JSON fields:
  - nationalities: List of player nationalities with ISO3 codes
  - positions: List of positions with codes and groups

Team JSON fields:
  - providers: List of provider mappings (SecondSpectrum, Perform, SportsDynamics)

The view provides complete player profile with team affiliation and JSON data
flattened into accessible columns.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '022_add_players_teams_view'
down_revision = '021_add_events_full_view'
branch_labels = None
depends_on = None


def upgrade():
    """Create v_players_teams_full VIEW with Player-Team join and JSON extraction"""
    
    op.execute("""
    CREATE OR REPLACE VIEW v_players_teams_full AS
    
    SELECT
      -- ========================================================================
      -- PLAYER IDENTIFICATION
      -- ========================================================================
      p.id as player_id,
      p.name as player_name,
      p.first_name,
      p.last_name,
      p.usage_name,
      
      -- ========================================================================
      -- PLAYER PROFILE
      -- ========================================================================
      p.photo,
      p.age,
      p.birthdate,
      
      -- ========================================================================
      -- PLAYER CURRENT TEAM (Denormalized)
      -- ========================================================================
      p.current_team_id,
      p.current_team_brand,
      
      -- ========================================================================
      -- PLAYER NATIONAL TEAM
      -- ========================================================================
      p.current_national_team_id,
      p.current_national_team_brand,
      
      -- ========================================================================
      -- PLAYER JSON: nationalities (JSONB array of objects)
      -- ========================================================================
      p.nationalities as nationalities_raw,
      p.nationalities::text as nationalities_json,
      
      -- ========================================================================
      -- PLAYER JSON: positions (JSONB array of objects)
      -- ========================================================================
      p.positions as positions_raw,
      p.positions::text as positions_json,
      
      -- Extract primary position (assuming first in list)
      (p.positions->0->>'code')::TEXT as primary_position_code,
      (p.positions->0->>'name')::TEXT as primary_position_name,
      
      -- ========================================================================
      -- TEAM IDENTIFICATION (via current_team_id)
      -- ========================================================================
      t.id as team_id,
      t.name as team_name,
      t.brand as team_brand,
      
      -- ========================================================================
      -- TEAM JSON: providers (Provider mappings)
      -- ========================================================================
      t.providers as providers_raw,
      t.providers::text as providers_json,
      
      -- Extract individual provider IDs
      (t.providers->>'SportsDynamics')::TEXT as provider_sportsdynamics_id,
      (t.providers->>'Perform')::TEXT as provider_perform_id,
      (t.providers->>'SecondSpectrum')::TEXT as provider_secondspectrum_id,
      
      -- ========================================================================
      -- TIMESTAMPS
      -- ========================================================================
      p.created_at as player_created_at,
      p.updated_at as player_updated_at,
      t.created_at as team_created_at,
      t.updated_at as team_updated_at
      
    FROM players p
    LEFT JOIN teams t ON p.current_team_id = t.id
    
    WHERE p.id IS NOT NULL
    ORDER BY p.name, t.name;
    """)


def downgrade():
    """Drop v_players_teams_full VIEW"""
    op.execute("DROP VIEW IF EXISTS v_players_teams_full CASCADE")
