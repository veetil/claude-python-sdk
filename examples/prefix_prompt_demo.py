"""
Prefix Prompt Demo

This example demonstrates how the SDK automatically prepends
the prefix-prompt.md content to all user prompts.
"""

import asyncio
from claude_sdk import ClaudeClient, ClaudeConfig


async def main():
    print("🎯 Prefix Prompt Demo")
    print("=" * 60)
    
    # Default configuration (prefix prompt enabled)
    config = ClaudeConfig(
        debug_mode=True,  # Show commands
    )
    
    print(f"\nPrefix prompt file: {config.prefix_prompt_file}")
    print(f"Prefix prompt enabled: {config.enable_prefix_prompt}")
    
    # Simple prompt that should trigger BatchTool usage
    user_prompt = "Write 3 Python functions: one for sorting, one for searching, and one for hashing"
    
    print(f"\nUser prompt: {user_prompt}")
    print("\nThe SDK will automatically prepend the prefix-prompt.md content.")
    print("Watch for BatchTool usage in the response...\n")
    
    async with ClaudeClient(config) as client:
        try:
            response = await client.query(user_prompt)
            print("Response:")
            print("-" * 60)
            print(response.content)
            
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("\nTo disable prefix prompt, use: ClaudeConfig(enable_prefix_prompt=False)")


if __name__ == "__main__":
    asyncio.run(main())