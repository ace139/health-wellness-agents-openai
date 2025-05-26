---
trigger: always_on
---

Use uv as the package manager

- Before installing any new package, verify existing dependencies in both pyproject.toml and uv.lock.

You are working with the OpenAI Agents SDK [https://openai.github.io/openai-agents-python/]

- Please use functional programming whenever possible, always perfer it over object-oriented-programming designs, especially if OpenAI Agent SDK doesn't absolutely require it.
- The package name is openai_agents, but for imports, use agents
- Refer to the official SDK documentation: https://openai.github.io/openai-agents-python/
- Before implementing anything with the Agents SDK, always perform a web search tool call to https://openai.github.io/openai-agents-python
- Study the patterns and implementations used in the official documentation

Pass every file thorough ruff, at each save.

- The uv environement is already set up with the necessary dependencies installed, everytime you need to run a .py file, first activate the virtual environment with $source .venv/bin/activate
- Don't automatically run the main.py file, always ask user to run it manually. 