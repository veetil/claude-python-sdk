"""
Type definitions for the Claude Python SDK.

This module contains all the type definitions, data classes, and protocols
used throughout the SDK.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Protocol, TypeVar, Generic
from pydantic import BaseModel, Field, validator
import json


class OutputFormat(str, Enum):
    """Supported output formats for Claude CLI."""
    
    TEXT = "text"
    JSON = "json"
    STREAM_JSON = "stream-json"


class LogLevel(str, Enum):
    """Supported log levels."""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SessionStatus(str, Enum):
    """Session status states."""
    
    CREATED = "created"
    ACTIVE = "active"
    IDLE = "idle"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class ClaudeResponse:
    """Response from Claude CLI operations."""
    
    content: str
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "content": self.content,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClaudeResponse":
        """Create response from dictionary."""
        timestamp = datetime.fromisoformat(data["timestamp"])
        return cls(
            content=data["content"],
            session_id=data.get("session_id"),
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
        )


@dataclass
class CommandResult:
    """Result of a command execution."""
    
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    command: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def success(self) -> bool:
        """Check if command was successful."""
        return self.exit_code == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": self.duration,
            "command": self.command,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
        }


@dataclass
class SessionInfo:
    """Information about a Claude session."""
    
    session_id: str
    status: SessionStatus
    created_at: datetime
    last_activity: datetime
    workspace_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session info to dictionary."""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "workspace_path": self.workspace_path,
            "metadata": self.metadata,
        }


@dataclass
class WorkspaceInfo:
    """Information about a workspace."""
    
    workspace_id: str
    path: str
    created_at: datetime
    size_bytes: int = 0
    file_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert workspace info to dictionary."""
        return {
            "workspace_id": self.workspace_id,
            "path": self.path,
            "created_at": self.created_at.isoformat(),
            "size_bytes": self.size_bytes,
            "file_count": self.file_count,
            "metadata": self.metadata,
        }


class StreamingCallback(Protocol):
    """Protocol for streaming output callbacks."""
    
    async def __call__(self, chunk: str) -> None:
        """Handle a chunk of streaming output."""
        ...


class CommandProcessor(Protocol):
    """Protocol for command processors."""
    
    async def process(self, command: str, **kwargs) -> CommandResult:
        """Process a command and return the result."""
        ...


class WorkspaceManager(Protocol):
    """Protocol for workspace managers."""
    
    async def create_workspace(self, workspace_id: str) -> WorkspaceInfo:
        """Create a new workspace."""
        ...
    
    async def cleanup_workspace(self, workspace_id: str) -> None:
        """Clean up a workspace."""
        ...


# Generic type for configuration
T = TypeVar('T')


class ConfigField(Generic[T]):
    """Configuration field with validation."""
    
    def __init__(
        self,
        default: T,
        description: str,
        validator_func: Optional[callable] = None,
    ):
        self.default = default
        self.description = description
        self.validator_func = validator_func
    
    def validate(self, value: T) -> T:
        """Validate the field value."""
        if self.validator_func:
            return self.validator_func(value)
        return value


class ClaudeCommand(BaseModel):
    """Represents a Claude CLI command."""
    
    action: str = Field(..., description="The main action to perform")
    prompt: Optional[str] = Field(None, description="Prompt text for Claude")
    files: List[str] = Field(default_factory=list, description="Files to include")
    output_format: OutputFormat = Field(
        OutputFormat.TEXT, description="Output format"
    )
    session_id: Optional[str] = Field(None, description="Session ID to use")
    workspace_path: Optional[str] = Field(None, description="Workspace path")
    timeout: float = Field(30.0, description="Command timeout in seconds")
    env_vars: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    
    @validator('files')
    def validate_files(cls, v):
        """Validate that files exist."""
        for file_path in v:
            if not Path(file_path).exists():
                raise ValueError(f"File not found: {file_path}")
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        """Validate timeout value."""
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v
    
    def to_cli_args(self) -> List[str]:
        """Convert command to CLI arguments."""
        args = ["claude"]
        
        if self.output_format != OutputFormat.TEXT:
            args.extend(["--output-format", self.output_format.value])
        
        if self.session_id:
            args.extend(["--session-id", self.session_id])
        
        if self.prompt:
            args.extend(["-p", self.prompt])
        
        for file_path in self.files:
            args.extend(["--file", file_path])
        
        return args


class StreamChunk(BaseModel):
    """Represents a chunk of streaming output."""
    
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    chunk_type: str = Field(default="output")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary."""
        return {
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "chunk_type": self.chunk_type,
            "metadata": self.metadata,
        }


class ErrorInfo(BaseModel):
    """Detailed error information."""
    
    error_type: str
    message: str
    code: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    traceback: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error info to dictionary."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "code": self.code,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback,
        }


# Type aliases for convenience
JSONType = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
ConfigDict = Dict[str, Any]
EnvDict = Dict[str, str]
PathLike = Union[str, Path]