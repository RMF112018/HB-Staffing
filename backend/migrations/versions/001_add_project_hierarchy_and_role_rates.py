"""Add project hierarchy and role rates

Revision ID: 001_project_hierarchy
Revises: 
Create Date: 2026-02-02

This migration adds:
- parent_project_id and is_folder columns to projects table for hierarchy support
- project_role_rates table for project-specific billable rates per role
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_project_hierarchy'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add hierarchy columns to projects table
    op.add_column('projects', sa.Column('parent_project_id', sa.Integer(), nullable=True))
    op.add_column('projects', sa.Column('is_folder', sa.Boolean(), nullable=True, server_default='false'))
    
    # Add foreign key constraint for self-referential relationship
    op.create_foreign_key(
        'fk_projects_parent_project_id',
        'projects',
        'projects',
        ['parent_project_id'],
        ['id']
    )
    
    # Create index for parent_project_id for efficient hierarchy queries
    op.create_index('ix_projects_parent_project_id', 'projects', ['parent_project_id'])
    
    # Create project_role_rates table
    op.create_table(
        'project_role_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('billable_rate', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_project_role_rates_project_id'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name='fk_project_role_rates_role_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'role_id', name='unique_project_role_rate')
    )
    
    # Create indexes for efficient lookups
    op.create_index('ix_project_role_rates_project_id', 'project_role_rates', ['project_id'])
    op.create_index('ix_project_role_rates_role_id', 'project_role_rates', ['role_id'])
    
    # Update existing projects to have is_folder = False
    op.execute("UPDATE projects SET is_folder = false WHERE is_folder IS NULL")


def downgrade():
    # Drop project_role_rates table
    op.drop_index('ix_project_role_rates_role_id', table_name='project_role_rates')
    op.drop_index('ix_project_role_rates_project_id', table_name='project_role_rates')
    op.drop_table('project_role_rates')
    
    # Drop hierarchy columns from projects table
    op.drop_index('ix_projects_parent_project_id', table_name='projects')
    op.drop_constraint('fk_projects_parent_project_id', 'projects', type_='foreignkey')
    op.drop_column('projects', 'is_folder')
    op.drop_column('projects', 'parent_project_id')

