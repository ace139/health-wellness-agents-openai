"""Main entry point for the Health and Wellness Assistant application."""

# Standard library imports
import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

# Third-party imports
from agents import Agent

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
            context: Additional context for the agent

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
            response, should_continue = await handler(
                user_input=user_input,
                session=self.session,
                agent=agent,
                context=context or {},
            )

            return response, should_continue

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
            return "Please start a session first."

        try:
            # Use router to determine next agent
            router_response = await self.router.determine_next_agent(
                user_input=user_input,
                session=self.session,
            )

            next_agent = router_response.get("target_agent", "FallbackAgent") 
            confidence = router_response.get("confidence", 0.0)
            reason = router_response.get("reason", "No reason provided")

            logger.info(
                f"Routing to {next_agent} (confidence: {confidence:.2f}): {reason}"
            )

            # Run the selected agent
            response, should_continue = await self.run_agent(
                next_agent,
                user_input,
                {"routing_reason": reason, "routing_confidence": confidence},
            )

            # If the agent indicates we should continue, stay with it
            if should_continue:
                self.current_agent_name = next_agent

            return response

        except Exception as e:
            logger.error(f"Error processing input: {e}", exc_info=True)
            return "I'm sorry, I encountered an error processing your request."
        except asyncio.CancelledError:
            logger.info("Input processing was cancelled.")
            # Log cancellation; run_cli handles KeyboardInterrupt for shutdown.
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
