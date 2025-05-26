"""Router agent for determining the appropriate agent to handle user input."""

# Standard library imports
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

# Third-party imports
from agents import Agent, Runner

# Local application imports
from ai_agents.session import HealthAssistantSession

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    # Local application imports
    from tools.conversation import log_conversation


class RouterAgent:
    """Handles routing between different agents based on user input."""

    def __init__(self):
        """Initialize the Router agent."""
        self.agent = self._create_router_agent()
        self.valid_agents = [
            "Greeter",
            "WellBeing",
            "HealthMonitor",
            "Planner",
            "Affirmation",
        ]

    def _create_router_agent(self) -> Agent:
        """Create and configure the Router agent.

        Returns:
            Configured Router Agent instance
        """
        return Agent(
            name="Router",
            instructions=(
                "You are a routing agent that safely determines user intent.\n\n"
                "Analyze the user input and classify it as:\n"
                '- "greeting": New conversation or greeting\n'
                '- "wellbeing": About feelings or emotional state\n'
                '- "health": About health metrics or readings\n'
                '- "planning": About meal planning or diet\n'
                '- "encouragement": Request for motivation\n'
                '- "inappropriate": Harmful or dangerous content\n\n'
                "Respond with ONLY a JSON object like:\n"
                "{\n"
                '    "intent": "greeting|wellbeing|health|planning|'
                'encouragement|inappropriate",\n'
                '    "confidence": 0.0-1.0,\n'
                '    "reason": "Brief explanation of your decision"\n'
                "}\n\n"
                "Examples:\n"
                '- "Hello!" -> {"intent": "greeting", '
                '"confidence": 0.95, "reason": "User greeting"}\n'
                '- "I\'m feeling great" -> {"intent": "wellbeing", '
                '"confidence": 0.9, "reason": "Sharing feelings"}\n'
                "IMPORTANT:\n"
                "- Be very confident before marking as inappropriate\n"
                "- Default to greeting for new conversations\n"
                "- When in doubt, choose the most specific intent"
            ),
        )

    def parse_router_response(self, response: str) -> Dict[str, Any]:
        """Safely parse the router's JSON response.

        Args:
            response: The raw response from the router agent

        Returns:
            Parsed response with default values if parsing fails
        """
        try:
            # Clean up the response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            data = json.loads(response)

            # Validate the response
            if not isinstance(data, dict):
                raise ValueError("Response is not a JSON object")

            intent = data.get("intent", "greeting").lower()
            valid_intents = [
                "greeting",
                "wellbeing",
                "health",
                "planning",
                "encouragement",
                "inappropriate",
            ]
            if intent not in valid_intents:
                intent = "greeting"

            confidence = float(data.get("confidence", 0.5))
            # Clamp between 0 and 1
            confidence = max(0.0, min(1.0, confidence))

            return {
                "intent": intent,
                "confidence": confidence,
                "reason": str(data.get("reason", "")),
            }

        except (json.JSONDecodeError, ValueError, AttributeError):
            # Default to greeting if parsing fails
            return {
                "intent": "greeting",
                "confidence": 0.5,
                "reason": "Failed to parse router response",
            }

    async def determine_next_agent(
        self,
        user_input: str,
        current_agent_name: str,
        session: "HealthAssistantSession",
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, float, str]:
        """Determine the next agent to handle the user input.

        Args:
            user_input: The user's input text
            current_agent_name: Name of the current agent
            session: Current health assistant session
            context: Additional context for the router

        Returns:
            Tuple of (next_agent_name, confidence, reason)
        """
        # Always log the conversation
        if session.user_id:
            log_conversation(
                db=session.db,
                user_id=session.user_id,
                session_id=session.session_id,
                role="user",
                message=user_input,
                agent_name=current_agent_name,
            )

        try:
            # Get the router's response using Runner.run_sync
            # SDK ctx: HealthAssistantSession. App 'context' dict unused by Runner.
            # Routing inputs (current_agent_name, etc.) in user_input/instr.
            logger.debug(f"Router: agent type={type(self.agent)}")
            run_result = await Runner.run(
                starting_agent=self.agent,
                input=user_input,
                context=session  # HealthAssistantSession instance as SDK context
            )

            if not isinstance(run_result.final_output, str):
                err_msg = (
                    f"Router output not str. Type: {type(run_result.final_output)}, "
                    f"Val: {run_result.final_output!r}"
                )
                raise ValueError(err_msg)

            agent_response_content = run_result.final_output
            
            # Parse the response
            result = self.parse_router_response(agent_response_content)

            # Log the routing decision
            if session.user_id:
                log_conversation(
                    db=session.db,
                    user_id=session.user_id,
                    session_id=session.session_id,
                    role="system",
                    message=(
                        f"Router: {result['intent']} "
                        f"(confidence: {result['confidence']:.2f}): {result['reason']}"
                    ),
                    agent_name="Router",
                )

            # Map intent to agent name
            intent_to_agent = {
                "greeting": "Greeter",
                "wellbeing": "WellBeing",
                "health": "HealthMonitor",
                "planning": "Planner",
                "encouragement": "Affirmation",
                "inappropriate": "Greeter",  # Fall back to Greeter if inappropriate
            }

            next_agent = intent_to_agent.get(result["intent"], "Greeter")

            return (next_agent, result["confidence"], result["reason"])

        except Exception as e:
            # Log the error and default to Greeter
            if session.user_id:
                log_conversation(
                    db=session.db,
                    user_id=session.user_id,
                    session_id=session.session_id,
                    role="system",
                    message=f"Router error: {e!s}",
                    agent_name="Router",
                )

            return ("Greeter", 0.5, "Error in router: " + str(e))


def parse_router_response(response: str) -> Tuple[str, float]:
    """Parse router agent's JSON response safely.

    Args:
        response: The raw response string from the router agent

    Returns:
        Tuple of (intent, confidence)
    """
    try:
        # Remove any potential code blocks
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]

        data = json.loads(response.strip())
        intent = data.get("intent", "continue")
        confidence = float(data.get("confidence", 0.5))

        # Validate intent
        valid_intents = ["continue", "query", "update", "restart", "inappropriate"]
        if intent not in valid_intents:
            intent = "continue"

        return intent, confidence
    except (json.JSONDecodeError, AttributeError, ValueError):
        return "continue", 0.5


def should_handoff_to_planner(cgm_status: str) -> bool:
    """Determine if we should handoff to planner based on CGM status.

    Args:
        cgm_status: The status of the CGM reading

    Returns:
        bool: True if should handoff to planner, False otherwise
    """
    return cgm_status not in [
        "normal",
        "dangerously_low",
        "dangerously_high",
        "invalid",
    ]
