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
    # Add client tracking columns to projects table (check if they exist first)
    conn = op.get_bind()
    
    # Check if columns already exist
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'projects' 
        AND column_name IN ('client_ip', 'user_agent', 'referrer')
    """))
    existing_columns = {row[0] for row in result}
    
    # Only add columns that don't exist
    if 'client_ip' not in existing_columns:
        op.add_column('projects', sa.Column('client_ip', sa.VARCHAR(), nullable=True))
    if 'user_agent' not in existing_columns:
        op.add_column('projects', sa.Column('user_agent', sa.VARCHAR(), nullable=True))
    if 'referrer' not in existing_columns:
        op.add_column('projects', sa.Column('referrer', sa.VARCHAR(), nullable=True))


def downgrade() -> None:
    # Remove client tracking columns from projects table
    op.drop_column('projects', 'referrer')
    op.drop_column('projects', 'user_agent')
    op.drop_column('projects', 'client_ip')