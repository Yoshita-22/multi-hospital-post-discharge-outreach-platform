"""Add CLAIMED status

Revision ID: f98bcb8fca67
Revises: e35c34ec3717
Create Date: 2026-09-14 11:39:16.423682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f98bcb8fca67'
down_revision: Union[str, None] = 'e35c34ec3717'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use execute to alter the enum type directly in Postgres
    op.execute("ALTER TYPE queueitemstatus_enum ADD VALUE IF NOT EXISTS 'CLAIMED'")


def downgrade() -> None:
    # Downgrading an enum in postgres is non-trivial, so we typically pass
    # or remove rows with CLAIMED and then rename/recreate the type. 
    # For prototype safety, we will leave it as-is.
    pass
