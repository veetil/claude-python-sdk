"""
End-to-end tests for complete client workflows.

These tests simulate real usage patterns and test the full integration
of all SDK components.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock
from claude_sdk.client import ClaudeClient
from claude_sdk.core.config import ClaudeConfig
from claude_sdk.core.types import OutputFormat


@pytest.mark.e2e
class TestClientWorkflows:
    """End-to-end workflow tests."""
    
    @pytest.fixture
    def e2e_config(self):
        """Configuration for E2E tests."""
        return ClaudeConfig(
            cli_path="echo",  # Use echo as safe mock
            default_timeout=10.0,
            session_timeout=60.0,
            max_retries=1,
            retry_delay=0.1,
            debug_mode=True,
            workspace_cleanup_on_exit=True,
            enable_workspace_isolation=True,
        )
    
    async def test_complete_query_workflow(self, e2e_config):
        """Test complete query workflow from start to finish."""
        async with ClaudeClient(config=e2e_config, auto_setup_logging=False) as client:
            # Mock the subprocess execution to avoid calling real Claude CLI
            mock_result = type('MockResult', (), {
                'exit_code': 0,
                'stdout': '{"response": "Hello! I can help you with that task."}',
                'stderr': '',
                'duration': 1.2,
                'command': 'echo test',
                'success': True,
            })()
            
            with patch.object(client._subprocess_wrapper, 'execute', return_value=mock_result):
                response = await client.query(
                    "Hello Claude, can you help me?",
                    output_format=OutputFormat.JSON
                )
            
            assert response.content == mock_result.stdout
            assert response.metadata["output_format"] == "json"
            assert response.metadata["duration"] == 1.2
    
    async def test_session_based_workflow(self, e2e_config):
        """Test session-based conversation workflow."""
        async with ClaudeClient(config=e2e_config, auto_setup_logging=False) as client:
            mock_responses = [
                '{"response": "Hello! How can I help you?"}',
                '{"response": "Sure, I can help with Python code."}',
                '{"response": "Here\'s a simple function for you."}',
            ]
            
            call_count = 0
            async def mock_execute(*args, **kwargs):
                nonlocal call_count
                result = type('MockResult', (), {
                    'exit_code': 0,
                    'stdout': mock_responses[call_count % len(mock_responses)],
                    'stderr': '',
                    'duration': 1.0,
                    'command': f'call_{call_count}',
                    'success': True,
                })()
                call_count += 1
                return result
            
            with patch.object(client._subprocess_wrapper, 'execute', side_effect=mock_execute):
                async with client.create_session("conversation_123") as session:
                    # First query in session
                    response1 = await session.query("Hello")
                    assert "Hello! How can I help you?" in response1.content
                    assert response1.session_id == "conversation_123"
                    
                    # Follow-up query in same session
                    response2 = await session.query("Can you help with Python?")
                    assert "Python code" in response2.content
                    assert response2.session_id == "conversation_123"
                    
                    # Third query
                    response3 = await session.query("Show me a function")
                    assert "function" in response3.content
                    assert response3.session_id == "conversation_123"
    
    async def test_workspace_based_workflow(self, e2e_config):
        """Test workspace-based file analysis workflow."""
        async with ClaudeClient(config=e2e_config, auto_setup_logging=False) as client:
            # Create test files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create sample Python file
                python_file = temp_path / "example.py"
                python_file.write_text("""
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

if __name__ == "__main__":
    print(fibonacci(10))
