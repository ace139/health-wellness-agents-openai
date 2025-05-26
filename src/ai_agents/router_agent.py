"""Router agent for determining the appropriate agent to handle user input."""

# Standard library imports
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

# Third-party imports
from agents import Agent, Runner

# Local application imports
from ai_agents.flow_manager import ConversationFlowManager  # For type hinting
from ai_agents.session import HealthAssistantSession
from tools.conversation import log_conversation

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    # Local application imports
    from ai_agents.flow_manager import ConversationFlowManager  # For type hinting


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

Available context variables (automatically injected into this prompt):
- {{routing_context_current_agent}}: Name of the last/current active agent.
- {{routing_context_current_state_summary}}: Summary of current task/state 
  (e.g., "Task: awaiting_cgm_reading", "General conversation").
- {{routing_context_flow_stack_summary}}: Indicates pending flows on stack 
  (e.g., "Pending flows: Yes (1 item)", "No pending flows").

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

    def _summarize_state_for_prompt(self, state_dict: Optional[Dict[str, Any]]) -> str:
        if not state_dict:
            return "No specific conversation state active."

        parts = []
        if current_task := state_dict.get("current_task"):
            parts.append(f"Current task: {current_task}.")
        if awaiting_input := state_dict.get("awaiting_input"):
            parts.append(f"Awaiting specific input: {awaiting_input}.")
        if collected_data_keys := list(state_dict.get("collected_data", {}).keys()):
            parts.append(f"Data collected so far: {collected_data_keys}.")

        if not parts:
            return "General conversation state, no specific task identified."
        return " ".join(parts)

    def _summarize_flow_stack_for_prompt(
        self, flow_manager: Optional["ConversationFlowManager"]
    ) -> str:
        if not flow_manager or not flow_manager.has_pending_flow():
            return "No pending flows."

        stack_size = len(flow_manager.flow_stack)
        if stack_size > 0 and flow_manager.flow_stack[-1]:
            last_flow_agent_name = flow_manager.flow_stack[-1][0]
            return (
                f"Pending flows: Yes ({stack_size} item(s) on stack. "
                f"Last interrupted agent: {last_flow_agent_name})"
            )
        return f"Pending flows: Yes ({stack_size} item(s) on stack)"

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
                "target_agent": "GreeterAgent",
                "confidence": 0.1,
                "reason": f"Critical error parsing router JSON response: {e!s}",
            }

    def _prepare_session_for_routing(
        self, session: "HealthAssistantSession", context_dict: Optional[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], str]:
        """Prepares session for routing, returns original values & log agent name."""
        if context_dict is None:
            context_dict = {}

        current_agent_name_for_prompt = context_dict.get("current_agent_name", "None")
        current_state_for_prompt = self._summarize_state_for_prompt(
            context_dict.get("current_state")
        )
        flow_stack_summary_for_prompt = self._summarize_flow_stack_for_prompt(
            getattr(session, "flow_manager", None)
        )

        original_context_values: Dict[str, Any] = {}
        context_attributes_to_set = {
            "routing_context_current_agent": current_agent_name_for_prompt,
            "routing_context_current_state_summary": current_state_for_prompt,
            "routing_context_flow_stack_summary": flow_stack_summary_for_prompt,
        }

        for key, value in context_attributes_to_set.items():
            if hasattr(session, key):
                original_context_values[key] = getattr(session, key)
            setattr(session, key, value)

        agent_name_for_log = (
            current_agent_name_for_prompt
            if current_agent_name_for_prompt != "None"
            else "UserDirectInput"
        )
        return original_context_values, agent_name_for_log

    async def determine_next_agent(
        self,
        user_input: str,
        session: "HealthAssistantSession",
        context_dict: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Determine next agent & action based on user input and conversation context.

        Args:
            user_input: User's input text.
            session: Current HealthAssistantSession instance.
            context_dict: Optional dict with 'current_agent_name', 'current_state',
                          'has_pending_flow'.

        Returns:
            A dictionary with the routing decision from parse_router_response.
        """
        original_context_values: Dict[str, Any] = {}
        agent_name_for_log = (
            "UserDirectInput"  # Default, updated by _prepare_session_for_routing
        )

        try:
            (
                original_context_values,
                agent_name_for_log,
            ) = self._prepare_session_for_routing(session, context_dict)

            # User Input Logging (To be extracted into a helper method later)
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

            # Main Agent Execution Block (To be further refactored)
            current_agent_ctx = getattr(session, "routing_context_current_agent", "N/A")
            current_state_ctx = getattr(
                session, "routing_context_current_state_summary", "N/A"
            )
            flow_stack_ctx = getattr(
                session, "routing_context_flow_stack_summary", "N/A"
            )
            self._log_router_invocation_details(
                user_input, current_agent_ctx, current_state_ctx, flow_stack_ctx
            )

            response_content = await self._execute_router_llm_run(
                self._router_agent, user_input, session.session_id
            )

            if not response_content: 
                return self.parse_router_response(response_content) 

            parsed_result = self.parse_router_response(response_content)
            logger.info(f"Router parsed decision: {parsed_result}")

            self._log_router_decision(session, parsed_result)

            return parsed_result

        except Exception as e:
            logger.error(
                f"Critical error in RouterAgent.determine_next_agent: {e}",
                exc_info=True,
            )
            error_payload = {
                "intent": "error_determine_next_agent_exception",
                "reason": f"Unhandled exception: {e!s}",
                "target_agent": "FallbackAgent",
                "confidence": 0.0,
                "is_interruption": False,
                "should_resume_after": False,
            }
            return self.parse_router_response(json.dumps(error_payload))
        finally:
            for key, value in original_context_values.items():
                setattr(session, key, value)
            attrs_to_clean = [
                "routing_context_current_agent",
                "routing_context_current_state_summary",
                "routing_context_flow_stack_summary",
            ]
            for attr in attrs_to_clean:
                if hasattr(session, attr):
                    try:
                        delattr(session, attr)
                    except AttributeError:
                        logger.warning(f"Could not delattr {attr} in cleanup.")

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
        self, router_agent: Agent, prompt: str, session_id: str
    ) -> str:
        """Executes the router agent and returns its string output or an error JSON."""
        try:
            run_result = await Runner.run(
                agent=router_agent, input=prompt, session_id=session_id
            )

            if not run_result or not isinstance(run_result.final_output, str):
                err_msg = (
                    f"LLM out empty/not str. T:{type(run_result.final_output)}, "
                    f"Value: {run_result.final_output!r}"
                )
                logger.error(err_msg)
                return json.dumps({
                    "intent": "error_router_llm_output_invalid",
                    "reason": err_msg,
                    "target_agent": "FallbackAgent",
                    "confidence": 0.0,
                    "is_interruption": False,
                    "should_resume_after": False,
                })
            return run_result.final_output
        except Exception as e:
            logger.error(f"Exception during router LLM run: {e!s}", exc_info=True)
            return json.dumps({
                "intent": "error_router_llm_run_exception",
                "reason": f"Exception in LLM run: {e!s}",
                "target_agent": "FallbackAgent",
                "confidence": 0.0,
                "is_interruption": False,
                "should_resume_after": False,
            })

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
