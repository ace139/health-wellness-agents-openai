"""WellBeing agent for tracking user's emotional state and wellbeing."""

# Standard library imports
import logging
from typing import TYPE_CHECKING

# Third-party imports
from agents import Agent, Runner, agent_output  # Alphabetized and on separate lines

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
    user_input: str, session: "HealthAssistantSession", agent: Agent
) -> agent_output:
    """Handle the user input using the WellBeing agent and return AgentOutput.

    Args:
        user_input: The user's input text
        session: Current health assistant session
        agent: Configured Wellbeing agent instance.

    Returns:
        Tuple of (response_text, should_continue)
    """
    session.log_conversation(role="user", message=user_input)

    try:
        run_result = await Runner.run(
            starting_agent=agent, input=user_input, context=session
        )

        # Ensure final_output is a string
        default_response = (
            "I'm sorry, I had trouble processing that. Let's try something else."
        )
        if (
            not isinstance(run_result.final_output, str)
            or run_result.final_output is None
        ):
            logger.warning(
                "WellBeingAgent output not str or None: %s. Using default.",
                run_result.final_output,
            )
            run_result.final_output = default_response
        else:
            run_result.final_output = run_result.final_output.strip()

        session.log_conversation(role="assistant", message=run_result.final_output)
        return run_result

    except Exception as e:
        logger.error(f"Error in WellBeingAgent: {e!s}", exc_info=True)
        error_response_content = (
            "I'm sorry, I encountered an error during our wellbeing check. "
            "Let's move on for now."
        )
        session.log_conversation(
            role="system", message=f"Error in WellBeingAgent: {e!s}"
        )
        session.log_conversation(role="assistant", message=error_response_content)

        return agent_output(
            final_output=error_response_content,
            tool_calls=[],
            tool_outputs=[],
            error=str(e),
            history=[],
        )
