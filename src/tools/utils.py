"""Utility functions for tools."""
from typing import Optional, Any, Dict


def validate_user_id(user_id: Any) -> Optional[int]:
    """Validate and convert user ID to integer."""
    try:
        uid = int(user_id)
        if 1 <= uid <= 999999:  # Reasonable range
            return uid
    except (ValueError, TypeError):
        pass
    return None


def sanitize_string(text: str, max_length: int = 500) -> str:
    """Sanitize and truncate string input."""
    if not isinstance(text, str):
        return ""
    # Remove any potential SQL injection attempts
    text = text.strip()
    # Truncate to max length
    return text[:max_length]


def format_error_response(error_message: str, **kwargs) -> Dict[str, Any]:
    """Format a standardized error response."""
    response = {
        "success": False,
        "error": error_message
    }
    response.update(kwargs)
    return response


def format_success_response(message: str = "", **kwargs) -> Dict[str, Any]:
    """Format a standardized success response."""
    response = {
        "success": True
    }
    if message:
        response["message"] = message
    response.update(kwargs)
    return response
