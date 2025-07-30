"""Add client tracking columns to projects table

Revision ID: 8f2c9d4e6a1b
Revises: ffdc03a2b920
Create Date: 2025-07-30 15:13:12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f2c9d4e6a1b'
down_revision: Union[str, None] = 'ffdc03a2b920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add client tracking columns to projects table
    op.add_column('projects', sa.Column('client_ip', sa.VARCHAR(), nullable=True))
    op.add_column('projects', sa.Column('user_agent', sa.VARCHAR(), nullable=True))
    op.add_column('projects', sa.Column('referrer', sa.VARCHAR(), nullable=True))


def downgrade() -> None:
    # Remove client tracking columns from projects table
    op.drop_column('projects', 'referrer')
    op.drop_column('projects', 'user_agent')
    op.drop_column('projects', 'client_ip')