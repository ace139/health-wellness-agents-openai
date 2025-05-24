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
- Analyzes user input to determine the most appropriate agent
- Handles conversation flow between agents
- Ensures smooth handoffs between different functionalities

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

The application follows a modular architecture with the following components:

- **Agents**: Specialized modules for different functionalities
- **Tools**: Utility functions for database operations and external services
- **Session Management**: Handles user sessions and conversation history
- **Router**: Directs user input to the appropriate agent

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
│   ├── main.py           # CLI entry point
│   ├── agents/           # Agent definitions
│   ├── tools/            # Tool implementations
│   └── db/              # Database operations
└── tests/               # Basic tests
```

MIT
