"""Change questions.category_id FK from CASCADE to RESTRICT

Revision ID: 005_change_questions_fk_to_restrict
Revises: 004_add_exam_system
Create Date: 2025-11-19 16:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_questions_fk_restrict'
down_revision = '004_add_exam_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing CASCADE foreign key constraint
    op.drop_constraint('questions_category_id_fkey', 'questions', type_='foreignkey')
    
    # Recreate with RESTRICT instead of CASCADE
    # This prevents category deletion if questions exist, even at database level
    op.create_foreign_key(
        'questions_category_id_fkey',
        'questions',
        'categories',
        ['category_id'],
        ['id'],
        ondelete='RESTRICT'
    )


def downgrade() -> None:
    # Revert back to CASCADE (not recommended, but for migration rollback)
    op.drop_constraint('questions_category_id_fkey', 'questions', type_='foreignkey')
    
    op.create_foreign_key(
        'questions_category_id_fkey',
        'questions',
        'categories',
        ['category_id'],
        ['id'],
        ondelete='CASCADE'
    )

