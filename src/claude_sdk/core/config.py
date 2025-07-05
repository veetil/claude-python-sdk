"""
Configuration management for the Claude Python SDK.

This module handles configuration loading, validation, and management
from various sources including environment variables, configuration files,
and programmatic settings.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from .types import LogLevel, OutputFormat, EnvDict, PathLike


class ClaudeConfig(BaseModel):
    """Configuration for the Claude Python SDK."""
    
    # API Configuration
    api_key: Optional[str] = Field(
        None,
        description="Claude API key (if applicable)",
        json_schema_extra={"env": "CLAUDE_API_KEY"},
    )
    
    # CLI Configuration
    cli_path: str = Field(
        "claude",
        description="Path to Claude CLI executable",
        json_schema_extra={"env": "CLAUDE_CLI_PATH"},
    )
    
    # Timeouts
    default_timeout: float = Field(
        30.0,
        description="Default timeout for commands in seconds",
        json_schema_extra={"env": "CLAUDE_DEFAULT_TIMEOUT"},
    )
    
    session_timeout: float = Field(
        300.0,
        description="Session timeout in seconds",
        json_schema_extra={"env": "CLAUDE_SESSION_TIMEOUT"},
    )
    
    # Output Configuration
    default_output_format: OutputFormat = Field(
        OutputFormat.TEXT,
        description="Default output format",
        json_schema_extra={"env": "CLAUDE_OUTPUT_FORMAT"},
    )
    
    # Logging Configuration
    log_level: LogLevel = Field(
        LogLevel.INFO,
        description="Logging level",
        json_schema_extra={"env": "CLAUDE_LOG_LEVEL"},
    )
    
    log_file: Optional[str] = Field(
        None,
        description="Path to log file",
        json_schema_extra={"env": "CLAUDE_LOG_FILE"},
    )
    
    # Workspace Configuration
    workspace_base_path: Optional[str] = Field(
        None,
        description="Base path for workspaces",
        json_schema_extra={"env": "CLAUDE_WORKSPACE_BASE_PATH"},
    )
    
    workspace_cleanup_on_exit: bool = Field(
        True,
        description="Clean up workspaces on exit",
        json_schema_extra={"env": "CLAUDE_WORKSPACE_CLEANUP"},
    )
    
    # Performance Configuration
    max_concurrent_sessions: int = Field(
        5,
        description="Maximum concurrent sessions",
        json_schema_extra={"env": "CLAUDE_MAX_CONCURRENT_SESSIONS"},
    )
    
    stream_buffer_size: int = Field(
        8192,
        description="Stream buffer size in bytes",
        json_schema_extra={"env": "CLAUDE_STREAM_BUFFER_SIZE"},
    )
    
    # Retry Configuration
    max_retries: int = Field(
        3,
        description="Maximum retry attempts",
        json_schema_extra={"env": "CLAUDE_MAX_RETRIES"},
    )
    
    retry_delay: float = Field(
        1.0,
        description="Base retry delay in seconds",
        json_schema_extra={"env": "CLAUDE_RETRY_DELAY"},
    )
    
    # Security Configuration
    enable_workspace_isolation: bool = Field(
        True,
        description="Enable workspace isolation",
        json_schema_extra={"env": "CLAUDE_ENABLE_WORKSPACE_ISOLATION"},
    )
    
    safe_mode: bool = Field(
        False,
        description="Enable safe mode (disables --dangerously-skip-permissions)",
        json_schema_extra={"env": "CLAUDE_SAFE_MODE"},
    )
    
    allowed_commands: List[str] = Field(
        default_factory=list,
        description="List of allowed commands (empty = all allowed)",
    )
    
    # Debug Configuration
    debug_mode: bool = Field(
        False,
        description="Enable debug mode",
        json_schema_extra={"env": "CLAUDE_DEBUG"},
    )
    
    verbose_logging: bool = Field(
        False,
        description="Enable verbose logging",
        json_schema_extra={"env": "CLAUDE_VERBOSE"},
    )
    
    # Environment Variables
    env_vars: EnvDict = Field(
        default_factory=dict,
        description="Additional environment variables",
    )
    
    @validator('default_timeout', 'session_timeout', 'retry_delay')
    def validate_positive_float(cls, v):
        """Validate that timeout values are positive."""
        if v <= 0:
            raise ValueError("Timeout values must be positive")
        return v
    
    @validator('max_concurrent_sessions', 'stream_buffer_size', 'max_retries')
    def validate_positive_int(cls, v):
        """Validate that integer values are positive."""
        if v <= 0:
            raise ValueError("Integer values must be positive")
        return v
    
    @validator('cli_path')
    def validate_cli_path(cls, v):
        """Validate that CLI path is not empty."""
        if not v.strip():
            raise ValueError("CLI path cannot be empty")
        return v.strip()
    
    @validator('workspace_base_path')
    def validate_workspace_path(cls, v):
        """Validate workspace base path."""
        if v is not None:
            path = Path(v)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
            if not path.is_dir():
                raise ValueError(f"Workspace base path must be a directory: {v}")
        return v
    
    @validator('log_file')
    def validate_log_file(cls, v):
        """Validate log file path."""
        if v is not None:
            log_path = Path(v)
            log_path.parent.mkdir(parents=True, exist_ok=True)
        return v
    
    @classmethod
    def from_env(cls) -> "ClaudeConfig":
        """Create configuration from environment variables."""
        config_data = {}
        
        # Load from environment variables
        for field_name, field_info in cls.model_fields.items():
            # Get the Field object which contains the json_schema_extra
            if hasattr(field_info, 'json_schema_extra') and field_info.json_schema_extra:
                env_name = field_info.json_schema_extra.get('env')
            else:
                # Check for env in field metadata
                env_name = None
                for key, value in field_info.metadata:
                    if hasattr(value, '__dict__') and 'env' in value.__dict__:
                        env_name = value.env
                        break
            
            if env_name and env_name in os.environ:
                value = os.environ[env_name]
                
                # Type conversion based on field type
                field_type = field_info.annotation
                if field_type == bool:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif field_type == int:
                    value = int(value)
                elif field_type == float:
                    value = float(value)
                elif hasattr(field_type, '__origin__'):
                    # Handle generic types like List[str]
                    if field_type.__origin__ == list:
                        value = [item.strip() for item in value.split(',')]
                
                config_data[field_name] = value
        
        return cls(**config_data)
    
    @classmethod
    def from_file(cls, config_path: PathLike) -> "ClaudeConfig":
        """Load configuration from a file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix.lower() == '.json':
                config_data = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
        
        return cls(**config_data)
    
    @classmethod
    def load_config(
        cls,
        config_file: Optional[PathLike] = None,
        env_override: bool = True,
    ) -> "ClaudeConfig":
        """
        Load configuration with priority order:
        1. Environment variables (if env_override=True)
        2. Configuration file (if provided)
        3. Default values
        """
        config_data = {}
        
        # Start with config file if provided
        if config_file:
            file_config = cls.from_file(config_file)
            config_data.update(file_config.dict())
        
        # Override with environment variables
        if env_override:
            env_config = cls.from_env()
            config_data.update({
                k: v for k, v in env_config.dict().items() 
                if v is not None
            })
        
        return cls(**config_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.dict()
    
    def to_json(self) -> str:
        """Convert configuration to JSON string."""
        return self.json(indent=2)
    
    def save_to_file(self, config_path: PathLike) -> None:
        """Save configuration to file."""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            if config_path.suffix.lower() == '.json':
                json.dump(self.dict(), f, indent=2)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
    
    def get_env_vars(self) -> EnvDict:
        """Get environment variables for subprocess execution."""
        env_vars = os.environ.copy()
        env_vars.update(self.env_vars)
        
        # Handle ANTHROPIC_API_KEY - unset or empty to avoid credit balance issues
        if 'ANTHROPIC_API_KEY' in env_vars:
            # Remove it to avoid credit balance issues with Claude CLI
            del env_vars['ANTHROPIC_API_KEY']
        
        # Add configuration-specific environment variables
        if self.api_key:
            env_vars['CLAUDE_API_KEY'] = self.api_key
        
        if self.debug_mode:
            env_vars['CLAUDE_DEBUG'] = '1'
        
        if self.verbose_logging:
            env_vars['CLAUDE_VERBOSE'] = '1'
        
        return env_vars
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of warnings."""
        warnings = []
        
        # Check for required tools
        if not self._check_cli_available():
            warnings.append(f"Claude CLI not found at path: {self.cli_path}")
        
        # Check workspace configuration
        if self.workspace_base_path:
            workspace_path = Path(self.workspace_base_path)
            if not workspace_path.exists():
                warnings.append(f"Workspace base path does not exist: {self.workspace_base_path}")
            elif not os.access(workspace_path, os.W_OK):
                warnings.append(f"Workspace base path is not writable: {self.workspace_base_path}")
        
        # Check log file
        if self.log_file:
            log_path = Path(self.log_file)
            if not log_path.parent.exists():
                warnings.append(f"Log file directory does not exist: {log_path.parent}")
            elif not os.access(log_path.parent, os.W_OK):
                warnings.append(f"Log file directory is not writable: {log_path.parent}")
        
        return warnings
    
    def _check_cli_available(self) -> bool:
        """Check if Claude CLI is available."""
        import shutil
        return shutil.which(self.cli_path) is not None


# Global configuration instance
_config: Optional[ClaudeConfig] = None


def get_config() -> ClaudeConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = ClaudeConfig.load_config()
    return _config


def set_config(config: ClaudeConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config
    _config = None