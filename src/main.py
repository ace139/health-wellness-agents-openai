"""Main entry point for the Health and Wellness Assistant application."""

# Standard library imports
import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

# Third-party imports
from agents import Agent, RunResult

# Local application imports
from ai_agents import (
    GREETER_AGENT,
    HealthAssistantSession,
    RouterAgent,
    create_agent,
    get_agent_handler,
)
from db.database import SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ANSI escape codes for colors
class Colors:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"  # Resets the color
    BOLD = "\033[1m"


class HealthAssistant:
    """Main class for the Health and Wellness Assistant application."""

    def __init__(self):
        """Initialize the Health Assistant with all required agents and components."""
        self.db = SessionLocal()
        self.router = RouterAgent()
        self.agents: Dict[str, Agent] = {}
        self.current_agent_name: str = GREETER_AGENT
        self.session: Optional[HealthAssistantSession] = None

    async def initialize(self):
        """Initialize all agents and components."""
        try:
            # Initialize all agents
            for agent_name in [
                GREETER_AGENT,
                "WellBeing",
                "HealthMonitor",
                "Planner",
                "Affirmation",
            ]:
                self.agents[agent_name] = create_agent(agent_name)

            logger.info("All agents initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            return False

    async def start_session(self, user_id: Optional[int] = None):
        """Start a new session with the health assistant.

        Args:
            user_id: Optional user ID if already known
        """
        try:
            self.session = HealthAssistantSession(user_id=user_id)
            logger.info(f"Started new session: {self.session.session_id}")

            # Start with the Greeter agent
            await self.run_agent(GREETER_AGENT, "")

        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            raise

    async def run_agent(
        self,
        agent_name: str,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, bool]:
        """Run the specified agent with the given input.

        Args:
            agent_name: Name of the agent to run
            user_input: User input to process
            # Log cancellation; run_cli handles KeyboardInterrupt.

        Returns:
            Tuple of (response_text, should_continue)
        """
        if not self.session:
            raise RuntimeError("No active session")

        try:
            agent = self.agents[agent_name]
            handler = get_agent_handler(agent_name)

            # Update the current agent
            self.current_agent_name = agent_name

            # Run the agent handler
            run_result: RunResult = await handler(
                user_input=user_input,
                session=self.session,
                agent=agent,
            )

            if not isinstance(run_result, RunResult):
                logger.error(
                    f"Handler for {agent_name} returned unexpected type: %s",
                    type(run_result),
                )
                return (
                    "I'm sorry, internal error (handler return type).",
                    False,  # Critical error, stop session processing
                )

            if run_result.final_output is None:
                logger.error(
                    f"Handler for {agent_name} returned RunResult with "
                    "final_output=None."
                )
                # Handler should populate final_output; this implies an error.
                return (
                    "I'm sorry, an internal error occurred (no final output).",
                    True,  # Allow user to try again
                )

            response_text = str(run_result.final_output)
            # If handler executed and produced output, the session loop should continue.
            should_continue_session = True

            return response_text, should_continue_session

        except KeyError:
            error_msg = (
                f"I'm sorry, I encountered an error. Unknown agent: {agent_name}"
            )
            logger.error(f"Unknown agent: {agent_name}")
            return error_msg, False
        except Exception as e:
            logger.error(f"Error in agent {agent_name}: {e}", exc_info=True)
            return f"I'm sorry, I encountered an error: {str(e)}", False

    async def process_input(self, user_input: str) -> str:
        """Process user input and return the appropriate response.

        Args:
            user_input: The user's input text

        Returns:
            The agent's response text
        """
        if not self.session:
            logger.warning("process_input called without an active session.")
            return "Please start a session first."

        try:
            # 1. Get routing decision from RouterAgent
            router_decision = await self.router.determine_next_agent(
                user_input=user_input,
                session=self.session, # RouterAgent uses this to prepare context
            )

            logger.info(
                f"Router proposed: {router_decision.get('target_agent')} "
                f"(Intent: {router_decision.get('intent')}, "
                f"Confidence: {router_decision.get('confidence', 0.0):.2f}, "
                f"Interruption: {router_decision.get('is_interruption', False)}, "
                f"Resume: {router_decision.get('should_resume_after', False)}) - "
                f"Reason: {router_decision.get('reason', 'N/A')}"
            )

            # 2. Let the session handle the routing decision and manage flow stack
            # Returns: agent to run, input for agent, and is_resumed_flow flag.
            # (HealthAssistantSession.handle_routing_decision will be updated next)
            agent_to_run, input_for_agent, is_resumed_flow = \
                await self.session.handle_routing_decision(
                    router_decision=router_decision,
                    original_user_input=user_input
                )

            logger.info(
                f"Session decided: Run '{agent_to_run}' (Resumed: {is_resumed_flow}) "
                f"with input: '{input_for_agent[:50]}...'"
            )

            # 3. Prepare context for the agent run
            agent_run_context = {
                "routing_decision": router_decision, # Full router output for agent
                "is_resumed_flow": is_resumed_flow,
            }

            # Update session with the task that is about to be run
            self.session.update_current_task_info(agent_to_run, input_for_agent)

            # 4. Run the selected agent
            response, should_continue = await self.run_agent(
                agent_name=agent_to_run,
                user_input=input_for_agent,
                context=agent_run_context,
            )

            # 5. Update current agent if the agent indicates continuation
            # The session's current_agent_name is updated by prepare_for_routing
            # and potentially by handle_routing_decision when resuming.
            # This self.current_agent_name is for the main loop's tracking.
            if should_continue:
                self.current_agent_name = agent_to_run
            elif is_resumed_flow:
                # If a resumed flow just finished (should_continue=False),
                # and a flow is pending, router guides to resume it.
                # If no flow pending, router guides to new flow (e.g. Greeter).
                # For now, just log. The next router call will handle it.
                logger.info(f"Resumed flow '{agent_to_run}' finished.")

            return response

        except Exception as e:
            logger.error(f"Error processing input: {e}", exc_info=True)
            return "I'm sorry, I encountered an error processing your request."
        except asyncio.CancelledError:
            logger.info("Input processing was cancelled.")
            return "Your request was cancelled."  # This message precedes "Goodbye!"

    async def close(self):
        """Clean up resources, including the session and database connection."""
        logger.info("Closing Health Assistant resources...")
        try:
            if self.session:
                logger.info(f"Closing session: {self.session.session_id}")
                await self.session.close()
                self.session = None  # Ensure session is cleared
                logger.info("Session closed.")
            if self.db:
                logger.info("Closing database connection.")
                self.db.close()  # Assuming db.close() is synchronous
                logger.info("Database connection closed.")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
        finally:
            logger.info("Health Assistant cleanup finished.")


async def run_cli():
    """Run the health assistant in CLI mode."""
    assistant = HealthAssistant()

    try:
        # Initialize the assistant
        success = await assistant.initialize()
        if not success:
            print(f"{Colors.RED}Initialization failed. Check logs.{Colors.ENDC}")
            return

        print(f"{Colors.YELLOW}Welcome to Health Assistant!{Colors.ENDC}")
        print(f"{Colors.YELLOW}Type 'exit' to quit at any time.\n{Colors.ENDC}")

        # Start a new session
        await assistant.start_session()

        # Main interaction loop
        while True:
            try:
                prompt = f"{Colors.BLUE}{Colors.BOLD}You: {Colors.ENDC}"
                user_input = input(prompt).strip()

                if user_input.lower() in ["exit", "quit", "bye"]:
                    print(f"{Colors.YELLOW}Goodbye! Take care!{Colors.ENDC}")
                    break

                if not user_input:
                    continue

                # Process the input and get the response
                response = await assistant.process_input(user_input)
                assistant_prompt = f"{Colors.GREEN}{Colors.BOLD}Assistant:{Colors.ENDC}"
                assistant_response = f"{Colors.GREEN}{response}{Colors.ENDC}"
                print(f"\n{assistant_prompt} {assistant_response}\n")

            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Goodbye!{Colors.ENDC}")
                break
            except Exception as e:
                print(f"\n{Colors.RED}An error occurred: {e}{Colors.ENDC}")
                logger.exception("Error in CLI loop")
                continue

    except Exception as e:
        logger.exception("Fatal error in CLI")
        print(f"{Colors.RED}A fatal error occurred: {e}{Colors.ENDC}")
    finally:
        await assistant.close()


if __name__ == "__main__":
    asyncio.run(run_cli())
