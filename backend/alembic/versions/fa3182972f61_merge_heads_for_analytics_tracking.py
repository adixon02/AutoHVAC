"""Merge heads for analytics tracking

Revision ID: fa3182972f61
Revises: add_audit_tables, bb3fb7369fd9
Create Date: 2025-07-30 14:35:02.484741

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa3182972f61'
down_revision: Union[str, None] = ('add_audit_tables', 'bb3fb7369fd9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
