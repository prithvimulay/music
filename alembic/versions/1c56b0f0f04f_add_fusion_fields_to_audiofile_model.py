"""Add fusion fields to AudioFile model

Revision ID: 1c56b0f0f04f
Revises: c3dca1aa56d6
Create Date: 2025-05-13 14:20:49.486554

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c56b0f0f04f'
down_revision: Union[str, None] = 'c3dca1aa56d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('audiofile', sa.Column('is_fusion', sa.Boolean(), nullable=True))
    op.add_column('audiofile', sa.Column('source_track1_id', sa.String(), nullable=True))
    op.add_column('audiofile', sa.Column('source_track2_id', sa.String(), nullable=True))
    op.add_column('audiofile', sa.Column('fusion_metadata', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('audiofile', 'fusion_metadata')
    op.drop_column('audiofile', 'source_track2_id')
    op.drop_column('audiofile', 'source_track1_id')
    op.drop_column('audiofile', 'is_fusion')
    # ### end Alembic commands ###
