"""Add planning exercises and over-allocation support

Revision ID: 002_planning_exercises
Revises: 001_project_hierarchy
Create Date: 2026-02-03

This migration adds:
- planning_exercises table for multi-project staffing planning
- planning_projects table for projects within planning exercises
- planning_roles table for role requirements with offsets and overlap modes
- allow_over_allocation column to assignments table
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_planning_exercises'
down_revision = '001_project_hierarchy'
branch_labels = None
depends_on = None


def upgrade():
    # Add allow_over_allocation column to assignments table
    op.add_column('assignments', sa.Column('allow_over_allocation', sa.Boolean(), nullable=True, server_default='false'))
    
    # Create planning_exercises table
    op.create_table(
        'planning_exercises',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_planning_exercises_created_by'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for status filtering
    op.create_index('ix_planning_exercises_status', 'planning_exercises', ['status'])
    op.create_index('ix_planning_exercises_created_by', 'planning_exercises', ['created_by'])
    
    # Create planning_projects table
    op.create_table(
        'planning_projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('duration_months', sa.Integer(), nullable=False, server_default='12'),
        sa.Column('location', sa.String(200), nullable=True),
        sa.Column('budget', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['exercise_id'], ['planning_exercises.id'], name='fk_planning_projects_exercise_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for exercise_id filtering
    op.create_index('ix_planning_projects_exercise_id', 'planning_projects', ['exercise_id'])
    
    # Create planning_roles table
    op.create_table(
        'planning_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('planning_project_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('start_month_offset', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('end_month_offset', sa.Integer(), nullable=True),
        sa.Column('allocation_percentage', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('hours_per_week', sa.Float(), nullable=False, server_default='40.0'),
        sa.Column('overlap_mode', sa.String(20), nullable=False, server_default='efficient'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['planning_project_id'], ['planning_projects.id'], name='fk_planning_roles_planning_project_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name='fk_planning_roles_role_id'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient queries
    op.create_index('ix_planning_roles_planning_project_id', 'planning_roles', ['planning_project_id'])
    op.create_index('ix_planning_roles_role_id', 'planning_roles', ['role_id'])
    
    # Update existing assignments to have allow_over_allocation = False
    op.execute("UPDATE assignments SET allow_over_allocation = false WHERE allow_over_allocation IS NULL")


def downgrade():
    # Drop planning_roles table
    op.drop_index('ix_planning_roles_role_id', table_name='planning_roles')
    op.drop_index('ix_planning_roles_planning_project_id', table_name='planning_roles')
    op.drop_table('planning_roles')
    
    # Drop planning_projects table
    op.drop_index('ix_planning_projects_exercise_id', table_name='planning_projects')
    op.drop_table('planning_projects')
    
    # Drop planning_exercises table
    op.drop_index('ix_planning_exercises_created_by', table_name='planning_exercises')
    op.drop_index('ix_planning_exercises_status', table_name='planning_exercises')
    op.drop_table('planning_exercises')
    
    # Remove allow_over_allocation column from assignments
    op.drop_column('assignments', 'allow_over_allocation')

