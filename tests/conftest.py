"""
Pytest configuration and shared fixtures for the Claude Python SDK tests.
"""

import asyncio
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from claude_sdk.core.config import ClaudeConfig
from claude_sdk.core.types import CommandResult, ClaudeResponse, WorkspaceInfo, SessionInfo, SessionStatus
from claude_sdk.core.subprocess_wrapper import AsyncSubprocessWrapper
from claude_sdk.core.workspace import WorkspaceManager
from claude_sdk.client import ClaudeClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return ClaudeConfig(
        cli_path="mock-claude",
        default_timeout=5.0,
        session_timeout=30.0,
        max_concurrent_sessions=2,
        max_retries=1,
        retry_delay=0.1,
        debug_mode=True,
        workspace_cleanup_on_exit=True,
        enable_workspace_isolation=True,
    )


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory(prefix="claude_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_subprocess_result():
    """Create a mock subprocess result."""
    return CommandResult(
        exit_code=0,
        stdout="Mock output from Claude CLI",
        stderr="",
        duration=1.5,
        command="mock-claude -p 'test prompt'",
    )


@pytest.fixture
def mock_claude_response():
    """Create a mock Claude response."""
    return ClaudeResponse(
        content="This is a mock response from Claude",
        session_id="test_session_123",
        metadata={
            "exit_code": 0,
            "duration": 1.5,
            "command": "mock-claude -p 'test prompt'",
            "output_format": "text",
        }
    )


@pytest.fixture
def mock_workspace_info(temp_workspace):
    """Create a mock workspace info."""
    return WorkspaceInfo(
        workspace_id="test_workspace_123",
        path=str(temp_workspace),
        created_at=asyncio.get_event_loop().time(),
        size_bytes=1024,
        file_count=3,
        metadata={"test": True}
    )


@pytest.fixture
def mock_session_info():
    """Create a mock session info."""
    return SessionInfo(
        session_id="test_session_123",
        status=SessionStatus.ACTIVE,
        created_at=asyncio.get_event_loop().time(),
        last_activity=asyncio.get_event_loop().time(),
        workspace_path=None,
        metadata={"test": True}
    )


@pytest.fixture
def mock_subprocess_wrapper(mock_config, mock_subprocess_result):
    """Create a mock subprocess wrapper."""
    wrapper = Mock(spec=AsyncSubprocessWrapper)
    wrapper.config = mock_config
    wrapper.execute = AsyncMock(return_value=mock_subprocess_result)
    wrapper.execute_streaming = AsyncMock()
    wrapper.cleanup = AsyncMock()
    return wrapper


@pytest.fixture
def mock_workspace_manager(mock_config, mock_workspace_info):
    """Create a mock workspace manager."""
    manager = Mock(spec=WorkspaceManager)
    manager.config = mock_config
    manager.create_workspace = AsyncMock(return_value=mock_workspace_info)
    manager.cleanup_workspace = AsyncMock()
    manager.list_workspaces = AsyncMock(return_value=[mock_workspace_info])
    manager.get_workspace = AsyncMock(return_value=mock_workspace_info)
    manager.cleanup_all_workspaces = AsyncMock()
    return manager


@pytest.fixture
async def claude_client(mock_config):
    """Create a Claude client for testing."""
    client = ClaudeClient(config=mock_config, auto_setup_logging=False)
    yield client
    await client.close()


@pytest.fixture
def mock_process():
    """Create a mock subprocess process."""
    process = Mock()
    process.returncode = 0
    process.communicate = AsyncMock(return_value=(b"test output", b""))
    process.wait = AsyncMock(return_value=0)
    process.terminate = Mock()
    process.kill = Mock()
    process.stdout = Mock()
    process.stderr = Mock()
    return process


@pytest.fixture
def sample_files(temp_workspace):
    """Create sample files for testing."""
    files = {}
    
    # Create a simple Python file
    python_file = temp_workspace / "test_script.py"
    python_file.write_text("""
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
""")
    files["python"] = str(python_file)
    
    # Create a text file
    text_file = temp_workspace / "readme.txt"
    text_file.write_text("This is a test file for Claude SDK testing.")
    files["text"] = str(text_file)
    
    # Create a JSON file
    json_file = temp_workspace / "config.json"
    json_file.write_text('{"test": true, "value": 42}')
    files["json"] = str(json_file)
    
    return files


@pytest.fixture
def mock_stream_chunks():
    """Create mock stream chunks for testing."""
    from claude_sdk.core.types import StreamChunk
    
    chunks = [
        StreamChunk(content="First chunk of output\n", chunk_type="stdout"),
        StreamChunk(content="Second chunk of output\n", chunk_type="stdout"),
        StreamChunk(content="Warning message\n", chunk_type="stderr"),
        StreamChunk(content="Final chunk\n", chunk_type="stdout"),
    ]
    return chunks


@pytest.fixture
def mock_env_vars():
    """Create mock environment variables."""
    return {
        "CLAUDE_API_KEY": "test_api_key_123",
        "CLAUDE_DEBUG": "1",
        "TEST_VAR": "test_value",
    }


# Markers for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.slow = pytest.mark.slow


# Test utilities
class AsyncContextManagerMock:
    """Mock async context manager for testing."""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
        self.entered = False
        self.exited = False
    
    async def __aenter__(self):
        self.entered = True
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exited = True
        return False


def create_mock_subprocess():
    """Helper to create a mock subprocess with all necessary attributes."""
    process = Mock()
    process.returncode = 0
    process.pid = 12345
    
    # Mock async methods
    process.communicate = AsyncMock(return_value=(b"test output", b""))
    process.wait = AsyncMock(return_value=0)
    
    # Mock sync methods
    process.poll = Mock(return_value=0)
    process.terminate = Mock()
    process.kill = Mock()
    
    # Mock streams
    process.stdout = Mock()
    process.stdout.read = AsyncMock(return_value=b"test output")
    process.stdout.readline = AsyncMock(side_effect=[b"line 1\n", b"line 2\n", b""])
    
    process.stderr = Mock()
    process.stderr.read = AsyncMock(return_value=b"")
    process.stderr.readline = AsyncMock(return_value=b"")
    
    return process


# Custom pytest assertions
def assert_command_result(result: CommandResult, expected_exit_code: int = 0):
    """Assert that a CommandResult has expected properties."""
    assert isinstance(result, CommandResult)
    assert result.exit_code == expected_exit_code
    assert result.success == (expected_exit_code == 0)
    assert isinstance(result.stdout, str)
    assert isinstance(result.stderr, str)
    assert result.duration >= 0
    assert result.command != ""


def assert_claude_response(response: ClaudeResponse):
    """Assert that a ClaudeResponse has expected properties."""
    assert isinstance(response, ClaudeResponse)
    assert isinstance(response.content, str)
    assert response.content != ""
    assert response.timestamp is not None
    assert isinstance(response.metadata, dict)


def assert_workspace_info(workspace_info: WorkspaceInfo):
    """Assert that a WorkspaceInfo has expected properties."""
    assert isinstance(workspace_info, WorkspaceInfo)
    assert workspace_info.workspace_id != ""
    assert workspace_info.path != ""
    assert Path(workspace_info.path).exists()
    assert workspace_info.created_at is not None
    assert workspace_info.size_bytes >= 0
    assert workspace_info.file_count >= 0