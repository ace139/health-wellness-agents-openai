"""User management tools for the health and wellness assistant."""

# Standard library imports
from typing import Dict

# Third-party imports
from agents import function_tool

# Local application imports
from db import crud
from db.database import get_db_context  # Added for internal session management

# Relative imports
from .utils import format_error_response, format_success_response, validate_user_id

# Constants
MAX_DIETARY_PREFERENCES_LENGTH = 1000


@function_tool
def fetch_user(user_id: int) -> Dict:
    """
    Fetch user profile from database with validation.

    Args:
        db: Database session
        user_id: The user's ID (must be positive integer)

    Returns:
        Dict with user info or error message
    """
    # Validate inputs
    validated_id = validate_user_id(user_id)
    if not validated_id:
        return format_error_response("Invalid user ID")

    try:
        with get_db_context() as db:
            # Get user from database
            user = crud.user.get(db, validated_id)

            if not user:
                return format_error_response(f"User with ID {validated_id} not found")

        # Return user details (excluding sensitive information)
        return format_success_response(
            user_id=user.id,
            email=user.email,
            full_name=user.first_name + " " + user.last_name,
            dietary_preferences=user.dietary_preference,
            is_active=True,  # Assuming is_active is always True for now
        )
    except Exception as e:
        return format_error_response(f"Failed to fetch user details: {str(e)}")


@function_tool
def update_dietary_preference(user_id: int, preference: str) -> Dict:
    """
    Update a user's dietary preference.

    Args:
        db: Database session
        user_id: Valid user ID
        preference: New dietary preference

    Returns:
        Dict with success/error status
    """
    # Validate inputs
    validated_id = validate_user_id(user_id)
    if not validated_id:
        return format_error_response("Invalid user ID")

    # Validate preference
    valid_preferences = ["vegetarian", "non-vegetarian", "vegan"]
    if preference.lower() not in valid_preferences:
        return format_error_response(
            f"Invalid preference. Must be one of: {', '.join(valid_preferences)}"
        )

    try:
        with get_db_context() as db:
            # Get user
            user = crud.user.get(db, validated_id)
            if not user:
                return format_error_response("User not found")

            # Update preference
            user.dietary_preference = preference.lower()
            db.add(user)
            db.commit()
            db.refresh(user)

            return format_success_response(
                message=f"Dietary preference updated to {preference}",
                new_preference=user.dietary_preference,
            )
    except Exception as e:
        # db.rollback() is handled by the context manager if an exception occurs
        return format_error_response(f"Failed to update dietary preference: {str(e)}")
