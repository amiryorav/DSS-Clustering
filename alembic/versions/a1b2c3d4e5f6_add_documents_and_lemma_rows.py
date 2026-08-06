"""Add documents and lemma_rows tables for corpus ingest.

Revision ID: a1b2c3d4e5f6
Revises: d4618c4753cd
Create Date: 2026-08-06 12:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d4618c4753cd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("book", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("corpus", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book"),
    )
    op.create_index(op.f("ix_documents_book"), "documents", ["book"], unique=False)
    op.create_index(op.f("ix_documents_corpus"), "documents", ["corpus"], unique=False)

    op.create_table(
        "lemma_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("text_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("verse_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("form", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("lemma", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("clean_lemma", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("row_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("pos", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("person", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("gender", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("number", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("tense", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("binyan", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("state", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("mood", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("subtype", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_lemma_rows_document_id"), "lemma_rows", ["document_id"], unique=False
    )
    op.create_index(
        op.f("ix_lemma_rows_text_id"), "lemma_rows", ["text_id"], unique=False
    )
    op.create_index(
        op.f("ix_lemma_rows_row_type"), "lemma_rows", ["row_type"], unique=False
    )
    op.create_index(
        "ix_lemma_rows_document_id_row_type",
        "lemma_rows",
        ["document_id", "row_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_lemma_rows_document_id_row_type", table_name="lemma_rows")
    op.drop_index(op.f("ix_lemma_rows_row_type"), table_name="lemma_rows")
    op.drop_index(op.f("ix_lemma_rows_text_id"), table_name="lemma_rows")
    op.drop_index(op.f("ix_lemma_rows_document_id"), table_name="lemma_rows")
    op.drop_table("lemma_rows")
    op.drop_index(op.f("ix_documents_corpus"), table_name="documents")
    op.drop_index(op.f("ix_documents_book"), table_name="documents")
    op.drop_table("documents")
