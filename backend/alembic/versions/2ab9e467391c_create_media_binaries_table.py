"""create media_binaries table

Revision ID: 2ab9e467391c
Revises: 9a5ab5704ada
Create Date: 2025-05-27 15:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ab9e467391c"
down_revision: Union[str, None] = "9a5ab5704ada"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create media_binaries table and migrate data."""
    # Create the new media_binaries table
    op.create_table(
        'media_binaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('media_object_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('mimetype', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['media_object_id'], ['media_objects.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('media_object_id', 'type', name='uq_media_object_type')
    )
    
    # Create index on media_object_id for faster lookups
    op.create_index('ix_media_binaries_media_object_id', 'media_binaries', ['media_object_id'])
    
    # Migrate existing data - since this is test data, we'll do a simple migration
    # In production, you'd want to batch this
    op.execute("""
        INSERT INTO media_binaries (id, media_object_id, type, data, mimetype, created_at)
        SELECT 
            gen_random_uuid(),
            id,
            'thumbnail',
            thumbnail,
            COALESCE(thumbnail_mimetype, 'image/jpeg'),
            created_at
        FROM media_objects
        WHERE thumbnail IS NOT NULL
    """)
    
    op.execute("""
        INSERT INTO media_binaries (id, media_object_id, type, data, mimetype, created_at)
        SELECT 
            gen_random_uuid(),
            id,
            'proxy',
            proxy,
            COALESCE(proxy_mimetype, 'image/jpeg'),
            created_at
        FROM media_objects
        WHERE proxy IS NOT NULL
    """)
    
    # Now drop the old columns from media_objects
    op.drop_column('media_objects', 'thumbnail')
    op.drop_column('media_objects', 'thumbnail_mimetype')
    op.drop_column('media_objects', 'proxy')
    op.drop_column('media_objects', 'proxy_mimetype')


def downgrade() -> None:
    """Revert to storing binaries in media_objects table."""
    # Add columns back to media_objects
    op.add_column('media_objects', sa.Column('thumbnail', sa.LargeBinary(), nullable=True))
    op.add_column('media_objects', sa.Column('thumbnail_mimetype', sa.String(), nullable=True))
    op.add_column('media_objects', sa.Column('proxy', sa.LargeBinary(), nullable=True))
    op.add_column('media_objects', sa.Column('proxy_mimetype', sa.String(), nullable=True))
    
    # Migrate data back (for test purposes, we'll just do thumbnails and proxies)
    op.execute("""
        UPDATE media_objects mo
        SET 
            thumbnail = mb.data,
            thumbnail_mimetype = mb.mimetype
        FROM media_binaries mb
        WHERE mo.id = mb.media_object_id AND mb.type = 'thumbnail'
    """)
    
    op.execute("""
        UPDATE media_objects mo
        SET 
            proxy = mb.data,
            proxy_mimetype = mb.mimetype
        FROM media_binaries mb
        WHERE mo.id = mb.media_object_id AND mb.type = 'proxy'
    """)
    
    # Drop the media_binaries table
    op.drop_index('ix_media_binaries_media_object_id')
    op.drop_table('media_binaries')