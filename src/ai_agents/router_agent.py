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
            "GreeterAgent",
            "WellBeingAgent",
            "HealthMonitorAgent",
            "PlannerAgent",
            "AffirmationAgent",
            "GeneralQueryAgent",
            "Done",  # For completed flows
        ]

    ROUTER_INSTRUCTIONS = """You are a sophisticated conversational flow router. 
    Your primary goal is to analyze the user's input and the current 
    conversational context to determine the correct course of action.

Available context variables (injected if present on session object for Runner.run):
- {{routing_context_current_agent}}: Name of the last/current active agent.
- {{routing_context_current_state_summary}}: Summary of current task/state 
  (e.g., "Task: awaiting_cgm_reading", "General conversation").
- {{routing_context_flow_stack_summary}}: Indicates pending flows on stack 
  (e.g., "Pending flows: Yes (1 item)", "No pending flows").
- {{routing_context_has_pending_flow}}: Boolean indicating if there's a pending flow.
- {{routing_context_interaction_count}}: Current interaction count in the session.

Your tasks:
1.  Classify the user's input. Intents can be:
    *   Flow-related:
        - 'continue_flow': User wants to continue current task/topic with the 
          previous agent or its successor.
        - 'interruption_query': User asks off-topic question or makes a comment 
          deviating from the current flow.
        - 'resume_flow': User explicitly wants to return to a previously 
          interrupted topic/task.
        - 'new_flow': User wants to start a new conversation/topic, or input 
          doesn't fit an ongoing flow.
    *   Content-related (if initiating a new flow or if the current flow is general):
        - 'greeting': Standard greetings, initiating conversation.
        - 'wellbeing': Discussions about feelings, mood, emotional state.
        - 'health_monitoring': Related to health metrics, CGM readings, symptoms.
        - 'meal_planning': Questions or discussions about diet, meal plans, food.
        - 'affirmation_seeking': User seeks encouragement or positive statements.
        - 'general_query': General question not fitting other categories and not 
          interrupting a specific task.
        - 'inappropriate': Harmful, dangerous, or off-limits content.

2.  Determine if input is an interruption to a focused task.
    - `is_interruption` (true/false): True if intent is 'interruption_query' 
      AND a clear ongoing task is deviated from (see 
      `routing_context_current_state_summary`).

3.  If interruption, decide if conversation should prompt to resume later.
    - `should_resume_after` (true/false): Typically true if `is_interruption` 
      is true and interruption is brief.

4.  Specify `target_agent` for this turn. Examples:
    - 'interruption_query': "GeneralQueryAgent"
    - 'resume_flow': "{{routing_context_current_agent}}" (or agent from stack; 
      calling code handles pop. Identify 'resume_flow' intent; target is often 
      the resumed agent).
    - 'new_flow' + 'greeting': "GreeterAgent"
    - 'new_flow' + 'health_monitoring': "HealthMonitorAgent"
    - 'continue_flow' with 'HealthMonitorAgent': "HealthMonitorAgent"
    - If 'inappropriate': "GreeterAgent" (as a safe default to handle it gracefully)

Output ONLY a JSON object with the following structure:
{
    "intent": "classified_intent_combination",
    "is_interruption": false,
    "should_resume_after": false,
    "target_agent": "NameOfAgent",
    "confidence": 0.9,
    "reason": "Brief explanation of routing, referencing context if helpful."
}

Example Scenarios:
- User: "Hello!", Ctx: agent="None", state="No task", flow="No pending"
  Output: {"intent": "new_flow_greeting", "is_interruption": false, 
  "should_resume_after": false, "target_agent": "GreeterAgent", 
  "confidence": 0.98, "reason": "User greeting, no active flow."}

- User: "Weather?", Context: current_agent="HealthMonitorAgent", 
  state_summary="Task: awaiting_cgm_reading", flow_summary="No pending"
  Output: {"intent": "interruption_query", "is_interruption": true, 
  "should_resume_after": true, "target_agent": "GeneralQueryAgent", 
  "confidence": 0.9, "reason": "Off-topic query during CGM task."}

- User: "Reading is 120.", Context: current_agent="HealthMonitorAgent", 
  state_summary="Task: awaiting_cgm_reading", flow_summary="No pending"
  Output: {"intent": "continue_flow_health_monitoring", 
  "is_interruption": false, "should_resume_after": false, 
  "target_agent": "HealthMonitorAgent", "confidence": 0.95, 
  "reason": "User providing requested CGM reading."}

- User: "Back to health readings.", Context: current_agent="GeneralQueryAgent", 
  state_summary="General convo", flow_summary="Pending: Yes (1 item, 
  HealthMonitorAgent)"
  Output: {"intent": "resume_flow", "is_interruption": false, 
  "should_resume_after": false, "target_agent": "HealthMonitorAgent", 
  "confidence": 0.99, "reason": "User wants to resume health discussion per stack."}

Important considerations:
- If `routing_context_flow_stack_summary` shows pending flow, and user says 
  "continue" or "back to it", intent is 'resume_flow'. `target_agent` is often 
  from stack top (e.g., `HealthMonitorAgent`).
- If `routing_context_current_agent` is focused (e.g., HealthMonitorAgent mid-task 
  per `routing_context_current_state_summary`) and input is unrelated, it's 
  likely 'interruption_query'.
- `target_agent` must be one of: "GreeterAgent", "WellBeingAgent", 
  "HealthMonitorAgent", "PlannerAgent", "AffirmationAgent", "GeneralQueryAgent".
- Be cautious with 'inappropriate' classification.
"""

    def _create_router_agent(self) -> Agent:
        """Create and configure the Router agent.

        Returns:
            Configured Router Agent instance
        """
        return Agent(
            name="Router",
            instructions=self.ROUTER_INSTRUCTIONS,
            context_variables=[
                "routing_context_current_agent",
                "routing_context_current_state_summary",
                "routing_context_flow_stack_summary",
                "routing_context_has_pending_flow",
                "routing_context_interaction_count",
            ],
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
