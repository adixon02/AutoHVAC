"""Add email_verification_tokens table

Revision ID: 8544ec44d179
Revises: 8f2c9d4e6a1b
Create Date: 2025-08-10 22:31:29.520920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8544ec44d179'
down_revision: Union[str, None] = '8f2c9d4e6a1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
