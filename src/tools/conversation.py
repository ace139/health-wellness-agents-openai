"""Conversation tools for the health and wellness assistant."""

# Standard library imports
from typing import Dict, Optional

# Third-party imports
# Local application imports
from db import crud
from db.database import get_db_context  # Import get_db_context

# Relative imports
from .utils import (
    format_error_response,
    format_success_response,
    sanitize_string,
    validate_user_id,
)

# Constants
VALID_ROLES = ["user", "agent", "system"]
MAX_MESSAGE_LENGTH = 2000
MAX_SESSION_ID_LENGTH = 100
MAX_AGENT_NAME_LENGTH = 50


def log_conversation(
    user_id: int,
    session_id: str,
    role: str,
    message: str,
    agent_name: Optional[str] = None,
) -> Dict:
    """
    Log a conversation turn with validation.

    Args:
        user_id: Valid user ID (0 for system messages)
        session_id: Session identifier
        role: One of 'user', 'agent', 'system'
        message: Message content (max 2000 chars)
        agent_name: Optional name of the agent

    Returns:
        Dict with success/error status
    """
    with get_db_context() as db:
        # Validate inputs
        validated_id = validate_user_id(user_id) or 0  # Allow 0 for system messages

        # Validate role
        if role not in VALID_ROLES:
            return format_error_response(
                f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"
            )

        # Sanitize strings
        session_id = sanitize_string(session_id, MAX_SESSION_ID_LENGTH)
        agent_name = (
            sanitize_string(agent_name, MAX_AGENT_NAME_LENGTH) if agent_name else None
        )
        message = sanitize_string(message, MAX_MESSAGE_LENGTH)

        if not message:
            return format_error_response("Message cannot be empty")

        try:
            # Create conversation log entry
            log_entry = crud.conversation_log.create(
                db=db,
                user_id=validated_id,
                session_id=session_id,
                role=role,
                message=message,
                agent_name=agent_name,
            )

            return format_success_response(
                log_id=log_entry.id, timestamp=log_entry.timestamp.isoformat()
            )
        except Exception as e:
            return format_error_response(f"Failed to log conversation: {str(e)}")
