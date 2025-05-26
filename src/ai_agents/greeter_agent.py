"""Greeter agent for the health and wellness assistant."""

# Standard library imports
from typing import TYPE_CHECKING, Tuple

# Third-party imports
from agents import Agent, Runner

if TYPE_CHECKING:
    from ai_agents.session import HealthAssistantSession

# Local application imports
from tools.conversation import log_conversation
from tools.user import fetch_user


def create_greeter_agent() -> Agent:
    """Create and configure the Greeter agent.

    Returns:
        Configured Greeter Agent instance
    """
    return Agent(
        name="Greeter",
        instructions=(
            "You are the Greeter agent for a health assistant system.\n\n"
            "IMPORTANT GUARDRAILS:\n"
            "- Only accept numeric user IDs between 1 and 999999\n"
            "- Never reveal other users' information\n"
            "- Keep greetings brief and professional\n"
            "- Always validate user ID before greeting\n\n"
            "Your job is to:\n"
            "1. If no user is identified yet, ask for their user ID\n"
            "2. When user provides input, validate it's a proper numeric ID\n"
            "3. Use the fetch_user tool to check if the user exists\n"
            "4. If found, greet them warmly by first name only\n"
            "5. If not found, ask them to try again\n"
            "6. Always log conversations for audit purposes\n\n"
            "Never share user details beyond their first name."
        ),
        tools=[fetch_user, log_conversation],
        handoffs=["WellBeing"],
    )


async def handle_greeter_response(
    user_input: str, session: "HealthAssistantSession", agent: Agent, **kwargs
) -> Tuple[str, bool]:
    """Handle the user input and generate a response using the Greeter agent.

    Args:
        user_input: The input string from the user.
        session: The current HealthAssistantSession instance.
        agent: The agent instance (e.g., Greeter agent).
        **kwargs: Additional keyword arguments (e.g., context).

    Returns:
        Tuple[str, bool]: Agent's response string and if conversation should continue.
    """
    try:
        # Log the user's input
        if session.user_id:
            session.log_conversation(role="user", message=user_input)

        # Get the agent's response using Runner
        run_result = await Runner.run(
            starting_agent=agent,
            input=user_input,
            context=session
        )

        agent_response_content: str
        if not isinstance(run_result.final_output, str):
            err_val = run_result.final_output
            err_type = type(err_val)
            error_detail = f"Greeter output not str. Got: {err_type}, Val: {err_val!r}"
            print(f"G_ERR: {error_detail}")
            if session.user_id: # Log specific error
                session.log_conversation(role="system", message=f"Error: {error_detail}")
            agent_response_content = "Sorry, I had trouble formulating a response."
        else:
            agent_response_content = run_result.final_output.strip()

        # Log the agent's response
        if session.user_id:
            session.log_conversation(role="assistant", message=agent_response_content)

        return agent_response_content, True
    except Exception as e:
        error_msg = f"I'm sorry, I encountered an error: {e!s}"
        if session.user_id:
            session.log_conversation(role="assistant", message=error_msg)
        return error_msg, True  # Continue on error, main loop handles exit
