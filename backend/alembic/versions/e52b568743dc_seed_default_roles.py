"""seed_default_roles

Revision ID: e52b568743dc
Revises: 72dd20886263
Create Date: 2025-06-10 15:20:06.829686

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String
import uuid


# revision identifiers, used by Alembic.
revision: str = 'e52b568743dc'
down_revision: Union[str, None] = '72dd20886263'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed default roles for the authentication system."""
    # Create a table reference for bulk operations
    roles_table = table('roles',
        column('id', String),
        column('name', String),
        column('description', String)
    )
    
    # Define default roles
    default_roles = [
        {
            'id': str(uuid.uuid4()),
            'name': 'administrator',
            'description': 'Administrator with full access'
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'member',
            'description': 'Basic JLLA member'
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'active',
            'description': 'Active JLLA member'
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'sustainer',
            'description': 'Sustainer JLLA member'
        }
    ]
    
    # Insert default roles
    op.bulk_insert(roles_table, default_roles)


def downgrade() -> None:
    """Remove seeded default roles."""
    # Delete the default roles
    op.execute("DELETE FROM roles WHERE name IN ('administrator', 'member', 'active', 'sustainer')")
