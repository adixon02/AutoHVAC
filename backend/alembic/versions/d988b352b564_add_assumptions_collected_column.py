"""Add assumptions_collected column

Revision ID: d988b352b564
Revises: 769d7e700a57
Create Date: 2025-07-27 20:18:25.707306

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd988b352b564'
down_revision: Union[str, None] = '769d7e700a57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('assumptions_collected', sa.Boolean(), nullable=False, server_default=sa.text('false::bool')))


def downgrade() -> None:
    op.drop_column('projects', 'assumptions_collected')
