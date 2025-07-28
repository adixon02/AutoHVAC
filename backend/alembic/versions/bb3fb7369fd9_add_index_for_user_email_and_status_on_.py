"""Add index for user_email and status on projects table

Revision ID: bb3fb7369fd9
Revises: 12d276ff92dc
Create Date: 2025-07-28 13:05:33.403238

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb3fb7369fd9'
down_revision: Union[str, None] = '12d276ff92dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create composite index for efficient rate limit queries
    op.create_index(
        'ix_projects_user_email_status',
        'projects',
        ['user_email', 'status'],
        unique=False
    )


def downgrade() -> None:
    # Drop the composite index
    op.drop_index('ix_projects_user_email_status', table_name='projects')
