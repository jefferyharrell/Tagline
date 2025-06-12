"""Add performance indexes for media objects

Revision ID: add_performance_indexes
Revises: 8915ed909a0a
Create Date: 2025-06-04 13:55:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'add_performance_indexes'
down_revision: Union[str, None] = '8915ed909a0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for natural sorting and prefix filtering."""
    # Add index for object_key to speed up prefix filtering
    op.create_index('idx_media_objects_object_key', 'media_objects', ['object_key'])
    
    # Add functional index for natural sorting
    # This creates an index on the regex-replaced version of object_key
    op.execute("""
        CREATE INDEX idx_media_objects_natural_sort 
        ON media_objects (regexp_replace(object_key, '(\\d+)', '000000000\\1', 'g'))
    """)


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index('idx_media_objects_natural_sort', table_name='media_objects')
    op.drop_index('idx_media_objects_object_key', table_name='media_objects')