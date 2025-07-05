# Claude Python SDK - Complete API Signature

## Core Client

### ClaudeClient

```python
class ClaudeClient:
    def __init__(
        self,
        config: Optional[ClaudeConfig] = None,
        auto_setup_logging: bool = True,
    )
```

#### Primary Methods

```python
async def query(
    self,
    prompt: str,
    *,
    session_id: Optional[str] = None,
    output_format: OutputFormat = OutputFormat.TEXT,
    timeout: Optional[float] = None,
    workspace_id: Optional[str] = None,
    files: Optional[List[str]] = None,
) -> ClaudeResponse

async def stream_query(
    self,
    prompt: str,
    *,
    session_id: Optional[str] = None,
    timeout: Optional[float] = None,
    workspace_id: Optional[str] = None,
    files: Optional[List[str]] = None,
) -> AsyncIterator[str]

async def execute_command(
    self,
    command: Union[str, List[str]],
    *,
    timeout: Optional[float] = None,
    workspace_id: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> CommandResult
```

#### Context Managers

```python
@asynccontextmanager
async def create_session(
    self, 
    session_id: Optional[str] = None
) -> SessionContext

@asynccontextmanager
async def create_workspace(
    self,
    workspace_id: Optional[str] = None,
    copy_files: Optional[List[str]] = None,
    **kwargs
) -> WorkspaceContext
```

#### Utility Methods

```python
async def list_sessions(self) -> List[SessionInfo]
async def list_workspaces(self) -> List[WorkspaceInfo]
def command_builder(self, base_command: str = "claude") -> CommandBuilder
async def close(self) -> None
```

## Configuration

### ClaudeConfig

```python
class ClaudeConfig(BaseModel):
    # API Configuration
    api_key: Optional[str] = None
    
    # CLI Configuration
    cli_path: str = "claude"
    
    # Timeouts
    default_timeout: float = 30.0
    session_timeout: float = 300.0
    
    # Output Configuration
    default_output_format: OutputFormat = OutputFormat.TEXT
    
    # Logging Configuration
    log_level: LogLevel = LogLevel.INFO
    log_file: Optional[str] = None
    
    # Workspace Configuration
    workspace_base_path: Optional[str] = None
    workspace_cleanup_on_exit: bool = True
    
    # Performance Configuration
    max_concurrent_sessions: int = 5
    stream_buffer_size: int = 8192
    
    # Retry Configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Security Configuration
    enable_workspace_isolation: bool = True
    safe_mode: bool = False  # When True, disables --dangerously-skip-permissions
    allowed_commands: List[str] = []
    
    # Debug Configuration
    debug_mode: bool = False
    verbose_logging: bool = False
    
    # Environment Variables
    env_vars: Dict[str, str] = {}
```

### Configuration Methods

```python
@classmethod
def from_env(cls) -> ClaudeConfig
@classmethod
def from_file(cls, config_path: PathLike) -> ClaudeConfig
@classmethod
def load_config(
    cls,
    config_file: Optional[PathLike] = None,
    env_override: bool = True,
) -> ClaudeConfig

def get_env_vars(self) -> Dict[str, str]
def validate_config(self) -> List[str]
def to_dict(self) -> Dict[str, Any]
def to_json(self) -> str
def save_to_file(self, config_path: PathLike) -> None
```

## Types and Enums

### OutputFormat
```python
class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    STREAM_JSON = "stream-json"
```

### LogLevel
```python
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
```

### Response Types

```python
@dataclass
class ClaudeResponse:
    content: str
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    command: List[str]
    duration: float

@dataclass
class StreamChunk:
    content: str
    chunk_type: str  # "stdout" or "stderr"
    timestamp: float

@dataclass
class SessionInfo:
    session_id: str
    status: SessionStatus
    created_at: datetime
    last_activity: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkspaceInfo:
    workspace_id: str
    path: str
    created_at: datetime
    files: List[str] = field(default_factory=list)
```

## Exceptions

