#!/usr/bin/env python3
"""
Claude SDK Interactive Help Utility

This script provides an interactive help system for the Claude Python SDK,
showing all available attributes, methods, and configuration options.
"""

import asyncio
import inspect
import pprint
from typing import Any, Dict, List, Optional, Type
from pathlib import Path

from claude_sdk import ClaudeClient, ClaudeConfig
from claude_sdk.core.types import OutputFormat
from claude_sdk.session_client import SessionAwareClient
from claude_sdk.exceptions import (
    ClaudeSDKError,
    AuthenticationError, 
    SessionError,
    CommandTimeoutError,
    WorkspaceError
)


class ClaudeSDKHelp:
    """Interactive help system for Claude SDK"""
    
    def __init__(self):
        self.pp = pprint.PrettyPrinter(indent=2, width=80)
    
    def print_header(self, text: str):
        """Print a formatted header"""
        print(f"\n{'=' * 70}")
        print(f"{text:^70}")
        print('=' * 70)
    
    def print_section(self, title: str):
        """Print a section title"""
        print(f"\n{title}")
        print('-' * len(title))
    
    def show_config_options(self):
        """Display all ClaudeConfig options"""
        self.print_header("ClaudeConfig - All Configuration Options")
        
        # Get config class attributes
        config = ClaudeConfig()
        
        print("\nDefault Configuration Values:")
        for attr in sorted(dir(config)):
            if not attr.startswith('_') and not callable(getattr(config, attr)):
                value = getattr(config, attr)
                print(f"  {attr:30} = {repr(value)}")
        
        print("\n\nConfiguration Parameters:")
        print("""
config = ClaudeConfig(
    # API Configuration
    api_key="your-api-key",                    # Claude API key
    model="claude-3-5-sonnet-20241022",        # Model to use
    
    # Command Configuration  
    claude_command="claude",                    # Base command
    default_output_format=OutputFormat.TEXT,    # Output format
    
    # Timeouts and Retries
    default_timeout=30.0,                      # Default timeout (seconds)
    max_retries=3,                             # Maximum retry attempts
    retry_delay=1.0,                           # Delay between retries
    
    # Logging and Debug
    debug_mode=False,                          # Show executed commands
    verbose_logging=False,                     # Enable verbose output
    log_level="INFO",                          # Logging level
    log_file=None,                             # Optional log file path
    
    # Prefix Prompt
    enable_prefix_prompt=True,                 # Enable automatic prefix
    prefix_prompt_file="prefix-prompt.md",     # Path to prefix file
    
    # Workspace Settings
    workspace_dir=".claude-workspaces",        # Directory for workspaces
    workspace_cleanup_on_exit=True,            # Auto-cleanup workspaces
    
    # Safety and Permissions
    safe_mode=False,                           # Skip permissions prompt
    
    # Process Settings
    max_concurrent_processes=10,               # Max concurrent processes
    process_cleanup_timeout=5.0,               # Process cleanup timeout
    stream_chunk_size=1024,                    # Stream chunk size
    stream_buffer_size=65536,                  # Stream buffer size
)
""")
    
    def show_client_methods(self):
        """Display all client methods with signatures"""
        self.print_header("ClaudeClient & SessionAwareClient Methods")
        
        # Standard client methods
        self.print_section("ClaudeClient Methods")
        
        methods = [
            ("query", "Send a query and get response"),
            ("stream_query", "Stream a query response"), 
            ("execute_command", "Execute raw command"),
            ("create_session", "Create managed session context"),
            ("create_workspace", "Create managed workspace"),
            ("list_sessions", "List all active sessions"),
            ("list_workspaces", "List all workspaces"),
            ("command_builder", "Create command builder"),
            ("close", "Close client and cleanup"),
        ]
        
        for method_name, description in methods:
            method = getattr(ClaudeClient, method_name, None)
            if method:
                sig = inspect.signature(method)
                print(f"\n{method_name}{sig}")
                print(f"  {description}")
        
        # Session-aware client methods
        self.print_section("SessionAwareClient Additional Methods")
        
        session_methods = [
            ("query_with_session", "Query with automatic session management"),
            ("last_session_id", "Get last session ID (property)"),
            ("clear_session", "Clear stored session"),
        ]
        
        for method_name, description in session_methods:
            if hasattr(SessionAwareClient, method_name):
                if callable(getattr(SessionAwareClient, method_name)):
                    method = getattr(SessionAwareClient, method_name)
                    sig = inspect.signature(method)
                    print(f"\n{method_name}{sig}")
                else:
                    print(f"\n{method_name} (property)")
                print(f"  {description}")
    
    def show_exceptions(self):
        """Display all exception types"""
        self.print_header("Exception Types")
        
        exceptions = [
            (ClaudeSDKError, "Base exception for all SDK errors"),
            (AuthenticationError, "API key or authentication issues"),
            (SessionError, "Session-related errors"),
            (CommandTimeoutError, "Operation timeout errors"),
            (WorkspaceError, "Workspace-related errors"),
        ]
        
        for exc_class, description in exceptions:
            print(f"\n{exc_class.__name__}")
            print(f"  {description}")
            if exc_class.__doc__:
                print(f"  {exc_class.__doc__.strip()}")
    
    def show_examples(self):
        """Display usage examples"""
        self.print_header("Usage Examples")
        
        examples = {
            "Basic Query": """
# Simple query
async with ClaudeClient() as client:
    response = await client.query("Hello, Claude!")
    print(response.content)
""",
            
            "Session Management": """
# Session with resumption
async with SessionAwareClient() as client:
    # First query creates session
    resp1 = await client.query_with_session("Create a Python script")
    session_id = resp1.session_id
    
    # Resume session
    resp2 = await client.query_with_session(
        "Add error handling",
        resume_session_id=session_id
    )
""",
            
            "Streaming Response": """
# Stream with progress tracking
async for chunk in client.stream_query("Write a story", timeout=120.0):
    print(chunk, end='', flush=True)
""",
            
            "Error Handling": """
# Timeout and retry
try:
    response = await client.query("Complex task", timeout=10.0)
except CommandTimeoutError:
    # Retry with longer timeout
    response = await client.query("Complex task", timeout=60.0)
""",
            
            "Parallel Execution": """
# Run multiple queries in parallel
tasks = [
    client.query("Task 1"),
    client.query("Task 2"),
    client.query("Task 3"),
]
results = await asyncio.gather(*tasks)
""",
        }
        
        for title, code in examples.items():
            self.print_section(title)
            print(code)
    
    def show_environment_vars(self):
        """Display environment variables"""
        self.print_header("Environment Variables")
        
        print("""
# Required
CLAUDE_API_KEY              # Your Claude API key

# Optional
CLAUDE_MODEL                # Model name (default: claude-3-5-sonnet-20241022)
CLAUDE_DEBUG                # Enable debug mode (true/false)
CLAUDE_TIMEOUT              # Default timeout in seconds
CLAUDE_PREFIX_PROMPT_FILE   # Path to prefix prompt file
CLAUDE_WORKSPACE_DIR        # Directory for workspaces
CLAUDE_LOG_FILE             # Path to log file
CLAUDE_LOG_LEVEL            # Logging level (DEBUG/INFO/WARNING/ERROR)
CLAUDE_SAFE_MODE            # Enable safe mode (true/false)
""")
    
    def show_output_formats(self):
        """Display output format options"""
        self.print_header("Output Formats")
        
        print("\nAvailable formats:")
        for format_opt in OutputFormat:
            print(f"  {format_opt.name:15} = {format_opt.value}")
        
        print("\nUsage:")
        print("""
# Text output (default)
response = await client.query("Hello", output_format=OutputFormat.TEXT)

# JSON output
response = await client.query("Hello", output_format=OutputFormat.JSON)

# Stream JSON (recommended for session tracking)
response = await client.query("Hello", output_format=OutputFormat.STREAM_JSON)
""")
    
    def show_all(self):
        """Show all help information"""
        print("🤖 Claude Python SDK - Complete Help Reference")
        print("Version: 0.1.0")
        
        self.show_config_options()
        self.show_client_methods()
        self.show_exceptions()
        self.show_output_formats()
        self.show_environment_vars()
        self.show_examples()
        
        self.print_header("Additional Resources")
        print("""
📚 Documentation Files:
  - README.md                    # Getting started guide
  - CLAUDE_SDK_HELP.md          # Complete API reference
  - examples/                    # Example scripts
  
🔧 Example Scripts:
  - session_stories_test.py     # Session management demo
  - session_stories_stream.py   # Advanced streaming demo
  - analytics_demo.py           # Data analysis workflow
  
🌐 Online Resources:
  - GitHub: https://github.com/your-repo/claude-sdk
  - Issues: https://github.com/your-repo/claude-sdk/issues
""")


