"""Add RETRY_PENDING to OutboundQueue

Revision ID: 8161cf356f97
Revises: 7be020ae3ae7
Create Date: 2026-09-14 14:28:44.712413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8161cf356f97'
down_revision: Union[str, None] = '7be020ae3ae7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE queueitemstatus_enum ADD VALUE IF NOT EXISTS 'RETRY_PENDING'")

def downgrade() -> None:
    pass
