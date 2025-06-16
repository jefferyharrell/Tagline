"""add move detection fields to media objects

Revision ID: 139d399f7ea1
Revises: 1a5ee6dfa5a4
Create Date: 2025-06-16 11:27:40.415226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '139d399f7ea1'
down_revision: Union[str, None] = '1a5ee6dfa5a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add move detection fields to media_objects table
    op.add_column('media_objects', sa.Column('content_hash', sa.String(length=64), nullable=True))
    op.add_column('media_objects', sa.Column('provider_file_id', sa.String(length=255), nullable=True))
    op.add_column('media_objects', sa.Column('provider_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('media_objects', sa.Column('previous_object_keys', postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column('media_objects', sa.Column('moved_from', sa.String(length=255), nullable=True))
    op.add_column('media_objects', sa.Column('move_detected_at', sa.DateTime(), nullable=True))
    op.add_column('media_objects', sa.Column('is_copy', sa.Boolean(), nullable=True, server_default='false'))
    
    # Create indexes for efficient lookups
    op.create_index(op.f('ix_media_objects_content_hash'), 'media_objects', ['content_hash'], unique=False)
    op.create_index(op.f('ix_media_objects_provider_file_id'), 'media_objects', ['provider_file_id'], unique=False)
    
    # Composite index for hash + size lookups (common query pattern)
    op.create_index('ix_media_objects_content_hash_file_size', 'media_objects', ['content_hash', 'file_size'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index('ix_media_objects_content_hash_file_size', table_name='media_objects')
    op.drop_index(op.f('ix_media_objects_provider_file_id'), table_name='media_objects')
    op.drop_index(op.f('ix_media_objects_content_hash'), table_name='media_objects')
    
    # Drop columns
    op.drop_column('media_objects', 'is_copy')
    op.drop_column('media_objects', 'move_detected_at')
    op.drop_column('media_objects', 'moved_from')
    op.drop_column('media_objects', 'previous_object_keys')
    op.drop_column('media_objects', 'provider_metadata')
    op.drop_column('media_objects', 'provider_file_id')
    op.drop_column('media_objects', 'content_hash')
