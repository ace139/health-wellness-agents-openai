"""Affirmation agent for providing positive affirmations and encouragement."""

# Standard library imports
import logging
from typing import TYPE_CHECKING, Tuple

# Third-party imports
from agents import Agent, Runner

# Local application imports
from tools.conversation import log_conversation
from tools.wellbeing import get_wellbeing_history, log_affirmation

logger = logging.getLogger(__name__)

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


async def handle_affirmation_response(
    user_input: str,
    session: "HealthAssistantSession",
    affirmation_agent: Agent,
) -> Tuple[str, bool]:
    """Handle user input and generate a response using the Affirmation agent."""
    session.log_conversation(role="user", message=user_input)

    try:
        # Session object itself is the context for Runner.run
        run_result = await Runner.run(
            starting_agent=affirmation_agent,
            input=user_input,
            context=session,  # Pass the entire session as context
        )

        if not isinstance(run_result.final_output, str):
            # Default or error response if final_output is not a string
            response_content = (
                "I'm here to support you. Remember, every day is a new opportunity."
            )
            logger.warning(
                f"AffirmationAgent output not str: {run_result.final_output}"
            )
        else:
            response_content = run_result.final_output.strip()

        session.log_conversation(role="assistant", message=response_content)

        # Affirmation agent typically doesn't continue the conversation in the old flow.
        # 'should_continue' refers to if this agent's turn leads to more turns
        # from *itself* or if it's done. Router will decide next agent.
        return response_content, False

    except Exception as e:
        # Log the exception
        logger.error(f"Error in AffirmationAgent: {e!s}", exc_info=True)
        error_msg = "I'm here to support you. Remember, every day is a new opportunity."
        # Log system message for the error
        session.log_conversation(
            role="system",
            message=f"Error generating affirmation: {e!s}",
        )
        return error_msg, False