def interactive_help():
    """Run interactive help menu"""
    help_system = ClaudeSDKHelp()
    
    while True:
        print("\n" + "=" * 50)
        print("Claude SDK Interactive Help")
        print("=" * 50)
        print("1. Configuration Options")
        print("2. Client Methods")
        print("3. Exception Types")
        print("4. Output Formats")
        print("5. Environment Variables")
        print("6. Usage Examples")
        print("7. Show All")
        print("0. Exit")
        
        choice = input("\nSelect option (0-7): ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            help_system.show_config_options()
        elif choice == '2':
            help_system.show_client_methods()
        elif choice == '3':
            help_system.show_exceptions()
        elif choice == '4':
            help_system.show_output_formats()
        elif choice == '5':
            help_system.show_environment_vars()
        elif choice == '6':
            help_system.show_examples()
        elif choice == '7':
            help_system.show_all()
        else:
            print("Invalid option. Please try again.")
        
        input("\nPress Enter to continue...")


async def test_configuration():
    """Test current configuration"""
    print("\n🔧 Testing Current Configuration")
    print("-" * 40)
    
    config = ClaudeConfig()
    print(f"API Key Set: {'Yes' if config.api_key else 'No'}")
    print(f"Debug Mode: {config.debug_mode}")
    print(f"Prefix Prompt: {'Enabled' if config.enable_prefix_prompt else 'Disabled'}")
    print(f"Default Timeout: {config.default_timeout}s")
    print(f"Safe Mode: {config.safe_mode}")
    print(f"Output Format: {config.default_output_format}")
    print(f"Max Retries: {config.max_retries}")
    print(f"Workspace Cleanup: {config.workspace_cleanup_on_exit}")
    
    if config.api_key:
        print("\n✅ Configuration appears valid")
    else:
        print("\n⚠️  Warning: CLAUDE_API_KEY not set")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        help_system = ClaudeSDKHelp()
        
        if sys.argv[1] == "--config":
            help_system.show_config_options()
        elif sys.argv[1] == "--methods":
            help_system.show_client_methods()
        elif sys.argv[1] == "--exceptions":
            help_system.show_exceptions()
        elif sys.argv[1] == "--formats":
            help_system.show_output_formats()
        elif sys.argv[1] == "--env":
            help_system.show_environment_vars()
        elif sys.argv[1] == "--examples":
            help_system.show_examples()
        elif sys.argv[1] == "--test":
            asyncio.run(test_configuration())
        else:
            help_system.show_all()
    else:
        # Run interactive menu
        interactive_help()