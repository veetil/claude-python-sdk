# Session ID Implementation Summary

## Overview

The Claude Python SDK now fully supports session ID extraction and resumption with proper error handling.

## Key Features Implemented

### 1. Session ID Extraction
- Automatically extracts session ID from `stream-json` output
- Parses all three JSON lines:
  - `system` init message with session_id
  - `assistant` message with content and session_id
  - `result` message with final result and session_id

### 2. Session Resumption
- Uses `-r SESSION_ID` flag to resume previous sessions
- Maintains conversation context across multiple queries

### 3. Error Handling
- Detects `is_error: true` in result messages
- Returns error messages appropriately
- Session ID still available even on errors

## JSON Stream Format

Claude CLI with `--output-format stream-json` returns:

```json
// Line 1: System initialization
{"type":"system","subtype":"init","session_id":"acc21b20-13b3-423c-9191-01925b546d5b",...}

// Line 2: Assistant message
{"type":"assistant","message":{"content":[{"type":"text","text":"London"}]},"session_id":"acc21b20-13b3-423c-9191-01925b546d5b"}

// Line 3: Result (success)
{"type":"result","subtype":"success","is_error":false,"result":"London","session_id":"acc21b20-13b3-423c-9191-01925b546d5b",...}

// OR Line 3: Result (error)
{"type":"result","subtype":"error","is_error":true,"error":"Error message","session_id":"acc21b20-13b3-423c-9191-01925b546d5b"}
```

## Usage Example

```python
from claude_sdk.session_client import SessionAwareClient

async with SessionAwareClient() as client:
    # Initial query - creates session
    response = await client.query_with_session(
        "write code for different tasks and write to folder output/"
    )
    session_id = response.session_id  # Extracted automatically
    
    # Check for errors
    if response.metadata.get('is_error'):
        print(f"Error: {response.metadata.get('error')}")
    
    # System validation...
    if not files_found_in_output:
        # Correction with session resumption
        response2 = await client.query_with_session(
            "error - you have to write to the correct folder which is output/",
            resume_session_id=session_id  # Uses -r flag
        )
```

## Command Line Equivalent

```bash
# Initial query
claude -p "your prompt" --output-format stream-json --verbose

# Resume session
claude -p "follow-up prompt" -r SESSION_ID --output-format stream-json --verbose
```

## Implementation Details

### SessionAwareClient

- Extends base `ClaudeClient`
- Default output format: `STREAM_JSON`
- Parses JSON lines to extract session ID
- Handles both success and error cases
- Stores last session ID for auto-resume

### Key Methods

```python
async def query_with_session(
    prompt: str,
    resume_session_id: Optional[str] = None,  # For -r flag
    auto_resume_last: bool = False,          # Auto use last session
    output_format: OutputFormat = OutputFormat.STREAM_JSON,
    ...
) -> SessionAwareResponse
```

### Response Object

```python
class SessionAwareResponse:
    content: str              # Result or error message
    session_id: Optional[str] # Extracted session ID
    metadata: Dict[str, Any]  # Includes is_error, error, etc.
    raw_json: Optional[Dict]  # Raw result JSON
```

## Error Handling

The SDK properly handles errors:

1. Checks `is_error` field in result
2. Extracts error message from `error` or `result` field
3. Still returns session ID for potential recovery
4. Logs errors appropriately

## Files Created

1. `src/claude_sdk/session_client.py` - Main implementation
2. `claude_sdk_enhanced.py` - Standalone enhanced version
3. `examples/session_management_demo.py` - Comprehensive examples
4. `examples/session_workflow_example.py` - Real-world workflow
5. `test_stream_json_parsing.py` - JSON parsing tests
6. `SESSION_MANAGEMENT.md` - User documentation

## Testing

Run tests with:
```bash
python test_stream_json_parsing.py
python test_session_functionality.py
python examples/session_workflow_example.py
```

## Benefits

1. **Session Continuity**: Maintain context across multiple queries
2. **Error Recovery**: Can retry in same session after errors  
3. **Workflow Support**: Perfect for multi-step operations
4. **Backward Compatible**: Works with existing SDK structure
5. **Automatic**: Session ID extraction happens transparently