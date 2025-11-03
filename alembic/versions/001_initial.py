"""Initial database schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create daily_questions table
    op.create_table(
        'daily_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('date', sa.String(length=10), nullable=False),
        sa.Column('questions_json', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('total_questions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_daily_questions_id'), 'daily_questions', ['id'], unique=False)
    op.create_index(op.f('ix_daily_questions_source'), 'daily_questions', ['source'], unique=False)
    op.create_index(op.f('ix_daily_questions_category'), 'daily_questions', ['category'], unique=False)
    op.create_index(op.f('ix_daily_questions_date'), 'daily_questions', ['date'], unique=False)
    op.create_index('idx_source_date', 'daily_questions', ['source', 'date'], unique=False)
    op.create_index('idx_category_date', 'daily_questions', ['category', 'date'], unique=False)

    # Create article_logs table
    op.create_table(
        'article_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('questions_generated', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_url')
    )
    op.create_index(op.f('ix_article_logs_id'), 'article_logs', ['id'], unique=False)
    op.create_index(op.f('ix_article_logs_source_url'), 'article_logs', ['source_url'], unique=True)
    op.create_index(op.f('ix_article_logs_category'), 'article_logs', ['category'], unique=False)
    op.create_index(op.f('ix_article_logs_source'), 'article_logs', ['source'], unique=False)
    op.create_index(op.f('ix_article_logs_status'), 'article_logs', ['status'], unique=False)
    op.create_index('idx_status_source', 'article_logs', ['status', 'source'], unique=False)
    op.create_index('idx_processed_at', 'article_logs', ['processed_at'], unique=False)

    # Create metadata_summary table
    op.create_table(
        'metadata_summary',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.String(length=10), nullable=False),
        sa.Column('feeds_processed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('articles_fetched', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('articles_processed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('articles_failed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('articles_skipped', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('questions_generated', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('errors_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('processing_time_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index(op.f('ix_metadata_summary_id'), 'metadata_summary', ['id'], unique=False)
    op.create_index(op.f('ix_metadata_summary_date'), 'metadata_summary', ['date'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_metadata_summary_date'), table_name='metadata_summary')
    op.drop_index(op.f('ix_metadata_summary_id'), table_name='metadata_summary')
    op.drop_table('metadata_summary')
    op.drop_index('idx_processed_at', table_name='article_logs')
    op.drop_index('idx_status_source', table_name='article_logs')
    op.drop_index(op.f('ix_article_logs_status'), table_name='article_logs')
    op.drop_index(op.f('ix_article_logs_source'), table_name='article_logs')
    op.drop_index(op.f('ix_article_logs_category'), table_name='article_logs')
    op.drop_index(op.f('ix_article_logs_source_url'), table_name='article_logs')
    op.drop_index(op.f('ix_article_logs_id'), table_name='article_logs')
    op.drop_table('article_logs')
    op.drop_index('idx_category_date', table_name='daily_questions')
    op.drop_index('idx_source_date', table_name='daily_questions')
    op.drop_index(op.f('ix_daily_questions_date'), table_name='daily_questions')
    op.drop_index(op.f('ix_daily_questions_category'), table_name='daily_questions')
    op.drop_index(op.f('ix_daily_questions_source'), table_name='daily_questions')
    op.drop_index(op.f('ix_daily_questions_id'), table_name='daily_questions')
    op.drop_table('daily_questions')

