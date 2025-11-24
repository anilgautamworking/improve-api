"""Add pdf_sources and pdf_chunks tables

Revision ID: 006_add_pdf_sources_and_chunks
Revises: 005_questions_fk_restrict
Create Date: 2025-11-24 06:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006_add_pdf_sources_and_chunks"
down_revision = "005_questions_fk_restrict"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pdf_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("drive_file_id", sa.String(length=255), nullable=True, unique=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("zip_name", sa.String(length=255), nullable=True),
        sa.Column("local_path", sa.String(length=500), nullable=False, unique=True),
        sa.Column("etag_hash", sa.String(length=128), nullable=True),
        sa.Column("subject", sa.String(length=100), nullable=True),
        sa.Column("grade", sa.String(length=50), nullable=True),
        sa.Column("book_title", sa.String(length=255), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="local_zip"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("total_pages", sa.Integer(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_reason", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ocr_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("idx_pdf_sources_status", "pdf_sources", ["status"])
    op.create_index("idx_pdf_sources_source_type", "pdf_sources", ["source_type"])
    op.create_index("idx_pdf_sources_subject_grade", "pdf_sources", ["subject", "grade"])
    op.create_index("idx_pdf_sources_etag", "pdf_sources", ["etag_hash"])

    op.create_table(
        "pdf_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pdf_source_id", sa.Integer(), sa.ForeignKey("pdf_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("chapter_title", sa.String(length=255), nullable=True),
        sa.Column("heading", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("error_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("pdf_source_id", "chunk_index", name="uq_pdf_chunk_source_index"),
    )

    op.create_index("idx_pdf_chunks_status", "pdf_chunks", ["status"])
    op.create_index("idx_pdf_chunks_source_idx", "pdf_chunks", ["pdf_source_id", "chunk_index"])


def downgrade() -> None:
    op.drop_index("idx_pdf_chunks_source_idx", table_name="pdf_chunks")
    op.drop_index("idx_pdf_chunks_status", table_name="pdf_chunks")
    op.drop_table("pdf_chunks")

    op.drop_index("idx_pdf_sources_etag", table_name="pdf_sources")
    op.drop_index("idx_pdf_sources_subject_grade", table_name="pdf_sources")
    op.drop_index("idx_pdf_sources_source_type", table_name="pdf_sources")
    op.drop_index("idx_pdf_sources_status", table_name="pdf_sources")
    op.drop_table("pdf_sources")
