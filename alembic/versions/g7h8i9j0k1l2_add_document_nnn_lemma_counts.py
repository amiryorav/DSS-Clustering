"""Precompute documents.n_nnn and documents.n_lemma for the catalog.

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-23 17:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("n_nnn", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "documents",
        sa.Column("n_lemma", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        """
        UPDATE documents AS d
        SET n_nnn = sub.n
        FROM (
            SELECT document_id, COUNT(*) AS n
            FROM lemma_rows
            WHERE row_type = 'NNN'
            GROUP BY document_id
        ) AS sub
        WHERE d.id = sub.document_id
        """
    )
    op.execute(
        """
        UPDATE documents AS d
        SET n_lemma = sub.n
        FROM (
            SELECT document_id, COUNT(*) AS n
            FROM lemma_rows
            WHERE row_type = 'NNN'
              AND clean_lemma IS NOT NULL
              AND BTRIM(clean_lemma) <> ''
              AND LOWER(BTRIM(clean_lemma)) <> 'nan'
            GROUP BY document_id
        ) AS sub
        WHERE d.id = sub.document_id
        """
    )


def downgrade() -> None:
    op.drop_column("documents", "n_lemma")
    op.drop_column("documents", "n_nnn")
