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

# NOTE: The SDK adds --dangerously-skip-permissions by default
# To disable this, use safe_mode=True in ClaudeConfig

# NOTE: The SDK automatically prepends prefix-prompt.md to all prompts
# To disable this, use enable_prefix_prompt=False in ClaudeConfig

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

## Full-Featured Example

This comprehensive example demonstrates all major SDK features:
- (a) Automatic prefix prompt inclusion
- (b) Real-time streaming output
- (c) Session resumption with context
- (d) Parallel task execution

```python
import asyncio
from pathlib import Path
from claude_sdk.session_client import SessionAwareClient
from claude_sdk import ClaudeConfig

async def full_featured_demo():
    """Demonstrates all major SDK features in one example"""
    
    # Configure with all features enabled
    config = ClaudeConfig(
        enable_prefix_prompt=True,    # (a) Automatically prepends prefix-prompt.md
        debug_mode=True,              # Shows commands with session IDs
        safe_mode=False,              # Uses --dangerously-skip-permissions
    )
    
    async with SessionAwareClient(config) as client:
        print("=== Full-Featured Claude SDK Demo ===\n")
        
        # PART 1: Initial query with automatic prefix prompt
        print("1. Creating initial content (with prefix prompt automatically applied)")
        initial_response = await client.query_with_session(
            "Create 5 Python files with different algorithms: "
            "sorting, searching, graph traversal, dynamic programming, and ML basics. "
            "Save them in output/algorithms/"
        )
        
        session_id = initial_response.session_id
        print(f"✅ Session ID: {session_id}")
        print(f"📝 Response: {initial_response.content[:200]}...\n")
        
        # PART 2: Real-time streaming with session context
        print("2. Streaming real-time updates")
        stream_chunks = []
        async for chunk in client.stream_query(
            "Add comprehensive docstrings to each algorithm file you created",
            session_id=f"resume:{session_id}"  # Resume previous session
        ):
            stream_chunks.append(chunk)
            if len(stream_chunks) % 10 == 0:  # Print every 10th chunk
                print(f"   Streaming... received {len(stream_chunks)} chunks")
        
        print(f"✅ Streamed {len(stream_chunks)} total chunks\n")
        
        # PART 3: Parallel execution with session resumption
        print("3. Parallel task execution (maintaining session context)")
        
        # Define 5 parallel tasks
        parallel_tasks = [
            ("Add unit tests for sorting.py", "tests/test_sorting.py"),
            ("Add unit tests for searching.py", "tests/test_searching.py"),
            ("Add unit tests for graph.py", "tests/test_graph.py"),
            ("Add unit tests for dp.py", "tests/test_dp.py"),
            ("Add unit tests for ml_basics.py", "tests/test_ml.py"),
        ]
        
        # Execute all tasks in parallel, resuming the same session
        async def create_test_file(prompt, filename):
            response = await client.query_with_session(
                f"{prompt} and save to output/algorithms/{filename}",
                resume_session_id=session_id  # All tasks use same session
            )
            return filename, response.content[:100]
        
        # Launch all tasks concurrently
        results = await asyncio.gather(*[
            create_test_file(prompt, filename) 
            for prompt, filename in parallel_tasks
        ])
        
        print("✅ Parallel execution results:")
        for filename, preview in results:
            print(f"   - {filename}: {preview}...")
        
        # PART 4: Final session operation with full context
        print(f"\n4. Creating summary using full session context")
        summary_response = await client.query_with_session(
            "Create output/algorithms/README.md that lists all algorithm files "
            "and their corresponding test files with brief descriptions",
            resume_session_id=session_id
        )
        
        print(f"✅ Summary created in session: {session_id}")
        
        # Verify files were created
        output_dir = Path("output/algorithms")
        if output_dir.exists():
            files = list(output_dir.glob("**/*.py"))
            print(f"\n📁 Created {len(files)} Python files")
            if (output_dir / "README.md").exists():
                print("📄 README.md successfully created")

async def main():
    # Clean up before demo
    output_dir = Path("output/algorithms")
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
    
    # Run the demo
    await full_featured_demo()
    
    print("\n✅ Demo complete! Check output/algorithms/ for results.")
    print("\nKey features demonstrated:")
    print("- Automatic prefix prompt inclusion (BatchTool usage)")
    print("- Real-time streaming output")
    print("- Session ID extraction and resumption") 
    print("- Parallel task execution with session context")
    print("- All in one simple, practical example!")

if __name__ == "__main__":
    asyncio.run(main())
```

### What This Example Shows

1. **Prefix Prompt**: The SDK automatically prepends `prefix-prompt.md` to encourage efficient BatchTool usage
2. **Real-time Streaming**: Shows progress as Claude processes the request
3. **Session Management**: Extracts session ID and reuses it across multiple operations
4. **Parallelism**: Executes 5 test file creations concurrently while maintaining session context

This example creates a complete algorithm library with tests, demonstrating how the SDK enables complex, multi-step workflows with maximum efficiency.

## Examples

The `examples/` directory contains comprehensive examples demonstrating various SDK features:

### Basic Examples
- `basic_usage.py` - Simple query and response handling
- `session_management.py` - Multi-turn conversations with session state
- `workspace_operations.py` - File operations with workspace isolation
- `error_handling.py` - Comprehensive error handling patterns

### Advanced Examples
- `parallel_haikus.py` - Parallel execution with 5 concurrent tasks
- `advanced_features.py` - Retry mechanisms, timeouts, and configuration
- `stream_json_simple.py` - JSON output formats with debug commands
- `stream_json_output.py` - Advanced streaming JSON analysis
- `show_claude_commands.py` - **See all Claude CLI commands the SDK generates**
- `prefix_prompt_demo.py` - Demonstrates automatic prefix prompt prepending
- `safe_mode.py` - Shows how to disable dangerous permissions flag
- `session_management_demo.py` - Comprehensive session ID and resumption demo
- `session_workflow_example.py` - Real-world workflow with session continuity
- `session_stories_test.py` - Write stories and improve titles using sessions
- `session_title_improvement_test.py` - Simple session resumption example

### Running Examples

```bash
# Show all Claude CLI commands
python examples/show_claude_commands.py

# Run parallel haiku generation
python examples/parallel_haikus.py

# See streaming JSON with debug output
python examples/stream_json_simple.py
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
- **Default behavior**: `--dangerously-skip-permissions` is added automatically
  - To run in safe mode: `ClaudeConfig(safe_mode=True)`
- **Prefix Prompt**: Automatically prepends `prefix-prompt.md` content to all prompts
  - To disable: `ClaudeConfig(enable_prefix_prompt=False)`
  - Custom file: `ClaudeConfig(prefix_prompt_file="custom-prefix.md")`

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

## Documentation

- [Quick Start Guide](QUICKSTART.md) - Get started quickly
- [API Reference](API_REFERENCE.md) - Concise API reference card
- [SDK Signature](SDK_SIGNATURE.md) - Complete API signature documentation
- [Examples](examples/) - Comprehensive example scripts
- [Changelog](CHANGELOG.md) - Version history

## Support

- Documentation: [https://claude-python-sdk.readthedocs.io](https://claude-python-sdk.readthedocs.io)
- Issues: [GitHub Issues](https://github.com/anthropics/claude-python-sdk/issues)
- Discussions: [GitHub Discussions](https://github.com/anthropics/claude-python-sdk/discussions)