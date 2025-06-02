"""Drop all tables and recreate with object_key as primary key

Revision ID: 8915ed909a0a
Revises: f1a2b3c4d5e6
Create Date: 2025-01-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8915ed909a0a'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop all existing tables in reverse order of dependencies
    op.drop_table('media_binaries')
    op.drop_table('media_objects')
    
    # Create media_objects table with object_key as primary key
    op.create_table('media_objects',
        sa.Column('object_key', sa.String(length=255), nullable=False),
        sa.Column('ingestion_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('object_metadata', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_mimetype', sa.String(length=255), nullable=True),
        sa.Column('file_last_modified', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('object_key')
    )
    
    # Create indexes
    op.create_index(op.f('ix_media_objects_ingestion_status'), 'media_objects', ['ingestion_status'], unique=False)
    op.create_index(op.f('ix_media_objects_created_at'), 'media_objects', ['created_at'], unique=False)
    op.create_index(op.f('ix_media_objects_updated_at'), 'media_objects', ['updated_at'], unique=False)
    
    # Create media_binaries table with foreign key to object_key
    op.create_table('media_binaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('media_object_key', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('s3_key', sa.String(length=255), nullable=False),
        sa.Column('size', sa.Integer(), nullable=True),
        sa.Column('mimetype', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['media_object_key'], ['media_objects.object_key'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('media_object_key', 'type', name='uq_media_object_type')
    )
    
    # Create indexes
    op.create_index(op.f('ix_media_binaries_media_object_key'), 'media_binaries', ['media_object_key'], unique=False)
    op.create_index(op.f('ix_media_binaries_s3_key'), 'media_binaries', ['s3_key'], unique=False)
    
    # Add full-text search columns and indexes
    op.add_column('media_objects', sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True))
    op.create_index('idx_media_objects_search_vector', 'media_objects', ['search_vector'], unique=False, postgresql_using='gin')
    
    # Create or update the trigger function for full-text search
    op.execute("""
        CREATE OR REPLACE FUNCTION update_media_objects_search_vector() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('english', coalesce(NEW.object_key, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.object_metadata->>'description', '')), 'B') ||
                setweight(to_tsvector('english', coalesce(array_to_string(ARRAY(SELECT jsonb_array_elements_text(NEW.object_metadata->'keywords')), ' '), '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create the trigger
    op.execute("""
        CREATE TRIGGER update_media_objects_search_vector_trigger
        BEFORE INSERT OR UPDATE ON media_objects
        FOR EACH ROW EXECUTE FUNCTION update_media_objects_search_vector();
    """)


def downgrade() -> None:
    # Drop triggers and functions
    op.execute("DROP TRIGGER IF EXISTS update_media_objects_search_vector_trigger ON media_objects")
    op.execute("DROP FUNCTION IF EXISTS update_media_objects_search_vector()")
    
    # Drop tables
    op.drop_table('media_binaries')
    op.drop_table('media_objects')
    
    # Recreate original tables with UUID primary keys
    op.create_table('media_objects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('object_key', sa.String(length=255), nullable=False),
        sa.Column('object_metadata', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('object_key')
    )
    
    op.create_table('media_binaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('media_object_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('s3_key', sa.String(length=255), nullable=False),
        sa.Column('size', sa.Integer(), nullable=True),
        sa.Column('mimetype', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['media_object_id'], ['media_objects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('media_object_id', 'type', name='uq_media_object_type')
    )