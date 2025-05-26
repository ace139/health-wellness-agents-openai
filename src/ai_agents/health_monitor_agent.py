"""Health Monitor agent for tracking CGM readings and health metrics."""

# Standard library imports
from typing import Tuple

# Third-party imports
from agents import Agent

# Local application imports
from ai_agents.session import HealthAssistantSession

# Relative imports
from tools.conversation import log_conversation
from tools.health import get_cgm_statistics, log_cgm_reading


def create_health_monitor_agent() -> Agent:
    """Create and configure the Health Monitor agent.

    Returns:
        Configured Health Monitor Agent instance
    """
    return Agent(
        name="HealthMonitor",
        instructions=(
            "You are the Health Monitor agent responsible for CGM readings.\n\n"
            "CRITICAL SAFETY GUARDRAILS:\n"
            "- Only accept numeric values between 20 and 600\n"
            "- For dangerous values (<50 or >250), ALWAYS advise medical attention\n"
            "- Never diagnose or provide specific medical advice\n"
            "- Assume mg/dL unless value is below 30 (then it's mmol/L)\n\n"
            "Your job is to:\n"
            "1. Ask for current blood glucose reading in mg/dL\n"
            "2. Validate input is numeric and within range (20-600)\n"
            "3. Use log_cgm_reading tool to record it\n"
            "4. Use get_cgm_statistics to show trends if available\n"
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


def handle_health_monitor_response(
    user_input: str, session: "HealthAssistantSession", health_monitor_agent: Agent
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
        response = health_monitor_agent.run(
            user_input,
            user_id=session.user_id,
            session_id=session.session_id,
            **session.get_context(),
        )

        # Log the agent's response
        session.log_conversation(role="assistant", message=response.content)

        # Check if we should hand off to another agent
        should_continue = not any(
            handoff in response.content.lower()
            for handoff in ["handing off to", "transferring to", "now to"]
        )

        return response.content.strip(), should_continue

    except Exception as e:
        error_msg = (
            "I'm sorry, I encountered an error while processing your health data: "
            f"{e!s}"
        )
        session.log_conversation(role="system", message=f"Error: {e!s}")
        return error_msg, True
