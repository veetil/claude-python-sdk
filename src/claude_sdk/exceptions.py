"""
Exception classes for the Claude Python SDK.

This module defines the exception hierarchy used throughout the SDK,
providing detailed error information and context for debugging.
"""

from typing import Any, Dict, Optional, List


class ClaudeSDKError(Exception):
    """Base exception for all Claude SDK errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
    
    def __str__(self) -> str:
        if self.context:
            return f"{self.message} (context: {self.context})"
        return self.message


class CommandError(ClaudeSDKError):
    """Base class for command-related errors."""
    
    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.command = command


class CommandNotFoundError(CommandError):
    """Raised when the Claude CLI command is not found."""
    
    def __init__(self, command: str = "claude"):
        super().__init__(
            f"Command '{command}' not found. Please ensure Claude CLI is installed.",
            command=command,
        )


class CommandTimeoutError(CommandError):
    """Raised when a command execution times out."""
    
    def __init__(
        self,
        command: str,
        timeout: float,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            f"Command '{command}' timed out after {timeout} seconds",
            command=command,
            context=context,
        )
        self.timeout = timeout


class CommandExecutionError(CommandError):
    """Raised when a command fails during execution."""
    
    def __init__(
        self,
        command: str,
        exit_code: int,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        message = f"Command '{command}' failed with exit code {exit_code}"
        if stderr:
            message += f": {stderr}"
        
        super().__init__(message, command=command, context=context)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class SessionError(ClaudeSDKError):
    """Base class for session-related errors."""
    
    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.session_id = session_id


class SessionCreationError(SessionError):
    """Raised when session creation fails."""
    
    def __init__(
        self,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            f"Failed to create session: {reason}",
            context=context,
        )


class SessionTimeoutError(SessionError):
    """Raised when session operations timeout."""
    
    def __init__(
        self,
        session_id: str,
        timeout: float,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            f"Session '{session_id}' timed out after {timeout} seconds",
            session_id=session_id,
            context=context,
        )
        self.timeout = timeout


class WorkspaceError(ClaudeSDKError):
    """Base class for workspace-related errors."""
    
    def __init__(
        self,
        message: str,
        workspace_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.workspace_path = workspace_path


class WorkspaceCreationError(WorkspaceError):
    """Raised when workspace creation fails."""
    
    def __init__(
        self,
        reason: str,
        workspace_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            f"Failed to create workspace: {reason}",
            workspace_path=workspace_path,
            context=context,
        )


class WorkspaceCleanupError(WorkspaceError):
    """Raised when workspace cleanup fails."""
    
    def __init__(
        self,
        reason: str,
        workspace_path: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            f"Failed to cleanup workspace '{workspace_path}': {reason}",
            workspace_path=workspace_path,
            context=context,
        )


class AuthenticationError(ClaudeSDKError):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)


class ValidationError(ClaudeSDKError):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        expected: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.field = field
        self.value = value
        self.expected = expected


class RateLimitError(ClaudeSDKError):
    """Raised when rate limits are exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.retry_after = retry_after


class ConfigurationError(ClaudeSDKError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.config_key = config_key


# Exception mapping for HTTP-like status codes
EXCEPTION_MAP = {
    401: AuthenticationError,
    403: AuthenticationError,
    404: CommandNotFoundError,
    408: CommandTimeoutError,
    429: RateLimitError,
    500: CommandExecutionError,
}


def map_error_code(code: int, message: str, **kwargs) -> ClaudeSDKError:
    """Map error codes to appropriate exception types."""
    exception_class = EXCEPTION_MAP.get(code, ClaudeSDKError)
    return exception_class(message, **kwargs)