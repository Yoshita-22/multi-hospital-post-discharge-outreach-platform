"""Add new campaign status values

Revision ID: 7be020ae3ae7
Revises: f98bcb8fca67
Create Date: 2026-09-14 13:04:28.336422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7be020ae3ae7'
down_revision: Union[str, None] = 'f98bcb8fca67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use execute to alter the enum type directly in Postgres
    op.execute("ALTER TYPE campaignstatus_enum ADD VALUE IF NOT EXISTS 'READY'")
    op.execute("ALTER TYPE campaignstatus_enum ADD VALUE IF NOT EXISTS 'CANCELLED'")
    op.execute("ALTER TYPE campaignstatus_enum ADD VALUE IF NOT EXISTS 'FAILED'")

def downgrade() -> None:
    pass
