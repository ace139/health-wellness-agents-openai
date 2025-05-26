"""Planner agent for creating personalized meal plans."""

# Standard library imports
import logging
from typing import TYPE_CHECKING

# Third-party imports
from agents import Agent, AgentOutput, Runner  # Alphabetized and on separate lines

# Local application imports
from tools.conversation import log_conversation
from tools.health import get_cgm_statistics
from tools.meal_planning import get_meal_plan, save_meal_plan
from tools.user import fetch_user

if TYPE_CHECKING:
    from ai_agents.session import HealthAssistantSession

logger = logging.getLogger(__name__) # Added logger


def create_planner_agent() -> Agent:
    """Create and configure the Planner agent.

    Returns:
        Configured Planner Agent instance
    """
    return Agent(
        name="Planner",
        instructions=(
            "You are the Meal Planner agent who creates personalized, "
            "safe meal plans.\n\n"
            "IMPORTANT GUARDRAILS:\n"
            "- Always respect dietary preferences exactly "
            "(no substitutions)\n"
            "- Focus on evidence-based nutrition for glucose management\n"
            "- Never suggest extreme diets or unsafe practices\n"
            "- Keep portions reasonable and balanced\n"
            "- Consider medical conditions in suggestions\n\n"
            "When activated:\n"
            "1. Use fetch_user to get dietary preferences and conditions\n"
            "2. Use get_cgm_statistics for 7-day glucose patterns\n"
            "3. Create a balanced meal plan that:\n"
            "   - STRICTLY follows dietary preference\n"
            "   - Helps stabilize glucose (low glycemic index if high)\n"
            "   - Includes portion sizes\n"
            "   - Considers medical conditions\n"
            "   - Is practical and accessible\n\n"
            "Format as:\n"
            '"Based on your [dietary preference] diet and recent glucose levels, '
            "here's tomorrow's meal plan:\n\n"
            "**Breakfast**: [Specific food with portion]\n"
            "**Lunch**: [Specific food with portion]\n"
            "**Dinner**: [Specific food with portion]\n\n"
            '**Tips**: [1-2 practical tips for glucose management]"\n\n'
            "4. Extract meals and save using save_meal_plan tool\n"
            '5. End with: "Remember to stay hydrated and monitor your '
            'glucose regularly!"\n\n'
            "NEVER suggest:\n"
            "- Foods against dietary restrictions\n"
            "- Extreme calorie restriction\n"
            "- Unbalanced meals\n"
            "- Expensive/rare ingredients"
        ),
        tools=[
            fetch_user,
            get_cgm_statistics,
            save_meal_plan,
            get_meal_plan,
            log_conversation,
        ],
        handoffs=["Done"],
    )


async def handle_planner_response(
    user_input: str,
    session: "HealthAssistantSession",
    planner_agent: Agent,  # Renamed parameter for clarity
) -> AgentOutput:
    """Handle the user input using the Planner agent and return AgentOutput.

    Args:
        user_input: The user's input text
        session: Current health assistant session
        agent: Configured Planner agent instance

    Returns:
        Tuple of (response_text, should_continue)
        - response_text: The agent's response text
        - should_continue: Whether to continue the conversation
    """
    # Log the user's input
    session.log_conversation(role="user", message=user_input)

    try:
        # Get response from the agent using Runner
        run_result = await Runner.run(
            starting_agent=planner_agent, # Used renamed parameter
            input=user_input,
            context=session,  # HealthAssistantSession is the SDK context
        )

        # Ensure final_output is a string
        default_response = (
            "Sorry, I had trouble generating the meal plan. "
            "Please try again."
        )
        if (
            not isinstance(run_result.final_output, str) 
            or run_result.final_output is None
        ):
            error_detail = (
                f"PlannerAgent output not str or None: "
                f"{run_result.final_output!r}"
            )
            logger.warning(error_detail)
            session.log_conversation(
                role="system", message=f"Error: {error_detail}"
            ) # Keep system log
            run_result.final_output = default_response
        else:
            run_result.final_output = run_result.final_output.strip()

        # Log the agent's response
        session.log_conversation(role="assistant", message=run_result.final_output)

        return run_result # Return the AgentOutput directly

    except Exception as e:
        logger.error(f"Error in PlannerAgent: {e!s}", exc_info=True)
        error_response_content = (
            "I'm sorry, I encountered an error while creating your meal plan. "
            "Please try again later."
        )
        session.log_conversation(
            role="system", message=f"Error in PlannerAgent: {e!s}"
        )
        session.log_conversation(role="assistant", message=error_response_content)

        return AgentOutput(
            final_output=error_response_content,
            tool_calls=[],
            tool_outputs=[],
            error=str(e),
            history=[]
        )
