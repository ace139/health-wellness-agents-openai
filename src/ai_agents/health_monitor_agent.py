"""Health Monitor agent for tracking CGM readings and health metrics."""

# Standard library imports
import logging
from typing import TYPE_CHECKING, Tuple

# Third-party imports
from agents import Agent, Runner

# Local application imports
from tools.conversation import log_conversation
from tools.health import get_cgm_statistics, log_cgm_reading

if TYPE_CHECKING:
    from .session import HealthAssistantSession  # noqa: F401

logger = logging.getLogger(__name__)


def create_health_monitor_agent() -> Agent:
    """Create and configure the Health Monitor agent.

    Returns:
        Configured Health Monitor Agent instance
    """
    return Agent(
        name="HealthMonitor",
        instructions=(
            "You are a Health Monitor agent. Your role is to help users log and "
            "understand their CGM readings and other vital health metrics. "
            "Be empathetic, informative, and encouraging.\n\n"
            "CRITICAL SAFETY GUARDRAILS:\n"
            "- Only accept numeric values between 20 and 600\n"
            "- For dangerous values (<50 or >250), ALWAYS advise medical attention\n"
            "- Never diagnose or provide specific medical advice\n"
            "- Assume mg/dL unless value is below 30 (then it's mmol/L)\n\n"
            "Your job is to:\n"
            "1. Ask for current blood glucose reading in mg/dL\n"
            "2. Validate input is numeric and within range (20-600)\n"
            "Then, provide a brief interpretation and ask if they want more details "
            "or statistics (use 'get_cgm_statistics').\n\n"
            "5. Respond based on status:\n"
            "   - Dangerously low/high: Urgent medical attention message\n"
            "   - Normal (70-140): Positive reinforcement\n"
            "   - Elevated/high: Offer meal planning help\n"
            "   - Invalid: Ask for a valid number\n\n"
            "If user says they don't have a reading:\n"
            '"No problem! Please check back when you have your reading. '
            'Remember to monitor regularly for better health management."\n\n'
            "NEVER:\n"
            "- Suggest specific medications\n"
            "- Change treatment plans\n"
            "- Minimize dangerous readings\n"
            "- Provide specific medical advice beyond general safety"
        ),
        tools=[log_cgm_reading, get_cgm_statistics, log_conversation],
        handoffs=["Planner", "Done"],
    )


async def handle_health_monitor_response(
    user_input: str,
    session: "HealthAssistantSession",
    agent: Agent,
) -> Tuple[str, bool]:
    """Handle the user input and generate a response using the Health Monitor agent.

    Args:
        user_input: The user's input text
        session: Current health assistant session
        health_monitor_agent: Configured Health Monitor agent instance

    Returns:
        Tuple of (response_text, should_continue)
        - response_text: The agent's response text
        - should_continue: Whether to continue the conversation
    """
    # Log the user's input
    session.log_conversation(role="user", message=user_input)

    try:
        # Get response from the agent
        run_result = await Runner.run(
            starting_agent=agent,
            input=user_input,
            context=session,  # Pass the HealthAssistantSession instance
        )

        if not isinstance(run_result.final_output, str):
            # Handle cases where the agent might not return a string
            # Or if there's an error within the agent execution handled by the Runner
            final_output_str = str(run_result.final_output)
            prefix = "HealthMonitor agent did not return a string: "
            ellipsis = "..."

            # Max len for logger.error() arg to keep total line under 88 chars.
            # Calculation: indent + logger.error() + content + ) <= 88.
            max_content_len_for_log = 62

            log_content: str
            if len(prefix) + len(final_output_str) > max_content_len_for_log:
                # Calculate space for the variable part of final_output_str
                len_available_for_var_part = (
                    max_content_len_for_log - len(prefix) - len(ellipsis)
                )
                # Ensure non-negative length for slicing
                len_available_for_var_part = max(0, len_available_for_var_part)

                truncated_var_part = final_output_str[:len_available_for_var_part]
                log_content = prefix + truncated_var_part + ellipsis
            else:
                log_content = prefix + final_output_str

            logger.error(log_content)
            response_content = "I'm sorry, I had trouble understanding that."
        else:
            response_content = run_result.final_output

        # Log the agent's response
        log_response_content = response_content
        if len(log_response_content) > 70:  # Truncate if too long for logging
            log_response_content = log_response_content[:67] + "..."
        session.log_conversation(role="assistant", message=log_response_content)

        # Check if we should hand off to another agent
        should_continue = not any(
            handoff in response_content.lower()
            for handoff in ["handing off to", "transferring to", "now to"]
        )

        return response_content.strip(), should_continue

    except Exception as e:
        error_msg = f"Sorry, an error occurred while processing your health data: {e!s}"
        # Truncate long exception messages for logging to avoid line length issues
        log_message = f"Error: {e!s}"
        if len(log_message) > 70:  # 70 to leave room for 'Error: ' and quotes
            log_message = log_message[:67] + "..."
        session.log_conversation(role="system", message=log_message)
        return error_msg, True
