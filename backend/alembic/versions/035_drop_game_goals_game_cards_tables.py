"""Drop obsolete game_goals and game_cards tables - migrated to events table"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '035_drop_game_goals_game_cards_tables'
down_revision = '034_add_possession_to_lineup_teams'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the view that depends on game_cards first
    op.execute("DROP VIEW IF EXISTS v_goalkeeper_events CASCADE")
    
    # Drop game_cards table
    op.drop_table('game_cards')
    # Drop game_goals table
    op.drop_table('game_goals')


def downgrade() -> None:
    # Recreate game_goals table
    op.create_table(
        'game_goals',
        sa.Column('id', sa.String(50), primary_key=True, nullable=False),
        sa.Column('game_id', sa.String(50), sa.ForeignKey('games.id'), nullable=False, index=True),
        sa.Column('player_id', sa.String(50), sa.ForeignKey('players.id'), nullable=False, index=True),
        sa.Column('team_id', sa.String(50), sa.ForeignKey('teams.id'), nullable=False, index=True),
        sa.Column('period', sa.Integer(), nullable=False),
        sa.Column('frame', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.Float(), nullable=True),
        sa.Column('own_goal', sa.Boolean(), default=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
    )
    
    # Recreate game_cards table
    op.create_table(
        'game_cards',
        sa.Column('id', sa.String(50), primary_key=True, nullable=False),
        sa.Column('game_id', sa.String(50), sa.ForeignKey('games.id'), nullable=False, index=True),
        sa.Column('player_id', sa.String(50), sa.ForeignKey('players.id'), nullable=False, index=True),
        sa.Column('team_id', sa.String(50), sa.ForeignKey('teams.id'), nullable=False, index=True),
        sa.Column('period', sa.Integer(), nullable=False),
        sa.Column('frame', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.Float(), nullable=True),
        sa.Column('card_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
    )
    
    # Recreate v_goalkeeper_events view
    op.execute("""
    CREATE OR REPLACE VIEW v_goalkeeper_events AS
    SELECT 
        'from_game_cards' as source,
        gc.id as event_id,
        gc.game_id,
        gc.player_id as goalkeeper_id,
        gc.team_id,
        gc.period,
        gc.frame,
        gc.timestamp,
        gc.card_type as event_type,
        'Card' as event_category,
        g.name as game_name,
        p.name as goalkeeper_name,
        t.name as team_name
    FROM game_cards gc
    LEFT JOIN games g ON gc.game_id = g.id
    LEFT JOIN players p ON gc.player_id = p.id
    LEFT JOIN teams t ON gc.team_id = t.id
    """)

