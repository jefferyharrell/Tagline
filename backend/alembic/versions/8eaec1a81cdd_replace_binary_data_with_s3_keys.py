"""replace_binary_data_with_s3_keys

Revision ID: 8eaec1a81cdd
Revises: 3bc9e467391d
Create Date: 2025-05-29 17:18:32.247203

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8eaec1a81cdd"
down_revision: Union[str, None] = "3bc9e467391d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace binary data storage with S3 keys."""
    # Since we're doing a fresh ingest and data is already empty,
    # we can simply drop the data column and add the s3_key column

    # Drop the large binary data column
    op.drop_column("media_binaries", "data")

    # Add s3_key column to store the S3 object key
    op.add_column("media_binaries", sa.Column("s3_key", sa.String(255), nullable=False))

    # Add size column for monitoring
    op.add_column("media_binaries", sa.Column("size", sa.Integer(), nullable=True))

    # Create index on s3_key for faster lookups
    op.create_index("ix_media_binaries_s3_key", "media_binaries", ["s3_key"])


def downgrade() -> None:
    """Revert to binary data storage."""
    # Drop the S3-related columns and index
    op.drop_index("ix_media_binaries_s3_key", "media_binaries")
    op.drop_column("media_binaries", "size")
    op.drop_column("media_binaries", "s3_key")

    # Re-add the binary data column
    op.add_column("media_binaries", sa.Column("data", sa.LargeBinary(), nullable=False))
