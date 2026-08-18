"""Add analysis_presets

Revision ID: e5f6a7b8c9d0
Revises: c3d4e5f6a7b8
Create Date: 2026-08-18 08:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_presets",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_analysis_presets_user_id", "analysis_presets", ["user_id"])
    op.create_index("ix_analysis_presets_name", "analysis_presets", ["name"])
    op.create_unique_constraint(
        "uq_analysis_presets_user_name", "analysis_presets", ["user_id", "name"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_analysis_presets_user_name", "analysis_presets", type_="unique"
    )
    op.drop_index("ix_analysis_presets_name", table_name="analysis_presets")
    op.drop_index("ix_analysis_presets_user_id", table_name="analysis_presets")
    op.drop_table("analysis_presets")
