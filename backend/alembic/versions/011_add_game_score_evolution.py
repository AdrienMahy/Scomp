"""Add game_score_evolution table

Revision ID: 011_add_game_score_evolution
Revises: 010_add_scraping_tasks
Create Date: 2026-08-27 10:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011_add_game_score_evolution'
down_revision = '010_add_scraping_tasks'
branch_labels = None
depends_on = None


def upgrade():
    # Create game_score_evolution table
    op.create_table(
        'game_score_evolution',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('game_id', sa.String(length=50), nullable=False),
        sa.Column('score', sa.String(length=20), nullable=False),
        sa.Column('score_home', sa.Integer(), nullable=False),
        sa.Column('score_away', sa.Integer(), nullable=False),
        sa.Column('frame_start', sa.Integer(), nullable=False),
        sa.Column('frame_end', sa.Integer(), nullable=True),
        sa.Column('timestamp_start', sa.Float(), nullable=True),
        sa.Column('timestamp_end', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
        sa.ForeignKeyConstraint(['period_id'], ['periods.id'], )
    )
    
    # Create indexes
    op.create_index('ix_game_score_evolution_game_id', 'game_score_evolution', ['game_id'], unique=False)
    op.create_index('ix_game_score_evolution_period_id', 'game_score_evolution', ['period_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('ix_game_score_evolution_period_id', table_name='game_score_evolution')
    op.drop_index('ix_game_score_evolution_game_id', table_name='game_score_evolution')
    
    # Drop table
    op.drop_table('game_score_evolution')
