"""
Async subprocess wrapper for Claude CLI with streaming support.

This module provides the core subprocess execution functionality with
async/await support, streaming output, timeout handling, and comprehensive
error management.
"""

import asyncio
import logging
import shlex
import signal
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional, Tuple, Union, Any
from ..exceptions import (
    CommandError,
    CommandExecutionError,
    CommandNotFoundError,
    CommandTimeoutError,
)
from .types import CommandResult, StreamChunk, EnvDict
from .config import ClaudeConfig, get_config


logger = logging.getLogger(__name__)


class AsyncSubprocessWrapper:
    """Async subprocess wrapper with streaming support."""
    
    def __init__(self, config: Optional[ClaudeConfig] = None):
        self.config = config or get_config()
        self._active_processes: Dict[str, asyncio.subprocess.Process] = {}
        self._process_counter = 0
    
    async def execute(
        self,
        command: Union[str, List[str]],
        *,
        timeout: Optional[float] = None,
        cwd: Optional[str] = None,
        env: Optional[EnvDict] = None,
        input_data: Optional[str] = None,
        capture_output: bool = True,
    ) -> CommandResult:
        """
        Execute a command and return the result.
        
        Args:
            command: Command to execute (string or list of arguments)
            timeout: Timeout in seconds (uses config default if None)
            cwd: Working directory for the command
            env: Environment variables
            input_data: Input data to send to the process
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            CommandResult with execution details
            
        Raises:
            CommandNotFoundError: If the command is not found
            CommandTimeoutError: If the command times out
            CommandExecutionError: If the command fails
        """
        start_time = time.time()
        timeout = timeout or self.config.default_timeout
        
        # Prepare command arguments
        if isinstance(command, str):
            cmd_args = shlex.split(command)
        else:
            cmd_args = list(command)
        
        # Prepare environment
        process_env = self._prepare_environment(env)
        
        # Validate command
        self._validate_command(cmd_args[0])
        
        logger.debug(f"Executing command: {' '.join(cmd_args)}")
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE if capture_output else None,
                stderr=asyncio.subprocess.PIPE if capture_output else None,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                cwd=cwd,
                env=process_env,
            )
            
            # Track the process
            process_id = f"proc_{self._process_counter}"
            self._process_counter += 1
            self._active_processes[process_id] = process
            
            try:
                # Execute with timeout
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input_data.encode() if input_data else None),
                    timeout=timeout
                )
                
                execution_time = time.time() - start_time
                
                # Decode output
                stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
                stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
                
                result = CommandResult(
                    exit_code=process.returncode,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    duration=execution_time,
                    command=' '.join(cmd_args),
                )
                
                logger.debug(f"Command completed: exit_code={result.exit_code}, duration={execution_time:.2f}s")
                
                # Check for errors
                if result.exit_code != 0:
                    raise CommandExecutionError(
                        command=' '.join(cmd_args),
                        exit_code=result.exit_code,
                        stdout=stdout_str,
                        stderr=stderr_str,
                    )
                
                return result
                
            except asyncio.TimeoutError:
                # Kill the process
                await self._terminate_process(process)
                raise CommandTimeoutError(
                    command=' '.join(cmd_args),
                    timeout=timeout,
                )
            
            finally:
                # Remove from tracking
                self._active_processes.pop(process_id, None)
                
        except FileNotFoundError:
            raise CommandNotFoundError(cmd_args[0])
        except Exception as e:
            if isinstance(e, (CommandNotFoundError, CommandTimeoutError, CommandExecutionError)):
                raise
            raise CommandError(f"Failed to execute command: {e}")
    
    async def execute_streaming(
        self,
        command: Union[str, List[str]],
        *,
        timeout: Optional[float] = None,
        cwd: Optional[str] = None,
        env: Optional[EnvDict] = None,
        buffer_size: Optional[int] = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute a command with streaming output.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            cwd: Working directory
            env: Environment variables
            buffer_size: Stream buffer size
            
        Yields:
            StreamChunk objects with output data
            
        Raises:
            CommandNotFoundError: If the command is not found
            CommandTimeoutError: If the command times out
            CommandExecutionError: If the command fails
        """
        timeout = timeout or self.config.default_timeout
        buffer_size = buffer_size or self.config.stream_buffer_size
        
        # Prepare command arguments
        if isinstance(command, str):
            cmd_args = shlex.split(command)
        else:
            cmd_args = list(command)
        
        # Prepare environment
        process_env = self._prepare_environment(env)
        
        # Validate command
        self._validate_command(cmd_args[0])
        
        logger.debug(f"Streaming command: {' '.join(cmd_args)}")
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=process_env,
            )
            
            # Track the process
            process_id = f"stream_{self._process_counter}"
            self._process_counter += 1
            self._active_processes[process_id] = process
            
            try:
                # Stream output with timeout
                async with asyncio.timeout(timeout):
                    # Create queues for output
                    output_queue = asyncio.Queue()
                    
                    async def collect_output(stream, stream_type):
                        """Collect output from a stream and put it in the queue."""
                        async for chunk in self._stream_output(stream, stream_type, buffer_size):
                            await output_queue.put(chunk)
                        await output_queue.put(None)  # Signal end of stream
                    
                    # Start collecting output from both streams
                    stdout_task = asyncio.create_task(collect_output(process.stdout, "stdout"))
                    stderr_task = asyncio.create_task(collect_output(process.stderr, "stderr"))
                    
                    # Stream output as it becomes available
                    streams_done = 0
                    while streams_done < 2:
                        chunk = await output_queue.get()
                        if chunk is None:
                            streams_done += 1
                        else:
                            yield chunk
                    
                    # Wait for process to complete
                    await process.wait()
                    
                    # Ensure tasks are complete
                    await stdout_task
                    await stderr_task
                    
                    # Check exit code
                    if process.returncode != 0:
                        raise CommandExecutionError(
                            command=' '.join(cmd_args),
                            exit_code=process.returncode,
                            stdout="",  # Already streamed
                            stderr="",  # Already streamed
                        )
                
            except asyncio.TimeoutError:
                await self._terminate_process(process)
                raise CommandTimeoutError(
                    command=' '.join(cmd_args),
                    timeout=timeout,
                )
            
            finally:
                # Remove from tracking
                self._active_processes.pop(process_id, None)
                
        except FileNotFoundError:
            raise CommandNotFoundError(cmd_args[0])
    
    async def _stream_output(
        self,
        stream: asyncio.StreamReader,
        stream_type: str,
        buffer_size: int,
    ) -> AsyncIterator[StreamChunk]:
        """Stream output from a subprocess stream."""
        while True:
            try:
                chunk = await stream.read(buffer_size)
                if not chunk:
                    break
                
                content = chunk.decode('utf-8', errors='replace')
                yield StreamChunk(
                    content=content,
                    chunk_type=stream_type,
                    metadata={"buffer_size": len(chunk)},
                )
                
            except Exception as e:
                logger.warning(f"Error reading from {stream_type}: {e}")
                break
    
    def _prepare_environment(self, env: Optional[EnvDict]) -> EnvDict:
        """Prepare environment variables for subprocess."""
        process_env = self.config.get_env_vars()
        if env:
            process_env.update(env)
        return process_env
    
    def _validate_command(self, command: str) -> None:
        """Validate that the command is allowed."""
        if self.config.allowed_commands:
            if command not in self.config.allowed_commands:
                raise CommandError(f"Command not allowed: {command}")
    
    async def _terminate_process(self, process: asyncio.subprocess.Process) -> None:
        """Gracefully terminate a process."""
        try:
            # Try graceful termination first
            process.terminate()
            
            # Wait a bit for graceful shutdown
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
                return
            except asyncio.TimeoutError:
                pass
            
            # Force kill if still running
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass  # Process already dead
                
        except Exception as e:
            logger.warning(f"Error terminating process: {e}")
    
    async def cleanup(self) -> None:
        """Clean up all active processes."""
        if not self._active_processes:
            return
        
        logger.info(f"Cleaning up {len(self._active_processes)} active processes")
        
        # Terminate all processes
        for process in self._active_processes.values():
            await self._terminate_process(process)
        
        self._active_processes.clear()
    
    @asynccontextmanager
    async def managed_execution(self):
        """Context manager for automatic cleanup."""
        try:
            yield self
        finally:
            await self.cleanup()


class CommandBuilder:
    """Builder for constructing Claude CLI commands."""
    
    def __init__(self, base_command: str = "claude"):
        self.base_command = base_command
        self._args: List[str] = []
        self._options: Dict[str, str] = {}
        self._flags: List[str] = []
    
    def add_prompt(self, prompt: str) -> "CommandBuilder":
        """Add a prompt to the command."""
        self._options["p"] = prompt
        return self
    
    def add_file(self, file_path: str) -> "CommandBuilder":
        """Add a file to the command."""
        self._args.extend(["--file", file_path])
        return self
    
    def set_output_format(self, format_type: str) -> "CommandBuilder":
        """Set the output format."""
        self._options["output-format"] = format_type
        return self
    
    def set_session_id(self, session_id: str) -> "CommandBuilder":
        """Set the session ID."""
        self._options["session-id"] = session_id
        return self
    
    def add_flag(self, flag: str) -> "CommandBuilder":
        """Add a flag to the command."""
        self._flags.append(flag)
        return self
    
    def add_option(self, key: str, value: str) -> "CommandBuilder":
        """Add an option to the command."""
        self._options[key] = value
        return self
    
    def build(self) -> List[str]:
        """Build the final command."""
        cmd = [self.base_command]
        
        # Add options
        for key, value in self._options.items():
            if len(key) == 1:
                cmd.extend([f"-{key}", value])
            else:
                cmd.extend([f"--{key}", value])
        
        # Add flags
        for flag in self._flags:
            if len(flag) == 1:
                cmd.append(f"-{flag}")
            else:
                cmd.append(f"--{flag}")
        
        # Add positional arguments
        cmd.extend(self._args)
        
        return cmd
    
    def __str__(self) -> str:
        """String representation of the command."""
        return " ".join(self.build())


# Convenience functions
async def execute_command(
    command: Union[str, List[str]],
    **kwargs
) -> CommandResult:
    """Execute a command using the default subprocess wrapper."""
    wrapper = AsyncSubprocessWrapper()
    async with wrapper.managed_execution():
        return await wrapper.execute(command, **kwargs)


async def stream_command(
    command: Union[str, List[str]],
    **kwargs
) -> AsyncIterator[StreamChunk]:
    """Stream a command using the default subprocess wrapper."""
    wrapper = AsyncSubprocessWrapper()
    async with wrapper.managed_execution():
        async for chunk in wrapper.execute_streaming(command, **kwargs):
            yield chunk