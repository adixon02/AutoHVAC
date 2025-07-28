"""add_progress_tracking_fields_to_projects

Revision ID: 458d242aaf4d
Revises: 12d276ff92dc
Create Date: 2025-07-28 09:13:10.124330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '458d242aaf4d'
down_revision: Union[str, None] = 'cf60711350c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add progress tracking fields to projects table (only if they don't exist)
    inspector = sa.inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('projects')]
    
    if 'progress_percent' not in columns:
        op.add_column(
            "projects",
            sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        )
    
    if 'current_stage' not in columns:
        op.add_column(
            "projects",
            sa.Column("current_stage", sa.String(length=50), nullable=False, server_default="'initializing'"),
        )


def downgrade() -> None:
    # Drop progress tracking fields if they exist
    inspector = sa.inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('projects')]
    
    if 'current_stage' in columns:
        op.drop_column('projects', 'current_stage')
    if 'progress_percent' in columns:
        op.drop_column('projects', 'progress_percent')
