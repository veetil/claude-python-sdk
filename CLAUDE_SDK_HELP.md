# Claude SDK Complete Help Guide

## Table of Contents
1. [Installation](#installation)
2. [Basic Usage](#basic-usage)
3. [Configuration Options](#configuration-options)
4. [Client Methods](#client-methods)
5. [Session Management](#session-management)
6. [Streaming Responses](#streaming-responses)
7. [Error Handling](#error-handling)
8. [Advanced Features](#advanced-features)
9. [Examples](#examples)

## Installation

```bash
pip install claude-sdk
```

## Basic Usage

```python
from claude_sdk import ClaudeClient, ClaudeConfig

# Simple query
async with ClaudeClient() as client:
    response = await client.query("Hello, Claude!")
    print(response.content)
```

## Configuration Options

### ClaudeConfig Parameters

```python
from claude_sdk import ClaudeConfig, OutputFormat

config = ClaudeConfig(
    # API Configuration
    api_key="your-api-key",                    # Claude API key (or use CLAUDE_API_KEY env var)
    model="claude-3-5-sonnet-20241022",        # Model to use
    
    # Command Configuration
    claude_command="claude",                    # Base claude command
    default_output_format=OutputFormat.TEXT,    # Default output format (TEXT, JSON, STREAM_JSON)
    
    # Timeout and Retry Settings
    default_timeout=30.0,                      # Default timeout in seconds
    max_retries=3,                             # Maximum retry attempts
    retry_delay=1.0,                           # Delay between retries in seconds
    
    # Logging and Debug
    debug_mode=False,                          # Enable debug logging
    verbose_logging=False,                     # Enable verbose output
    log_level="INFO",                          # Logging level
    log_file=None,                             # Optional log file path
    
    # Prefix Prompt
    enable_prefix_prompt=True,                 # Enable automatic prefix prompt
    prefix_prompt_file="prefix-prompt.md",     # Path to prefix prompt file
    
    # Workspace Settings
    workspace_dir=".claude-workspaces",        # Directory for workspaces
    workspace_cleanup_on_exit=True,            # Auto-cleanup workspaces
    
    # Safety and Permissions
    safe_mode=False,                           # Use --dangerously-skip-permissions by default
    
    # Process Settings
    max_concurrent_processes=10,               # Max concurrent subprocess operations
    process_cleanup_timeout=5.0,               # Timeout for process cleanup
    
    # Stream Buffer Settings
    stream_chunk_size=1024,                    # Size of streaming chunks
    stream_buffer_size=65536,                  # Stream buffer size
)
```

## Client Methods

### ClaudeClient

```python
from claude_sdk import ClaudeClient, OutputFormat
from claude_sdk.session_client import SessionAwareClient

# Standard Client
client = ClaudeClient(config)

# Session-Aware Client (recommended for session management)
client = SessionAwareClient(config)
```

### Core Methods

#### 1. query()
```python
response = await client.query(
    prompt="Your question here",
    session_id=None,                    # Optional session ID
    output_format=OutputFormat.TEXT,    # Output format
    timeout=60.0,                       # Timeout in seconds (overrides default)
    workspace_id=None,                  # Optional workspace ID
    files=["file1.py", "file2.txt"],   # Optional files to include
)

# Response attributes
print(response.content)             # Response text
print(response.session_id)          # Session ID if available
print(response.metadata)            # Additional metadata
```

#### 2. stream_query()
```python
# Stream responses in real-time
async for chunk in client.stream_query(
    prompt="Write a long story",
    session_id=None,
    timeout=120.0,                  # Longer timeout for streaming
    workspace_id=None,
    files=None,
):
    print(chunk, end='', flush=True)
```

#### 3. execute_command()
```python
# Execute raw commands
result = await client.execute_command(
    command=["claude", "--version"],
    timeout=10.0,
    workspace_id=None,
    env={"CUSTOM_VAR": "value"},   # Custom environment variables
)

print(result.stdout)
print(result.stderr)
print(result.exit_code)
print(result.duration)
```

### Session Management Methods (SessionAwareClient)

#### 1. query_with_session()
```python
from claude_sdk.session_client import SessionAwareClient

client = SessionAwareClient(config)

# First query - creates new session
response1 = await client.query_with_session(
    prompt="Create a Python script",
    resume_session_id=None,         # None creates new session
    auto_resume_last=False,         # Auto-resume last session
    output_format=OutputFormat.STREAM_JSON,
    timeout=60.0,
    workspace_id=None,
    files=None,
)

session_id = response1.session_id   # Save for later use

# Resume session
response2 = await client.query_with_session(
    prompt="Add error handling to the script",
    resume_session_id=session_id,   # Resume specific session
    timeout=60.0,
)

# Or use auto-resume
response3 = await client.query_with_session(
    prompt="Add documentation",
    auto_resume_last=True,          # Automatically use last session
)
```

#### 2. Session Properties
```python
# Get last session ID
last_session = client.last_session_id

# Clear stored session
client.clear_session()
```

### Context Managers

#### 1. Workspace Context
```python
async with client.create_workspace(
    workspace_id="my-workspace",
    copy_files=["input.txt", "data.csv"],
) as workspace:
    # Execute commands in isolated workspace
    response = await client.query(
        "Process the input files",
        workspace_id=workspace.workspace_id
    )
    
    # Access workspace info
    print(workspace.path)           # Workspace directory path
    print(workspace.workspace_id)   # Workspace ID
```

#### 2. Session Context
```python
async with client.create_session("my-session") as session:
    # All queries in this context use the same session
    response1 = await session.query("First query")
    response2 = await session.query("Follow-up query")
    
    # Stream in session context
    async for chunk in session.stream_query("Stream this"):
        print(chunk)
```

## Streaming Responses

### Basic Streaming
```python
async for chunk in client.stream_query("Generate a long response"):
    print(chunk, end='', flush=True)
```

### Advanced Streaming with Visual Formatter
```python
from visual_formatter import EnhancedStreamFormatter
from visual_formatter.parser import JSONParser

# Create formatter
formatter = EnhancedStreamFormatter()

# Stream with formatting
async for chunk in client.stream_query("Complex task", output_format=OutputFormat.STREAM_JSON):
    # Parse JSON events
    parser = JSONParser()
    for line in chunk.split('\n'):
        if line.strip():
            event = parser.parse_line(line)
            if event:
                # Format and display
                formatted = formatter.format_event(event)
                if formatted:
                    print(formatted)
```

### Stream with Progress Tracking
```python
from visual_formatter import StreamProcessor

processor = StreamProcessor()

async def process_with_progress():
    async for chunk in client.stream_query("Multi-step task"):
        # Process chunk and update progress
        processed = processor.process_chunk(chunk)
        
        # Display progress
        if processed.progress_update:
            print(f"Progress: {processed.progress}%")
        
        # Display formatted output
        if processed.formatted_output:
            print(processed.formatted_output)
```

## Error Handling

### Exception Types
```python
from claude_sdk.exceptions import (
    ClaudeSDKError,         # Base exception
    AuthenticationError,    # API key issues
    SessionError,           # Session-related errors
    TimeoutError,           # Operation timeouts
    WorkspaceError,         # Workspace issues
)

try:
    response = await client.query("Hello", timeout=5.0)
except TimeoutError:
    print("Request timed out")
except AuthenticationError:
    print("Check your API key")
except ClaudeSDKError as e:
    print(f"SDK Error: {e}")
```

### Error Response Handling
```python
response = await client.query_with_session("Do something")

# Check for errors in response
if response.metadata.get('is_error'):
    error_msg = response.metadata.get('error')
    print(f"Claude returned error: {error_msg}")
```

## Advanced Features

### 1. Parallel Execution
```python
import asyncio

async def parallel_queries():
    # Execute multiple queries in parallel
    tasks = [
        client.query("Task 1"),
        client.query("Task 2"),
        client.query("Task 3"),
    ]
    
    responses = await asyncio.gather(*tasks)
    return responses
```

### 2. Custom Command Building
```python
# Build custom commands
builder = client.command_builder()
builder.add_prompt("My prompt")
builder.add_flag("verbose")
builder.add_option("model", "claude-3-5-sonnet-20241022")
builder.add_file("input.txt")
builder.set_output_format("json")

command = builder.build()
result = await client.execute_command(command)
```

### 3. Retry with Backoff
```python
from claude_sdk.utils.retry import retry_with_backoff

@retry_with_backoff(max_retries=5, base_delay=2.0)
async def reliable_query():
    return await client.query("Important query")
```

### 4. Workspace Operations
```python
# List all workspaces
workspaces = await client.list_workspaces()
for ws in workspaces:
    print(f"ID: {ws.workspace_id}, Path: {ws.path}")

# Clean up specific workspace
await client._workspace_manager.cleanup_workspace("workspace-id")
```

### 5. Environment Variables
```python
# Set via environment
export CLAUDE_API_KEY="your-key"
export CLAUDE_MODEL="claude-3-5-sonnet-20241022"
export CLAUDE_DEBUG=true
export CLAUDE_TIMEOUT=120

# Or in Python
import os
os.environ['CLAUDE_API_KEY'] = 'your-key'
```

## Examples

### Example 1: Complete Task with Error Handling
```python
async def complete_task_with_retry():
    config = ClaudeConfig(
        debug_mode=True,
        default_timeout=120.0,
        max_retries=3,
        enable_prefix_prompt=True,
    )
    
    async with SessionAwareClient(config) as client:
        try:
            # Initial attempt
            response = await client.query_with_session(
                "Create a web scraper in scraper.py",
                timeout=60.0,
            )
            
            # Verify file was created
            if not Path("scraper.py").exists():
                # Retry with correction
                response = await client.query_with_session(
                    "The file wasn't created. Please create scraper.py with the web scraper code.",
                    auto_resume_last=True,
                    timeout=60.0,
                )
            
            return response
            
        except TimeoutError:
            print("Operation timed out, increasing timeout...")
            return await client.query_with_session(
                "Continue where you left off",
                auto_resume_last=True,
                timeout=240.0,  # Double the timeout
            )
```

### Example 2: Streaming with Visual Formatting
```python
from visual_formatter import create_stream_processor

async def formatted_streaming():
    processor = create_stream_processor(
        show_hierarchy=True,
        show_progress=True,
        use_colors=True,
    )
    
    async with SessionAwareClient() as client:
        stream = client.stream_query(
            "Implement a sorting algorithm with tests",
            timeout=120.0,
        )
        
        async for formatted_output in processor.process_stream(stream):
            print(formatted_output, end='', flush=True)
```

### Example 3: Multi-Phase Development
```python
async def multi_phase_development():
    config = ClaudeConfig(
        enable_prefix_prompt=True,
        debug_mode=True,
    )
    
    async with SessionAwareClient(config) as client:
        phases = [
            ("Phase 1: Architecture", "Design the system architecture for a chat application"),
            ("Phase 2: Backend", "Implement the backend API with FastAPI"),
            ("Phase 3: Frontend", "Create the frontend with React"),
            ("Phase 4: Testing", "Write comprehensive tests for all components"),
            ("Phase 5: Documentation", "Create user and API documentation"),
        ]
        
        session_id = None
        
        for phase_name, phase_prompt in phases:
            print(f"\n{'='*60}")
            print(f"{phase_name}")
            print('='*60)
            
            response = await client.query_with_session(
                phase_prompt,
                resume_session_id=session_id,
                timeout=180.0,  # 3 minutes per phase
            )
            
            # First phase creates session, others resume it
            if not session_id:
                session_id = response.session_id
                print(f"Created session: {session_id}")
            
            print(f"Completed {phase_name}")
            
            # Optional: Add delay between phases
            await asyncio.sleep(2)
        
        return session_id
```

### Example 4: Workspace Isolation
```python
async def isolated_execution():
    async with ClaudeClient() as client:
        # Create isolated workspace for experiments
        async with client.create_workspace(
            workspace_id="experiment-1",
            copy_files=["requirements.txt", "config.yml"],
        ) as workspace:
            
            # All operations happen in isolated directory
            response = await client.query(
                "Install dependencies and run experiments",
                workspace_id=workspace.workspace_id,
                timeout=300.0,  # 5 minutes for installation
            )
            
            # Files are created in workspace
            print(f"Workspace path: {workspace.path}")
            
            # Workspace auto-cleans on exit
```

## Output Formats

### 1. TEXT (default)
```python
response = await client.query("Hello", output_format=OutputFormat.TEXT)
# Returns plain text response
```

### 2. JSON
```python
response = await client.query("Hello", output_format=OutputFormat.JSON)
# Returns JSON object with full response structure
```

### 3. STREAM_JSON (recommended for session tracking)
```python
response = await client.query("Hello", output_format=OutputFormat.STREAM_JSON)
# Returns newline-delimited JSON events
# Automatically extracts session_id
```

## Debugging

### Enable Debug Mode
```python
config = ClaudeConfig(
    debug_mode=True,           # Show all commands
    verbose_logging=True,      # Detailed logging
    log_level="DEBUG",         # Maximum log detail
    log_file="claude.log",     # Save logs to file
)

# Or set environment variable
export CLAUDE_DEBUG=true
```

### View Commands Being Executed
```python
# Debug mode shows exact commands
# Example output:
# DEBUG: Executing command: ['claude', '--output-format', 'stream-json', '--verbose', 'Hello']
```

### Performance Monitoring
```python
# Check response metadata for timing
response = await client.query("Task")
print(f"Duration: {response.metadata['duration']}s")
print(f"Exit code: {response.metadata['exit_code']}")
```

## Best Practices

1. **Always use context managers** for automatic cleanup
2. **Set appropriate timeouts** based on task complexity
3. **Use session management** for multi-step tasks
4. **Enable debug mode** during development
5. **Handle errors gracefully** with proper exception handling
6. **Use streaming** for long-running operations
7. **Leverage workspaces** for file isolation
8. **Configure retries** for reliability

## Environment Configuration

```bash
# Required
export CLAUDE_API_KEY="your-api-key"

# Optional
export CLAUDE_MODEL="claude-3-5-sonnet-20241022"
export CLAUDE_DEBUG=true
export CLAUDE_TIMEOUT=120
export CLAUDE_PREFIX_PROMPT_FILE="custom-prefix.md"
export CLAUDE_WORKSPACE_DIR="/tmp/claude-workspaces"
export CLAUDE_LOG_FILE="/var/log/claude.log"
export CLAUDE_LOG_LEVEL="DEBUG"
```

## Troubleshooting

### Common Issues

1. **Timeout Errors**
   - Increase timeout: `timeout=300.0`
   - Use streaming for long operations
   - Break complex tasks into phases

2. **Session Not Found**
   - Ensure session_id is captured from first response
   - Use `auto_resume_last=True` for convenience
   - Check session hasn't expired

3. **Memory Issues with Large Responses**
   - Use streaming instead of full response
   - Process data in chunks
   - Set appropriate buffer sizes

4. **Permission Errors**
   - Check workspace permissions
   - Use `safe_mode=False` if appropriate
   - Ensure proper file paths

5. **JSON Parsing Errors**
   - Use `OutputFormat.STREAM_JSON` for session tracking
   - Handle malformed JSON gracefully
   - Check for `is_error` in responses