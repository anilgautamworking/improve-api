"""Add frontend schema for user-facing quiz app

Revision ID: 003_add_frontend_schema
Revises: 002_add_articles_table
Create Date: 2025-11-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_frontend_schema'
down_revision = '002_add_articles_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_categories_name', 'categories', ['name'], unique=True)

    # Insert initial categories
    op.execute("""
        INSERT INTO categories (name, description) VALUES
        ('Current Affairs', 'Latest news and events from India and around the world'),
        ('India GK', 'General Knowledge about India - Geography, Polity, Governance'),
        ('History', 'Indian History - Ancient, Medieval, Modern and Freedom Struggle'),
        ('Economy', 'Indian Economy - Development, Banking, Fiscal Policy'),
        ('News This Month', 'Current month news and trending events'),
        ('News Last 3 Months', 'News and events from last 3 months')
        ON CONFLICT (name) DO NOTHING
    """)

    # Create questions table (frontend format)
    op.create_table(
        'questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_format', sa.Text(), server_default='multiple_choice', nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('option_a', sa.Text(), nullable=True),
        sa.Column('option_b', sa.Text(), nullable=True),
        sa.Column('option_c', sa.Text(), nullable=True),
        sa.Column('option_d', sa.Text(), nullable=True),
        sa.Column('correct_answer', sa.Text(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.Text(), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=True),  # Added: tracks which article source
        sa.Column('source_date', sa.String(length=10), nullable=True),  # Added: tracks article date
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.CheckConstraint("question_format IN ('multiple_choice', 'statement')", name='check_question_format'),
        sa.CheckConstraint("correct_answer IN ('a', 'b', 'c', 'd')", name='check_correct_answer'),
        sa.CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name='check_difficulty'),
        sa.CheckConstraint("points IN (10, 15, 20)", name='check_points')
    )
    op.create_index('idx_questions_category_id', 'questions', ['category_id'])
    op.create_index('idx_questions_format', 'questions', ['question_format'])
    op.create_index('idx_questions_source', 'questions', ['source'])
    op.create_index('idx_questions_source_date', 'questions', ['source_date'])
    op.create_index('idx_questions_created_at', 'questions', ['created_at'])

    # Create quiz_attempts table
    op.create_table(
        'quiz_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('score', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_questions', sa.Integer(), server_default='0', nullable=False),
        sa.Column('percentage', sa.Numeric(5, 2), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE')
    )
    op.create_index('idx_quiz_attempts_user_id', 'quiz_attempts', ['user_id'])

    # Create user_answers table
    op.create_table(
        'user_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('selected_answer', sa.Text(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE')
    )
    op.create_index('idx_user_answers_user_id', 'user_answers', ['user_id'])
    op.create_index('idx_user_answers_question_id', 'user_answers', ['question_id'])


def downgrade() -> None:
    # Drop in reverse order due to foreign key constraints
    op.drop_index('idx_user_answers_question_id', table_name='user_answers')
    op.drop_index('idx_user_answers_user_id', table_name='user_answers')
    op.drop_table('user_answers')

    op.drop_index('idx_quiz_attempts_user_id', table_name='quiz_attempts')
    op.drop_table('quiz_attempts')

    op.drop_index('idx_questions_created_at', table_name='questions')
    op.drop_index('idx_questions_source_date', table_name='questions')
    op.drop_index('idx_questions_source', table_name='questions')
    op.drop_index('idx_questions_format', table_name='questions')
    op.drop_index('idx_questions_category_id', table_name='questions')
    op.drop_table('questions')

    op.drop_index('ix_categories_name', table_name='categories')
    op.drop_table('categories')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')

