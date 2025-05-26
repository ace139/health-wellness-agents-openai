# Health & Wellness Agent

A CLI-based health and wellness assistant powered by OpenAI's GPT-4, designed to help users track their wellbeing and manage their health through natural language interactions.

## Features

- **User Authentication**: Simple user ID-based authentication
- **Wellbeing Tracking**: Log and track daily feelings and emotions
- **CGM Monitoring**: Record and analyze Continuous Glucose Monitor readings
- **Meal Planning**: Generate personalized meal plans based on dietary preferences
- **Positive Reinforcement**: Receive affirmations for maintaining healthy glucose levels
- **Multi-Agent System**: Specialized agents for different health and wellness tasks
- **Conversation Logging**: Track interactions for better context and personalization
- **Advanced Conversation Management**: Sophisticated handling of multi-turn conversations, interruptions, and context resumption.

## Agent System Overview

The Health & Wellness Assistant uses a multi-agent architecture where each agent is specialized for a specific task:

### 1. Greeter Agent
- First point of contact for users
- Handles user identification and authentication
- Provides a warm welcome and explains available features

### 2. WellBeing Agent
- Tracks and analyzes emotional states
- Provides insights based on mood patterns
- Offers support and coping strategies

### 3. HealthMonitor Agent
- Records and analyzes health metrics (e.g., glucose levels)
- Provides feedback on health trends
- Alerts about potential health concerns

### 4. Planner Agent
- Creates personalized meal plans
- Considers dietary restrictions and preferences
- Suggests recipes and meal timing

### 5. Affirmation Agent
- Provides positive reinforcement
- Celebrates user achievements
- Offers encouragement and motivation

### 6. Router Agent
- Central component for intelligent conversation navigation.
- Analyzes user input and session context to determine the most appropriate agent or action.
- Manages conversation flow, including handling interruptions, saving current task context, and resuming prior conversations seamlessly.
- Works closely with `HealthAssistantSession` and `ConversationFlowManager` to orchestrate complex interaction patterns.
- Ensures smooth handoffs and maintains conversational coherence across different functionalities.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- OpenAI API key
- `uv` package manager

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/health-wellness-assistant.git
   cd health-wellness-assistant
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies using uv:
   ```bash
   uv pip install -r requirements.txt
   ```

4. Set up your environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key and other settings
   ```

## Usage

### Running the Application

```bash
# Start the CLI application
python -m src.main
```

### Available Commands

- `exit` or `quit`: Exit the application
- `help`: Show available commands
- `log [feeling]`: Log how you're feeling today
- `glucose [reading]`: Log a glucose reading
- `plan meals`: Get a personalized meal plan
- `affirmation`: Receive a positive affirmation

### Example Session

```
Welcome to the Health and Wellness Assistant!
Type 'exit' to quit at any time.

Assistant: Hello! I'm your Health and Wellness Assistant. May I have your user ID to get started?

You: 12345

Assistant: Welcome back, John! How can I assist you with your health and wellness today?

You: I'm feeling a bit tired today

Assistant: I'm sorry to hear you're feeling tired. Would you like to log this in your wellbeing journal?

You: yes

Assistant: I've logged that you're feeling tired today. Would you like to talk about what might be causing this?
```

## Architecture

The Health & Wellness Assistant employs a sophisticated, modular architecture designed for robust and flexible conversational AI experiences. Key components include:

-   **`HealthAssistant` (in `src/main.py`)**:
    -   The main application class that orchestrates the overall CLI interaction.
    -   Initializes and manages the user session (`HealthAssistantSession`).
    -   Contains the primary input processing loop, which involves invoking the `RouterAgent` and then the selected agent.

-   **`HealthAssistantSession` (in `src/ai_agents/session.py`)**:
    -   Manages the state of a single user's conversation.
    -   Tracks user ID, interaction counts, and general conversation context.
    -   Crucially, it owns and utilizes the `ConversationFlowManager` to handle complex conversational dynamics.
    -   Prepares context for the `RouterAgent` and processes its decisions to determine the next agent and input.
    -   Stores information about the current task being executed, which is vital for saving context during interruptions.

-   **`RouterAgent` (in `src/ai_agents/router_agent.py`)**:
    -   The central "brain" for conversation navigation.
    -   Uses an LLM to analyze user input, current session state (including active flows from `ConversationFlowManager`), and agent capabilities to decide the next step.
    -   Determines the `intent` (e.g., new flow, resume flow, interruption), the `target_agent`, and whether an interruption should lead to saving the current flow.

-   **`ConversationFlowManager` (in `src/ai_agents/session.py` or a dedicated `flow_manager.py`)**:
    -   Manages a stack of conversation flows.
    -   Allows the system to "push" (save) the context of an ongoing agent interaction (including its input and session state) when an interruption occurs.
    -   Allows the system to "pop" (resume) a previously saved flow, restoring its context and allowing the user to continue where they left off.
    -   This enables natural handling of tangents and multi-topic conversations.

-   **Specialized Agents (e.g., `GreeterAgent`, `PlannerAgent` in `src/ai_agents/`)**:
    -   Modules responsible for specific functionalities (greeting, meal planning, etc.).
    -   Receive input and session context, execute their logic (often involving an LLM call via `Runner.run`), and return a response and a continuation flag.
    -   Designed to be largely independent, relying on the `RouterAgent` for orchestration.

-   **`Runner` (from `openai_agents` SDK)**:
    -   A utility provided by the OpenAI Agents SDK to execute agent logic, typically involving LLM calls.
    -   Handles the low-level details of interacting with the OpenAI API.

-   **Tools (in `src/tools/`)**:
    -   Utility functions that agents can use (though not heavily implemented in the current example, this is a standard pattern). Examples could include database access, external API calls, etc.

### Conversation Flow Dynamics

A key aspect of this architecture is its ability to manage complex conversation flows:
1.  User input is first processed by the `RouterAgent`.
2.  The `RouterAgent` decides if the input is a new task, a continuation, an interruption of an existing task, or a request to resume a previous task.
3.  If an interruption occurs and the current task needs to be saved, `HealthAssistantSession` (using `ConversationFlowManager`) pushes the current agent's name, its input, and a snapshot of the session state onto a flow stack.
4.  The interrupting task is then handled by its designated agent.
5.  If the `RouterAgent` decides to resume a task, `HealthAssistantSession` pops the flow from the stack, restores its state, and directs execution back to the resumed agent with its original input.
6.  This allows for a natural, multi-threaded feel to the conversation, where users can switch topics and return without losing context.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with OpenAI's GPT-4 and the OpenAI Agents SDK
- Uses SQLAlchemy for database operations
- Inspired by the need for better personal health management tools

## Project Structure

```
health-assistant/
├── README.md
├── pyproject.toml
├── .env
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── main.py                     # CLI entry point, HealthAssistant class
│   ├── ai_agents/                  # Core agent logic and conversation management
│   │   ├── __init__.py
│   │   ├── session.py              # HealthAssistantSession, ConversationFlowManager
│   │   ├── router_agent.py         # RouterAgent definition
│   │   ├── greeter_agent.py        # GreeterAgent definition
│   │   ├── planner_agent.py        # PlannerAgent definition
│   │   ├── wellbeing_agent.py      # WellBeingAgent definition
│   │   ├── health_monitor_agent.py # HealthMonitorAgent definition
│   │   ├── affirmation_agent.py    # AffirmationAgent definition
│   │   └── general_query_agent.py  # GeneralQueryAgent definition
│   ├── tools/                      # Tool implementations (if any)
│   └── db/                       # Database operations (SQLAlchemy models, etc.)
└── tests/               # Basic tests
```

MIT
