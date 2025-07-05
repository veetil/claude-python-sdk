"""
Safe Mode Example

This example demonstrates how to use safe mode to disable
the --dangerously-skip-permissions flag.
"""

import asyncio
from claude_sdk import ClaudeClient, ClaudeConfig


async def compare_modes():
    """Compare default mode vs safe mode."""
    print("🔒 Safe Mode Comparison")
    print("=" * 60)
    
    # Default mode (includes --dangerously-skip-permissions)
    print("\n1. Default Mode:")
    print("-" * 40)
    
    default_config = ClaudeConfig(
        debug_mode=True,  # Show commands
    )
    
    async with ClaudeClient(default_config) as client:
        print("Executing query in default mode...")
        print("Watch for --dangerously-skip-permissions in the command\n")
        
        try:
            response = await client.query("What is 1+1?")
            print(f"Response: {response.content.strip()}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    
    # Safe mode (no --dangerously-skip-permissions)
    print("\n2. Safe Mode:")
    print("-" * 40)
    
    safe_config = ClaudeConfig(
        safe_mode=True,   # Disable dangerous flag
        debug_mode=True,  # Show commands
    )
    
    async with ClaudeClient(safe_config) as client:
        print("Executing query in safe mode...")
        print("Notice: No --dangerously-skip-permissions flag\n")
        
        try:
            response = await client.query("What is 2+2?")
            print(f"Response: {response.content.strip()}")
        except Exception as e:
            print(f"Error: {e}")
            print("\nNote: If this fails with permission errors,")
            print("you may need to grant appropriate permissions")
            print("or use default mode instead.")


async def safe_mode_with_sessions():
    """Example using safe mode with sessions."""
    print("\n\n" + "=" * 60)
    print("Safe Mode with Sessions")
    print("=" * 60)
    
    config = ClaudeConfig(
        safe_mode=True,
        debug_mode=True,
    )
    
    async with ClaudeClient(config) as client:
        async with client.create_session() as session:
            print("\nStarting conversation in safe mode...")
            
            # First message
            response1 = await session.query("Hello! Let's talk about Python.")
            print(f"\nClaude: {response1.content.strip()}")
            
            # Follow-up
            response2 = await session.query("What makes Python good for beginners?")
            print(f"\nClaude: {response2.content.strip()[:200]}...")


async def environment_variable_example():
    """Show how to set safe mode via environment variable."""
    print("\n\n" + "=" * 60)
    print("Safe Mode via Environment Variable")
    print("=" * 60)
    
    import os
    
    # Save original value
    original = os.environ.get("CLAUDE_SAFE_MODE")
    
    try:
        # Set safe mode via environment
        os.environ["CLAUDE_SAFE_MODE"] = "true"
        
        print("\nSet CLAUDE_SAFE_MODE=true")
        print("Creating config from environment...")
        
        config = ClaudeConfig.from_env()
        print(f"Safe mode enabled: {config.safe_mode}")
        print(f"Debug mode: {config.debug_mode}")
        
        # Also enable debug to see commands
        config.debug_mode = True
        
        async with ClaudeClient(config) as client:
            response = await client.query("Environment test")
            print(f"\nResponse: {response.content.strip()[:100]}...")
            
    finally:
        # Restore original value
        if original is None:
            os.environ.pop("CLAUDE_SAFE_MODE", None)
        else:
            os.environ["CLAUDE_SAFE_MODE"] = original


async def when_to_use_safe_mode():
    """Explain when to use safe mode."""
    print("\n\n" + "=" * 60)
    print("When to Use Safe Mode")
    print("=" * 60)
    
    print("""
Safe mode (safe_mode=True) disables the --dangerously-skip-permissions flag.

Use safe mode when:
1. Running in production environments with strict security
2. Working with sensitive data that requires permission checks
3. Integrating with systems that enforce access controls
4. Testing security configurations

Use default mode when:
1. Developing locally
2. Running in trusted environments
3. Need faster execution without permission checks
4. Working with Claude CLI in standard scenarios

Example production config:
""")
    
    print("""
production_config = ClaudeConfig(
    safe_mode=True,              # No dangerous flags
    enable_workspace_isolation=True,  # Isolate file operations
    debug_mode=False,            # No debug output
    log_level=LogLevel.WARNING,  # Only important logs
)
""")


async def main():
    """Run all examples."""
    await compare_modes()
    await safe_mode_with_sessions()
    await environment_variable_example()
    await when_to_use_safe_mode()
    
    print("\n\n✅ Safe mode examples completed!")
    print("\nKey takeaways:")
    print("- Default: --dangerously-skip-permissions is included")
    print("- Safe mode: Set safe_mode=True to disable the flag")
    print("- Environment: Use CLAUDE_SAFE_MODE=true")


if __name__ == "__main__":
    asyncio.run(main())