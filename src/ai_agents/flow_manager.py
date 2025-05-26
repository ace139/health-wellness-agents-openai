from typing import Any, Dict, List, Optional, Tuple


class ConversationFlowManager:
    """Manages conversation flow, interruptions, and context switching."""

    def __init__(self):
        self.flow_stack: List[
            Tuple[str, Dict[str, Any], Dict[str, Any], Optional[str]]
        ] = []  # Stack of (agent_name, context, state, user_input)
        self.current_flow: Optional[
            Tuple[str, Dict[str, Any], Dict[str, Any], Optional[str]]
        ] = None

    def push_flow(
        self, agent_name: str, context: Dict[str, Any], state: Dict[str, Any],
        user_input: Optional[str] = None  # Added for storing interrupted input
    ):
        """Save current flow to stack before handling interruption or switching flow."""
        flow_data = (agent_name, context, state, user_input)
        if self.current_flow:
            self.flow_stack.append(self.current_flow)
        self.current_flow = flow_data

    def pop_flow(
        self,
    ) -> Optional[Tuple[str, Dict[str, Any], Dict[str, Any], Optional[str]]]:
        """Return to previous flow after interruption or when a sub-flow completes."""
        if self.flow_stack:
            self.current_flow = self.flow_stack.pop()
            return self.current_flow
        # If stack is empty, it means there's no previous flow to return to.
        self.current_flow = None
        return None

    def should_resume_flow(self, user_input: str) -> bool:
        """Determine if we should resume a previous flow based on user input."""
        # Simple heuristic. More sophisticated NLP may be needed for robust detection.
        resume_phrases = [
            "back to",
            "continue with",
            "let's go back",
            "where were we",
            "anyway",
            "as i was saying",
            "resume my previous task",
            "back to what we were doing",
        ]
        return any(phrase in user_input.lower() for phrase in resume_phrases)

    def get_current_context(self) -> Optional[Dict[str, Any]]:
        """Retrieve the context of the current flow."""
        if self.current_flow:
            return self.current_flow[1]  # context is the second element in the tuple
        return None

    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """Retrieve the state of the current flow."""
        if self.current_flow:
            return self.current_flow[2]  # state is the third element in the tuple
        return None

    def get_current_agent_name(self) -> Optional[str]:
        """Retrieve the agent name of the current flow."""
        if self.current_flow:
            return self.current_flow[0]  # agent_name is the first element
        return None

    def has_pending_flow(self) -> bool:
        """Check if there are any flows saved in the stack."""
        return len(self.flow_stack) > 0

    def get_stack_summary(self) -> str:
        """Provides a summary of the agent names in the flow stack."""
        if not self.flow_stack:
            return "Flow stack is empty."
        # The stack is (agent_name, context, state). We need agent_name (index 0).
        # Stack top is at end of list. For "top to bottom" summary, reverse.
        agent_names = [flow_item[0] for flow_item in self.flow_stack]
        return f"S: {', '.join(reversed(agent_names))}"

    # Consider methods to clear stack/current flow for session resets.
    def clear_flow(self):
        """Clears the current flow and the flow stack."""
        self.flow_stack = []
        self.current_flow = None
