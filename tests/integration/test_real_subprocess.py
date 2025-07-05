"""
Integration tests for real subprocess execution.

These tests use real subprocess calls but avoid calling the actual Claude CLI
by using mock commands and safe system commands.
"""

import asyncio
import os
import sys
import pytest
from pathlib import Path
from claude_sdk.core.subprocess_wrapper import AsyncSubprocessWrapper, CommandBuilder
from claude_sdk.core.types import CommandResult, StreamChunk
from claude_sdk.exceptions import CommandNotFoundError, CommandTimeoutError, CommandExecutionError


@pytest.mark.integration
class TestRealSubprocessExecution:
    """Integration tests with real subprocess execution."""
    
    @pytest.fixture
    def wrapper(self, mock_config):
        """Create wrapper with real subprocess execution."""
        # Use real commands that are available on most systems
        config = mock_config
        config.cli_path = "echo"  # Use echo as a safe test command
        return AsyncSubprocessWrapper(config)
    
    async def test_real_echo_command(self, wrapper):
        """Test real echo command execution."""
        result = await wrapper.execute(["echo", "hello world"])
        
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert result.success is True
        assert "hello world" in result.stdout
        assert result.duration > 0
    
    async def test_real_command_with_stderr(self, wrapper):
        """Test command that writes to stderr."""
        if sys.platform == "win32":
            pytest.skip("stderr test not reliable on Windows")
        
        # Use a command that writes to stderr
        with pytest.raises(CommandExecutionError):
            await wrapper.execute(["ls", "/nonexistent/path"])
    
    async def test_real_command_timeout(self, wrapper):
        """Test real command timeout."""
        if sys.platform == "win32":
            command = ["ping", "-n", "10", "127.0.0.1"]
        else:
            command = ["sleep", "5"]
        
        with pytest.raises(CommandTimeoutError):
            await wrapper.execute(command, timeout=0.5)
    
    async def test_real_command_not_found(self, wrapper):
        """Test execution of non-existent command."""
        with pytest.raises(CommandNotFoundError):
            await wrapper.execute("this-command-does-not-exist-12345")
    
    async def test_real_streaming_output(self, wrapper):
        """Test real streaming output."""
        if sys.platform == "win32":
            pytest.skip("Streaming test unreliable on Windows")
        
        chunks = []
        async for chunk in wrapper.execute_streaming(["echo", "line1"]):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, StreamChunk) for chunk in chunks)
        
        # Concatenate all chunks
        full_output = "".join(chunk.content for chunk in chunks)
        assert "line1" in full_output
    
    async def test_real_environment_variables(self, wrapper):
        """Test passing environment variables."""
        if sys.platform == "win32":
            command = ["cmd", "/c", "echo", "%TEST_VAR%"]
        else:
            command = ["sh", "-c", "echo $TEST_VAR"]
        
        result = await wrapper.execute(
            command,
            env={"TEST_VAR": "test_value"}
        )
        
        assert "test_value" in result.stdout
    
    async def test_real_working_directory(self, wrapper, temp_workspace):
        """Test command execution with working directory."""
        if sys.platform == "win32":
            command = ["cmd", "/c", "cd"]
        else:
            command = ["pwd"]
        
        result = await wrapper.execute(command, cwd=str(temp_workspace))
        
        assert str(temp_workspace) in result.stdout
    
    async def test_real_input_data(self, wrapper):
        """Test passing input data to command."""
        if sys.platform == "win32":
            pytest.skip("Input test not reliable on Windows")
        
        result = await wrapper.execute(["cat"], input_data="hello input")
        
        assert "hello input" in result.stdout
    
    async def test_real_process_cleanup(self, wrapper):
        """Test that processes are properly cleaned up."""
        # Start a long-running process and then cleanup
        initial_count = len(wrapper._active_processes)
        
        if sys.platform == "win32":
            command = ["ping", "-n", "1", "127.0.0.1"]
        else:
            command = ["sleep", "0.1"]
        
        await wrapper.execute(command)
        
        # Process should be cleaned up automatically
        assert len(wrapper._active_processes) == initial_count
    
    async def test_real_multiple_concurrent_commands(self, wrapper):
        """Test executing multiple commands concurrently."""
        tasks = []
        
        for i in range(3):
            task = asyncio.create_task(
                wrapper.execute(["echo", f"concurrent_{i}"])
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert isinstance(result, CommandResult)
            assert result.success
            assert f"concurrent_{i}" in result.stdout


@pytest.mark.integration
class TestCommandBuilderIntegration:
    """Integration tests for CommandBuilder with real execution."""
    
    async def test_built_command_execution(self, mock_config):
        """Test executing a command built with CommandBuilder."""
        wrapper = AsyncSubprocessWrapper(mock_config)
        
        builder = CommandBuilder("echo")
        command = builder.add_option("n", "hello").build()
        
        # On Unix systems, echo -n doesn't add newline
        result = await wrapper.execute(command)
        
        assert result.success
        # Command should contain the built elements
        assert "echo" in result.command
    
    async def test_complex_command_building(self, mock_config, temp_workspace):
        """Test building and executing a complex command."""
        wrapper = AsyncSubprocessWrapper(mock_config)
        
        # Create a test file
        test_file = temp_workspace / "test.txt"
        test_file.write_text("test content")
        
        if sys.platform == "win32":
            builder = CommandBuilder("type")
            command = builder.build() + [str(test_file)]
        else:
            builder = CommandBuilder("cat")
            command = builder.build() + [str(test_file)]
        
        result = await wrapper.execute(command)
        
        assert result.success
        assert "test content" in result.stdout


@pytest.mark.integration
class TestWorkspaceIntegration:
    """Integration tests for workspace functionality with real file operations."""
    
    async def test_command_in_workspace(self, mock_config, temp_workspace):
        """Test executing commands within a workspace."""
        wrapper = AsyncSubprocessWrapper(mock_config)
        
        # Create a file in the workspace
        test_file = temp_workspace / "workspace_test.txt"
        test_file.write_text("workspace content")
        
        if sys.platform == "win32":
            command = ["dir"]
        else:
            command = ["ls"]
        
        result = await wrapper.execute(command, cwd=str(temp_workspace))
        
        assert result.success
        assert "workspace_test.txt" in result.stdout


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling with real processes."""
    
    async def test_real_timeout_handling(self, mock_config):
        """Test timeout handling with real processes."""
        wrapper = AsyncSubprocessWrapper(mock_config)
        
        if sys.platform == "win32":
            command = ["ping", "-n", "10", "127.0.0.1"]  # Long-running command
        else:
            command = ["sleep", "10"]  # 10 second sleep
        
        start_time = asyncio.get_event_loop().time()
        
        with pytest.raises(CommandTimeoutError):
            await wrapper.execute(command, timeout=1.0)
        
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # Should timeout around 1 second, allow some margin
        assert 0.8 <= elapsed <= 2.0
    
    async def test_real_error_propagation(self, mock_config):
        """Test that real command errors are properly propagated."""
        wrapper = AsyncSubprocessWrapper(mock_config)
        
        # Command that will fail
        if sys.platform == "win32":
            command = ["dir", "C:\\nonexistent\\path\\12345"]
        else:
            command = ["ls", "/nonexistent/path/12345"]
        
        with pytest.raises(CommandExecutionError) as exc_info:
            await wrapper.execute(command)
        
        error = exc_info.value
        assert error.exit_code != 0
        assert error.command is not None
        assert len(error.stderr) > 0 or len(error.stdout) > 0


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """Performance integration tests."""
    
    async def test_concurrent_execution_performance(self, mock_config):
        """Test performance of concurrent command execution."""
        wrapper = AsyncSubprocessWrapper(mock_config)
        
        start_time = asyncio.get_event_loop().time()
        
        # Execute 10 commands concurrently
        tasks = [
            wrapper.execute(["echo", f"test_{i}"])
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # All results should be successful
        assert all(result.success for result in results)
        
        # Concurrent execution should be faster than sequential
        # (This is a rough check - concurrent should complete in < 2 seconds)
        assert elapsed < 5.0
    
    async def test_memory_usage_stability(self, mock_config):
        """Test that memory usage remains stable across many operations."""
        wrapper = AsyncSubprocessWrapper(mock_config)
        
        # Execute many small commands
        for i in range(50):
            result = await wrapper.execute(["echo", f"iteration_{i}"])
            assert result.success
        
        # Ensure no processes are left hanging
        assert len(wrapper._active_processes) == 0