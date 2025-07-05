# Claude Python SDK - Quick Start Guide

## Installation

```bash
# Install from GitHub
pip install git+https://github.com/veetil/claude-python-sdk.git

# Or clone and install in development mode
git clone https://github.com/veetil/claude-python-sdk.git
cd claude-python-sdk
pip install -e ".[dev]"
```

## Prerequisites

- Python 3.9 or higher
- Claude CLI installed and configured (`npm install -g @anthropic-ai/claude-code`)
- **Important**: Unset `ANTHROPIC_API_KEY` to avoid credit balance issues:
  ```bash
  unset ANTHROPIC_API_KEY  # Or: export ANTHROPIC_API_KEY=""
  ```

## Default Behavior

The SDK adds `--dangerously-skip-permissions` to all Claude CLI commands by default. To disable this:

```python
from claude_sdk import ClaudeClient, ClaudeConfig

# Safe mode - no dangerous flags
config = ClaudeConfig(safe_mode=True)
async with ClaudeClient(config) as client:
    response = await client.query("Hello!")
```

## Basic Usage

```python
import asyncio
from claude_sdk import ClaudeClient

async def main():
    async with ClaudeClient() as client:
        response = await client.query("Hello, Claude!")
        print(response.content)

asyncio.run(main())
```

## Streaming Responses

```python
import asyncio
from claude_sdk import ClaudeClient

async def stream_example():
    async with ClaudeClient() as client:
        print("Claude: ", end="", flush=True)
        async for chunk in client.stream_query("Tell me a joke"):
            print(chunk, end="", flush=True)
        print()  # New line at end

asyncio.run(stream_example())
```

## Parallel Execution Example

```python
import asyncio
from claude_sdk import ClaudeClient

async def parallel_queries():
    async with ClaudeClient() as client:
        # Execute 5 queries in parallel
        tasks = [
            client.query(f"What is the capital of {country}?")
            for country in ["France", "Japan", "Brazil", "Egypt", "Canada"]
        ]
        
        responses = await asyncio.gather(*tasks)
        
        for country, response in zip(["France", "Japan", "Brazil", "Egypt", "Canada"], responses):
            print(f"{country}: {response.content.strip()}")

asyncio.run(parallel_queries())
```

## Session Management (Multi-turn Conversations)

```python
import asyncio
from claude_sdk import ClaudeClient

async def conversation():
    async with ClaudeClient() as client:
        async with client.create_session() as session:
            # First message
            response1 = await session.query("Let's play 20 questions. Think of an animal.")
            print(f"Claude: {response1.content}")
            
            # Follow-up questions in same session
            response2 = await session.query("Is it a mammal?")
            print(f"Claude: {response2.content}")
            
            response3 = await session.query("Does it live in water?")
            print(f"Claude: {response3.content}")

asyncio.run(conversation())
```

## JSON Output Format

```python
import asyncio
import json
from claude_sdk import ClaudeClient
from claude_sdk.core.types import OutputFormat

async def json_output():
    async with ClaudeClient() as client:
        response = await client.query(
            "List 3 programming languages with their key features",
            output_format=OutputFormat.JSON
        )
        
        # Parse the JSON response
        try:
            data = json.loads(response.content)
            print("Parsed JSON:", json.dumps(data, indent=2))
        except json.JSONDecodeError:
            print("Raw response:", response.content)

asyncio.run(json_output())
```

## Error Handling and Retries

```python
import asyncio
from claude_sdk import ClaudeClient, ClaudeConfig
from claude_sdk.exceptions import CommandTimeoutError, CommandExecutionError

async def error_handling_example():
    # Configure with retries and timeout
    config = ClaudeConfig(
        default_timeout=10.0,
        max_retries=3,
        retry_delay=2.0
    )
    
    async with ClaudeClient(config=config) as client:
        try:
            response = await client.query("Complex analysis task")
            print(response.content)
        except CommandTimeoutError:
            print("Query timed out after 10 seconds")
        except CommandExecutionError as e:
            print(f"Execution failed: {e.stderr}")

asyncio.run(error_handling_example())
```

## Workspace Operations

```python
import asyncio
from pathlib import Path
from claude_sdk import ClaudeClient

async def workspace_example():
    async with ClaudeClient() as client:
        # Create a temporary file
        test_file = Path("test_code.py")
        test_file.write_text('''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print([fibonacci(i) for i in range(10)])
''')
        
        # Create workspace with the file
        async with client.create_workspace(copy_files=["test_code.py"]) as workspace:
            response = await client.query(
                "Review this Python code and suggest improvements",
                workspace_id=workspace.workspace_id,
                files=["test_code.py"]
            )
            print(response.content)
        
        # Cleanup
        test_file.unlink()

asyncio.run(workspace_example())
```

## Run Examples

```bash
# Basic examples
python examples/basic_usage.py

# Parallel haiku generation (5 concurrent tasks)
python examples/parallel_haikus.py

# Session management
python examples/session_management.py

# Workspace operations
python examples/workspace_operations.py

# Advanced features
python examples/advanced_features.py

# Streaming JSON output
python examples/stream_json_simple.py
python examples/stream_json_output.py
```

## Configuration Options

```python
from claude_sdk import ClaudeClient, ClaudeConfig

# Custom configuration
config = ClaudeConfig(
    cli_path="claude",                    # Path to Claude CLI
    default_timeout=30.0,                  # Command timeout in seconds
    max_retries=3,                         # Retry attempts
    debug_mode=True,                       # Enable debug logging
    workspace_cleanup_on_exit=True,        # Auto-cleanup workspaces
    stream_buffer_size=8192,               # Streaming buffer size
)

async with ClaudeClient(config=config) as client:
    # Use configured client
    pass
```

## Key Features

- ✅ **Async/await support** - Built for modern Python async patterns
- ✅ **Streaming responses** - Real-time output streaming
- ✅ **Parallel execution** - Run multiple queries concurrently
- ✅ **Session management** - Multi-turn conversations
- ✅ **Workspace isolation** - Secure file operations
- ✅ **Error handling** - Comprehensive exception hierarchy
- ✅ **Retry mechanisms** - Automatic retries with backoff
- ✅ **Type safety** - Full type hints and mypy support
- ✅ **JSON output** - Structured output formats
- ✅ **Credit balance fix** - Automatic ANTHROPIC_API_KEY handling

## Common Issues

### Credit Balance Error
If you see "Credit balance is too low", make sure `ANTHROPIC_API_KEY` is unset:
```bash
unset ANTHROPIC_API_KEY
```
The SDK automatically handles this for you.

### Module Not Found
Make sure all dependencies are installed:
```bash
pip install -e ".[dev]"
```

### Claude CLI Not Found
Install Claude CLI:
```bash
npm install -g @anthropic-ai/claude-code
```

## Documentation

See the [README.md](README.md) for full documentation and API reference.