"""Add thumbnail_mimetype

Revision ID: e05b1143264b
Revises: cf52e411bb53
Create Date: 2025-05-01 22:33:07.285105

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e05b1143264b"
down_revision: Union[str, None] = "cf52e411bb53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "media_objects", sa.Column("thumbnail_mimetype", sa.String(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("media_objects", "thumbnail_mimetype")
    # ### end Alembic commands ###
