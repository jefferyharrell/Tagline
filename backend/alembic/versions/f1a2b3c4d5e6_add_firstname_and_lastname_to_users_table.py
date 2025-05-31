"""add firstname and lastname to users table

Revision ID: f1a2b3c4d5e6
Revises: e05b1143264b
Create Date: 2025-05-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = '8eaec1a81cdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add firstname and lastname columns to users table
    op.add_column('users', sa.Column('firstname', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('lastname', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove firstname and lastname columns from users table
    op.drop_column('users', 'lastname')
    op.drop_column('users', 'firstname')