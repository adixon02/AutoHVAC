"""Add progress tracking fields to Project model

Revision ID: add_progress_tracking
Revises: cf60711350c0
Create Date: 2025-07-28 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_progress_tracking'
down_revision = 'cf60711350c0'
branch_labels = None
depends_on = None


def upgrade():
    """Add progress tracking fields"""
    # Add progress tracking fields to projects table
    op.add_column('projects', sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('projects', sa.Column('current_stage', sa.String(length=255), nullable=True, server_default='initializing'))


def downgrade():
    """Remove progress tracking fields"""
    op.drop_column('projects', 'current_stage')
    op.drop_column('projects', 'progress_percent')