"""
Show Claude Commands Example

This example demonstrates all the different claude CLI commands
that the SDK generates for various operations.
"""

import asyncio
from claude_sdk import ClaudeClient, ClaudeConfig
from claude_sdk.core.types import OutputFormat
from claude_sdk.core.subprocess_wrapper import CommandBuilder


async def show_all_command_variations():
    """Show all the different command variations the SDK can generate."""
    print("🔍 Claude CLI Command Examples")
    print("=" * 80)
    print("This demonstrates the exact commands the SDK generates\n")
    
    # Create a command builder to show examples
    builder = CommandBuilder()
    
    # 1. Basic prompt (with default --dangerously-skip-permissions)
    print("1. Basic text prompt (default config):")
    print("-" * 40)
    cmd = builder.add_prompt("Hello, Claude!").build()
    print(f"Command: {' '.join(cmd)}")
    print(f"Note: --dangerously-skip-permissions is added by default")
    print()
    
    # 2. JSON output
    print("2. JSON output format:")
    print("-" * 40)
    builder = CommandBuilder()
    cmd = builder.add_prompt("What is 2+2?").set_output_format("json").build()
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # 3. Stream JSON output
    print("3. Stream JSON output format:")
    print("-" * 40)
    builder = CommandBuilder()
    cmd = builder.add_prompt("Tell a joke").set_output_format("stream-json").build()
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # 4. With session ID
    print("4. With session ID (for conversations):")
    print("-" * 40)
    builder = CommandBuilder()
    cmd = builder.add_prompt("Continue our chat").set_session_id("session-123").build()
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # 5. With workspace
    print("5. With workspace ID:")
    print("-" * 40)
    builder = CommandBuilder()
    cmd = builder.add_prompt("Analyze this code").set_workspace_id("workspace-456").build()
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # 6. With files
    print("6. With files to include:")
    print("-" * 40)
    builder = CommandBuilder()
    cmd = builder.add_prompt("Review these files").add_files(["main.py", "test.py"]).build()
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # 7. With timeout
    print("7. With custom timeout:")
    print("-" * 40)
    builder = CommandBuilder()
    cmd = builder.add_prompt("Long task").set_timeout(60).build()
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # 8. Combined options
    print("8. Combined options (session + JSON + files):")
    print("-" * 40)
    builder = CommandBuilder()
    cmd = (builder
           .add_prompt("Complex query")
           .set_session_id("session-789")
           .set_output_format("json")
           .add_files(["data.json", "config.yaml"])
           .set_timeout(45)
           .build())
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # 9. Multiple files with workspace
    print("9. Multiple files with workspace:")
    print("-" * 40)
    builder = CommandBuilder()
    cmd = (builder
           .add_prompt("Refactor this project")
           .set_workspace_id("workspace-project")
           .add_files(["src/main.py", "src/utils.py", "tests/test_main.py"])
           .build())
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # 10. Raw command
    print("10. Raw command execution:")
    print("-" * 40)
    builder = CommandBuilder()
    cmd = builder.add_raw_args(["--help"]).build()
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # 11. Safe mode (no --dangerously-skip-permissions)
    print("11. Safe mode (disables dangerous flag):")
    print("-" * 40)
    from claude_sdk import ClaudeConfig
    safe_config = ClaudeConfig(safe_mode=True)
    builder = CommandBuilder(config=safe_config)
    cmd = builder.add_prompt("Safe query").build()
    print(f"Command: {' '.join(cmd)}")
    print(f"Note: No --dangerously-skip-permissions when safe_mode=True")
    print()


async def demonstrate_actual_execution():
    """Show actual command execution with debug output."""
    print("\n\n" + "=" * 80)
    print("ACTUAL COMMAND EXECUTION")
    print("=" * 80)
    
    # Configure with debug mode to see commands
    config = ClaudeConfig(
        debug_mode=True,
        verbose_logging=True,
    )
    
    async with ClaudeClient(config=config) as client:
        print("\n1. Simple query (watch the debug output above):")
        print("-" * 40)
        
        try:
            response = await client.query("What is the capital of France?")
            print(f"Response: {response.content.strip()}")
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n2. JSON format query:")
        print("-" * 40)
        
        try:
            response = await client.query(
                "List 3 colors",
                output_format=OutputFormat.JSON
            )
            print(f"Response preview: {response.content[:100]}...")
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n3. Streaming query:")
        print("-" * 40)
        
        try:
            print("Streaming: ", end="", flush=True)
            async for chunk in client.stream_query("Count to 3"):
                print(chunk, end="", flush=True)
            print()
        except Exception as e:
            print(f"Error: {e}")


async def show_environment_handling():
    """Show how environment variables are handled."""
    print("\n\n" + "=" * 80)
    print("ENVIRONMENT VARIABLE HANDLING")
    print("=" * 80)
    
    import os
    
    # Show current ANTHROPIC_API_KEY status
    if 'ANTHROPIC_API_KEY' in os.environ:
        print("⚠️  ANTHROPIC_API_KEY is set in environment")
        print("   The SDK will automatically remove it to avoid credit balance issues")
    else:
        print("✅ ANTHROPIC_API_KEY is not set (good!)")
    
    # Show what environment the SDK will use
    config = ClaudeConfig()
    env_vars = config.get_env_vars()
    
    print("\nEnvironment variables passed to Claude CLI:")
    print("-" * 40)
    
    # Show relevant environment variables
    relevant_vars = ['ANTHROPIC_API_KEY', 'CLAUDE_API_KEY', 'CLAUDE_DEBUG', 'CLAUDE_VERBOSE']
    for var in relevant_vars:
        if var in env_vars:
            print(f"  {var}: {env_vars[var]}")
        else:
            print(f"  {var}: (not set)")


async def main():
    """Run all examples."""
    await show_all_command_variations()
    await demonstrate_actual_execution()
    await show_environment_handling()
    
    print("\n\n" + "=" * 80)
    print("✅ All command examples completed!")
    print("=" * 80)
    print("\nTips:")
    print("- Use debug_mode=True to see commands in your own code")
    print("- The SDK handles all command building for you")
    print("- ANTHROPIC_API_KEY is automatically removed to avoid issues")


if __name__ == "__main__":
    asyncio.run(main())