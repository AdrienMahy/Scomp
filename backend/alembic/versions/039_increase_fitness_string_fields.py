"""Increase VARCHAR(50) fields in player_fitness_runs to String(100)

Revision ID: 039_increase_fitness_string_fields
Revises: 038_increase_error_message_length
Create Date: 2026-09-09 11:57:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '039_increase_fitness_string_fields'
down_revision = '038_increase_error_message_length'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Increase VARCHAR(50) fields to String(100) in player_fitness_runs table"""
    
    # Increase spatial positioning fields
    op.alter_column('player_fitness_runs', 'start_third',
               existing_type=sa.String(50),
               type_=sa.String(100),
               existing_nullable=True)
    
    op.alter_column('player_fitness_runs', 'end_third',
               existing_type=sa.String(50),
               type_=sa.String(100),
               existing_nullable=True)
    
    op.alter_column('player_fitness_runs', 'start_channel',
               existing_type=sa.String(50),
               type_=sa.String(100),
               existing_nullable=True)
    
    op.alter_column('player_fitness_runs', 'end_channel',
               existing_type=sa.String(50),
               type_=sa.String(100),
               existing_nullable=True)
    
    # Increase acceleration level field
    op.alter_column('player_fitness_runs', 'acceleration_intensity_level',
               existing_type=sa.String(50),
               type_=sa.String(100),
               existing_nullable=True)
    
    # Increase tactical context fields
    op.alter_column('player_fitness_runs', 'context',
               existing_type=sa.String(50),
               type_=sa.String(100),
               existing_nullable=True)
    
    op.alter_column('player_fitness_runs', 'direction',
               existing_type=sa.String(50),
               type_=sa.String(100),
               existing_nullable=True)
    
    op.alter_column('player_fitness_runs', 'possession_label',
               existing_type=sa.String(50),
               type_=sa.String(100),
               existing_nullable=True)


def downgrade() -> None:
    """Revert VARCHAR fields back to String(50)"""
    
    op.alter_column('player_fitness_runs', 'start_third',
               existing_type=sa.String(100),
               type_=sa.String(50),
               existing_nullable=True)
    
    op.alter_column('player_fitness_runs', 'end_third',
               existing_type=sa.String(100),
               type_=sa.String(50),
               existing_nullable=True)
    
    op.alter_column('player_fitness_runs', 'start_channel',
               existing_type=sa.String(100),
               type_=sa.String(50),
               existing_nullable=True)
    
    op.alter_column('player_fitness_runs', 'end_channel',
               existing_type=sa.String(100),
               type_=sa.String(50),
               existing_nullable=True)
    
    op.alter_column('player_fitness_runs', 'acceleration_intensity_level',
               existing_type=sa.String(100),
               type_=sa.String(50),
               existing_nullable=True)
    
    op.alter_column('player_fitness_runs', 'context',
               existing_type=sa.String(100),
               type_=sa.String(50),
               existing_nullable=True)
    
    op.alter_column('player_fitness_runs', 'direction',
               existing_type=sa.String(100),
               type_=sa.String(50),
               existing_nullable=True)
    
    op.alter_column('player_fitness_runs', 'possession_label',
               existing_type=sa.String(100),
               type_=sa.String(50),
               existing_nullable=True)
