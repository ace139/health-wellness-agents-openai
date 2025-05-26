"""Router agent for determining the appropriate agent to handle user input."""

# Standard library imports
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

# Third-party imports
from agents import Agent, Runner

# Local application imports
from ai_agents.session import HealthAssistantSession
from tools.conversation import log_conversation

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    # Local application imports
    pass  # For type hinting


class RouterAgent:
    """Handles routing between different agents based on user input."""

    def __init__(self):
        """Initialize the Router agent."""
        self.agent = self._create_router_agent()
        self.valid_agents = [
            "Greeter",
            "Planner",
            "HealthMonitor",
            "GeneralQuery",
            "Affirmation",
            "WellBeing",
            "Done",  # For completed flows
        ]

    ROUTER_INSTRUCTIONS = (
        "Your role is to determine the most appropriate next agent based on the user's "
        "input and conversation history.\n\n"
        "**IMPORTANT**: The 'Greeter' agent's primary role is initial User ID "
        "collection. If the `session.user_id` is already set, you should **NOT** "
        "route to 'Greeter' unless the user explicitly asks to change their User ID "
        "or restart the identification process. The main application loop handles "
        "initial calls to 'Greeter' when no User ID is present.\n\n"
        "Consider the following specialized agents (available *after* User ID is "
        "collected):\n"
        "- Planner: Manages health plans, schedules, and goals. Use for inputs "
        "related to planning, scheduling appointments, setting health goals, or "
        "modifying existing plans.\n"
        "- HealthMonitor: Tracks and logs user's health metrics (e.g., heart rate, "
        "sleep, activity) and food intake. Use for inputs about logging data, or "
        "asking about past logged data.\n"
        "- GeneralQuery: Answers general health and wellness questions that don't fit "
        "other specialized agents. This is a good default if no other agent is a "
        "clear match.\n"
        "- Affirmation: Provides positive affirmations and motivational support. "
        "Use for requests for encouragement, positive statements, or to boost mood.\n"
        "- WellBeing: Focuses on mental wellbeing, stress management, mindfulness "
        "exercises, and emotional support. Use for inputs related to stress, "
        "anxiety, meditation, or general emotional state.\n\n"
        "Based on the user's latest input and the conversation history (if available), "
        "select the most relevant agent from the list above.\n"
        "If the user's input is ambiguous or doesn't clearly map to a specialized "
        "agent, route to 'GeneralQuery'.\n\n"
        'Output *only* the name of the chosen agent (e.g., "Planner", '
        '"GeneralQuery").'
    )

    def _create_router_agent(self) -> Agent:
        """Create and configure the Router agent.

        Returns:
            Configured Router Agent instance
        """
        return Agent(
            name="Router",
            instructions=self.ROUTER_INSTRUCTIONS,
            # model="gpt-4-turbo-preview", # Cheaper and often sufficient
            model="gpt-4o",  # Use the latest model
        )

    def parse_router_response(self, response: str) -> Dict[str, Any]:
        """Safely parse the router's new JSON response structure.

        Args:
            response: The raw response from the router agent.

        Returns:
            Parsed response dictionary with default values.
        """
        try:
            response = response.strip()

            data = json.loads(response)

            if not isinstance(data, dict):
                err_msg = f"Router response not a dict. Content: '{response[:200]}...'"
                raise ValueError(err_msg)

            parsed = {
                "intent": str(data.get("intent", "new_flow")).lower(),
                "is_interruption": bool(data.get("is_interruption", False)),
                "should_resume_after": bool(data.get("should_resume_after", False)),
                "target_agent": str(data.get("target_agent", "GreeterAgent")),
                "confidence": float(data.get("confidence", 0.5)),
                "reason": str(data.get("reason", "No reason provided.")),
            }

            parsed["confidence"] = max(0.0, min(1.0, parsed["confidence"]))

            if parsed["target_agent"] not in self.valid_agents:
                logger.warning(
                    f"Router returned unknown agent: '{parsed['target_agent']}'. "
                    f"Defaulting to GreeterAgent. Raw response: {response[:200]}"
                )
                # Fallback could be: parsed["target_agent"] = "GreeterAgent"

            return parsed

        except (json.JSONDecodeError, ValueError, AttributeError, TypeError) as e:
            logger.error(
                f"Error parsing router response: '{response[:500]}'. Error: {e}",
                exc_info=True,
            )
            return {
                "intent": "error_parsing_router_response",
                "is_interruption": False,
                "should_resume_after": False,
                "target_agent": "GreeterAgent",  # Default to a safe agent
                "confidence": 0.1,
                "reason": f"Critical error parsing router JSON response: {e!s}",
            }

    async def determine_next_agent(
        self,
        user_input: str,
        session: "HealthAssistantSession",
        context_dict: Optional[Dict[str, Any]] = None,  # Retained for flexibility
    ) -> Dict[str, Any]:
        """Determine next agent & action based on user input and conversation context.

        Args:
            user_input: User's input text.
            session: Current HealthAssistantSession instance.
            context_dict: Additional context (e.g., from main loop) that might not be
                          part of standard session attributes. This can be used by
                          session.prepare_for_routing if needed.

        Returns:
            A dictionary containing the routing decision.
        """
        try:
            # 1. Prepare session attributes for the router's context variables
            # session.prepare_for_routing() will use context_dict if it's relevant
            session.prepare_for_routing(context_dict=context_dict)

            # 2. Log user input
            # Use routing_context_current_agent (reflects context for this route)
            agent_name_for_log = session.routing_context_current_agent or "RouterCaller"
            self._log_user_input(session, user_input, agent_name_for_log)

            # 3. Log invocation details using the prepared session attributes
            self._log_router_invocation_details(
                user_input,
                session.routing_context_current_agent or "None",
                session.routing_context_current_state_summary or "N/A",
                session.routing_context_flow_stack_summary or "N/A",
            )

            # 4. Execute the router agent
            router_response_str = await self._execute_router_llm_run(
                router_agent=self.agent,  # From self._create_router_agent()
                session=session,
                user_input_for_prompt=user_input,
            )

            # 5. Parse the response
            parsed_result = self.parse_router_response(router_response_str)

            # 6. Log the router's decision
            self._log_router_decision(session, parsed_result)

            return parsed_result

        except Exception as e:
            logger.error(
                f"Critical error in RouterAgent.determine_next_agent: {e}",
                exc_info=True,
            )
            # Fallback response in case of any unhandled error in the process
            return {
                "intent": "error_determine_next_agent_exception",
                "is_interruption": False,
                "should_resume_after": False,
                "target_agent": "FallbackAgent",  # A safe default
                "confidence": 0.0,
                "reason": f"Unhandled exception in determine_next_agent: {e!s}",
            }

    def _log_user_input(
        self,
        session: "HealthAssistantSession",
        user_input: str,
        agent_name_for_log: str,
    ) -> None:
        """Logs the user's input."""
        if (
            hasattr(session, "user_id")
            and session.user_id
            and hasattr(session, "db")
            and "log_conversation" in globals()
        ):
            try:
                log_conversation(
                    db=session.db,
                    user_id=session.user_id,
                    session_id=session.session_id,
                    role="user",
                    message=user_input,
                    agent_name=agent_name_for_log,
                )
            except Exception as log_e:
                logger.error(f"Failed to log user input for router: {log_e}")

    def _log_router_invocation_details(
        self,
        user_input: str,
        current_agent_ctx: str,
        current_state_ctx: str,
        flow_stack_ctx: str,
    ) -> None:
        """Logs the details provided to the router agent for decision making."""
        logger.debug(
            f"I:'{user_input}'A:'{current_agent_ctx}'"
            f"St='{current_state_ctx}', Flw='{flow_stack_ctx}'"
        )

    async def _execute_router_llm_run(
        self,
        router_agent: Agent,
        session: "HealthAssistantSession",
        user_input_for_prompt: str,
    ) -> str:
        """Executes the router agent and returns its string output or an error JSON."""
        # The prompt for the LLM is now primarily the user_input, as other necessary
        # context (current_agent, state_summary, flow_stack_summary) is expected
        # to be accessed by the LLM from the session object's attributes directly,
        # as defined in ROUTER_INSTRUCTIONS (e.g., {{routing_context_current_agent}}).
        # The Runner.run call will make these session attributes available.

        # We pass user_input_for_prompt as the 'input' to Runner.run.
        # The ROUTER_INSTRUCTIONS should guide the LLM on how to use this input
        # in conjunction with the context variables from the session object.
        prompt_for_llm = (
            user_input_for_prompt  # Or a more structured format if needed later
        )

        try:
            run_result = await Runner.run(
                starting_agent=router_agent,  # Corrected: 'starting_agent'
                input=prompt_for_llm,
                context=session,  # Pass the full session object as context
            )

            if not run_result or not isinstance(run_result.final_output, str):
                err_msg = (
                    f"LLM out empty/not str. T:{type(run_result.final_output)}, "
                    f"Value: {run_result.final_output!r}"
                )
                logger.error(err_msg)
                return json.dumps(
                    {
                        "intent": "error_router_llm_output_invalid",
                        "reason": err_msg,
                        "target_agent": "FallbackAgent",
                        "confidence": 0.0,
                        "is_interruption": False,
                        "should_resume_after": False,
                    }
                )
            return run_result.final_output
        except Exception as e:
            logger.error(f"Exception during router LLM run: {e!s}", exc_info=True)
            return json.dumps(
                {
                    "intent": "error_router_llm_run_exception",
                    "reason": f"Exception in LLM run: {e!s}",
                    "target_agent": "FallbackAgent",
                    "confidence": 0.0,
                    "is_interruption": False,
                    "should_resume_after": False,
                }
            )

    def _log_router_decision(
        self, session: "HealthAssistantSession", parsed_result: Dict[str, Any]
    ) -> None:
        """Logs the router's decision."""
        if (
            hasattr(session, "user_id")
            and session.user_id
            and hasattr(session, "db")
            and "log_conversation" in globals()
        ):
            try:
                intent = parsed_result.get("intent", "N/A")
                target_agent = parsed_result.get("target_agent", "N/A")
                is_interruption = parsed_result.get("is_interruption", False)
                should_resume_after = parsed_result.get("should_resume_after", False)
                confidence = parsed_result.get("confidence", 0.0)
                reason = parsed_result.get("reason", "N/A")

                log_message = (
                    f"Router: int='{intent}', tgt='{target_agent}', "
                    f"intr={is_interruption}, res={should_resume_after}, "
                    f"conf={confidence:.2f}. Reason: {reason}"
                )
                log_conversation(
                    db=session.db,
                    user_id=session.user_id,
                    session_id=session.session_id,
                    role="system",
                    message=log_message,
                    agent_name="Router",
                )
            except Exception as log_e:
                logger.error(f"Failed to log router decision: {log_e}")
