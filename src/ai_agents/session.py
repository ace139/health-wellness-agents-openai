"""Session management for the health assistant system."""

# Standard library imports
import copy  # Added for deepcopy
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple  # Added Tuple

# Third-party imports
# from sqlalchemy.orm import Session as DBSession # No longer needed here
# Local application imports
# from db.session import get_db # Incorrect import, and session will not be managed here
from tools.conversation import log_conversation

from .flow_manager import ConversationFlowManager  # Added

logger = logging.getLogger(__name__)


class HealthAssistantSession:
    """Manages a conversation session with the health assistant."""

    def __init__(self, user_id: Optional[int] = None):
        """Initialize a new session.

        Args:
            user_id: Optional ID of the authenticated user.
        """
        self.session_id = str(uuid.uuid4())
        self.user_id: Optional[int] = user_id
        # self.conversation_stack: List[str] = [] # Removed old stack
        self.current_agent_name: str = "Greeter"  # Initial agent
        self.interaction_count: int = 0
        self.started_at: datetime = datetime.utcnow()
        self._context: Dict[str, Any] = {}  # General purpose context

        self.flow_manager = ConversationFlowManager()
        self.conversation_state: Dict[str, Any] = {
            "current_task": None,
            "pending_data": {},
            "interruption_count": 0,
            "last_complete_state": None,
            # Other session-wide state variables can be added here
        }
        # Attributes for RouterAgent context, prepared by prepare_for_routing()
        self.routing_context_current_agent: Optional[str] = None
        self.routing_context_current_state_summary: Optional[str] = None
        self.routing_context_flow_stack_summary: Optional[str] = None
        self.routing_context_has_pending_flow: bool = False
        self.routing_context_interaction_count: int = 0

    # Old push_agent and pop_agent methods removed.

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
            # db=self.db, # log_conversation tool manages its own session
            user_id=self.user_id,
            session_id=self.session_id,
            role=role,
            message=message,
            agent_name=agent_name or self.current_agent_name,
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
            "current_agent_name": self.current_agent_name,  # Standardized key
            "interaction_count": self.interaction_count,
            "conversation_state": self.conversation_state,  # Added
            **self._context,  # General context key-values
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

    async def close(self) -> None:
        """Perform any cleanup for the session, if necessary."""
        # No specific cleanup needed currently; method for compatibility.
        pass

    # New methods for flow and state management
    def get_context_snapshot(self) -> Dict[str, Any]:
        """Captures session-level context to be restored when a flow resumes."""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "current_agent_name": self.current_agent_name,
            "interaction_count": self.interaction_count,
            "conversation_state": copy.deepcopy(self.conversation_state),
            "_context": copy.deepcopy(self._context),
        }

    def apply_context_snapshot(self, context_snapshot: Dict[str, Any]) -> None:
        """Restores session-level context from a snapshot."""
        self.user_id = context_snapshot.get("user_id", self.user_id)
        self.session_id = context_snapshot.get("session_id", self.session_id)
        self.current_agent_name = context_snapshot.get(
            "current_agent_name", self.current_agent_name
        )
        self.interaction_count = context_snapshot.get(
            "interaction_count", self.interaction_count
        )
        self.conversation_state = context_snapshot.get(
            "conversation_state", self.conversation_state
        )
        self._context = context_snapshot.get("_context", self._context)

    def save_conversation_state(
        self, agent_name: str, agent_specific_state: Dict[str, Any]
    ) -> None:
        """Saves the current flow (session context + agent state) to the flow stack."""
        session_context_snapshot = self.get_context_snapshot()
        self.flow_manager.push_flow(
            agent_name, session_context_snapshot, agent_specific_state
        )
        # Optional: logger.info(f"Saved flow for {agent_name}.")

    def restore_conversation_state(
        self,
    ) -> Optional[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
        """
        Restores a flow from the stack.

        Returns:
            Tuple: (agent_name, agent_state, session_snapshot)
            or None if the stack is empty.
        """
        flow_data = self.flow_manager.pop_flow()
        if flow_data:
            resumed_agent_name, session_context_snapshot, agent_specific_state = (
                flow_data
            )
            self.apply_context_snapshot(session_context_snapshot)
            # Optional: logger.info(f"Restored flow for {resumed_agent_name}.")
            return resumed_agent_name, agent_specific_state, session_context_snapshot
        return None

    def prepare_for_routing(self) -> None:
        """
        Prepares session attributes that the RouterAgent might use as context_variables.
        These attributes are set directly on the session object and are prefixed
        with 'routing_context_' to be easily identifiable.
        """
        self.routing_context_current_agent = self.current_agent_name or "None"

        current_task = self.conversation_state.get("current_task", "N/A")
        pending_data = self.conversation_state.get("pending_data", {})
        pending_data_summary = (
            f"Keys:{','.join(pending_data.keys())}" if pending_data else "None"
        )
        self.routing_context_current_state_summary = (
            f"Task:{current_task},Pending:{pending_data_summary}"
        )

        self.routing_context_flow_stack_summary = self.flow_manager.get_stack_summary()
        self.routing_context_has_pending_flow = self.flow_manager.has_pending_flow()
        self.routing_context_interaction_count = self.interaction_count

    async def handle_routing_decision(
        self, router_decision: Dict[str, Any], original_user_input: str
    ) -> Tuple[str, str, bool]:
        """
        Processes the router's decision to manage conversation flow and determine
        the next agent and input.

        Args:
            router_decision: The output from RouterAgent.determine_next_agent().
            original_user_input: The raw input from the user for the current turn.

        Returns:
            A tuple: (agent_to_run_next: str,
                      input_for_that_agent: str,
                      is_resumed_flow: bool)
        """
        intent = router_decision.get("intent", "new_flow")
        target_agent = router_decision.get("target_agent", "GreeterAgent")
        is_interruption = router_decision.get("is_interruption", False)
        should_resume_interrupted_after_new_flow = router_decision.get(
            "should_resume_after", False
        )

        # Log the state *before* this decision is handled
        # current_agent_name was set by prepare_for_routing or a previous run.
        previous_agent_for_flow_stack = self.current_agent_name
        # Capture state relevant to previous_agent. self.conversation_state is general.
        previous_agent_specific_state = self.conversation_state.copy()

        if is_interruption:
            logger.info(
                f"Router interruption. Prev agent: {previous_agent_for_flow_stack}."
            )
            if (
                should_resume_interrupted_after_new_flow
                and previous_agent_for_flow_stack
            ):
                # Input for interrupted agent isn't directly here.
                self.flow_manager.push_flow(
                    agent_name=previous_agent_for_flow_stack,
                    agent_input="<interrupted_flow_placeholder_input>",  # TODO: Refine
                    session_context_snapshot=self.get_context_snapshot(),
                    agent_specific_state=previous_agent_specific_state,
                )
                logger.info(
                    f"Saved flow for '{previous_agent_for_flow_stack}'. "
                    f"New target: '{target_agent}'."
                )
            # Proceed with the interrupting agent
            self.current_agent_name = target_agent
            return target_agent, original_user_input, False

        # Check if router explicitly wants to resume a pending flow.
        # Relies on router setting intent to 'resume_flow'.
        if intent == "resume_flow" and self.flow_manager.has_pending_flow():
            logger.info("Router intent 'resume_flow', attempting to resume.")
            resumed_flow_data = self.flow_manager.pop_flow()
            if resumed_flow_data:
                (
                    resumed_agent_name,
                    resumed_agent_input,  # Input that started the resumed flow
                    session_context_snapshot,  # Session state at interruption
                    agent_specific_state,  # Specific state of the agent
                ) = resumed_flow_data

                self.apply_context_snapshot(session_context_snapshot)
                self.conversation_state = agent_specific_state  # Restore agent state
                self.current_agent_name = resumed_agent_name  # Critical for context

                logger.info(
                    f"Resuming for '{resumed_agent_name}' with input: "
                    f"'{resumed_agent_input[:50]}...'"
                )
                return resumed_agent_name, resumed_agent_input, True
            else:
                logger.warning("Router 'resume_flow', but flow stack empty on pop.")
                self.current_agent_name = target_agent
                return target_agent, original_user_input, False

        # Default: new flow or continuation
        logger.info(f"Proceeding with '{target_agent}' as new/continuing flow.")
        self.current_agent_name = target_agent
        return target_agent, original_user_input, False
