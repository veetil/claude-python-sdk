#!/usr/bin/env python3
"""
Test script to verify stream-json parsing for session ID extraction
"""

import json
from typing import Optional, Tuple


def parse_stream_json_output(output: str) -> Tuple[str, Optional[str]]:
    """
    Parse stream-json output from Claude CLI.
    
    Returns:
        Tuple of (content/result, session_id)
    """
    lines = output.strip().split('\n')
    
    session_id = None
    content = ""
    
    # Process lines to extract information
    for line in lines:
        if not line.strip():
            continue
            
        try:
            json_obj = json.loads(line)
            
            # Handle different message types
            if json_obj.get('type') == 'system' and json_obj.get('subtype') == 'init':
                # Initial system message contains session_id
                if not session_id:
                    session_id = json_obj.get('session_id')
                print(f"System init - session_id: {session_id}")
                
            elif json_obj.get('type') == 'assistant':
                # Assistant message contains the response content
                message = json_obj.get('message', {})
                message_content = message.get('content', [])
                
                # Extract text content
                for item in message_content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        content = item.get('text', '')
                        print(f"Assistant message - content: {content}")
                
                # Session ID is also in assistant messages
                msg_session_id = json_obj.get('session_id')
                if msg_session_id and not session_id:
                    session_id = msg_session_id
                    
            elif json_obj.get('type') == 'result':
                # Final result line - check for errors
                is_error = json_obj.get('is_error', False)
                result_session_id = json_obj.get('session_id')
                
                if is_error:
                    # Handle error case
                    error_msg = json_obj.get('error', json_obj.get('result', 'Unknown error'))
                    print(f"❌ Error in result: {error_msg}")
                    content = f"Error: {error_msg}"
                else:
                    # Success case
                    result = json_obj.get('result', '')
                    # Use result as content if we don't have content yet
                    if result and not content:
                        content = result
                    
                # Always use session_id from result if available
                if result_session_id:
                    session_id = result_session_id
                    
                print(f"Result line - is_error: {is_error}, result: {json_obj.get('result')}, session_id: {result_session_id}")
                
        except json.JSONDecodeError as e:
            print(f"Failed to parse line: {line[:50]}... - Error: {e}")
            continue
    
    return content, session_id


# Test with the success example output
test_output_success = '''{"type":"system","subtype":"init","cwd":"/Users/mi/Projects/claude-test/claude-python-sdk","session_id":"acc21b20-13b3-423c-9191-01925b546d5b","tools":["Task","Bash","Glob","Grep","LS","exit_plan_mode","Read","Edit","MultiEdit","Write","NotebookRead","NotebookEdit","WebFetch","TodoRead","TodoWrite","WebSearch"],"mcp_servers":[],"model":"claude-opus-4-20250514","permissionMode":"default","apiKeySource":"none"}
{"type":"assistant","message":{"id":"msg_01Vm3Y5Pg9sxSz2fpkfuzs6n","type":"message","role":"assistant","model":"claude-opus-4-20250514","content":[{"type":"text","text":"London"}],"stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":4,"cache_creation_input_tokens":15342,"cache_read_input_tokens":0,"output_tokens":1,"service_tier":"standard"}},"parent_tool_use_id":null,"session_id":"acc21b20-13b3-423c-9191-01925b546d5b"}
{"type":"result","subtype":"success","is_error":false,"duration_ms":4744,"duration_api_ms":7954,"num_turns":1,"result":"London","session_id":"acc21b20-13b3-423c-9191-01925b546d5b","total_cost_usd":0.2882215,"usage":{"input_tokens":4,"cache_creation_input_tokens":15342,"cache_read_input_tokens":0,"output_tokens":5,"server_tool_use":{"web_search_requests":0}}}'''

# Test with error example
test_output_error = '''{"type":"system","subtype":"init","session_id":"err21b20-13b3-423c-9191-01925b546d5b","tools":[],"model":"claude-opus-4-20250514"}
{"type":"result","subtype":"error","is_error":true,"error":"Permission denied: Cannot access file system","session_id":"err21b20-13b3-423c-9191-01925b546d5b"}'''

print("=== Testing Stream JSON Parsing ===\n")

# Test 1: Success case
print("Test 1: Success Case")
print("-" * 30)
print("Input:")
print(test_output_success[:200] + "...")
print("\n" + "="*50 + "\n")

content, session_id = parse_stream_json_output(test_output_success)

print("\n" + "="*50)
print("\nFinal Results:")
print(f"Content: {content}")
print(f"Session ID: {session_id}")

# Test 2: Error case
print("\n\nTest 2: Error Case")
print("-" * 30)
print("Input:")
print(test_output_error)
print("\n" + "="*50 + "\n")

content_err, session_id_err = parse_stream_json_output(test_output_error)

print("\n" + "="*50)
print("\nFinal Results:")
print(f"Content: {content_err}")
print(f"Session ID: {session_id_err}")

# Test session resumption command
print("\n" + "="*50)
print("\nSession Resumption Command:")
print(f'claude -p "What else can you tell me about it?" -r {session_id} --output-format stream-json --verbose')

# Show what the SDK will do
print("\n" + "="*50)
print("\nSDK Usage Example:")
print("""
from claude_sdk.session_client import SessionAwareClient

async with SessionAwareClient() as client:
    # First query
    response1 = await client.query_with_session("What is capital of England?")
    print(f"Answer: {response1.content}")  # "London"
    print(f"Session: {response1.session_id}")  # "acc21b20-13b3-423c-9191-01925b546d5b"
    
    # Follow-up in same session
    response2 = await client.query_with_session(
        "What else can you tell me about it?",
        resume_session_id=response1.session_id
    )
""")