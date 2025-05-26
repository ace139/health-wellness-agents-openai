"""Health Monitor agent for tracking CGM readings and health metrics."""

# Standard library imports
import logging
from typing import TYPE_CHECKING

# Third-party imports
from agents import Agent, Runner, agent_output

from tools.conversation import log_conversation
from tools.health import get_cgm_statistics, log_cgm_reading

if TYPE_CHECKING:
    from .session import HealthAssistantSession

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
    health_monitor_agent: Agent, # Renamed parameter
) -> agent_output:
    """Handle the user input using the Health Monitor agent and return AgentOutput.

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
            starting_agent=health_monitor_agent, # Used renamed parameter
            input=user_input,
            context=session,  # Pass the HealthAssistantSession instance
        )

        # Ensure final_output is a string
        default_response = (
            "I'm sorry, I had trouble understanding that. "
            "Could you please try again?"
        )
        if (
            not isinstance(run_result.final_output, str) 
            or run_result.final_output is None
        ):
            logger.warning(
                "HealthMonitorAgent output not str or None: %s. "
                "Using default.",
                run_result.final_output,
            )
            run_result.final_output = default_response
        else:
            run_result.final_output = run_result.final_output.strip()

        # Log the agent's response (potentially truncated)
        log_response_content = run_result.final_output
        if len(log_response_content) > 70:
            log_response_content = log_response_content[:67] + "..."
        session.log_conversation(role="assistant", message=log_response_content)

        return run_result # Return the AgentOutput directly

    except Exception as e:
        logger.error(f"Error in HealthMonitorAgent: {e!s}", exc_info=True)
        error_response_content = (
            "Sorry, an error occurred while processing your health data. "
            "Please try again later."
        )
        # Log system message for the error, then the agent's fallback response
        session.log_conversation(
            role="system", message=f"Error in HealthMonitorAgent: {e!s}"
        )
        session.log_conversation(role="assistant", message=error_response_content)

        return agent_output(
            final_output=error_response_content,
            tool_calls=[],
            tool_outputs=[],
            error=str(e),
            history=[]
        )
