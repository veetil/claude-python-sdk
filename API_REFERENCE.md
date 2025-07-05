# Claude Python SDK - Quick API Reference

## Installation
```bash
pip install git+https://github.com/veetil/claude-python-sdk.git
```

## Basic Client Usage

```python
from claude_sdk import ClaudeClient

# Simple query
async with ClaudeClient() as client:
    response = await client.query("Hello!")
    print(response.content)

# Streaming
async with ClaudeClient() as client:
    async for chunk in client.stream_query("Tell a story"):
        print(chunk, end="")
```

## Core Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `query(prompt, **kwargs)` | Send query and get response | `ClaudeResponse` |
| `stream_query(prompt, **kwargs)` | Stream response chunks | `AsyncIterator[str]` |
| `execute_command(cmd, **kwargs)` | Execute raw command | `CommandResult` |
| `create_session(session_id)` | Create conversation session | `SessionContext` |
| `create_workspace(**kwargs)` | Create isolated workspace | `WorkspaceContext` |

## Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | `str` | required | The prompt to send |
| `session_id` | `Optional[str]` | `None` | Session for conversations |
| `output_format` | `OutputFormat` | `TEXT` | Output format (TEXT/JSON) |
| `timeout` | `Optional[float]` | `30.0` | Timeout in seconds |
| `workspace_id` | `Optional[str]` | `None` | Workspace for file ops |
| `files` | `Optional[List[str]]` | `None` | Files to include |

## Configuration Options

```python
from claude_sdk import ClaudeConfig

config = ClaudeConfig(
    # Core settings
    cli_path="claude",              # Path to Claude CLI
    default_timeout=30.0,           # Default timeout (seconds)
    
    # Retry settings
    max_retries=3,                  # Max retry attempts
    retry_delay=1.0,                # Base retry delay
    
    # Debug settings
    debug_mode=True,                # Show debug output
    verbose_logging=True,           # Extra verbose logs
    
    # Workspace settings
    workspace_cleanup_on_exit=True, # Auto-cleanup
    
    # Security settings
    safe_mode=False,                # True disables --dangerously-skip-permissions
    
    # Performance
    stream_buffer_size=8192,        # Stream buffer size
    max_concurrent_sessions=5,      # Max concurrent sessions
)
```

## Output Formats

```python
from claude_sdk.core.types import OutputFormat

OutputFormat.TEXT         # Default text output
OutputFormat.JSON         # JSON formatted output
OutputFormat.STREAM_JSON   # Streaming JSON chunks
```

## Exception Handling

```python
from claude_sdk.exceptions import (
    CommandTimeoutError,
    CommandExecutionError,
    SessionError,
    WorkspaceError
)

try:
    response = await client.query("Task", timeout=10)
except CommandTimeoutError:
    print("Query timed out")
except CommandExecutionError as e:
    print(f"Error: {e.stderr}")
```

## Session Management

```python
# Multi-turn conversation
async with client.create_session() as session:
    r1 = await session.query("Hello")
    r2 = await session.query("Follow-up")  # Maintains context
```

## Workspace Operations

```python
# Isolated file operations
files = ["main.py", "config.json"]
async with client.create_workspace(copy_files=files) as ws:
    response = await client.query(
        "Analyze these files",
        workspace_id=ws.workspace_id,
        files=files
    )
```

## Parallel Execution

```python
# Run multiple queries concurrently
tasks = [
    client.query(f"Query {i}")
    for i in range(5)
]
responses = await asyncio.gather(*tasks)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_CLI_PATH` | Path to Claude CLI | `claude` |
| `CLAUDE_DEFAULT_TIMEOUT` | Default timeout | `30.0` |
| `CLAUDE_LOG_LEVEL` | Log level | `INFO` |
| `CLAUDE_DEBUG` | Debug mode | `false` |
| `CLAUDE_MAX_RETRIES` | Max retries | `3` |

**Note**: 
- `ANTHROPIC_API_KEY` is automatically removed to avoid credit balance issues
- `--dangerously-skip-permissions` is added by default (disable with `safe_mode=True`)

## Common Patterns

### Error Recovery
```python
config = ClaudeConfig(max_retries=5, retry_delay=2.0)
async with ClaudeClient(config) as client:
    # Automatic retry with exponential backoff
    response = await client.query("Task")
```

### Debug Mode
```python
# See all Claude CLI commands
config = ClaudeConfig(debug_mode=True, verbose_logging=True)
async with ClaudeClient(config) as client:
    await client.query("Hello")  # Shows: claude --dangerously-skip-permissions -p "Hello"

# Safe mode (no dangerous flag)
config = ClaudeConfig(safe_mode=True)
async with ClaudeClient(config) as client:
    await client.query("Hello")  # Shows: claude -p "Hello"
```

### JSON Output
```python
response = await client.query(
    "List 3 items",
    output_format=OutputFormat.JSON
)
data = json.loads(response.content)
```

## Complete Example

```python
import asyncio
from claude_sdk import ClaudeClient, ClaudeConfig
from claude_sdk.core.types import OutputFormat

async def main():
    # Configure client
    config = ClaudeConfig(
        debug_mode=True,
        max_retries=3,
        default_timeout=60.0
    )
    
    async with ClaudeClient(config) as client:
        # Simple query
        response = await client.query("What is Python?")
        print(response.content)
        
        # Streaming with session
        async with client.create_session() as session:
            print("Claude: ", end="")
            async for chunk in session.stream_query("Tell a joke"):
                print(chunk, end="", flush=True)
            print()
        
        # Parallel tasks with workspace
        async with client.create_workspace() as workspace:
            tasks = [
                client.query(
                    f"Task {i}",
                    workspace_id=workspace.workspace_id
                )
                for i in range(3)
            ]
            responses = await asyncio.gather(*tasks)

asyncio.run(main())
```