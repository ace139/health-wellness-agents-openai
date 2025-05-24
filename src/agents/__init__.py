"""Agent definitions for the health and wellness assistant."""

# Standard library imports
from typing import Any, List

# Third-party imports
# (none currently)
# Local application imports
from .affirmation_agent import (
    create_affirmation_agent,
    handle_affirmation_response,
)
from .general_query_agent import (
    create_general_query_agent,
    handle_general_query_response,
)
from .greeter_agent import create_greeter_agent, handle_greeter_response
from .health_monitor_agent import (
    create_health_monitor_agent,
    handle_health_monitor_response,
)
from .planner_agent import create_planner_agent, handle_planner_response
from .router_agent import (
    RouterAgent,
    parse_router_response,
    should_handoff_to_planner,
)
from .session import HealthAssistantSession
from .wellbeing_agent import create_wellbeing_agent, handle_wellbeing_response

# Re-export agent creation functions and handlers
__all__: List[str] = [
    # Session
    "HealthAssistantSession",
    # Router
    "RouterAgent",
    "parse_router_response",
    "should_handoff_to_planner",
    # Agent creators
    "create_greeter_agent",
    "create_wellbeing_agent",
    "create_health_monitor_agent",
    "create_planner_agent",
    "create_affirmation_agent",
    "create_general_query_agent",
    # Agent handlers
    "handle_greeter_response",
    "handle_wellbeing_response",
    "handle_health_monitor_response",
    "handle_planner_response",
    "handle_affirmation_response",
    "handle_general_query_response",
]

# Agent name constants
GREETER_AGENT = "Greeter"
WELLBEING_AGENT = "WellBeing"
HEALTH_MONITOR_AGENT = "HealthMonitor"
PLANNER_AGENT = "Planner"
AFFIRMATION_AGENT = "Affirmation"
GENERAL_QUERY_AGENT = "GeneralQuery"

# Agent name list for easy iteration
AGENT_NAMES = [
    GREETER_AGENT,
    WELLBEING_AGENT,
    GENERAL_QUERY_AGENT,
    HEALTH_MONITOR_AGENT,
    PLANNER_AGENT,
    AFFIRMATION_AGENT,
]

# Agent creation function mapping
AGENT_CREATORS = {
    GREETER_AGENT: create_greeter_agent,
    WELLBEING_AGENT: create_wellbeing_agent,
    HEALTH_MONITOR_AGENT: create_health_monitor_agent,
    PLANNER_AGENT: create_planner_agent,
    AFFIRMATION_AGENT: create_affirmation_agent,
}

# Agent handler function mapping
AGENT_HANDLERS = {
    GREETER_AGENT: handle_greeter_response,
    WELLBEING_AGENT: handle_wellbeing_response,
    HEALTH_MONITOR_AGENT: handle_health_monitor_response,
    PLANNER_AGENT: handle_planner_response,
    AFFIRMATION_AGENT: handle_affirmation_response,
}

def create_agent(agent_name: str) -> Any:
    """Create an agent by name.
    
    Args:
        agent_name: Name of the agent to create
        
    Returns:
        The created agent instance
        
    Raises:
        ValueError: If the agent name is not recognized
    """
    if agent_name == GREETER_AGENT:
        return create_greeter_agent()
    elif agent_name == WELLBEING_AGENT:
        return create_wellbeing_agent()
    elif agent_name == HEALTH_MONITOR_AGENT:
        return create_health_monitor_agent()
    elif agent_name == PLANNER_AGENT:
        return create_planner_agent()
    elif agent_name == AFFIRMATION_AGENT:
        return create_affirmation_agent()
    elif agent_name == GENERAL_QUERY_AGENT:
        return create_general_query_agent()
    else:
        raise ValueError(f"Unknown agent name: {agent_name}")

def get_agent_handler(agent_name: str):
    """Get the handler function for an agent by name.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        The handler function for the agent
        
    Raises:
        ValueError: If the agent name is not recognized
    """
    if agent_name == GREETER_AGENT:
        return handle_greeter_response
    elif agent_name == WELLBEING_AGENT:
        return handle_wellbeing_response
    elif agent_name == HEALTH_MONITOR_AGENT:
        return handle_health_monitor_response
    elif agent_name == PLANNER_AGENT:
        return handle_planner_response
    elif agent_name == AFFIRMATION_AGENT:
        return handle_affirmation_response
    elif agent_name == GENERAL_QUERY_AGENT:
        return handle_general_query_response
    else:
        raise ValueError(f"No handler for agent: {agent_name}")
