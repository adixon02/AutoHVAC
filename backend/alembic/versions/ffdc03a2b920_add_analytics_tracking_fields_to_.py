"""Add analytics tracking fields to projects

Revision ID: ffdc03a2b920
Revises: fa3182972f61
Create Date: 2025-07-30 14:35:07.899381

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffdc03a2b920'
down_revision: Union[str, None] = 'fa3182972f61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add analytics tracking columns to projects table
    op.add_column('projects', sa.Column('client_ip', sa.String(length=45), nullable=True))
    op.add_column('projects', sa.Column('user_agent', sa.String(length=512), nullable=True))
    op.add_column('projects', sa.Column('referrer', sa.String(length=512), nullable=True))


def downgrade() -> None:
    # Remove analytics tracking columns from projects table
    op.drop_column('projects', 'referrer')
    op.drop_column('projects', 'user_agent')
    op.drop_column('projects', 'client_ip')
