"""Add users and manual_clusters

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-16 08:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("google_sub", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("local_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("display_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)
    op.create_index("ix_users_local_key", "users", ["local_key"], unique=True)

    op.create_table(
        "manual_clusters",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("document_ids", sa.JSON(), nullable=False),
        sa.Column("feature_mode", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "comparison_scope_type",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column(
            "comparison_scope_value",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_manual_clusters_user_id", "manual_clusters", ["user_id"])
    op.create_index("ix_manual_clusters_name", "manual_clusters", ["name"])
    op.create_unique_constraint(
        "uq_manual_clusters_user_name", "manual_clusters", ["user_id", "name"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_manual_clusters_user_name", "manual_clusters", type_="unique"
    )
    op.drop_index("ix_manual_clusters_name", table_name="manual_clusters")
    op.drop_index("ix_manual_clusters_user_id", table_name="manual_clusters")
    op.drop_table("manual_clusters")
    op.drop_index("ix_users_local_key", table_name="users")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_table("users")
