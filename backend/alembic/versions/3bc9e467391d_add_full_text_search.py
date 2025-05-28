"""add full text search

Revision ID: 3bc9e467391d
Revises: 2ab9e467391c
Create Date: 2025-05-27 17:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3bc9e467391d"
down_revision: Union[str, None] = "2ab9e467391c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add full-text search support to media_objects table."""
    
    # Create a function to generate the search vector from media object fields
    op.execute("""
        CREATE OR REPLACE FUNCTION media_object_search_vector(object_key text, metadata jsonb)
        RETURNS tsvector AS $$
        BEGIN
            RETURN (
                -- Weight A: description (highest priority)
                setweight(
                    to_tsvector('english', COALESCE(metadata->>'description', '')), 
                    'A'
                ) ||
                -- Weight B: keywords (medium priority)
                setweight(
                    to_tsvector('english', COALESCE(
                        array_to_string(
                            ARRAY(SELECT jsonb_array_elements_text(metadata->'keywords')), 
                            ' '
                        ), 
                        ''
                    )), 
                    'B'
                ) ||
                -- Weight C: filename without path and extension (lower priority)
                setweight(
                    to_tsvector('english', 
                        regexp_replace(
                            regexp_replace(object_key, '^.*/', ''),  -- Remove path
                            '\\.[^.]*$', ''  -- Remove extension
                        )
                    ), 
                    'C'
                )
            );
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
    """)
    
    # Add a generated column for the search vector
    op.execute("""
        ALTER TABLE media_objects 
        ADD COLUMN search_vector tsvector 
        GENERATED ALWAYS AS (
            media_object_search_vector(object_key, object_metadata)
        ) STORED;
    """)
    
    # Create a GIN index for fast full-text search
    op.create_index(
        'ix_media_objects_search_vector',
        'media_objects',
        ['search_vector'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    """Remove full-text search support."""
    
    # Drop indexes
    op.drop_index('ix_media_objects_search_vector')
    
    # Drop the generated column
    op.drop_column('media_objects', 'search_vector')
    
    # Drop the function
    op.execute("DROP FUNCTION IF EXISTS media_object_search_vector(text, jsonb);")