"""add_prefix_query_optimization_indexes

Revision ID: 1a5ee6dfa5a4
Revises: 9bd71a7c2a0d
Create Date: 2025-06-13 15:46:47.283867

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a5ee6dfa5a4"
down_revision: Union[str, None] = "9bd71a7c2a0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add optimized indexes for prefix queries and natural sorting."""

    # Optimized prefix index using text_pattern_ops for LIKE queries
    # This enables efficient prefix matching with LIKE 'prefix%'
    op.execute(
        """
        CREATE INDEX idx_media_objects_object_key_pattern 
        ON media_objects (object_key text_pattern_ops);
    """
    )

    # Composite index for prefix + natural sort ordering
    # This combines prefix filtering with the expensive regexp_replace sorting
    op.execute(
        """
        CREATE INDEX idx_media_objects_prefix_natural_sort 
        ON media_objects (
            object_key text_pattern_ops,
            regexp_replace(object_key, '(\\d+)', '000000000\\1', 'g')
        );
    """
    )

    # Path depth optimization - add a computed column for path depth
    # This helps with the "exclude subfolders" logic
    op.add_column("media_objects", sa.Column("path_depth", sa.Integer, nullable=True))

    # Update path_depth for existing records
    op.execute(
        """
        UPDATE media_objects 
        SET path_depth = array_length(string_to_array(object_key, '/'), 1);
    """
    )

    # Make path_depth NOT NULL after populating
    op.alter_column("media_objects", "path_depth", nullable=False)

    # Index on path_depth for efficient subfolder exclusion
    op.create_index("idx_media_objects_path_depth", "media_objects", ["path_depth"])

    # Composite index for prefix + path_depth (for excluding subfolders efficiently)
    op.execute(
        """
        CREATE INDEX idx_media_objects_prefix_depth_sort 
        ON media_objects (
            object_key text_pattern_ops,
            path_depth,
            regexp_replace(object_key, '(\\d+)', '000000000\\1', 'g')
        );
    """
    )


def downgrade() -> None:
    """Remove prefix query optimization indexes."""

    op.drop_index("idx_media_objects_prefix_depth_sort", table_name="media_objects")
    op.drop_index("idx_media_objects_path_depth", table_name="media_objects")
    op.drop_column("media_objects", "path_depth")
    op.drop_index("idx_media_objects_prefix_natural_sort", table_name="media_objects")
    op.drop_index("idx_media_objects_object_key_pattern", table_name="media_objects")
