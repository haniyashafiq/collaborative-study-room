"""add role to users and creator_id to rooms

Revision ID: e855a67b0663
Revises: e2f9c4d4f8bb
Create Date: 2025-11-05 12:42:53.280986

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e855a67b0663'
down_revision: Union[str, Sequence[str], None] = 'e2f9c4d4f8bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add role column to users
    op.add_column('users', sa.Column('role', sa.String(), server_default='user'))

    # Step 1: Add creator_id column as nullable
    op.add_column(
        'rooms', 
        sa.Column('creator_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True)
    )

    # Step 2: Backfill existing rows (if needed)
    op.execute("UPDATE rooms SET creator_id = 1 WHERE creator_id IS NULL")

    # Step 3: Make creator_id non-nullable
    op.alter_column('rooms', 'creator_id', nullable=False)


def downgrade():
    op.drop_column('rooms', 'creator_id')
    op.drop_column('users', 'role')