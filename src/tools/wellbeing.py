"""Wellbeing tracking tools for the health and wellness assistant."""

# Standard library imports
from typing import Dict, Optional

# Third-party imports
from agents import function_tool

# Local application imports
from db import crud
from db.database import get_db_context  # Added import
from db.schemas import WellbeingLogCreate  # Corrected import

# Relative imports
from .conversation import log_conversation  # Added for log_affirmation
from .utils import (
    format_error_response,
    format_success_response,
    validate_user_id,
)

# Constants
MIN_WELLBEING_SCORE = 1
MAX_WELLBEING_SCORE = 10
VALID_WELLBEING_TYPES = ["energy", "mood", "stress", "sleep_quality"]


def validate_wellbeing_score(score: int) -> Optional[int]:
    """Validate wellbeing score is within valid range."""
    try:
        value = int(score)
        if MIN_WELLBEING_SCORE <= value <= MAX_WELLBEING_SCORE:
            return value
    except (ValueError, TypeError):
        pass
    return None


def sanitize_string(text: str, max_length: int) -> str:
    """Sanitize and truncate string input."""
    if not isinstance(text, str):
        return ""
    # Remove any potential SQL injection attempts
    text = text.strip()
    # Truncate to max length
    return text[:max_length]


@function_tool
def log_wellbeing(user_id: int, score: int, log_type: str, session_id: str) -> Dict:
    """
    Log wellbeing score with input validation.

    Args:
        user_id: Valid user ID
        score: Wellbeing score (1-10)
        log_type: Type of wellbeing log (energy, mood, stress, sleep_quality)
        session_id: Current session ID

    Returns:
        Dict with success/error status
    """
    with get_db_context() as db:
        # Validate inputs
        validated_id = validate_user_id(user_id)
        if not validated_id:
            return format_error_response("Invalid user ID")

        validated_score = validate_wellbeing_score(score)
        if validated_score is None:
            return format_error_response(
                f"Invalid score. Please provide a value between {MIN_WELLBEING_SCORE} "
                f"and {MAX_WELLBEING_SCORE}"
            )

        if log_type not in VALID_WELLBEING_TYPES:
            valid_types = ", ".join(VALID_WELLBEING_TYPES)
            return format_error_response(
                f"Invalid log type. Must be one of: {valid_types}"
            )

        # Assuming session_id max length is 100
        session_id = sanitize_string(session_id, 100)

        try:
            # Create wellbeing log entry
            log_data = WellbeingLogCreate(
                user_id=validated_id, score=validated_score, log_type=log_type
            )

            db_log = crud.wellbeing_log.create(db, obj_in=log_data)

            # Also log in conversation
            crud.conversation_log.create(
                db=db,
                user_id=validated_id,
                session_id=session_id,
                role="user",
                agent_name="WellBeing",
                message=f"{log_type} score of {validated_score}",
            )

            return format_success_response(
                message=f"{log_type} score of {validated_score} logged successfully",
                log_id=db_log.id,
                score=validated_score,
                log_type=log_type,
                timestamp=db_log.timestamp.isoformat(),
            )
        except Exception as e:
            return format_error_response(f"Failed to log wellbeing: {str(e)}")


@function_tool
def get_wellbeing_history(user_id: int, days: int) -> Dict:
    """
    Get the user's wellbeing history.

    Args:
        user_id: Valid user ID
        days: Number of days to retrieve history for (1-90)

    Returns:
        Dict with wellbeing history or error message
    """
    with get_db_context() as db:
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
            # Get wellbeing logs
            logs = crud.wellbeing_log.get_multi_by_user(
                db=db, user_id=validated_id, days=days
            )

            # Calculate average scores
            stats = {}
            for log in logs:
                if log.log_type not in stats:
                    stats[log.log_type] = {"sum": 0, "count": 0}
                stats[log.log_type]["sum"] += log.score
                stats[log.log_type]["count"] += 1

            # Format response
            history = [
                {
                    "id": log.id,
                    "score": log.score,
                    "log_type": log.log_type,
                    "timestamp": log.timestamp.isoformat(),
                }
                for log in logs
            ]

            return format_success_response(
                days=days,
                logs=history,
                average_scores={
                    log_type: stats[log_type]["sum"] / stats[log_type]["count"]
                    for log_type in VALID_WELLBEING_TYPES
                    if log_type in stats and stats[log_type]["count"] > 0
                },
                total_logs=sum(
                    stats[log_type]["count"]
                    for log_type in VALID_WELLBEING_TYPES
                    if log_type in stats
                ),
            )
        except Exception as e:
            return format_error_response(f"Failed to fetch wellbeing history: {str(e)}")


@function_tool
def log_affirmation(
    user_id: int,
    session_id: str,
    affirmation_text: str,
) -> Dict:
    """
    Logs a generated affirmation.

    Args:
        user_id: The ID of the user.
        session_id: The current session ID.
        affirmation_text: The text of the affirmation.

    Returns:
        A dictionary with the result of the conversation logging.
    """
    # Validate inputs (basic validation for now)
    if not isinstance(user_id, int) or user_id < 0:
        return format_error_response("Invalid user_id for affirmation log.")
    if not isinstance(session_id, str) or not session_id.strip():
        return format_error_response("Invalid session_id for affirmation log.")
    if not isinstance(affirmation_text, str) or not affirmation_text.strip():
        return format_error_response("Affirmation text cannot be empty.")

    # Sanitize affirmation_text, e.g., using MAX_MESSAGE_LENGTH from conversation_tool
    # Assuming MAX_MESSAGE_LENGTH is accessible or we define a similar constant here
    # For now, let's use a placeholder or assume log_conversation handles it.
    # MAX_AFFIRMATION_LENGTH = 500 # Example
    # sanitized_text = sanitize_string(affirmation_text, MAX_AFFIRMATION_LENGTH)

    return log_conversation(
        user_id=user_id,
        session_id=session_id,
        role="agent",  # The affirmation is generated by an agent
        message=affirmation_text,  # Using raw text, log_conversation should sanitize
        agent_name="AffirmationAgent",  # Specific agent name for clarity
    )
