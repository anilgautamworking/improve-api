"""Add articles table

Revision ID: 002_add_articles_table
Revises: 001_initial
Create Date: 2023-10-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_articles_table'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('published_date', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_articles_id'), 'articles', ['id'], unique=False)
    op.create_index(op.f('ix_articles_url'), 'articles', ['url'], unique=True)
    op.create_index(op.f('ix_articles_source'), 'articles', ['source'], unique=False)
    op.create_index(op.f('ix_articles_category'), 'articles', ['category'], unique=False)
    op.create_index(op.f('ix_articles_published_date'), 'articles', ['published_date'], unique=False)
    op.create_index('idx_source_category_date', 'articles', ['source', 'category', 'published_date'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_source_category_date', table_name='articles')
    op.drop_index(op.f('ix_articles_published_date'), table_name='articles')
    op.drop_index(op.f('ix_articles_category'), table_name='articles')
    op.drop_index(op.f('ix_articles_source'), table_name='articles')
    op.drop_index(op.f('ix_articles_url'), table_name='articles')
    op.drop_index(op.f('ix_articles_id'), table_name='articles')
    op.drop_table('articles')
