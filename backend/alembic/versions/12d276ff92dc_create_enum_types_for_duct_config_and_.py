"""Create enum types for duct_config and heating_fuel

Revision ID: 12d276ff92dc
Revises: cf60711350c0
Create Date: 2025-07-28 01:38:35.467971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12d276ff92dc'
down_revision: Union[str, None] = '458d242aaf4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types that PostgreSQL expects (idempotent)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ductconfig AS ENUM ('ducted_attic', 'ducted_crawl', 'ductless');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE heatingfuel AS ENUM ('gas', 'heat_pump', 'electric');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE jobstatus AS ENUM ('pending', 'processing', 'completed', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)


def downgrade() -> None:
    # Drop enum types  
    op.execute("DROP TYPE IF EXISTS ductconfig")
    op.execute("DROP TYPE IF EXISTS heatingfuel")
    op.execute("DROP TYPE IF EXISTS jobstatus")
