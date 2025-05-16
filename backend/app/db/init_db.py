"""
Database initialization and seeding utilities.

This module provides functions to initialize the database with default data,
such as seeding the default roles for the authentication system.
"""

import logging

from sqlalchemy.orm import Session

from app.auth_models import Role

logger = logging.getLogger(__name__)


def seed_default_roles(db: Session):
    """Seed the default roles for the authentication system."""
    logger.info("Seeding default roles...")

    # Use the class method from the Role model
    Role.seed_default_roles(db)

    logger.info("Default roles seeded successfully.")


def init_db(db: Session):
    """Initialize the database with default data."""
    logger.info("Initializing database...")

    # Seed default roles
    seed_default_roles(db)

    logger.info("Database initialization complete.")
