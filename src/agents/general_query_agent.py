"""General query agent for handling health-related questions."""
# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
from openai_agents import Agent

if TYPE_CHECKING:
    from src.agents.session import HealthAssistantSession

# Local application imports
from src.tools.conversation import log_conversation


def create_general_query_agent() -> Agent:
    """Create and configure the General Query agent.
    
    Returns:
        Configured General Query Agent instance
    """
    instructions = """You are a health knowledge assistant who answers general 
    questions safely.

STRICT GUARDRAILS:
- Provide only general health information
- Never diagnose conditions
- Never recommend specific medications
- Never contradict medical professionals
- Keep answers brief (2-3 sentences)
- Always include disclaimers when appropriate

When answering:
1. Provide evidence-based general information
2. Use phrases like "generally," "typically," "often"
3. For medical questions, add: "Please consult your healthcare provider for 
   personalized advice."
4. End with: "Now, let's continue with your health check."

Good examples:
- "Foods high in fiber like oats and beans generally help stabilize blood sugar."
- "Regular physical activity typically helps improve glucose control."

Never say:
- "You have diabetes"
- "Stop taking your medication"
- "This reading means you're sick"
- "Ignore your doctor's advice"

Log all interactions for quality assurance."""

    return Agent(
        name="GeneralQuery",
        instructions=instructions,
        tools=[log_conversation],
        handoffs=[]
    )


def handle_general_query_response(
    user_input: str,
    session: 'HealthAssistantSession',
    general_query_agent: Agent
) -> str:
    """Handle the user input and generate a response using the General Query agent.
    
    Args:
        user_input: The user's input text
        session: Current health assistant session
        general_query_agent: Configured General Query agent instance
        
    Returns:
        The agent's response text
    """
    try:
        # Log the conversation
        session.log_conversation(role="user", message=user_input)
        
        # Get response from the agent
        response = general_query_agent.run(user_input)
        
        # Log the response
        session.log_conversation(role="assistant", message=response.content)
        
        return response.content.strip()
        
    except Exception as e:
        error_msg = (
            "I'm sorry, I encountered an error while processing your query: "
            f"{e!s}"
        )
        session.log_conversation(role="system", message=f"Error: {e!s}")
        return error_msg
