"""Greeter agent for the health and wellness assistant."""

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
from agents import Agent, Runner, agent_output  # Alphabetized

# Local application imports
from tools.conversation import log_conversation
from tools.user import fetch_user

if TYPE_CHECKING:
    from ai_agents.session import HealthAssistantSession  # Local, but for type checking



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
    user_input: str, session: "HealthAssistantSession", agent: Agent
) -> agent_output:
    """Handle the user input using the Greeter agent and return the agent's output.

    Args:
        user_input: The input string from the user.
        session: The current HealthAssistantSession instance.
        agent: The agent instance (e.g., Greeter agent).

    Returns:
        Runner.RunOutput: The output from the agent execution.
    """
    try:
        # Log the user's input
        if session.user_id:
            session.log_conversation(role="user", message=user_input)

        # Get the agent's response using Runner
        run_result: agent_output = await Runner.run(
            starting_agent=agent, input=user_input, context=session
        )

        # Ensure final_output is a string
        if not isinstance(run_result.final_output, str):
            err_val = run_result.final_output
            err_type = type(err_val)
            error_detail = (
                f"Greeter agent output was not a string. "
                f"Type: {err_type}, Value: {err_val!r}"
            )
            print(f"GREETER_AGENT_ERROR: {error_detail}")
            if session.user_id:
                # Log a concise system error message
                log_msg = "System: Greeter agent produced non-string output."
                session.log_conversation(role="system", message=log_msg)
            # Replace non-string output with a generic error message for the user
            run_result.final_output = (
                "I'm having a little trouble formulating a response right now. "
                "Please try again shortly."
            )
        elif run_result.final_output is not None: # Guard against None before stripping
            run_result.final_output = run_result.final_output.strip()
        else: # Handle case where final_output is None
            error_detail = "Greeter agent output was None."
            print(f"GREETER_AGENT_ERROR: {error_detail}")
            if session.user_id:
                log_msg = "System: Greeter agent produced no output (None)."
                session.log_conversation(role="system", message=log_msg)
            run_result.final_output = (
                "I seem to be at a loss for words. "
                "Could you try rephrasing?"
            )

        # Logging of user input and agent response can be centralized
        # in the session manager or main loop after this handler returns AgentOutput.
        return run_result
    except Exception as e:
        # If an exception occurs, we should ideally return an AgentOutput
        # that signifies an error. The openai-agents SDK's AgentOutput
        # can carry error information. For now, creating a mock error response.
        # This needs alignment with how the main loop handles agent exceptions.
        error_response_content = f"I'm sorry, I encountered an error: {e!s}"
        if session.user_id:
            session.log_conversation(role="assistant", message=error_response_content)
        
        # Construct a valid AgentOutput for error case
        # This is a simplified error representation. A more robust solution
        # might involve creating an agent_output with error details.
        # For now, we'll mimic a simple string output within AgentOutput.
        return agent_output(
            final_output=error_response_content,
            tool_calls=[],
            tool_outputs=[],
            error=str(e),
            history=[]
        )
