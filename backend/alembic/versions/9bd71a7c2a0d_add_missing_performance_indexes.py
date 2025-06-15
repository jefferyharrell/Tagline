"""add_missing_performance_indexes

Revision ID: 9bd71a7c2a0d
Revises: e52b568743dc
Create Date: 2025-06-10 15:44:28.244302

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9bd71a7c2a0d"
down_revision: Union[str, None] = "e52b568743dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing performance indexes for frequently queried columns."""

    # Auth table indexes for common query patterns
    # ================================================

    # Users table - for sorting and filtering
    op.create_index("idx_users_lastname_firstname", "users", ["lastname", "firstname"])
    op.create_index("idx_users_is_active", "users", ["is_active"])
    op.create_index("idx_users_created_at", "users", ["created_at"])
    op.create_index("idx_users_stytch_user_id", "users", ["stytch_user_id"])

    # User roles association table - for role-based queries
    op.create_index("idx_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("idx_user_roles_role_id", "user_roles", ["role_id"])

    # Eligible emails - for batch operations
    op.create_index("idx_eligible_emails_batch_id", "eligible_emails", ["batch_id"])
    op.create_index("idx_eligible_emails_created_at", "eligible_emails", ["created_at"])

    # Media object indexes for performance
    # ====================================

    # File attributes for filtering and sorting
    op.create_index("idx_media_objects_file_size", "media_objects", ["file_size"])
    op.create_index(
        "idx_media_objects_file_mimetype", "media_objects", ["file_mimetype"]
    )
    op.create_index(
        "idx_media_objects_file_last_modified", "media_objects", ["file_last_modified"]
    )

    # Timestamps for sorting and analytics
    op.create_index("idx_media_objects_created_at", "media_objects", ["created_at"])
    op.create_index("idx_media_objects_updated_at", "media_objects", ["updated_at"])

    # Thumbnail and proxy keys for fast lookups
    op.create_index(
        "idx_media_objects_thumbnail_key", "media_objects", ["thumbnail_object_key"]
    )
    op.create_index(
        "idx_media_objects_proxy_key", "media_objects", ["proxy_object_key"]
    )

    # Composite indexes for common query patterns
    # ===========================================

    # Status + timestamps for dashboard queries
    op.create_index(
        "idx_media_objects_status_created",
        "media_objects",
        ["ingestion_status", "created_at"],
    )

    # Object key prefix + status for folder navigation
    op.create_index(
        "idx_media_objects_key_prefix_status",
        "media_objects",
        [sa.text("substring(object_key, 1, 100)"), "ingestion_status"],
    )

    # File type + size for analytics
    op.create_index(
        "idx_media_objects_mimetype_size",
        "media_objects",
        ["file_mimetype", "file_size"],
    )


def downgrade() -> None:
    """Remove performance indexes."""

    # Remove composite indexes
    op.drop_index("idx_media_objects_mimetype_size", table_name="media_objects")
    op.drop_index("idx_media_objects_key_prefix_status", table_name="media_objects")
    op.drop_index("idx_media_objects_status_created", table_name="media_objects")

    # Remove media object indexes
    op.drop_index("idx_media_objects_proxy_key", table_name="media_objects")
    op.drop_index("idx_media_objects_thumbnail_key", table_name="media_objects")
    op.drop_index("idx_media_objects_updated_at", table_name="media_objects")
    op.drop_index("idx_media_objects_created_at", table_name="media_objects")
    op.drop_index("idx_media_objects_file_last_modified", table_name="media_objects")
    op.drop_index("idx_media_objects_file_mimetype", table_name="media_objects")
    op.drop_index("idx_media_objects_file_size", table_name="media_objects")

    # Remove auth table indexes
    op.drop_index("idx_eligible_emails_created_at", table_name="eligible_emails")
    op.drop_index("idx_eligible_emails_batch_id", table_name="eligible_emails")
    op.drop_index("idx_user_roles_role_id", table_name="user_roles")
    op.drop_index("idx_user_roles_user_id", table_name="user_roles")
    op.drop_index("idx_users_stytch_user_id", table_name="users")
    op.drop_index("idx_users_created_at", table_name="users")
    op.drop_index("idx_users_is_active", table_name="users")
    op.drop_index("idx_users_lastname_firstname", table_name="users")
