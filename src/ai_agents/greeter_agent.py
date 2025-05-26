"""Greeter agent for the health and wellness assistant."""

# Standard library imports
import logging
from typing import TYPE_CHECKING

# Third-party imports
from agents import Agent, Runner, agent_output  # type: ignore

# Local application imports
from tools.conversation import log_conversation
from tools.user import fetch_user

if TYPE_CHECKING:
    from session import HealthAssistantSession  # type: ignore


logger = logging.getLogger(__name__)


def _parse_user_id_from_input(
    user_input: str, session: "HealthAssistantSession"
) -> bool:
    """Attempt to parse User ID from input and update session.

    Returns:
        True if User ID was newly captured, False otherwise.
    """
    if session.user_id is None and user_input and user_input.strip():
        try:
            parsed_id = int(user_input.strip())
            session.user_id = parsed_id
            log_msg_part1 = f"GreeterAgent captured User ID: {session.user_id}"
            log_msg_part2 = f" from input '{user_input}'"
            logger.info(log_msg_part1 + log_msg_part2)
            return True
        except ValueError:
            logger.info(
                f"GreeterAgent: input '{user_input}' not a parsable User ID. "
                "LLM will re-prompt."
            )
    return False


def _get_fallback_response(
    session: "HealthAssistantSession", id_newly_captured: bool
) -> str:
    """Generate a fallback response if LLM output is empty."""
    if session.user_id is None:
        return "I still need your User ID. Please provide it."
    if id_newly_captured:
        return f"Thank you, User ID {session.user_id} recorded. How can I help?"
    # This implies user_id was already known
    return f"User ID {session.user_id} active. How can I assist?"


def create_greeter_agent() -> Agent:
    """Create and configure the Greeter agent.

    Returns:
        Configured Greeter Agent instance
    """
    return Agent(
        name="Greeter",
        instructions=(
            "You are the Greeter for a Health Assistant. "
            "Your **sole purpose** right now "
            "is to collect a numeric User ID.\n\n"
            "- If this is the first interaction (input is empty or User ID is not yet "
            "known by the system):\n"
            "  - Your response MUST be a polite request for the User ID. "
            'Example: "Hello! To get started, please provide your User ID."\n'
            "- If the user provides input that is NOT a number or seems like a "
            "question/statement instead of an ID:\n"
            "  - Your response MUST be a polite insistence on needing the User ID. "
            "Example: "
            '"I need a valid User ID to continue. Please enter your numeric User ID."\n'
            "  - DO NOT answer any questions. DO NOT engage in other conversation. "
            "Only ask for the User ID.\n"
            "- If the user provides what looks like a numeric User ID (e.g., the input "
            'was "123") AND the system has just captured it:\n'
            "  - Your response should be a confirmation. Example: "
            '"Thank you! User ID {user_id} received. How can I help you today?"\n\n'
            "If the system indicates the User ID was already known and this is just a "
            "re-greeting, you can offer help directly.\n\n"
            "STRICTLY ADHERE to this ID collection task. Do not deviate."
        ),
        tools=[fetch_user, log_conversation],
        handoffs=["WellBeing"],
    )


async def handle_greeter_response(
    user_input: str, session: "HealthAssistantSession", agent: Agent
) -> agent_output:
    """Handle user input for the Greeter agent, focusing on User ID collection.

    Attempts to parse User ID from input if not already in session.
    Calls the LLM and provides fallback responses if LLM output is empty.

    Args:
        user_input: The input string from the user.
        session: The current HealthAssistantSession instance.
        agent: The Greeter agent instance.

    Returns:
        An agent_output object containing the agent's response.
    """
    try:
        # Log conversational user input if User ID is known.
        # (ID-only input is not logged as a conversational turn).
        # Avoid logging if input is just an ID and user_id is already set
        if session.user_id and not user_input.strip().isdigit():
            session.log_conversation(role="user", message=user_input)

        id_newly_captured = _parse_user_id_from_input(user_input, session)

        # If ID was newly captured, ID-specific logging occurs in the helper.
        # is handled in _parse_user_id_from_input. More logs can go here.
        if id_newly_captured:
            # Successful ID capture is logged in _parse_user_id_from_input.
            # Additional system log here if desired.
            pass

        run_result = await Runner.run(
            starting_agent=agent, input=user_input, context=session
        )

        if run_result.final_output:
            final_output_str = str(run_result.final_output).strip()
        else:
            final_output_str = ""

        if not final_output_str:
            logger.warning("GreeterAgent LLM output empty. Constructing fallback.")
            final_output_str = _get_fallback_response(session, id_newly_captured)

        run_result.final_output = final_output_str

        # Log assistant's response if User ID is known (newly captured or pre-existing).
        if session.user_id:
            session.log_conversation(role="assistant", message=final_output_str)
        return run_result

    except Exception as e:
        logger.error(f"Error in GreeterAgent: {e!s}", exc_info=True)
        error_msg = "I encountered an error."
        if session.user_id is None:
            error_msg += " Please try providing your User ID again."

        # Log system error and assistant error message to conversation if user_id exists
        if session.user_id:
            system_error_log = f"System: Error in Greeter agent - {e!s}"
            session.log_conversation(role="system", message=system_error_log)
            session.log_conversation(role="assistant", message=error_msg)

        return agent_output(
            final_output=error_msg,
            tool_calls=[],
            tool_outputs=[],
            error=str(e),
            history=[],
        )
