"""
Basic usage examples for the Claude Python SDK.

This script demonstrates the fundamental operations you can perform
with the Claude Python SDK.
"""

import asyncio
import logging
from claude_sdk import ClaudeClient, ClaudeConfig
from claude_sdk.core.types import OutputFormat

# Configure logging
logging.basicConfig(level=logging.INFO)


async def basic_query_example():
    """Example of a basic query to Claude."""
    print("=== Basic Query Example ===")
    
    async with ClaudeClient() as client:
        response = await client.query("What is the capital of France?")
        print(f"Claude: {response.content}")
        print(f"Duration: {response.metadata.get('duration', 'unknown')} seconds")


async def json_output_example():
    """Example of requesting JSON output format."""
    print("\n=== JSON Output Example ===")
    
    async with ClaudeClient() as client:
        response = await client.query(
            "List 3 programming languages and their primary use cases",
            output_format=OutputFormat.JSON
        )
        print(f"JSON Response: {response.content}")


async def streaming_example():
    """Example of streaming a response from Claude."""
    print("\n=== Streaming Example ===")
    
    async with ClaudeClient() as client:
        print("Claude (streaming): ", end="", flush=True)
        
        async for chunk in client.stream_query(
            "Explain how async/await works in Python in a few sentences"
        ):
            print(chunk, end="", flush=True)
        
        print()  # New line after streaming


async def error_handling_example():
    """Example of error handling with the SDK."""
    print("\n=== Error Handling Example ===")
    
    from claude_sdk.exceptions import CommandTimeoutError, CommandExecutionError
    
    config = ClaudeConfig(default_timeout=0.001)  # Very short timeout to trigger error
    
    async with ClaudeClient(config=config) as client:
        try:
            await client.query("This will likely timeout")
        except CommandTimeoutError as e:
            print(f"Caught timeout error: {e}")
        except CommandExecutionError as e:
            print(f"Caught execution error: {e}")
        except Exception as e:
            print(f"Caught unexpected error: {e}")


async def configuration_example():
    """Example of using custom configuration."""
    print("\n=== Configuration Example ===")
    
    config = ClaudeConfig(
        cli_path="claude",  # Path to Claude CLI
        default_timeout=30.0,
        max_retries=2,
        debug_mode=True,
        workspace_cleanup_on_exit=True,
    )
    
    async with ClaudeClient(config=config) as client:
        response = await client.query("Hello with custom config!")
        print(f"Response: {response.content}")


async def command_building_example():
    """Example of building complex commands."""
    print("\n=== Command Building Example ===")
    
    async with ClaudeClient() as client:
        # Build a command using the fluent interface
        builder = client.command_builder()
        command = (builder
                  .add_prompt("Analyze this code structure")
                  .set_output_format("json")
                  .add_flag("verbose")
                  .build())
        
        print(f"Built command: {' '.join(command)}")
        
        # Execute the built command
        result = await client.execute_command(command)
        print(f"Command result: {result.stdout[:100]}...")


async def main():
    """Run all examples."""
    print("Claude Python SDK - Basic Usage Examples")
    print("=" * 50)
    
    try:
        await basic_query_example()
        await json_output_example()
        await streaming_example()
        await error_handling_example()
        await configuration_example()
        await command_building_example()
        
    except Exception as e:
        print(f"Example failed: {e}")
        print("Note: These examples require Claude CLI to be installed and configured.")
    
    print("\n" + "=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())