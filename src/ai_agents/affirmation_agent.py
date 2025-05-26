"""Affirmation agent for providing positive affirmations and encouragement."""

# Standard library imports
import logging
from typing import TYPE_CHECKING

# Third-party imports
from agents import Agent, AgentOutput, Runner

# Local application imports
from tools.conversation import log_conversation
from tools.wellbeing import get_wellbeing_history, log_affirmation

if TYPE_CHECKING:
    from ai_agents.session import HealthAssistantSession

logger = logging.getLogger(__name__)


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
) -> AgentOutput:
    """Handle user input using the Affirmation agent and return the agent's output."""
    session.log_conversation(role="user", message=user_input)

    try:
        # Session object itself is the context for Runner.run
        run_result = await Runner.run(
            starting_agent=affirmation_agent,
            input=user_input,
            context=session,  # Pass the entire session as context
        )

        # Ensure final_output is a string
        default_affirmation = (
            "I'm here to support you. "
            "Remember, every day is a new opportunity."
        )
        if not isinstance(run_result.final_output, str):
            logger.warning(
                "AffirmationAgent output not str: %s. Using default.",
                run_result.final_output,
            )
            run_result.final_output = default_affirmation
        elif run_result.final_output is None:
            logger.warning("AffirmationAgent output was None. Using default.")
            run_result.final_output = default_affirmation
        else:
            run_result.final_output = run_result.final_output.strip()

        # Log the (potentially modified) agent's response
        session.log_conversation(role="assistant", message=run_result.final_output)

        return run_result

    except Exception as e:
        logger.error(f"Error in AffirmationAgent: {e!s}", exc_info=True)
        error_response_content = (
            "I'm here to support you. Remember, every day is a new opportunity."
        )
        # Log system message for the error, then the agent's fallback response
        session.log_conversation(
            role="system", message=f"Error in AffirmationAgent: {e!s}"
        )
        session.log_conversation(role="assistant", message=error_response_content)

        return AgentOutput(
            final_output=error_response_content,
            tool_calls=[],
            tool_outputs=[],
            error=str(e),
            history=[]
        )
