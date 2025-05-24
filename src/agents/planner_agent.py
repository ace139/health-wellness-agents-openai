"""Planner agent for creating personalized meal plans."""
# Standard library imports
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

# Third-party imports
from openai_agents import Agent

if TYPE_CHECKING:
    from agents.session import HealthAssistantSession

# Local application imports
from tools.conversation import log_conversation
from tools.health import get_cgm_statistics
from tools.meal_planning import get_meal_plan, save_meal_plan
from tools.user import fetch_user


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
            "\"Based on your [dietary preference] diet and recent glucose levels, "
            "here's tomorrow's meal plan:\n\n"
            "**Breakfast**: [Specific food with portion]\n"
            "**Lunch**: [Specific food with portion]\n"
            "**Dinner**: [Specific food with portion]\n\n"
            "**Tips**: [1-2 practical tips for glucose management]\"\n\n"
            "4. Extract meals and save using save_meal_plan tool\n"
            '5. End with: "Remember to stay hydrated and monitor your '\
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
        handoffs=["Done"]
    )


def handle_planner_response(
    user_input: str,
    session: 'HealthAssistantSession',
    planner_agent: Agent,
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, bool]:
    """Handle the user input and generate a response using the Planner agent.
    
    Args:
        user_input: The user's input text
        session: Current health assistant session
        planner_agent: Configured Planner agent instance
        context: Additional context for the agent
        
    Returns:
        Tuple of (response_text, should_continue)
        - response_text: The agent's response text
        - should_continue: Whether to continue the conversation
    """
    # Log the user's input
    session.log_conversation(role="user", message=user_input)
    
    try:
        # Prepare the context for the agent
        agent_context = session.get_context()
        if context:
            agent_context.update(context)
        
        # Get response from the agent
        response = planner_agent.run(
            user_input,
            user_id=session.user_id,
            session_id=session.session_id,
            **agent_context
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
            "I'm sorry, I encountered an error while creating your meal plan: "
            f"{e!s}"
        )
        session.log_conversation(role="system", message=f"Error: {str(e)}")
        return error_msg, True
