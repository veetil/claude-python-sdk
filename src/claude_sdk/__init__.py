"""
Claude Python SDK

A lightweight subprocess wrapper for Claude CLI with async support, streaming output,
workspace isolation, and comprehensive error handling.
"""

from .client import ClaudeClient
from .exceptions import (
    ClaudeSDKError,
    CommandError,
    CommandExecutionError,
    CommandNotFoundError,
    CommandTimeoutError,
    SessionError,
    WorkspaceError,
    AuthenticationError,
)
from .core.config import ClaudeConfig
from .core.types import (
    ClaudeResponse,
    CommandResult,
    SessionInfo,
    WorkspaceInfo,
)

__version__ = "0.1.0"
__author__ = "Claude Code"
__email__ = "code@anthropic.com"

__all__ = [
    # Main client
    "ClaudeClient",
    # Configuration
    "ClaudeConfig",
    # Types
    "ClaudeResponse",
    "CommandResult",
    "SessionInfo",
    "WorkspaceInfo",
    # Exceptions
    "ClaudeSDKError",
    "CommandError",
    "CommandExecutionError",
    "CommandNotFoundError",
    "CommandTimeoutError",
    "SessionError",
    "WorkspaceError",
    "AuthenticationError",
]