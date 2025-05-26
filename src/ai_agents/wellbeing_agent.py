"""WellBeing agent for tracking user's emotional state and wellbeing."""

# Standard library imports
import logging
from typing import TYPE_CHECKING, Tuple

# Third-party imports
from agents import Agent, Runner

if TYPE_CHECKING:
    from ai_agents.session import HealthAssistantSession

# Local application imports
from tools.conversation import log_conversation
from tools.wellbeing import log_wellbeing

logger = logging.getLogger(__name__)


def create_wellbeing_agent() -> Agent:
    """Create and configure the WellBeing agent.

    Returns:
        Configured WellBeing Agent instance
    """
    return Agent(
        name="WellBeing",
        instructions=(
            "You are the WellBeing agent who checks on users' emotional state.\n\n"
            "IMPORTANT GUARDRAILS:\n"
            "- Accept feelings up to 500 characters\n"
            "- Be empathetic but maintain professional boundaries\n"
            "- Never provide medical or psychological diagnoses\n"
            "- Keep responses supportive and brief\n\n"
            "Your job is to:\n"
            '1. Ask: "How are you feeling today, {first_name}?" '
            "(use their name if available)\n"
            "2. Accept any response about their feelings\n"
            "3. Use log_wellbeing tool to record their response\n"
            "4. Acknowledge appropriately without medical advice\n"
            '5. Transition to health metrics: "Thank you for sharing. '
            "Let's check your health metrics.\"\n\n"
            "Examples of good responses:\n"
            '- "Thank you for sharing that you\'re feeling tired."\n'
            "- \"I'm glad to hear you're doing well!\"\n"
            '- "I understand you\'re going through a tough time."\n\n'
            "Never say things like:\n"
            '- "That sounds like depression"\n'
            '- "You should see a therapist"\n'
            '- "That\'s abnormal"'
        ),
        tools=[log_wellbeing, log_conversation],
        handoffs=["HealthMonitor"],
    )


async def handle_wellbeing_response(
    user_input: str, session: "HealthAssistantSession", wellbeing_agent: Agent
) -> Tuple[str, bool]:
    """Handle the user input and generate a response using the WellBeing agent.

    Args:
        user_input: The user's input text
        session: Current health assistant session
        wellbeing_agent: Configured WellBeing agent instance

    Returns:
        Tuple of (response_text, should_continue)
    """
    session.log_conversation(role="user", message=user_input)

    try:
        run_result = await Runner.run(
            starting_agent=wellbeing_agent,
            input=user_input,
            context=session,
        )

        if not isinstance(run_result.final_output, str):
            response_content = "I'm sorry, I had trouble processing that."
            logger.warning(
                f"WellBeingAgent output not str: {run_result.final_output}"
            )
        else:
            response_content = run_result.final_output.strip()

        session.log_conversation(role="assistant", message=response_content)
        return response_content, False

    except Exception as e:
        logger.error(f"Error in WellBeingAgent: {e!s}", exc_info=True)
        error_msg = (
            "I'm sorry, I encountered an error while processing your wellbeing check."
        )
        session.log_conversation(
            role="system", message=f"Error wellbeing check: {e!s}"
        )
        return error_msg, False
