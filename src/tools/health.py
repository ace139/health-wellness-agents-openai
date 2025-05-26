"""Health monitoring tools for the health and wellness assistant."""

# Standard library imports
from datetime import datetime
from typing import Dict, Optional

# Third-party imports
from agents import function_tool

# Local application imports
from db import crud
from db.database import get_db_context
from db.schemas import CGMReadingCreate

# Relative imports
from .utils import (
    format_error_response,
    format_success_response,
    validate_user_id,
)

# Constants
MIN_CGM_READING = 20
MAX_CGM_READING = 600
VALID_READING_TYPES = ["breakfast", "lunch", "dinner"]


def validate_cgm_reading(reading: float) -> Optional[float]:
    """Validate CGM reading is within plausible range."""
    try:
        value = float(reading)
        if MIN_CGM_READING <= value <= MAX_CGM_READING:
            return value
    except (ValueError, TypeError):
        pass
    return None


@function_tool
def log_cgm_reading(
    user_id: int,
    reading: float,
    reading_type: Optional[str] = None,
) -> Dict:
    """
    Log a CGM reading with validation and automatic time classification.

    Args:
        db: Database session
        user_id: Valid user ID
        reading: CGM reading value (20-600 mg/dL)
        reading_type: Optional reading type (breakfast, lunch, dinner)

    Returns:
        Dict with success/error status and reading details
    """
    # Validate inputs
    validated_id = validate_user_id(user_id)
    if not validated_id:
        return format_error_response("Invalid user ID")

    validated_reading = validate_cgm_reading(reading)
    if validated_reading is None:
        return format_error_response(
            f"Invalid reading. Please provide a value between {MIN_CGM_READING} "
            f"and {MAX_CGM_READING}"
        )

    # Determine reading type based on current time if not provided
    if not reading_type or reading_type.lower() not in VALID_READING_TYPES:
        hour = datetime.now().hour
        if 6 <= hour < 11:
            reading_type = "breakfast"
        elif 11 <= hour < 16:
            reading_type = "lunch"
        else:
            reading_type = "dinner"

    try:
        with get_db_context() as db:
            # Create CGM reading
            reading_data = CGMReadingCreate(
                user_id=validated_id,
                reading=validated_reading,
                reading_type=reading_type,
            )

        db_reading = crud.cgm_reading.create(db, obj_in=reading_data)

        message = (
            f"CGM reading of {validated_reading} mg/dL logged as {reading_type} reading"
        )
        return format_success_response(
            message=message,
            reading_id=db_reading.id,
            reading=validated_reading,
            reading_type=reading_type,
            timestamp=db_reading.timestamp.isoformat(),
        )
    except Exception as e:
        return format_error_response(f"Failed to log CGM reading: {str(e)}")


@function_tool
def get_cgm_statistics(user_id: int, days: int = 7) -> Dict:
    """
    Get CGM statistics for a user.

    Args:
        db: Database session
        user_id: Valid user ID
        days: Number of days to analyze (1-90)

    Returns:
        Dict with statistics or error message
    """
    # Validate inputs
    validated_id = validate_user_id(user_id)
    if not validated_id:
        return format_error_response("Invalid user ID")

    # Validate days
    try:
        days = max(1, min(90, int(days)))  # Clamp between 1 and 90
    except (ValueError, TypeError):
        return format_error_response("Invalid days parameter")

    try:
        with get_db_context() as db:
            # Get statistics using our CRUD operation
            stats = crud.cgm_reading.get_stats(db, user_id=validated_id, days=days)

        # Format the response
        return format_success_response(
            days=days,
            average=stats.get("average"),
            minimum=stats.get("min"),
            maximum=stats.get("max"),
            total_readings=stats.get("count", 0),
            by_meal_type=stats.get("by_meal_type", {}),
        )
    except Exception as e:
        return format_error_response(f"Failed to get CGM statistics: {str(e)}")
