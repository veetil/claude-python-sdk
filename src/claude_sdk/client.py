"""
Main client interface for the Claude Python SDK.

This module provides the primary ClaudeClient class that integrates all
SDK components and provides a high-level interface for Claude CLI operations.
"""

import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from .core.config import ClaudeConfig, get_config
from .core.subprocess_wrapper import AsyncSubprocessWrapper, CommandBuilder
from .core.workspace import WorkspaceManager, WorkspaceContext, SecureWorkspaceManager
from .core.types import (
    ClaudeResponse,
    CommandResult,
    OutputFormat,
    SessionInfo,
    SessionStatus,
    StreamChunk,
    WorkspaceInfo,
)
from .exceptions import ClaudeSDKError, SessionError, AuthenticationError
from .utils.logging import setup_logging
from .utils.retry import retry_with_backoff


logger = logging.getLogger(__name__)


class ClaudeClient:
    """
    Main client for interacting with Claude CLI.
    
    Provides async/await interface with streaming support, workspace isolation,
    session management, and comprehensive error handling.
    """
    
    def __init__(
        self,
        config: Optional[ClaudeConfig] = None,
        auto_setup_logging: bool = True,
    ):
        """
        Initialize the Claude client.
        
        Args:
            config: Configuration object (uses default if None)
            auto_setup_logging: Whether to automatically setup logging
        """
        self.config = config or get_config()
        self._subprocess_wrapper = AsyncSubprocessWrapper(self.config)
        self._workspace_manager = SecureWorkspaceManager(self.config)
        self._sessions: Dict[str, SessionInfo] = {}
        self._closed = False
        
        if auto_setup_logging:
            setup_logging(self.config)
        
        logger.debug("Claude client initialized")
    
    async def query(
        self,
        prompt: str,
        *,
        session_id: Optional[str] = None,
        output_format: OutputFormat = OutputFormat.TEXT,
        timeout: Optional[float] = None,
        workspace_id: Optional[str] = None,
        files: Optional[List[str]] = None,
    ) -> ClaudeResponse:
        """
        Send a query to Claude CLI and get the response.
        
        Args:
            prompt: The prompt to send to Claude
            session_id: Optional session ID to use
            output_format: Output format for the response
            timeout: Timeout in seconds
            workspace_id: Optional workspace to execute in
            files: Optional list of files to include
            
        Returns:
            ClaudeResponse with the result
            
        Raises:
            ClaudeSDKError: If the query fails
        """
        self._check_not_closed()
        
        logger.debug(f"Executing query: {prompt[:100]}...")
        
        # Build command
        command_builder = CommandBuilder()
        command_builder.add_prompt(prompt)
        
        if session_id:
            command_builder.set_session_id(session_id)
        
        if output_format != OutputFormat.TEXT:
            command_builder.set_output_format(output_format.value)
        
        if files:
            for file_path in files:
                command_builder.add_file(file_path)
        
        command = command_builder.build()
        
        # Execute with retry
        result = await retry_with_backoff(
            self._execute_command,
            command,
            timeout=timeout,
            workspace_id=workspace_id,
            max_retries=self.config.max_retries,
            base_delay=self.config.retry_delay,
        )
        
        # Parse response
        response = ClaudeResponse(
            content=result.stdout,
            session_id=session_id,
            metadata={
                "exit_code": result.exit_code,
                "duration": result.duration,
                "command": result.command,
                "output_format": output_format.value,
            }
        )
        
        logger.debug(f"Query completed: {len(response.content)} characters")
        return response
    
    async def stream_query(
        self,
        prompt: str,
        *,
        session_id: Optional[str] = None,
        timeout: Optional[float] = None,
        workspace_id: Optional[str] = None,
        files: Optional[List[str]] = None,
    ) -> AsyncIterator[str]:
        """
        Send a query to Claude CLI and stream the response.
        
        Args:
            prompt: The prompt to send to Claude
            session_id: Optional session ID to use
            timeout: Timeout in seconds
            workspace_id: Optional workspace to execute in
            files: Optional list of files to include
            
        Yields:
            String chunks of the response
            
        Raises:
            ClaudeSDKError: If the query fails
        """
        self._check_not_closed()
        
        logger.debug(f"Streaming query: {prompt[:100]}...")
        
        # Build command
        command_builder = CommandBuilder()
        command_builder.add_prompt(prompt)
        
        if session_id:
            command_builder.set_session_id(session_id)
        
        if files:
            for file_path in files:
                command_builder.add_file(file_path)
        
        command = command_builder.build()
        
        # Stream execution
        async for chunk in self._stream_command(
            command,
            timeout=timeout,
            workspace_id=workspace_id,
        ):
            yield chunk.content
    
    async def execute_command(
        self,
        command: Union[str, List[str]],
        *,
        timeout: Optional[float] = None,
        workspace_id: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> CommandResult:
        """
        Execute a raw command.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            workspace_id: Optional workspace to execute in
            env: Environment variables
            
        Returns:
            CommandResult with execution details
            
        Raises:
            ClaudeSDKError: If the command fails
        """
        self._check_not_closed()
        
        return await self._execute_command(
            command,
            timeout=timeout,
            workspace_id=workspace_id,
            env=env,
        )
    
    @asynccontextmanager
    async def create_session(self, session_id: Optional[str] = None):
        """
        Create a managed session context.
        
        Args:
            session_id: Optional session ID
            
        Yields:
            Session context manager
        """
        session_id = session_id or f"session_{len(self._sessions)}"
        
        session_info = SessionInfo(
            session_id=session_id,
            status=SessionStatus.CREATED,
            created_at=datetime.now(),
            last_activity=datetime.now(),
        )
        
        self._sessions[session_id] = session_info
        
        try:
            session_info.status = SessionStatus.ACTIVE
            yield SessionContext(self, session_info)
        finally:
            session_info.status = SessionStatus.TERMINATED
            self._sessions.pop(session_id, None)
    
    @asynccontextmanager
    async def create_workspace(
        self,
        workspace_id: Optional[str] = None,
        copy_files: Optional[List[str]] = None,
        **kwargs
    ) -> WorkspaceContext:
        """
        Create a managed workspace context.
        
        Args:
            workspace_id: Optional workspace ID
            copy_files: Files to copy into workspace
            **kwargs: Additional workspace options
            
        Yields:
            Workspace context manager
        """
        self._check_not_closed()
        
        workspace_info = await self._workspace_manager.create_workspace(
            workspace_id=workspace_id,
            copy_files=copy_files,
            **kwargs
        )
        
        context = WorkspaceContext(
            self._workspace_manager,
            workspace_info,
            auto_cleanup=self.config.workspace_cleanup_on_exit,
        )
        
        async with context:
            yield context
    
    async def list_sessions(self) -> List[SessionInfo]:
        """List all active sessions."""
        return list(self._sessions.values())
    
    async def list_workspaces(self) -> List[WorkspaceInfo]:
        """List all active workspaces."""
        return await self._workspace_manager.list_workspaces()
    
    def command_builder(self, base_command: str = "claude") -> CommandBuilder:
        """Create a new command builder."""
        return CommandBuilder(base_command)
    
    async def _execute_command(
        self,
        command: Union[str, List[str]],
        *,
        timeout: Optional[float] = None,
        workspace_id: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> CommandResult:
        """Internal command execution."""
        # Determine working directory
        cwd = None
        if workspace_id:
            workspace_info = await self._workspace_manager.get_workspace(workspace_id)
            if workspace_info:
                cwd = workspace_info.path
        
        return await self._subprocess_wrapper.execute(
            command,
            timeout=timeout,
            cwd=cwd,
            env=env,
        )
    
    async def _stream_command(
        self,
        command: Union[str, List[str]],
        *,
        timeout: Optional[float] = None,
        workspace_id: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Internal command streaming."""
        # Determine working directory
        cwd = None
        if workspace_id:
            workspace_info = await self._workspace_manager.get_workspace(workspace_id)
            if workspace_info:
                cwd = workspace_info.path
        
        async for chunk in self._subprocess_wrapper.execute_streaming(
            command,
            timeout=timeout,
            cwd=cwd,
            env=env,
        ):
            yield chunk
    
    def _check_not_closed(self) -> None:
        """Check that the client is not closed."""
        if self._closed:
            raise ClaudeSDKError("Client is closed")
    
    async def close(self) -> None:
        """Close the client and clean up resources."""
        if self._closed:
            return
        
        logger.debug("Closing Claude client")
        
        try:
            # Clean up subprocess wrapper
            await self._subprocess_wrapper.cleanup()
            
            # Clean up workspaces if configured
            if self.config.workspace_cleanup_on_exit:
                await self._workspace_manager.cleanup_all_workspaces()
            
        except Exception as e:
            logger.error(f"Error during client cleanup: {e}")
        finally:
            self._closed = True
        
        logger.debug("Claude client closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


class SessionContext:
    """Context for session-scoped operations."""
    
    def __init__(self, client: ClaudeClient, session_info: SessionInfo):
        self.client = client
        self.session_info = session_info
    
    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self.session_info.session_id
    
    async def query(
        self,
        prompt: str,
        **kwargs
    ) -> ClaudeResponse:
        """Send a query within this session."""
        return await self.client.query(
            prompt,
            session_id=self.session_id,
            **kwargs
        )
    
    async def stream_query(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a query within this session."""
        async for chunk in self.client.stream_query(
            prompt,
            session_id=self.session_id,
            **kwargs
        ):
            yield chunk


# Convenience functions for simple usage
async def query(prompt: str, **kwargs) -> ClaudeResponse:
    """Simple query function using default client."""
    async with ClaudeClient() as client:
        return await client.query(prompt, **kwargs)


async def stream_query(prompt: str, **kwargs) -> AsyncIterator[str]:
    """Simple streaming query function using default client."""
    async with ClaudeClient() as client:
        async for chunk in client.stream_query(prompt, **kwargs):
            yield chunk