"""Add assumptions_collected column

Revision ID: d988b352b564
Revises: 769d7e700a57
Create Date: 2025-07-27 20:18:25.707306

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = 'd988b352b564'
down_revision: Union[str, None] = '769d7e700a57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column already exists before adding it
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Get existing columns in projects table
    try:
        cols = {c["name"] for c in inspector.get_columns("projects")}
        if "assumptions_collected" not in cols:
            op.add_column(
                'projects', 
                sa.Column(
                    'assumptions_collected', 
                    sa.Boolean(), 
                    nullable=False, 
                    server_default=text('false')
                )
            )
    except Exception:
        # If table doesn't exist yet, this will be handled by earlier migrations
        # Just proceed with adding the column
        op.add_column(
            'projects', 
            sa.Column(
                'assumptions_collected', 
                sa.Boolean(), 
                nullable=False, 
                server_default=text('false')
            )
        )


def downgrade() -> None:
    # Check if column exists before dropping it
    conn = op.get_bind()
    inspector = inspect(conn)
    
    try:
        cols = {c["name"] for c in inspector.get_columns("projects")}
        if "assumptions_collected" in cols:
            op.drop_column('projects', 'assumptions_collected')
    except Exception:
        # If table doesn't exist, nothing to drop
        pass
