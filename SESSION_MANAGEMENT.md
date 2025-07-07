# Session Management in Claude Python SDK

This document describes the enhanced session management capabilities added to the Claude Python SDK.

## Overview

The enhanced SDK now supports:
- **Automatic session ID extraction** from Claude responses
- **Session resumption** using the `-r` flag
- **Session continuity** for multi-step workflows
- **Error correction** within the same session context

## Installation

The session management features are available through the `SessionAwareClient` class:

```python
from claude_sdk.session_client import SessionAwareClient
```

## Basic Usage

### 1. Simple Query with Session ID Extraction

```python
import asyncio
from claude_sdk.session_client import SessionAwareClient

async def example():
    async with SessionAwareClient() as client:
        response = await client.query_with_session(
            "Write a Python function to calculate fibonacci numbers"
        )
        
        print(f"Response: {response.content}")
        print(f"Session ID: {response.session_id}")  # Automatically extracted

asyncio.run(example())
```

### 2. Resuming a Session

```python
async def resume_example():
    async with SessionAwareClient() as client:
        # First query creates a session
        response1 = await client.query_with_session(
            "Create a function to sort a list"
        )
        session_id = response1.session_id
        
        # Resume the same session with -r flag
        response2 = await client.query_with_session(
            "Now create unit tests for the sorting function",
            resume_session_id=session_id
        )
```

### 3. Auto-Resume Last Session

```python
async def auto_resume_example():
    async with SessionAwareClient() as client:
        # First query
        await client.query_with_session("Write code for task 1")
        
        # Automatically resume last session
        await client.query_with_session(
            "Write code for task 2",
            auto_resume_last=True
        )
```

## Real-World Example: Error Correction

This example demonstrates the exact use case of checking for files and correcting errors:

```python
import asyncio
from pathlib import Path
from claude_sdk.session_client import SessionAwareClient

async def file_creation_with_validation():
    async with SessionAwareClient() as client:
        # Step 1: Request file creation
        response = await client.query_with_session(
            "Write Python code for sorting algorithms and save to output/"
        )
        session_id = response.session_id
        print(f"Got session ID: {session_id}")
        
        # Step 2: System checks for files
        output_dir = Path("output")
        expected_files = ["sort.py", "search.py", "utils.py"]
        missing_files = [f for f in expected_files if not (output_dir / f).exists()]
        
        if missing_files:
            print(f"ERROR: Files not found: {missing_files}")
            
            # Step 3: Correct the error in the same session
            correction_response = await client.query_with_session(
                f"ERROR - You need to write to the correct folder 'output/'. "
                f"Please create these files: {', '.join(missing_files)}",
                resume_session_id=session_id  # Resume with -r flag
            )
            print("Correction sent in same session")

asyncio.run(file_creation_with_validation())
```

## Multi-Step Workflows

Session management is perfect for complex, multi-step workflows:

```python
async def project_setup_workflow():
    async with SessionAwareClient() as client:
        # Step 1: Create project structure
        response1 = await client.query_with_session(
            "Create a Python project structure in output/myproject/"
        )
        session_id = response1.session_id
        
        # Step 2: Add main module
        await client.query_with_session(
            "Add a main.py file with CLI argument parsing",
            resume_session_id=session_id
        )
        
        # Step 3: Add configuration
        await client.query_with_session(
            "Create a config.py with configuration management",
            resume_session_id=session_id
        )
        
        # Step 4: Add tests
        await client.query_with_session(
            "Create comprehensive unit tests in tests/ directory",
            resume_session_id=session_id
        )
        
        print(f"Completed entire workflow in session: {session_id}")
```

## Wrapper Class for Simplified Usage

For even simpler usage, use the `ClaudeSDKWrapper`:

```python
from claude_sdk_enhanced import ClaudeSDKWrapper

async def simple_example():
    async with ClaudeSDKWrapper() as sdk:
        # First command
        content, session_id = await sdk.execute(
            "Write code for different tasks and write to folder output/"
        )
        
        # Check results...
        if not Path("output").exists():
            # Retry with correction, automatically uses last session
            content, _ = await sdk.execute(
                "ERROR - write to the correct folder which is output/",
                resume_last_session=True
            )
```

## Command Line Equivalent

The SDK generates commands equivalent to:

```bash
# Initial query (creates session)
claude -p "Your prompt" --output-format stream-json --verbose

# Resume session with -r flag
claude -p "Follow-up prompt" -r SESSION_ID --output-format stream-json --verbose
```

The stream-json output format returns:
1. System init message with session_id
2. Assistant message with content
3. Result message with both result and session_id

Example output:
```json
{"type":"system","subtype":"init","session_id":"acc21b20-13b3-423c-9191-01925b546d5b",...}
{"type":"assistant","message":{"content":[{"type":"text","text":"London"}]},"session_id":"acc21b20-13b3-423c-9191-01925b546d5b"}
{"type":"result","result":"London","session_id":"acc21b20-13b3-423c-9191-01925b546d5b",...}
```

## API Reference

### SessionAwareClient

Main client class with session management:

```python
class SessionAwareClient(ClaudeClient):
    async def query_with_session(
        prompt: str,
        *,
        resume_session_id: Optional[str] = None,
        auto_resume_last: bool = False,
        output_format: OutputFormat = OutputFormat.JSON,
        timeout: Optional[float] = None,
        workspace_id: Optional[str] = None,
        files: Optional[list[str]] = None,
    ) -> SessionAwareResponse
```

### SessionAwareResponse

Enhanced response object:

```python
class SessionAwareResponse:
    content: str              # Response content
    session_id: Optional[str] # Extracted session ID
    metadata: Dict[str, Any]  # Additional metadata
    raw_json: Optional[Dict]  # Raw JSON response (if available)
```

## Configuration

Session management works with all existing configuration options:

```python
from claude_sdk import ClaudeConfig
from claude_sdk.session_client import SessionAwareClient

config = ClaudeConfig(
    enable_prefix_prompt=True,   # Works with prefix prompts
    debug_mode=True,            # See commands with -r flag
    safe_mode=False,            # Normal operation
)

client = SessionAwareClient(config)
```

## Best Practices

1. **Always check session_id**: Not all responses may include a session ID
2. **Store session IDs**: Keep track of session IDs for complex workflows
3. **Use auto_resume_last**: For sequential operations in the same context
4. **Handle errors gracefully**: Session resumption may fail if session expired

## Troubleshooting

### No Session ID Returned

Some Claude configurations may not return session IDs. Check:
- Output format is set to JSON
- Claude CLI version supports session management
- Response parsing is working correctly

### Session Resumption Fails

Sessions may expire or become invalid. Always have a fallback:

```python
try:
    response = await client.query_with_session(
        prompt, 
        resume_session_id=old_session_id
    )
except Exception as e:
    # Fallback to new session
    response = await client.query_with_session(prompt)
```

## Examples

See the `examples/` directory for complete examples:
- `session_management_demo.py` - Comprehensive demo of all features
- `claude_sdk_enhanced.py` - Full implementation with examples

## Testing

Run the test script to verify functionality:

```bash
python test_session_functionality.py
```

This will test:
- Session ID extraction
- Command generation with -r flag
- Session resumption
- Auto-resume functionality