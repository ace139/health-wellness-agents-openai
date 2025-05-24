"""Session management for the health assistant system."""
# Standard library imports
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

# Third-party imports
from sqlalchemy.orm import Session as DBSession

# Local application imports
from db.session import get_db
from tools.conversation import log_conversation


class HealthAssistantSession:
    """Manages a conversation session with the health assistant."""

    def __init__(self, db: Optional[DBSession] = None):
        """Initialize a new session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.session_id = str(uuid.uuid4())
        self.user_id: Optional[int] = None
        self.current_agent_name: str = "Greeter"
        self.conversation_stack: List[str] = []
        self.interaction_count: int = 0
        self.started_at: datetime = datetime.utcnow()
        self.db = db if db is not None else next(get_db())
        self._context: Dict[str, Any] = {}

    def push_agent(self, agent_name: str) -> None:
        """Push current agent to stack before switching.
        
        Args:
            agent_name: Name of the agent to push to stack
        """
        if len(self.conversation_stack) < 10:  # Prevent stack overflow
            self.conversation_stack.append(self.current_agent_name)
        self.current_agent_name = agent_name

    def pop_agent(self) -> str:
        """Return to previous agent from stack.
        
        Returns:
            Name of the previous agent
        """
        if self.conversation_stack:
            self.current_agent_name = self.conversation_stack.pop()
        return self.current_agent_name

    def log_conversation(
        self, role: str, message: str, agent_name: Optional[str] = None
    ) -> None:
        """Log a conversation turn.
        
        Args:
            role: Role of the message sender ('user', 'assistant', 'system')
            message: The message content
            agent_name: Name of the agent handling the message
        """
        if not self.user_id:
            return  # Don't log pre-authentication messages
            
        log_conversation(
            db=self.db,
            user_id=self.user_id,
            session_id=self.session_id,
            role=role,
            message=message,
            agent_name=agent_name or self.current_agent_name
        )

    def update_context(self, **kwargs: Any) -> None:
        """Update the session context with new key-value pairs.
        
        Args:
            **kwargs: Key-value pairs to add/update in the context
        """
        self._context.update(kwargs)

    def get_context(self) -> Dict[str, Any]:
        """Get the current session context.
        
        Returns:
            Dictionary containing the current session context
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "current_agent": self.current_agent_name,
            "interaction_count": self.interaction_count,
            **self._context,
        }

    def increment_interactions(self) -> None:
        """Increment the interaction counter."""
        self.interaction_count += 1

    def set_user(self, user_id: int) -> None:
        """Set the current user for the session.
        
        Args:
            user_id: ID of the authenticated user
        """
        self.user_id = user_id
