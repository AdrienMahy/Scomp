"""Extend goals with own-goal and phase context.

Revision ID: 20261010_000000
Revises: 20261009_130000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20261010_000000"
down_revision = "20261009_130000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "goals",
        sa.Column(
            "opponent_team_id",
            sa.String(length=50),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_goals_opponent_team_id_teams",
        "goals",
        "teams",
        ["opponent_team_id"],
        ["id"],
    )
    op.add_column(
        "goals",
        sa.Column(
            "is_own_goal",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    for column in (
        "possession_id",
        "type_of_play_id",
        "phase_of_play_id",
        "individual_possession_id",
    ):
        op.add_column(
            "goals",
            sa.Column(column, postgresql.UUID(as_uuid=False), nullable=True),
        )
    for column in ("phase", "own_goal_context"):
        op.add_column(
            "goals",
            sa.Column(column, postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )

    op.create_index("idx_goals_opponent_team", "goals", ["opponent_team_id"])
    op.create_index("idx_goals_possession", "goals", ["possession_id"])
    op.create_index(
        "idx_goals_phase_jointure",
        "goals",
        ["phase_of_play_id", "type_of_play_id"],
    )
    op.create_index(
        "idx_goals_individual_possession",
        "goals",
        ["individual_possession_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_goals_individual_possession", table_name="goals")
    op.drop_index("idx_goals_phase_jointure", table_name="goals")
    op.drop_index("idx_goals_possession", table_name="goals")
    op.drop_index("idx_goals_opponent_team", table_name="goals")

    for column in (
        "own_goal_context",
        "phase",
        "individual_possession_id",
        "phase_of_play_id",
        "type_of_play_id",
        "possession_id",
        "is_own_goal",
    ):
        op.drop_column("goals", column)

    op.drop_constraint(
        "fk_goals_opponent_team_id_teams",
        "goals",
        type_="foreignkey",
    )
    op.drop_column("goals", "opponent_team_id")
