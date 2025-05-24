"""Greeter agent for the health and wellness assistant."""
# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
from openai_agents import Agent

if TYPE_CHECKING:
    from agents.session import HealthAssistantSession

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
        handoffs=["WellBeing"]
    )


def handle_greeter_response(
    user_input: str,
    session: 'HealthAssistantSession',
    greeter_agent: Agent
) -> str:
    """Handle the user input and generate a response using the Greeter agent.
    
    Args:
        user_input: The user's input text
        session: Current health assistant session
        greeter_agent: Configured Greeter agent instance
        
    Returns:
        The agent's response text
    """
    # Log the user's input
    if session.user_id:
        session.log_conversation(role="user", message=user_input)
    
    try:
        # Get response from the agent
        response = greeter_agent.run(
            user_input,
            user_id=session.user_id or 0,  # Use 0 for unauthenticated users
            session_id=session.session_id,
            **session.get_context()
        )
        
        # Check if we have a valid user ID in the response
        if session.user_id is None and hasattr(response, 'tool_calls'):
            for tool_call in response.tool_calls:
                if (tool_call.function.name == "fetch_user" and 
                        tool_call.function.arguments):
                    try:
                        # Extract user ID from the tool call
                        import json
                        args = json.loads(tool_call.function.arguments)
                        if (user_id := args.get('user_id')):
                            session.set_user(user_id)
                            session.update_context(user_authenticated=True)
                            break
                    except (json.JSONDecodeError, AttributeError):
                        continue
        
        # Log the agent's response
        if session.user_id:
            session.log_conversation(role="assistant", message=response.content)
        
        return response.content.strip()
    except Exception as e:
        error_msg = f"I'm sorry, I encountered an error: {e!s}"
        if session.user_id:
            session.log_conversation(
                role="system", 
                message=f"Error: {e!s}"
            )
        return error_msg
