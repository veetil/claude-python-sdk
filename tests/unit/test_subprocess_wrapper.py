"""
Unit tests for the AsyncSubprocessWrapper.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from claude_sdk.core.subprocess_wrapper import AsyncSubprocessWrapper, CommandBuilder
from claude_sdk.core.types import CommandResult, StreamChunk
from claude_sdk.exceptions import (
    CommandNotFoundError,
    CommandTimeoutError,
    CommandExecutionError,
    CommandError,
)


@pytest.mark.unit
class TestAsyncSubprocessWrapper:
    """Test cases for AsyncSubprocessWrapper."""
    
    @pytest.fixture
    def wrapper(self, mock_config):
        """Create subprocess wrapper for testing."""
        return AsyncSubprocessWrapper(mock_config)
    
    async def test_execute_success(self, wrapper, mock_process):
        """Test successful command execution."""
        mock_process.communicate.return_value = (b"success output", b"")
        mock_process.returncode = 0
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await wrapper.execute("echo test")
        
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert result.stdout == "success output"
        assert result.stderr == ""
        assert result.success is True
        assert result.duration > 0
        assert "echo" in result.command
    
    async def test_execute_command_failure(self, wrapper, mock_process):
        """Test command execution with non-zero exit code."""
        mock_process.communicate.return_value = (b"", b"error message")
        mock_process.returncode = 1
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with pytest.raises(CommandExecutionError) as exc_info:
                await wrapper.execute("false")
        
        error = exc_info.value
        assert error.exit_code == 1
        assert error.stderr == "error message"
        assert "false" in error.command
    
    async def test_execute_command_not_found(self, wrapper):
        """Test execution of non-existent command."""
        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError()):
            with pytest.raises(CommandNotFoundError):
                await wrapper.execute("nonexistent-command")
    
    async def test_execute_timeout(self, wrapper, mock_process):
        """Test command execution timeout."""
        mock_process.communicate.side_effect = asyncio.TimeoutError()
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch.object(wrapper, '_terminate_process') as mock_terminate:
                with pytest.raises(CommandTimeoutError) as exc_info:
                    await wrapper.execute("sleep 10", timeout=0.1)
        
        error = exc_info.value
        assert error.timeout == 0.1
        assert "sleep" in error.command
        mock_terminate.assert_called_once_with(mock_process)
    
    async def test_execute_with_input(self, wrapper, mock_process):
        """Test command execution with input data."""
        mock_process.communicate.return_value = (b"processed input", b"")
        mock_process.returncode = 0
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            await wrapper.execute("cat", input_data="test input")
        
        # Verify input was passed to communicate
        mock_process.communicate.assert_called_once_with(b"test input")
    
    async def test_execute_with_environment(self, wrapper, mock_process):
        """Test command execution with custom environment."""
        mock_process.communicate.return_value = (b"output", b"")
        mock_process.returncode = 0
        
        custom_env = {"CUSTOM_VAR": "custom_value"}
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            await wrapper.execute("env", env=custom_env)
        
        # Verify environment was merged
        call_kwargs = mock_exec.call_args[1]
        assert "CUSTOM_VAR" in call_kwargs["env"]
        assert call_kwargs["env"]["CUSTOM_VAR"] == "custom_value"
    
    async def test_execute_with_working_directory(self, wrapper, mock_process, temp_workspace):
        """Test command execution with custom working directory."""
        mock_process.communicate.return_value = (b"output", b"")
        mock_process.returncode = 0
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            await wrapper.execute("pwd", cwd=str(temp_workspace))
        
        # Verify working directory was set
        call_kwargs = mock_exec.call_args[1]
        assert call_kwargs["cwd"] == str(temp_workspace)
    
    async def test_execute_streaming_success(self, wrapper, mock_process):
        """Test successful streaming command execution."""
        # Mock stream reading
        mock_process.stdout.read.side_effect = [b"chunk1", b"chunk2", b""]
        mock_process.stderr.read.side_effect = [b""]
        mock_process.returncode = 0
        mock_process.wait.return_value = 0
        
        chunks = []
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            async for chunk in wrapper.execute_streaming("echo test"):
                chunks.append(chunk)
        
        assert len(chunks) >= 1
        assert all(isinstance(chunk, StreamChunk) for chunk in chunks)
    
    async def test_command_validation_allowed(self, wrapper):
        """Test command validation with allowed commands."""
        wrapper.config.allowed_commands = ["echo", "cat"]
        
        # Should not raise for allowed command
        wrapper._validate_command("echo")
        wrapper._validate_command("cat")
    
    async def test_command_validation_disallowed(self, wrapper):
        """Test command validation with disallowed commands."""
        wrapper.config.allowed_commands = ["echo"]
        
        # Should raise for disallowed command
        with pytest.raises(CommandError):
            wrapper._validate_command("rm")
    
    async def test_cleanup(self, wrapper):
        """Test cleanup of active processes."""
        # Mock active processes
        mock_proc1 = Mock()
        mock_proc2 = Mock()
        
        wrapper._active_processes = {
            "proc1": mock_proc1,
            "proc2": mock_proc2,
        }
        
        with patch.object(wrapper, '_terminate_process') as mock_terminate:
            await wrapper.cleanup()
        
        assert len(wrapper._active_processes) == 0
        assert mock_terminate.call_count == 2
    
    async def test_terminate_process_graceful(self, wrapper):
        """Test graceful process termination."""
        mock_process = Mock()
        mock_process.wait.return_value = asyncio.Future()
        mock_process.wait.return_value.set_result(0)
        
        with patch('asyncio.wait_for', return_value=0):
            await wrapper._terminate_process(mock_process)
        
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_not_called()
    
    async def test_terminate_process_force_kill(self, wrapper):
        """Test forced process termination."""
        mock_process = Mock()
        mock_process.wait.return_value = asyncio.Future()
        mock_process.wait.return_value.set_result(0)
        
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
            await wrapper._terminate_process(mock_process)
        
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()


@pytest.mark.unit
class TestCommandBuilder:
    """Test cases for CommandBuilder."""
    
    def test_basic_command_building(self):
        """Test basic command construction."""
        builder = CommandBuilder("test-cli")
        command = builder.build()
        
        assert command == ["test-cli"]
    
    def test_add_prompt(self):
        """Test adding prompt to command."""
        builder = CommandBuilder("claude")
        command = builder.add_prompt("Hello Claude").build()
        
        assert "-p" in command
        assert "Hello Claude" in command
    
    def test_add_file(self):
        """Test adding file to command."""
        builder = CommandBuilder("claude")
        command = builder.add_file("test.py").build()
        
        assert "--file" in command
        assert "test.py" in command
    
    def test_set_output_format(self):
        """Test setting output format."""
        builder = CommandBuilder("claude")
        command = builder.set_output_format("json").build()
        
        assert "--output-format" in command
        assert "json" in command
    
    def test_add_flag(self):
        """Test adding flags."""
        builder = CommandBuilder("claude")
        command = builder.add_flag("verbose").build()
        
        assert "--verbose" in command
    
    def test_add_option(self):
        """Test adding options."""
        builder = CommandBuilder("claude")
        command = builder.add_option("timeout", "30").build()
        
        assert "--timeout" in command
        assert "30" in command
    
    def test_complex_command(self):
        """Test building a complex command."""
        builder = CommandBuilder("claude")
        command = (builder
                  .add_prompt("Analyze this code")
                  .add_file("main.py")
                  .add_file("utils.py")
                  .set_output_format("json")
                  .add_flag("verbose")
                  .add_option("timeout", "60")
                  .build())
        
        assert "claude" in command
        assert "-p" in command
        assert "Analyze this code" in command
        assert "--file" in command
        assert "main.py" in command
        assert "utils.py" in command
        assert "--output-format" in command
        assert "json" in command
        assert "--verbose" in command
        assert "--timeout" in command
        assert "60" in command
    
    def test_string_representation(self):
        """Test string representation of command."""
        builder = CommandBuilder("claude")
        builder.add_prompt("test")
        
        cmd_str = str(builder)
        assert "claude" in cmd_str
        assert "-p" in cmd_str
        assert "test" in cmd_str


@pytest.mark.unit
class TestConvenienceFunctions:
    """Test convenience functions."""
    
    async def test_execute_command_function(self, mock_config):
        """Test execute_command convenience function."""
        from claude_sdk.core.subprocess_wrapper import execute_command
        
        mock_result = CommandResult(
            exit_code=0,
            stdout="test output",
            stderr="",
            duration=1.0,
            command="echo test"
        )
        
        with patch('claude_sdk.core.subprocess_wrapper.AsyncSubprocessWrapper') as MockWrapper:
            mock_wrapper = Mock()
            mock_wrapper.execute = AsyncMock(return_value=mock_result)
            mock_wrapper.managed_execution = AsyncMock()
            mock_wrapper.managed_execution.return_value.__aenter__ = AsyncMock(return_value=mock_wrapper)
            mock_wrapper.managed_execution.return_value.__aexit__ = AsyncMock()
            MockWrapper.return_value = mock_wrapper
            
            result = await execute_command("echo test")
        
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
    
    async def test_stream_command_function(self, mock_config, mock_stream_chunks):
        """Test stream_command convenience function."""
        from claude_sdk.core.subprocess_wrapper import stream_command
        
        async def mock_stream(*args, **kwargs):
            for chunk in mock_stream_chunks:
                yield chunk
        
        with patch('claude_sdk.core.subprocess_wrapper.AsyncSubprocessWrapper') as MockWrapper:
            mock_wrapper = Mock()
            mock_wrapper.execute_streaming = mock_stream
            mock_wrapper.managed_execution = AsyncMock()
            mock_wrapper.managed_execution.return_value.__aenter__ = AsyncMock(return_value=mock_wrapper)
            mock_wrapper.managed_execution.return_value.__aexit__ = AsyncMock()
            MockWrapper.return_value = mock_wrapper
            
            chunks = []
            async for chunk in stream_command("echo test"):
                chunks.append(chunk)
        
        assert len(chunks) == len(mock_stream_chunks)
        assert all(isinstance(chunk, StreamChunk) for chunk in chunks)