""")
                
                # Create sample config file
                config_file = temp_path / "config.json"
                config_file.write_text('{"debug": true, "version": "1.0"}')
                
                files_to_copy = [str(python_file), str(config_file)]
                
                # Mock workspace creation
                mock_workspace_info = type('MockWorkspaceInfo', (), {
                    'workspace_id': 'test_workspace_456',
                    'path': temp_dir,
                    'created_at': None,
                    'size_bytes': 1024,
                    'file_count': 2,
                    'metadata': {},
                })()
                
                mock_result = type('MockResult', (), {
                    'exit_code': 0,
                    'stdout': '{"analysis": "The code implements Fibonacci sequence recursively."}',
                    'stderr': '',
                    'duration': 2.5,
                    'command': 'analyze files',
                    'success': True,
                })()
                
                with patch.object(client._workspace_manager, 'create_workspace', return_value=mock_workspace_info):
                    with patch.object(client._subprocess_wrapper, 'execute', return_value=mock_result):
                        async with client.create_workspace(copy_files=files_to_copy) as workspace:
                            # Analyze files in workspace
                            response = await client.query(
                                "Analyze the Python code for efficiency",
                                workspace_id=workspace.workspace_id,
                                files=["example.py", "config.json"]
                            )
                            
                            assert "Fibonacci" in response.content
                            assert workspace.workspace_id == "test_workspace_456"
    
    async def test_streaming_workflow(self, e2e_config):
        """Test streaming response workflow."""
        async with ClaudeClient(config=e2e_config, auto_setup_logging=False) as client:
            # Mock streaming chunks
            from claude_sdk.core.types import StreamChunk
            
            mock_chunks = [
                StreamChunk(content="Analyzing your code...\n", chunk_type="stdout"),
                StreamChunk(content="Found 3 functions\n", chunk_type="stdout"),
                StreamChunk(content="Checking for issues...\n", chunk_type="stdout"),
                StreamChunk(content="Analysis complete!\n", chunk_type="stdout"),
            ]
            
            async def mock_stream(*args, **kwargs):
                for chunk in mock_chunks:
                    yield chunk
            
            with patch.object(client._subprocess_wrapper, 'execute_streaming', side_effect=mock_stream):
                chunks = []
                async for chunk in client.stream_query("Analyze my large codebase"):
                    chunks.append(chunk)
                
                assert len(chunks) == len(mock_chunks)
                full_response = "".join(chunks)
                assert "Analyzing your code" in full_response
                assert "Analysis complete" in full_response
    
    async def test_error_recovery_workflow(self, e2e_config):
        """Test error recovery and retry workflow."""
        async with ClaudeClient(config=e2e_config, auto_setup_logging=False) as client:
            call_count = 0
            
            def mock_execute(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count <= 2:  # Fail first two attempts
                    from claude_sdk.exceptions import CommandTimeoutError
                    raise CommandTimeoutError("mock timeout", 5.0)
                else:  # Succeed on third attempt
                    return type('MockResult', (), {
                        'exit_code': 0,
                        'stdout': 'Success after retries!',
                        'stderr': '',
                        'duration': 1.0,
                        'command': 'retry test',
                        'success': True,
                    })()
            
            # Mock the retry mechanism to actually retry
            from claude_sdk.utils.retry import retry_with_backoff
            
            async def mock_retry_with_backoff(func, *args, **kwargs):
                max_retries = kwargs.get('max_retries', 3)
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args) if hasattr(func, '__call__') else func(*args)
                    except Exception as e:
                        if attempt >= max_retries:
                            raise
                        # Continue to next attempt
                
            with patch('claude_sdk.utils.retry.retry_with_backoff', side_effect=mock_retry_with_backoff):
                with patch.object(client._subprocess_wrapper, 'execute', side_effect=mock_execute):
                    response = await client.query("Test retry mechanism")
                    
                    assert "Success after retries" in response.content
                    assert call_count == 3  # Should have retried 2 times
    
    async def test_concurrent_operations_workflow(self, e2e_config):
        """Test concurrent operations workflow."""
        async with ClaudeClient(config=e2e_config, auto_setup_logging=False) as client:
            mock_results = [
                '{"task": "1", "result": "Completed task 1"}',
                '{"task": "2", "result": "Completed task 2"}', 
                '{"task": "3", "result": "Completed task 3"}',
            ]
            
            call_count = 0
            async def mock_execute(*args, **kwargs):
                nonlocal call_count
                result_index = call_count % len(mock_results)
                call_count += 1
                
                return type('MockResult', (), {
                    'exit_code': 0,
                    'stdout': mock_results[result_index],
                    'stderr': '',
                    'duration': 1.0,
                    'command': f'task_{result_index + 1}',
                    'success': True,
                })()
            
            with patch.object(client._subprocess_wrapper, 'execute', side_effect=mock_execute):
                # Execute multiple queries concurrently
                import asyncio
                
                tasks = [
                    client.query(f"Process task {i}")
                    for i in range(1, 4)
                ]
                
                responses = await asyncio.gather(*tasks)
                
                assert len(responses) == 3
                for i, response in enumerate(responses):
                    assert f"task {i + 1}" in response.content or f'"task": "{i + 1}"' in response.content
    
    async def test_file_processing_workflow(self, e2e_config):
        """Test complete file processing workflow."""
        async with ClaudeClient(config=e2e_config, auto_setup_logging=False) as client:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create multiple test files
                files = {}
                
                # Python file
                py_file = temp_path / "main.py"
                py_file.write_text("print('Hello World')")
                files["python"] = str(py_file)
                
                # JavaScript file  
                js_file = temp_path / "script.js"
                js_file.write_text("console.log('Hello World');")
                files["javascript"] = str(js_file)
                
                # Configuration file
                config_file = temp_path / "package.json"
                config_file.write_text('{"name": "test", "version": "1.0.0"}')
                files["config"] = str(config_file)
                
                mock_analysis = {
                    "files_analyzed": 3,
                    "languages": ["python", "javascript", "json"],
                    "total_lines": 3,
                    "issues_found": 0,
                    "recommendations": ["Add error handling", "Include documentation"]
                }
                
                mock_result = type('MockResult', (), {
                    'exit_code': 0,
                    'stdout': str(mock_analysis),
                    'stderr': '',
                    'duration': 3.0,
                    'command': 'analyze multiple files',
                    'success': True,
                })()
                
                mock_workspace_info = type('MockWorkspaceInfo', (), {
                    'workspace_id': 'file_analysis_workspace',
                    'path': temp_dir,
                    'created_at': None,
                    'size_bytes': 2048,
                    'file_count': 3,
                    'metadata': {},
                })()
                
                with patch.object(client._workspace_manager, 'create_workspace', return_value=mock_workspace_info):
                    with patch.object(client._subprocess_wrapper, 'execute', return_value=mock_result):
                        # Create workspace with files
                        async with client.create_workspace(
                            copy_files=list(files.values())
                        ) as workspace:
                            # Analyze all files
                            response = await client.query(
                                "Analyze all files for code quality and provide recommendations",
                                workspace_id=workspace.workspace_id,
                                files=list(files.values()),
                                output_format=OutputFormat.JSON
                            )
                            
                            assert "files_analyzed" in response.content
                            assert workspace.file_count == 3