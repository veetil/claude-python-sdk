"""
Simple Stream JSON Output Example

This example demonstrates how to capture and display streaming JSON output
from Claude CLI commands, with better error handling.
"""

import asyncio
import json
import time
from typing import Dict, Any, List
from claude_sdk import ClaudeClient, ClaudeConfig
from claude_sdk.core.types import OutputFormat
from claude_sdk.exceptions import CommandExecutionError


async def stream_with_json_output():
    """Demonstrate streaming with JSON output format."""
    print("🌊 Streaming JSON Output Example")
    print("=" * 60)
    
    # Configure client
    config = ClaudeConfig(
        default_timeout=30.0,
        debug_mode=False,  # Set to True to see more details
    )
    
    async with ClaudeClient(config=config) as client:
        # Example 1: Simple query with JSON output
        print("\n1. Simple Query with JSON Output:")
        print("-" * 40)
        
        try:
            response = await client.query(
                "What is 2+2?",
                output_format=OutputFormat.JSON
            )
            
            print("Raw JSON response:")
            print(response.content[:500])
            
            # Try to parse the JSON
            try:
                json_data = json.loads(response.content)
                print("\nParsed JSON structure:")
                print(json.dumps(json_data, indent=2)[:500])
            except json.JSONDecodeError:
                print("\nNote: Response is not valid JSON")
        
        except CommandExecutionError as e:
            print(f"Error: {e}")
            print(f"Exit code: {e.exit_code}")
            if e.stderr:
                print(f"Error output: {e.stderr}")
        
        # Example 2: Streaming response
        print("\n\n2. Streaming Response (showing chunks):")
        print("-" * 40)
        
        chunks_collected = []
        chunk_count = 0
        
        try:
            async for chunk in client.stream_query("Tell me a very short joke"):
                chunk_count += 1
                chunks_collected.append(chunk)
                print(f"[Chunk {chunk_count:03d}] {chunk[:50]}{'...' if len(chunk) > 50 else ''}")
            
            print(f"\nTotal chunks received: {chunk_count}")
            print(f"Complete response: {''.join(chunks_collected)}")
            
        except Exception as e:
            print(f"Streaming error: {e}")
        
        # Example 3: Direct subprocess streaming to see raw output
        print("\n\n3. Raw Subprocess Streaming:")
        print("-" * 40)
        
        from claude_sdk.core.subprocess_wrapper import CommandBuilder
        
        builder = CommandBuilder()
        command = (builder
                  .add_prompt("Say 'Hello World'")
                  .set_output_format("json")
                  .build())
        
        print(f"Command: {' '.join(command)}")
        print("\nRaw streaming output:")
        
        try:
            chunk_count = 0
            async for chunk in client._subprocess_wrapper.execute_streaming(command):
                chunk_count += 1
                print(f"\n[Chunk {chunk_count}]")
                print(f"  Type: {chunk.chunk_type}")
                print(f"  Size: {len(chunk.content)} bytes")
                print(f"  Content preview: {chunk.content[:100]}{'...' if len(chunk.content) > 100 else ''}")
                
                # Try to parse as JSON if it looks like JSON
                if chunk.content.strip().startswith('{'):
                    try:
                        json_obj = json.loads(chunk.content.strip())
                        print(f"  Parsed JSON keys: {list(json_obj.keys())}")
                    except json.JSONDecodeError:
                        pass
        
        except CommandExecutionError as e:
            print(f"Execution error: {e}")
            print(f"Exit code: {e.exit_code}")
        except Exception as e:
            print(f"Unexpected error: {type(e).__name__}: {e}")


async def test_json_parsing():
    """Test JSON parsing from Claude responses."""
    print("\n\n" + "="*60)
    print("JSON Parsing Test")
    print("="*60)
    
    # Sample JSON response (what we might expect from Claude)
    sample_json = """{
        "type": "result",
        "subtype": "success",
        "is_error": false,
        "duration_ms": 1234,
        "result": "This is the response content",
        "session_id": "test-session-123",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20
        }
    }"""
    
    print("Sample JSON structure:")
    print(sample_json)
    
    print("\nParsed data:")
    data = json.loads(sample_json)
    print(f"  Type: {data.get('type')}")
    print(f"  Success: {not data.get('is_error')}")
    print(f"  Duration: {data.get('duration_ms')}ms")
    print(f"  Result: {data.get('result')}")
    print(f"  Session ID: {data.get('session_id')}")
    print(f"  Token usage: {data.get('usage')}")


async def demonstrate_output_formats():
    """Show different output format options."""
    print("\n\n" + "="*60)
    print("Output Format Options")
    print("="*60)
    
    print("\nAvailable output formats in Claude SDK:")
    for format_type in OutputFormat:
        print(f"  - {format_type.value}: {format_type.name}")
    
    print("\nCommand line equivalents:")
    print("  claude -p 'prompt'                    # Default text output")
    print("  claude -p 'prompt' --output-format json       # JSON output")
    print("  claude -p 'prompt' --output-format stream-json  # Streaming JSON")


async def main():
    """Run the examples."""
    try:
        await stream_with_json_output()
        await test_json_parsing()
        await demonstrate_output_formats()
        
        print("\n\n✅ Examples completed!")
        print("\nNote: Some examples may fail if Claude CLI is not properly configured.")
        print("Make sure you have Claude CLI installed: npm install -g @anthropic-ai/claude-code")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())