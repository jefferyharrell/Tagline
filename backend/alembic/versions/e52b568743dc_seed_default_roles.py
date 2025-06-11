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
    # Define default roles
    default_roles = [
        ('administrator', 'Administrator with full access'),
        ('member', 'Basic JLLA member'),
        ('active', 'Active JLLA member'),
        ('sustainer', 'Sustainer JLLA member')
    ]
    
    # Insert default roles with ON CONFLICT DO NOTHING to handle existing records
    for role_name, description in default_roles:
        role_id = str(uuid.uuid4())
        op.execute(f"""
            INSERT INTO roles (id, name, description)
            VALUES ('{role_id}', '{role_name}', '{description}')
            ON CONFLICT (name) DO NOTHING
        """)


def downgrade() -> None:
    """Remove seeded default roles."""
    # Delete the default roles
    op.execute("DELETE FROM roles WHERE name IN ('administrator', 'member', 'active', 'sustainer')")
