"""
Unit tests for the ClaudeClient.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from claude_sdk.client import ClaudeClient, SessionContext, query, stream_query
from claude_sdk.core.types import ClaudeResponse, OutputFormat, SessionStatus
from claude_sdk.exceptions import ClaudeSDKError


@pytest.mark.unit
class TestClaudeClient:
    """Test cases for ClaudeClient."""
    
    @pytest.fixture
    def client(self, mock_config):
        """Create client for testing."""
        return ClaudeClient(config=mock_config, auto_setup_logging=False)
    
    async def test_client_initialization(self, mock_config):
        """Test client initialization."""
        client = ClaudeClient(config=mock_config, auto_setup_logging=False)
        
        assert client.config == mock_config
        assert not client._closed
        assert len(client._sessions) == 0
        
        await client.close()
    
    async def test_query_success(self, client, mock_subprocess_result):
        """Test successful query execution."""
        client._subprocess_wrapper.execute = AsyncMock(return_value=mock_subprocess_result)
        
        with patch('claude_sdk.utils.retry.retry_with_backoff') as mock_retry:
            mock_retry.return_value = mock_subprocess_result
            
            response = await client.query("Test prompt")
        
        assert isinstance(response, ClaudeResponse)
        assert response.content == mock_subprocess_result.stdout
        assert response.metadata["exit_code"] == 0
        assert response.metadata["output_format"] == "text"
    
    async def test_query_with_session_id(self, client, mock_subprocess_result):
        """Test query with session ID."""
        client._subprocess_wrapper.execute = AsyncMock(return_value=mock_subprocess_result)
        
        with patch('claude_sdk.utils.retry.retry_with_backoff') as mock_retry:
            mock_retry.return_value = mock_subprocess_result
            
            response = await client.query("Test prompt", session_id="test_session")
        
        assert response.session_id == "test_session"
    
    async def test_query_with_files(self, client, mock_subprocess_result, sample_files):
        """Test query with files."""
        client._subprocess_wrapper.execute = AsyncMock(return_value=mock_subprocess_result)
        
        with patch('claude_sdk.utils.retry.retry_with_backoff') as mock_retry:
            mock_retry.return_value = mock_subprocess_result
            
            response = await client.query(
                "Analyze these files",
                files=[sample_files["python"], sample_files["text"]]
            )
        
        assert isinstance(response, ClaudeResponse)
    
    async def test_query_with_output_format(self, client, mock_subprocess_result):
        """Test query with JSON output format."""
        client._subprocess_wrapper.execute = AsyncMock(return_value=mock_subprocess_result)
        
        with patch('claude_sdk.utils.retry.retry_with_backoff') as mock_retry:
            mock_retry.return_value = mock_subprocess_result
            
            response = await client.query(
                "Test prompt",
                output_format=OutputFormat.JSON
            )
        
        assert response.metadata["output_format"] == "json"
    
    async def test_stream_query(self, client, mock_stream_chunks):
        """Test streaming query execution."""
        async def mock_stream(*args, **kwargs):
            for chunk in mock_stream_chunks:
                yield chunk
        
        client._subprocess_wrapper.execute_streaming = mock_stream
        
        chunks = []
        async for chunk in client.stream_query("Stream test"):
            chunks.append(chunk)
        
        assert len(chunks) == len(mock_stream_chunks)
        assert all(isinstance(chunk, str) for chunk in chunks)
    
    async def test_execute_command(self, client, mock_subprocess_result):
        """Test raw command execution."""
        client._subprocess_wrapper.execute = AsyncMock(return_value=mock_subprocess_result)
        
        result = await client.execute_command("echo test")
        
        assert result == mock_subprocess_result
        client._subprocess_wrapper.execute.assert_called_once()
    
    async def test_create_session_context(self, client):
        """Test session context creation."""
        async with client.create_session("test_session") as session:
            assert isinstance(session, SessionContext)
            assert session.session_id == "test_session"
            assert "test_session" in client._sessions
            
            session_info = client._sessions["test_session"]
            assert session_info.status == SessionStatus.ACTIVE
        
        # Session should be removed after context exit
        assert "test_session" not in client._sessions
    
    async def test_create_workspace_context(self, client, mock_workspace_info):
        """Test workspace context creation."""
        client._workspace_manager.create_workspace = AsyncMock(return_value=mock_workspace_info)
        
        async with client.create_workspace("test_workspace") as workspace:
            assert workspace.workspace_id == "test_workspace"
            assert workspace.path.exists()
        
        client._workspace_manager.create_workspace.assert_called_once()
    
    async def test_list_sessions(self, client, mock_session_info):
        """Test listing sessions."""
        client._sessions["test_session"] = mock_session_info
        
        sessions = await client.list_sessions()
        
        assert len(sessions) == 1
        assert sessions[0] == mock_session_info
    
    async def test_list_workspaces(self, client, mock_workspace_info):
        """Test listing workspaces."""
        client._workspace_manager.list_workspaces = AsyncMock(return_value=[mock_workspace_info])
        
        workspaces = await client.list_workspaces()
        
        assert len(workspaces) == 1
        assert workspaces[0] == mock_workspace_info
    
    async def test_command_builder(self, client):
        """Test command builder creation."""
        builder = client.command_builder()
        
        assert builder is not None
        command = builder.add_prompt("test").build()
        assert "claude" in command
        assert "-p" in command
        assert "test" in command
    
    async def test_client_closed_error(self, client):
        """Test operations on closed client."""
        await client.close()
        
        with pytest.raises(ClaudeSDKError, match="Client is closed"):
            await client.query("test")
    
    async def test_client_context_manager(self, mock_config):
        """Test client as async context manager."""
        async with ClaudeClient(config=mock_config, auto_setup_logging=False) as client:
            assert not client._closed
        
        assert client._closed
    
    async def test_client_close_cleanup(self, client):
        """Test client cleanup on close."""
        client._subprocess_wrapper.cleanup = AsyncMock()
        client._workspace_manager.cleanup_all_workspaces = AsyncMock()
        
        await client.close()
        
        assert client._closed
        client._subprocess_wrapper.cleanup.assert_called_once()
        client._workspace_manager.cleanup_all_workspaces.assert_called_once()


@pytest.mark.unit
class TestSessionContext:
    """Test cases for SessionContext."""
    
    @pytest.fixture
    def session_context(self, client, mock_session_info):
        """Create session context for testing."""
        return SessionContext(client, mock_session_info)
    
    async def test_session_query(self, session_context, mock_claude_response):
        """Test query within session context."""
        session_context.client.query = AsyncMock(return_value=mock_claude_response)
        
        response = await session_context.query("test prompt")
        
        assert response == mock_claude_response
        session_context.client.query.assert_called_once_with(
            "test prompt",
            session_id=session_context.session_id
        )
    
    async def test_session_stream_query(self, session_context, mock_stream_chunks):
        """Test streaming query within session context."""
        async def mock_stream(*args, **kwargs):
            for chunk in mock_stream_chunks:
                yield chunk.content
        
        session_context.client.stream_query = mock_stream
        
        chunks = []
        async for chunk in session_context.stream_query("test prompt"):
            chunks.append(chunk)
        
        assert len(chunks) == len(mock_stream_chunks)
    
    def test_session_id_property(self, session_context):
        """Test session ID property."""
        assert session_context.session_id == session_context.session_info.session_id


@pytest.mark.unit
class TestConvenienceFunctions:
    """Test convenience functions."""
    
    async def test_query_function(self, mock_claude_response):
        """Test query convenience function."""
        with patch('claude_sdk.client.ClaudeClient') as MockClient:
            mock_client = Mock()
            mock_client.query = AsyncMock(return_value=mock_claude_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockClient.return_value = mock_client
            
            response = await query("test prompt")
        
        assert response == mock_claude_response
    
    async def test_stream_query_function(self, mock_stream_chunks):
        """Test stream_query convenience function."""
        async def mock_stream(*args, **kwargs):
            for chunk in mock_stream_chunks:
                yield chunk.content
        
        with patch('claude_sdk.client.ClaudeClient') as MockClient:
            mock_client = Mock()
            mock_client.stream_query = mock_stream
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockClient.return_value = mock_client
            
            chunks = []
            async for chunk in stream_query("test prompt"):
                chunks.append(chunk)
        
        assert len(chunks) == len(mock_stream_chunks)


@pytest.mark.unit
class TestClientIntegration:
    """Integration tests for client components."""
    
    async def test_query_with_workspace(self, client, mock_workspace_info, mock_subprocess_result):
        """Test query execution within a workspace."""
        client._workspace_manager.get_workspace = AsyncMock(return_value=mock_workspace_info)
        client._subprocess_wrapper.execute = AsyncMock(return_value=mock_subprocess_result)
        
        with patch('claude_sdk.utils.retry.retry_with_backoff') as mock_retry:
            mock_retry.return_value = mock_subprocess_result
            
            response = await client.query(
                "test prompt",
                workspace_id="test_workspace"
            )
        
        assert isinstance(response, ClaudeResponse)
        client._workspace_manager.get_workspace.assert_called_once_with("test_workspace")
    
    async def test_error_handling_propagation(self, client):
        """Test that errors are properly propagated."""
        client._subprocess_wrapper.execute = AsyncMock(side_effect=ClaudeSDKError("Test error"))
        
        with patch('claude_sdk.utils.retry.retry_with_backoff') as mock_retry:
            mock_retry.side_effect = ClaudeSDKError("Test error")
            
            with pytest.raises(ClaudeSDKError, match="Test error"):
                await client.query("test prompt")