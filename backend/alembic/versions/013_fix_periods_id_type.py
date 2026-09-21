"""Change periods.id type from INTEGER to VARCHAR

Revision ID: 013_fix_periods_id_type
Revises: 012_add_missing_periods_columns
Create Date: 2026-08-27 10:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '013_fix_periods_id_type'
down_revision = '012_add_missing_periods_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the foreign key constraint in game_score_evolution first
    op.drop_constraint('game_score_evolution_period_id_fkey', 'game_score_evolution', type_='foreignkey')
    
    # Drop the primary key constraint in periods
    op.drop_constraint('periods_pkey', 'periods', type_='primary')
    
    # Change periods.id type from INTEGER to VARCHAR(50)
    op.alter_column(
        'periods',
        'id',
        existing_type=sa.Integer(),
        type_=sa.String(length=50),
        existing_nullable=False
    )
    
    # Change game_score_evolution.period_id type from INTEGER to VARCHAR(50)
    op.alter_column(
        'game_score_evolution',
        'period_id',
        existing_type=sa.Integer(),
        type_=sa.String(length=50),
        existing_nullable=False
    )
    
    # Recreate the primary key constraint in periods
    op.create_primary_key('periods_pkey', 'periods', ['id'])
    
    # Recreate the foreign key constraint in game_score_evolution
    op.create_foreign_key(
        'game_score_evolution_period_id_fkey',
        'game_score_evolution',
        'periods',
        ['period_id'],
        ['id']
    )


def downgrade():
    # Drop the foreign key constraint in game_score_evolution first
    op.drop_constraint('game_score_evolution_period_id_fkey', 'game_score_evolution', type_='foreignkey')
    
    # Drop the primary key constraint in periods
    op.drop_constraint('periods_pkey', 'periods', type_='primary')
    
    # Change periods.id type back to INTEGER
    op.alter_column(
        'periods',
        'id',
        existing_type=sa.String(length=50),
        type_=sa.Integer(),
        existing_nullable=False
    )
    
    # Change game_score_evolution.period_id type back to INTEGER
    op.alter_column(
        'game_score_evolution',
        'period_id',
        existing_type=sa.String(length=50),
        type_=sa.Integer(),
        existing_nullable=False
    )
    
    # Recreate the primary key constraint in periods
    op.create_primary_key('periods_pkey', 'periods', ['id'])
    
    # Recreate the foreign key constraint in game_score_evolution
    op.create_foreign_key(
        'game_score_evolution_period_id_fkey',
        'game_score_evolution',
        'periods',
        ['period_id'],
        ['id']
    )
