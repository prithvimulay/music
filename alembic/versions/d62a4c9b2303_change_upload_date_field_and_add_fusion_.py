"""change_upload_date_field_and_add_fusion_fields_in_audio_files

Revision ID: d62a4c9b2303
Revises: ebc24a9539ea
Create Date: 2025-05-16 18:15:45.903472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd62a4c9b2303'
down_revision: Union[str, None] = 'ebc24a9539ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
