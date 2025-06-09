"""
CSV utilities for user management.

This module provides functions for parsing and generating CSV files
for the user management system. Supports variable column format where
the first three columns are fixed (firstname, lastname, email) and
additional columns represent roles.
"""

import csv
import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)


async def parse_users_csv(file: UploadFile) -> List[Dict[str, Any]]:
    """
    Parse CSV with variable columns for user management.

    Expected format:
    firstname,lastname,email,[role1],[role2],...

    Args:
        file: Uploaded CSV file

    Returns:
        List of user dictionaries with keys: firstname, lastname, email, roles

    Raises:
        HTTPException: If CSV format is invalid
    """
    # Check file size (10MB limit)
    file_size = 0
    content = bytearray()

    while chunk := await file.read(8192):  # Read in chunks
        file_size += len(chunk)
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="CSV file size exceeds 10MB limit",
            )
        content.extend(chunk)

    # Reset file position
    await file.seek(0)

    try:
        # Decode content
        text_content = content.decode("utf-8-sig")  # Handle BOM if present

        # Parse CSV
        csv_reader = csv.reader(io.StringIO(text_content))

        # Skip comment lines and empty lines to find first data row
        first_row = None
        for row in csv_reader:
            # Skip empty rows
            if not row:
                continue
            # Skip comment lines (lines starting with #)
            if len(row) >= 1 and row[0].strip().startswith("#"):
                continue
            first_row = row
            break

        if not first_row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file is empty"
            )

        # Check if first row is header (contains "email" or starts with "firstname")
        is_header = len(first_row) >= 3 and (
            first_row[0].lower() == "firstname"
            or "email" in [col.lower() for col in first_row]
        )

        users = []
        row_number = 2 if is_header else 1

        # If not header, process first row
        if not is_header:
            if len(first_row) < 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Row 1: Insufficient columns. Expected at least 3 (firstname, lastname, email)",
                )

            user = {
                "firstname": first_row[0].strip(),
                "lastname": first_row[1].strip(),
                "email": first_row[2].strip().lower(),
                "roles": [role.strip() for role in first_row[3:] if role.strip()],
            }
            users.append(user)

        # Process remaining rows
        for row in csv_reader:
            # Skip empty rows
            if not row or all(not col.strip() for col in row):
                continue
            # Skip comment lines (lines starting with #)
            if len(row) >= 1 and row[0].strip().startswith("#"):
                continue

            if len(row) < 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Row {row_number}: Insufficient columns. Expected at least 3 (firstname, lastname, email)",
                )

            user = {
                "firstname": row[0].strip(),
                "lastname": row[1].strip(),
                "email": row[2].strip().lower(),
                "roles": [role.strip() for role in row[3:] if role.strip()],
            }

            # Validate email format (basic check)
            if not user["email"] or "@" not in user["email"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Row {row_number}: Invalid email format: {row[2]}",
                )

            users.append(user)
            row_number += 1

        if not users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid user data found in CSV",
            )

        logger.info(f"Successfully parsed {len(users)} users from CSV")
        return users

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file encoding error. Please ensure the file is UTF-8 encoded",
        )
    except csv.Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV parsing error: {str(e)}",
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Unexpected error parsing CSV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while parsing the CSV",
        )


def generate_users_csv(users: List[Any]) -> str:
    """
    Generate CSV content from user list with variable role columns.

    Args:
        users: List of User objects with roles relationship

    Returns:
        CSV content as string
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header with comment
    output.write("# Tagline User Management Export\n")
    output.write("# Format: firstname,lastname,email,[roles...]\n")
    output.write(f"# Generated at: {datetime.utcnow().isoformat()}\n\n")

    # Write header row
    writer.writerow(["firstname", "lastname", "email", "roles..."])

    # Sort users by lastname, then firstname
    sorted_users = sorted(
        users,
        key=lambda u: (
            (u.lastname or "").lower(),
            (u.firstname or "").lower(),
            u.email.lower(),
        ),
    )

    # Write user data
    for user in sorted_users:
        row = [user.firstname or "", user.lastname or "", user.email]

        # Add roles as additional columns
        # Sort roles for consistency (member first, then admin, then others)
        role_names = sorted(
            [role.name for role in user.roles],
            key=lambda r: (r != "member", r != "administrator", r),
        )
        row.extend(role_names)

        writer.writerow(row)

    return output.getvalue()


def validate_roles_against_db(
    csv_roles: Set[str], db_roles: Set[str]
) -> Tuple[Set[str], Set[str]]:
    """
    Validate role names from CSV against available roles in database.

    Args:
        csv_roles: Set of role names found in CSV
        db_roles: Set of valid role names from database

    Returns:
        Tuple of (valid_roles, invalid_roles)
    """
    # Case-insensitive comparison
    db_roles_lower = {role.lower(): role for role in db_roles}

    valid_roles = set()
    invalid_roles = set()

    for csv_role in csv_roles:
        role_lower = csv_role.lower()
        if role_lower in db_roles_lower:
            # Use the database version for consistent casing
            valid_roles.add(db_roles_lower[role_lower])
        else:
            invalid_roles.add(csv_role)

    return valid_roles, invalid_roles


def analyze_import_changes(
    csv_users: List[Dict[str, Any]], existing_users: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Analyze what changes would be made by importing CSV data.

    Args:
        csv_users: Parsed user data from CSV
        existing_users: Dict of existing users keyed by email

    Returns:
        Dictionary with keys: to_add, to_update, to_deactivate
    """
    csv_emails = {user["email"] for user in csv_users}
    existing_emails = set(existing_users.keys())

    to_add = []
    to_update = []

    # Users in CSV
    for csv_user in csv_users:
        email = csv_user["email"]
        if email in existing_emails:
            existing = existing_users[email]
            # Check if anything changed
            if (
                csv_user["firstname"] != (existing.firstname or "")
                or csv_user["lastname"] != (existing.lastname or "")
                or set(csv_user["roles"]) != {r.name for r in existing.roles}
            ):
                to_update.append(
                    {**csv_user, "previous_roles": [r.name for r in existing.roles]}
                )
        else:
            to_add.append(csv_user)

    # Users not in CSV (to be deactivated)
    to_deactivate = []
    for email in existing_emails - csv_emails:
        user = existing_users[email]
        # Don't deactivate users who are administrators and not in CSV
        # This is a safety measure
        if not any(role.name == "administrator" for role in user.roles):
            to_deactivate.append(
                {
                    "email": email,
                    "firstname": user.firstname or "",
                    "lastname": user.lastname or "",
                    "roles": [r.name for r in user.roles],
                }
            )

    return {"to_add": to_add, "to_update": to_update, "to_deactivate": to_deactivate}
