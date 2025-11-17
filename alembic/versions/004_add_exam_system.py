"""Add exam system with exam-category mapping

Revision ID: 004_add_exam_system
Revises: 003_add_frontend_schema
Create Date: 2025-11-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_exam_system'
down_revision = '003_add_frontend_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create exams table
    op.create_table(
        'exams',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('category', sa.Text(), nullable=True),  # "Engineering", "Medical", etc.
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_exams_name', 'exams', ['name'], unique=True)

    # Create exam_category junction table (many-to-many)
    op.create_table(
        'exam_category',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('exam_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('exam_id', 'category_id', name='uq_exam_category')
    )
    op.create_index('idx_exam_category_exam_id', 'exam_category', ['exam_id'])
    op.create_index('idx_exam_category_category_id', 'exam_category', ['category_id'])
    op.create_index('idx_exam_category_composite', 'exam_category', ['exam_id', 'category_id'])

    # Add optional exam_id to users table (nullable, can be changed)
    op.add_column('users', sa.Column('exam_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_users_exam_id', 'users', 'exams', ['exam_id'], ['id'], ondelete='SET NULL')
    op.create_index('idx_users_exam_id', 'users', ['exam_id'])

    # Add role column to users table (for admin functionality)
    op.add_column('users', sa.Column('role', sa.Text(), server_default='user', nullable=False))
    op.create_index('idx_users_role', 'users', ['role'])

    # Insert initial exams
    op.execute("""
        INSERT INTO exams (name, category, description) VALUES
        ('JEE', 'Engineering', 'Joint Entrance Examination - Engineering'),
        ('NEET', 'Medical', 'National Eligibility cum Entrance Test - Medical'),
        ('UPSC', 'Civil Services', 'Union Public Service Commission - Civil Services'),
        ('Banking', 'Banking', 'Banking and Financial Services'),
        ('SSC', 'Government', 'Staff Selection Commission - Government Jobs')
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    # Drop indexes and foreign keys
    op.drop_index('idx_users_role', table_name='users')
    op.drop_index('idx_users_exam_id', table_name='users')
    op.drop_constraint('fk_users_exam_id', 'users', type_='foreignkey')
    
    # Drop columns
    op.drop_column('users', 'role')
    op.drop_column('users', 'exam_id')

    # Drop exam_category table
    op.drop_index('idx_exam_category_composite', table_name='exam_category')
    op.drop_index('idx_exam_category_category_id', table_name='exam_category')
    op.drop_index('idx_exam_category_exam_id', table_name='exam_category')
    op.drop_table('exam_category')

    # Drop exams table
    op.drop_index('ix_exams_name', table_name='exams')
    op.drop_table('exams')


