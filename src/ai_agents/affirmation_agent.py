"""Affirmation agent for providing positive affirmations and encouragement."""

# Standard library imports
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

# Third-party imports
from agents import Agent

# Local application imports
from tools.conversation import log_conversation
from tools.wellbeing import get_wellbeing_history, log_affirmation

if TYPE_CHECKING:
    from ai_agents.session import HealthAssistantSession


def create_affirmation_agent() -> Agent:
    """Create and configure the Affirmation agent.

    Returns:
        Configured Affirmation Agent instance
    """
    return Agent(
        name="Affirmation",
        instructions=(
            "You are the Affirmation agent who provides positive "
            "affirmations and encouragement.\n\n"
            "IMPORTANT GUIDELINES:\n"
            "- Keep affirmations brief, positive, and personalized\n"
            "- Base affirmations on the user's wellbeing data when available\n"
            "- Be encouraging but realistic\n"
            "- Maintain a warm, supportive tone\n"
            "- Avoid generic platitudes\n\n"
            "Your job is to:\n"
            "1. Check user's wellbeing history using get_wellbeing_history\n"
            "2. Generate a personalized affirmation or encouragement\n"
            "3. Use log_affirmation to record the affirmation\n"
            "4. Keep responses concise (1-2 sentences)\n\n"
            "Examples of good affirmations:\n"
            '- "I notice you\'ve been consistent with your tracking."\n'
            '- "Even on challenging days, you\'re making progress."\n\n'
            "Never:\n"
            "- Make promises about health outcomes\n"
            "- Use negative language\n"
            "- Be overly effusive or insincere\n"
            "- Provide medical advice"
        ),
        tools=[get_wellbeing_history, log_affirmation, log_conversation],
        handoffs=["Done"],
    )


def handle_affirmation_response(
    user_input: str,
    session: "HealthAssistantSession",
    affirmation_agent: Agent,
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, bool]:
    """Handle user input and generate a response using the Affirmation agent.

    Args:
        user_input: The user's input text
        session: Current health assistant session
        affirmation_agent: Configured Affirmation agent instance
        context: Additional context for the agent

    Returns:
        Tuple of (response_text, should_continue)
            - response_text: The agent's response text
            - should_continue: Whether to continue the conversation
    """
    # Log the user's input
    session.log_conversation(role="user", message=user_input)

    try:
        # Prepare the context for the agent
        agent_context = session.get_context()
        if context:
            agent_context.update(context)

        # Get response from the agent
        response = affirmation_agent.run(
            user_input,
            user_id=session.user_id,
            session_id=session.session_id,
            **agent_context,
        )

        # Log the agent's response
        session.log_conversation(
            role="assistant",
            message=response.content,
        )

        # Affirmation agent typically doesn't continue the conversation
        return response.content.strip(), False

    except Exception as e:
        error_msg = "I'm here to support you. Remember, every day is a new opportunity."
        session.log_conversation(
            role="system",
            message=f"Error generating affirmation: {e!s}",
        )
        return error_msg, False
