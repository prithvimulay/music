"""merge migration branches

Revision ID: 09e0fb3f5111
Revises: b19790e8405d, d62a4c9b2303
Create Date: 2025-05-17 03:04:23.425692

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09e0fb3f5111'
down_revision: Union[str, None] = ('b19790e8405d', 'd62a4c9b2303')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