```python
class ClaudeSDKError(Exception)
class CommandError(ClaudeSDKError)
class CommandTimeoutError(CommandError)
class CommandExecutionError(CommandError)
class SessionError(ClaudeSDKError)
class WorkspaceError(ClaudeSDKError)
class AuthenticationError(ClaudeSDKError)
class ConfigurationError(ClaudeSDKError)
```

## Session Context

```python
class SessionContext:
    @property
    def session_id(self) -> str
    
    async def query(
        self,
        prompt: str,
        **kwargs
    ) -> ClaudeResponse
    
    async def stream_query(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncIterator[str]
```

## Workspace Context

```python
class WorkspaceContext:
    @property
    def workspace_id(self) -> str
    
    @property
    def path(self) -> str
    
    async def add_files(self, files: List[str]) -> None
    async def list_files(self) -> List[str]
    async def cleanup(self) -> None
```

## Command Builder

```python
class CommandBuilder:
    def __init__(self, base_command: str = "claude", config: Optional[ClaudeConfig] = None)
    
    def add_prompt(self, prompt: str) -> CommandBuilder
    def set_session_id(self, session_id: str) -> CommandBuilder
    def set_output_format(self, format: str) -> CommandBuilder
    def set_workspace_id(self, workspace_id: str) -> CommandBuilder
    def add_file(self, file_path: str) -> CommandBuilder
    def add_files(self, file_paths: List[str]) -> CommandBuilder
    def set_timeout(self, timeout: float) -> CommandBuilder
    def add_raw_args(self, args: List[str]) -> CommandBuilder
    def build(self) -> List[str]  # Adds --dangerously-skip-permissions by default unless safe_mode=True
```

## Convenience Functions

```python
async def query(prompt: str, **kwargs) -> ClaudeResponse
async def stream_query(prompt: str, **kwargs) -> AsyncIterator[str]
```

## Usage Examples

### Basic Usage
```python
import asyncio
from claude_sdk import ClaudeClient

async with ClaudeClient() as client:
    response = await client.query("Hello, Claude!")
    print(response.content)
```

### With Configuration
```python
from claude_sdk import ClaudeClient, ClaudeConfig

config = ClaudeConfig(
    debug_mode=True,
    max_retries=5,
    default_timeout=60.0,
)

async with ClaudeClient(config=config) as client:
    response = await client.query("Complex task")
```

### Session Management
```python
async with ClaudeClient() as client:
    async with client.create_session() as session:
        resp1 = await session.query("First message")
        resp2 = await session.query("Follow-up")
```

### Workspace Operations
```python
async with ClaudeClient() as client:
    async with client.create_workspace(copy_files=["main.py"]) as workspace:
        response = await client.query(
            "Analyze this code",
            workspace_id=workspace.workspace_id,
            files=["main.py"]
        )
```

### Streaming
```python
async with ClaudeClient() as client:
    async for chunk in client.stream_query("Tell me a story"):
        print(chunk, end="", flush=True)
```

### Parallel Execution
```python
async with ClaudeClient() as client:
    tasks = [
        client.query(f"Task {i}")
        for i in range(5)
    ]
    responses = await asyncio.gather(*tasks)
```

## Environment Variables

The SDK automatically handles these environment variables:

- `ANTHROPIC_API_KEY` - **Automatically removed** to avoid credit balance issues
- `CLAUDE_CLI_PATH` - Path to Claude CLI executable
- `CLAUDE_DEFAULT_TIMEOUT` - Default timeout in seconds
- `CLAUDE_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `CLAUDE_DEBUG` - Enable debug mode (true/false)
- `CLAUDE_WORKSPACE_BASE_PATH` - Base path for workspaces
- `CLAUDE_MAX_RETRIES` - Maximum retry attempts
- `CLAUDE_RETRY_DELAY` - Base retry delay in seconds

## Package Structure

```
claude_sdk/
├── __init__.py          # Public API exports
├── client.py            # Main ClaudeClient
├── core/
│   ├── config.py        # Configuration management
│   ├── subprocess_wrapper.py  # Async subprocess handling
│   ├── types.py         # Type definitions
│   └── workspace.py     # Workspace management
├── exceptions.py        # Exception hierarchy
└── utils/
    ├── logging.py       # Logging utilities
    └── retry.py         # Retry mechanisms
```