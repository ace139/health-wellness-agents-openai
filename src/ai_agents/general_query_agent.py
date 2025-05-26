"""General query agent for handling health-related questions."""

# Standard library imports
import logging
from typing import TYPE_CHECKING

# Third-party imports
from agents import Agent, AgentOutput, Runner

# Local application imports
from tools.conversation import log_conversation

if TYPE_CHECKING:
    from ai_agents.session import HealthAssistantSession

logger = logging.getLogger(__name__)

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
        handoffs=[],
    )


async def handle_general_query_response(
    user_input: str, session: "HealthAssistantSession", general_query_agent: Agent
) -> AgentOutput:
    """Handle user input with General Query agent & return AgentOutput.

    Args:
        user_input: The user's input text
        session: Current health assistant session
        general_query_agent: Configured General Query agent instance

    Returns:
        Tuple of (response_text, should_continue)
    """
    try:
        session.log_conversation(role="user", message=user_input)

        run_result = await Runner.run(
            starting_agent=general_query_agent,
            input=user_input,
            context=session
        )

        # Ensure final_output is a string
        default_response = (
            "I'm sorry, I had trouble understanding that. "
            "Could you please rephrase?"
        )
        if not isinstance(run_result.final_output, str):
            logger.warning(
                "GeneralQueryAgent output not str: %s. Using default.",
                run_result.final_output,
            )
            run_result.final_output = default_response
        elif run_result.final_output is None:
            logger.warning(
                "GeneralQueryAgent output was None. Using default."
            )
            run_result.final_output = default_response
        else:
            run_result.final_output = run_result.final_output.strip()

        session.log_conversation(role="assistant", message=run_result.final_output)
        return run_result

    except Exception as e:
        logger.error(f"Error in GeneralQueryAgent: {e!s}", exc_info=True)
        error_response_content = (
            "I'm sorry, I encountered an error while processing your query. "
            "Please try again later."
        )
        session.log_conversation(
            role="system", message=f"Error in GeneralQueryAgent: {e!s}"
        )
        session.log_conversation(role="assistant", message=error_response_content)

        return AgentOutput(
            final_output=error_response_content,
            tool_calls=[],
            tool_outputs=[],
            error=str(e),
            history=[]
        )
