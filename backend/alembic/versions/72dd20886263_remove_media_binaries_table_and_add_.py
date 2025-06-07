"""remove media_binaries table and add object_key columns

Revision ID: 72dd20886263
Revises: add_performance_indexes
Create Date: 2025-06-06 23:44:03.850053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '72dd20886263'
down_revision: Union[str, None] = 'add_performance_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add object key columns and migrate data from media_binaries."""
    # Add new columns to media_objects
    op.add_column('media_objects', sa.Column('thumbnail_object_key', sa.String(255), nullable=True))
    op.add_column('media_objects', sa.Column('proxy_object_key', sa.String(255), nullable=True))
    
    # Migrate existing data from media_binaries to new columns
    op.execute("""
        UPDATE media_objects 
        SET thumbnail_object_key = mb.s3_key
        FROM media_binaries mb 
        WHERE mb.media_object_key = media_objects.object_key 
        AND mb.type = 'thumbnail'
    """)
    
    op.execute("""
        UPDATE media_objects 
        SET proxy_object_key = mb.s3_key
        FROM media_binaries mb 
        WHERE mb.media_object_key = media_objects.object_key 
        AND mb.type = 'proxy'
    """)
    
    # Drop the media_binaries table
    op.drop_table('media_binaries')


def downgrade() -> None:
    """Recreate media_binaries table and migrate data back."""
    # Recreate media_binaries table with correct schema
    op.create_table('media_binaries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('media_object_key', sa.String(255), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('s3_key', sa.String(255), nullable=False),
        sa.Column('size', sa.Integer(), nullable=True),
        sa.Column('mimetype', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['media_object_key'], ['media_objects.object_key'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('media_object_key', 'type', name='uq_media_object_type')
    )
    
    # Create indexes
    op.create_index('ix_media_binaries_media_object_key', 'media_binaries', ['media_object_key'])
    op.create_index('ix_media_binaries_type', 'media_binaries', ['type'])
    
    # Migrate data back from columns to table
    op.execute("""
        INSERT INTO media_binaries (id, media_object_key, type, s3_key, mimetype, created_at)
        SELECT 
            gen_random_uuid(),
            object_key,
            'thumbnail',
            thumbnail_object_key,
            'image/jpeg',
            created_at
        FROM media_objects 
        WHERE thumbnail_object_key IS NOT NULL
    """)
    
    op.execute("""
        INSERT INTO media_binaries (id, media_object_key, type, s3_key, mimetype, created_at)
        SELECT 
            gen_random_uuid(),
            object_key,
            'proxy', 
            proxy_object_key,
            'image/jpeg',
            created_at
        FROM media_objects 
        WHERE proxy_object_key IS NOT NULL
    """)
    
    # Drop the new columns
    op.drop_column('media_objects', 'proxy_object_key')
    op.drop_column('media_objects', 'thumbnail_object_key')