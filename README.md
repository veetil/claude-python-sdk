# Claude Python SDK

A lightweight subprocess wrapper for Claude CLI with async support, streaming output, workspace isolation, and comprehensive error handling.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/claude-python-sdk.svg)](https://badge.fury.io/py/claude-python-sdk)
[![Tests](https://github.com/anthropics/claude-python-sdk/workflows/Tests/badge.svg)](https://github.com/anthropics/claude-python-sdk/actions)

## Features

- **Async/Await Support**: Built-in asyncio support for concurrent operations
- **Streaming Output**: Real-time streaming of Claude CLI responses
- **Workspace Isolation**: Secure temporary workspaces for file operations
- **Comprehensive Error Handling**: Detailed error types with retry mechanisms
- **Session Management**: Persistent sessions for multi-turn conversations
- **Type Safety**: Full type hints and mypy compatibility
- **Modern Python**: Supports Python 3.9+ with modern async patterns

## Installation

```bash
pip install claude-python-sdk
```

### Development Installation

```bash
git clone https://github.com/anthropics/claude-python-sdk.git
cd claude-python-sdk
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

```python
import asyncio
from claude_sdk import ClaudeClient

async def main():
    async with ClaudeClient() as client:
        response = await client.query("Hello, Claude!")
        print(response.content)

asyncio.run(main())
```

### Streaming Responses

```python
import asyncio
from claude_sdk import ClaudeClient

async def stream_example():
    async with ClaudeClient() as client:
        async for chunk in client.stream_query("Analyze this large codebase"):
            print(chunk, end='', flush=True)

asyncio.run(stream_example())
```

### Session-based Conversations

```python
import asyncio
from claude_sdk import ClaudeClient

async def conversation_example():
    async with ClaudeClient() as client:
        async with client.create_session() as session:
            # First message
            response1 = await session.query("Hello, I'm working on a Python project")
            print(f"Claude: {response1.content}")
            
            # Follow-up in same session
            response2 = await session.query("Can you help me with error handling?")
            print(f"Claude: {response2.content}")

asyncio.run(conversation_example())
```

### Workspace Operations

```python
import asyncio
from claude_sdk import ClaudeClient

async def workspace_example():
    async with ClaudeClient() as client:
        # Create workspace with files
        files_to_copy = ["src/main.py", "requirements.txt"]
        
        async with client.create_workspace(copy_files=files_to_copy) as workspace:
            response = await client.query(
                "Review this Python project for best practices",
                workspace_id=workspace.workspace_id,
                files=["main.py", "requirements.txt"]
            )
            print(response.content)

asyncio.run(workspace_example())
```

## Configuration

### Environment Variables

```bash
# NOTE: The SDK automatically removes ANTHROPIC_API_KEY from the environment
# when calling Claude CLI to avoid "credit balance" issues
unset ANTHROPIC_API_KEY  # Or set to empty string

export CLAUDE_CLI_PATH="/path/to/claude"
export CLAUDE_LOG_LEVEL="INFO"
export CLAUDE_DEBUG="true"
```

### Programmatic Configuration

```python
from claude_sdk import ClaudeClient, ClaudeConfig

config = ClaudeConfig(
    cli_path="claude",
    default_timeout=30.0,
    max_retries=3,
    debug_mode=True,
    workspace_cleanup_on_exit=True,
)

async with ClaudeClient(config=config) as client:
    response = await client.query("Hello!")
```

## Advanced Features

### Custom Error Handling

```python
from claude_sdk import ClaudeClient
from claude_sdk.exceptions import CommandTimeoutError, CommandExecutionError

async with ClaudeClient() as client:
    try:
        response = await client.query("Complex analysis task", timeout=60.0)
    except CommandTimeoutError:
        print("Query timed out, try breaking it into smaller parts")
    except CommandExecutionError as e:
        print(f"Execution failed: {e.stderr}")
```

### Retry Configuration

```python
from claude_sdk import ClaudeConfig, ClaudeClient

config = ClaudeConfig(
    max_retries=5,
    retry_delay=2.0,
)

async with ClaudeClient(config=config) as client:
    # Will automatically retry up to 5 times with exponential backoff
    response = await client.query("Potentially flaky operation")
```

### Concurrent Operations

```python
import asyncio
from claude_sdk import ClaudeClient

async def concurrent_example():
    async with ClaudeClient() as client:
        # Execute multiple queries concurrently
        tasks = [
            client.query(f"Analyze file {i}")
            for i in range(1, 6)
        ]
        
        responses = await asyncio.gather(*tasks)
        for i, response in enumerate(responses):
            print(f"Response {i + 1}: {response.content[:100]}...")

asyncio.run(concurrent_example())
```

## API Reference

### ClaudeClient

The main client for interacting with Claude CLI.

#### Methods

- `query(prompt, **kwargs)` - Send a query and get response
- `stream_query(prompt, **kwargs)` - Stream a query response
- `execute_command(command, **kwargs)` - Execute raw command
- `create_session(session_id=None)` - Create session context
- `create_workspace(**kwargs)` - Create workspace context

### Configuration

#### ClaudeConfig

Configuration class for the SDK.

**Key Parameters:**
- `cli_path`: Path to Claude CLI executable
- `default_timeout`: Default command timeout
- `max_retries`: Maximum retry attempts
- `debug_mode`: Enable debug logging
- `workspace_cleanup_on_exit`: Auto-cleanup workspaces

### Exceptions

- `ClaudeSDKError` - Base exception
- `CommandError` - Command-related errors
- `CommandTimeoutError` - Command timeout
- `CommandExecutionError` - Command execution failure
- `SessionError` - Session-related errors
- `WorkspaceError` - Workspace-related errors

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m e2e

# Run with coverage
pytest --cov=claude_sdk --cov-report=html
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/anthropics/claude-python-sdk.git
cd claude-python-sdk

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run type checking
mypy src/claude_sdk

# Run linting
ruff check src/claude_sdk
black --check src/claude_sdk
```

## Security Considerations

- The SDK implements workspace isolation for secure file operations
- All subprocess calls use safe argument passing (no shell injection)
- Sensitive data is filtered from logs
- Input validation prevents path traversal attacks
- Environment variables are handled securely

## Performance

- Async/await for concurrent operations
- Streaming support for large responses
- Connection pooling for subprocess management
- Memory-efficient chunk processing
- Configurable timeouts and retries

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and version history.

## Support

- Documentation: [https://claude-python-sdk.readthedocs.io](https://claude-python-sdk.readthedocs.io)
- Issues: [GitHub Issues](https://github.com/anthropics/claude-python-sdk/issues)
- Discussions: [GitHub Discussions](https://github.com/anthropics/claude-python-sdk/discussions)