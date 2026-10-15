"""Add public-health knowledge documents and chunks."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0003_knowledge_base"
down_revision = "0002_doctors_appointments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())

    if "knowledge_documents" not in existing:
        op.create_table(
            "knowledge_documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("source_url", sa.String(500), nullable=False),
            sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("retrieval_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("version", sa.String(80), nullable=False, server_default="1.0"),
            sa.Column("licence", sa.String(220), nullable=False, server_default="review-required"),
            sa.Column("allowed_use", sa.Text(), nullable=False, server_default="internal evaluation"),
            sa.Column("provenance", sa.Text(), nullable=False, server_default=""),
            sa.Column("language", sa.String(20), nullable=False, server_default="en"),
            sa.Column("category", sa.String(80), nullable=False, server_default="public_health"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_knowledge_documents_title", "knowledge_documents", ["title"])

    if "knowledge_chunks" not in existing:
        op.create_table(
            "knowledge_chunks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "document_id",
                sa.Integer(),
                sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("embedding", sa.JSON(), nullable=True),
            sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("citation", sa.String(255), nullable=False, server_default=""),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_document_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index("ix_knowledge_documents_title", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
