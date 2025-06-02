"""Add enhanced fusion status tracking

Revision ID: b19790e8405d
Revises: 
Create Date: 2025-05-16 18:41:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b19790e8405d'
down_revision = None  # Replace with your actual previous migration ID
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns for enhanced status tracking
    op.add_column('fusions', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('fusions', sa.Column('progress', sa.Integer(), nullable=False, server_default='0'))
    
    # If you need to modify the status column to use the new values, you can do it manually
    # For example, update any existing records to use the new status values
    # op.execute("UPDATE fusions SET status = 'pending' WHERE status = 'PENDING'")


def downgrade():
    # Remove the new columns
    op.drop_column('fusions', 'progress')
    op.drop_column('fusions', 'error_message')
