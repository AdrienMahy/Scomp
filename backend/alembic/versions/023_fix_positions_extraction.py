"""Fix v_players_teams_full - Correct positions JSON extraction

Revision ID: 023_fix_positions_extraction
Revises: 022_add_players_teams_view
Create Date: 2026-09-07 17:30:00.000000

The positions JSON structure is:
{
  "items": [
    {
      "id": "...",
      "position": {
        "name": "Center Back",
        "code": "CB",
        "group": "Defender"
      }
    }
  ]
}

Fix the extraction path from positions->0->>'code' to 
positions->'items'->0->'position'->>'code'

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '023_fix_positions_extraction'
down_revision = '022_add_players_teams_view'
branch_labels = None
depends_on = None


def upgrade():
    """Fix position extraction in v_players_teams_full"""
    
    op.execute("""
    DROP VIEW IF EXISTS v_players_teams_full CASCADE;
    
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
      -- PLAYER JSON: positions (JSONB with items array)
      -- Structure: {"items": [{"id": "...", "position": {"name": "CB", "code": "CB", "group": "Defender"}}]}
      -- ========================================================================
      p.positions as positions_raw,
      p.positions::text as positions_json,
      
      -- Extract primary position (first item in positions.items array)
      (p.positions->'items'->0->'position'->>'code')::TEXT as primary_position_code,
      (p.positions->'items'->0->'position'->>'name')::TEXT as primary_position_name,
      (p.positions->'items'->0->'position'->>'group')::TEXT as primary_position_group,
      
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
    """Revert to previous version of v_players_teams_full"""
    
    op.execute("""
    DROP VIEW IF EXISTS v_players_teams_full CASCADE;
    
    CREATE OR REPLACE VIEW v_players_teams_full AS
    
    SELECT
      p.id as player_id,
      p.name as player_name,
      p.first_name,
      p.last_name,
      p.usage_name,
      p.photo,
      p.age,
      p.birthdate,
      p.current_team_id,
      p.current_team_brand,
      p.current_national_team_id,
      p.current_national_team_brand,
      p.nationalities as nationalities_raw,
      p.nationalities::text as nationalities_json,
      p.positions as positions_raw,
      p.positions::text as positions_json,
      (p.positions->0->>'code')::TEXT as primary_position_code,
      (p.positions->0->>'name')::TEXT as primary_position_name,
      t.id as team_id,
      t.name as team_name,
      t.brand as team_brand,
      t.providers as providers_raw,
      t.providers::text as providers_json,
      (t.providers->>'SportsDynamics')::TEXT as provider_sportsdynamics_id,
      (t.providers->>'Perform')::TEXT as provider_perform_id,
      (t.providers->>'SecondSpectrum')::TEXT as provider_secondspectrum_id,
      p.created_at as player_created_at,
      p.updated_at as player_updated_at,
      t.created_at as team_created_at,
      t.updated_at as team_updated_at
    FROM players p
    LEFT JOIN teams t ON p.current_team_id = t.id
    WHERE p.id IS NOT NULL
    ORDER BY p.name, t.name;
    """)
