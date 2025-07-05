"""
Workspace isolation and management for the Claude Python SDK.

This module provides secure workspace creation, management, and cleanup
with proper isolation and security controls.
"""

import asyncio
import logging
import os
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from ..exceptions import WorkspaceError, WorkspaceCreationError, WorkspaceCleanupError
from .types import WorkspaceInfo
from .config import ClaudeConfig, get_config


logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages isolated workspaces for Claude CLI operations."""
    
    def __init__(self, config: Optional[ClaudeConfig] = None):
        self.config = config or get_config()
        self._active_workspaces: Dict[str, WorkspaceInfo] = {}
        self._cleanup_lock = asyncio.Lock()
    
    async def create_workspace(
        self,
        workspace_id: Optional[str] = None,
        base_path: Optional[str] = None,
        copy_files: Optional[List[str]] = None,
        permissions: Optional[int] = None,
    ) -> WorkspaceInfo:
        """
        Create a new isolated workspace.
        
        Args:
            workspace_id: Optional workspace identifier
            base_path: Base path for workspace creation
            copy_files: Files to copy into the workspace
            permissions: File permissions for the workspace
            
        Returns:
            WorkspaceInfo object with workspace details
            
        Raises:
            WorkspaceCreationError: If workspace creation fails
        """
        workspace_id = workspace_id or str(uuid.uuid4())
        base_path = base_path or self.config.workspace_base_path
        permissions = permissions or 0o700
        
        logger.debug(f"Creating workspace: {workspace_id}")
        
        try:
            # Create workspace directory
            if base_path:
                workspace_path = Path(base_path) / workspace_id
                workspace_path.mkdir(parents=True, exist_ok=True)
            else:
                # Use temporary directory
                temp_dir = tempfile.mkdtemp(prefix=f"claude_workspace_{workspace_id}_")
                workspace_path = Path(temp_dir)
            
            # Set secure permissions
            if self.config.enable_workspace_isolation:
                os.chmod(workspace_path, permissions)
            
            # Copy files if specified
            if copy_files:
                await self._copy_files_to_workspace(workspace_path, copy_files)
            
            # Create workspace info
            workspace_info = WorkspaceInfo(
                workspace_id=workspace_id,
                path=str(workspace_path),
                created_at=datetime.now(),
                metadata={
                    "permissions": oct(permissions),
                    "isolation_enabled": self.config.enable_workspace_isolation,
                    "copied_files": copy_files or [],
                }
            )
            
            # Update workspace stats
            await self._update_workspace_stats(workspace_info)
            
            # Track workspace
            self._active_workspaces[workspace_id] = workspace_info
            
            logger.info(f"Created workspace {workspace_id} at {workspace_path}")
            return workspace_info
            
        except Exception as e:
            raise WorkspaceCreationError(
                reason=str(e),
                workspace_path=str(workspace_path) if 'workspace_path' in locals() else None,
                context={"workspace_id": workspace_id, "base_path": base_path}
            )
    
    async def cleanup_workspace(
        self,
        workspace_id: str,
        force: bool = False,
    ) -> None:
        """
        Clean up a workspace and remove all files.
        
        Args:
            workspace_id: Workspace identifier to clean up
            force: Force cleanup even if workspace is not tracked
            
        Raises:
            WorkspaceCleanupError: If cleanup fails
        """
        async with self._cleanup_lock:
            workspace_info = self._active_workspaces.get(workspace_id)
            
            if not workspace_info and not force:
                logger.warning(f"Workspace {workspace_id} not found in active workspaces")
                return
            
            workspace_path = workspace_info.path if workspace_info else None
            
            if not workspace_path:
                logger.warning(f"No path found for workspace {workspace_id}")
                return
            
            logger.debug(f"Cleaning up workspace: {workspace_id}")
            
            try:
                path = Path(workspace_path)
                if path.exists():
                    # Remove the entire workspace directory
                    shutil.rmtree(path, ignore_errors=True)
                    
                    # Verify removal
                    if path.exists():
                        # Try more aggressive cleanup
                        await self._force_cleanup_directory(path)
                
                # Remove from tracking
                self._active_workspaces.pop(workspace_id, None)
                
                logger.info(f"Cleaned up workspace {workspace_id}")
                
            except Exception as e:
                raise WorkspaceCleanupError(
                    reason=str(e),
                    workspace_path=workspace_path,
                    context={"workspace_id": workspace_id}
                )
    
    async def list_workspaces(self) -> List[WorkspaceInfo]:
        """List all active workspaces."""
        return list(self._active_workspaces.values())
    
    async def get_workspace(self, workspace_id: str) -> Optional[WorkspaceInfo]:
        """Get workspace information by ID."""
        return self._active_workspaces.get(workspace_id)
    
    async def cleanup_all_workspaces(self) -> None:
        """Clean up all active workspaces."""
        if not self._active_workspaces:
            return
        
        logger.info(f"Cleaning up {len(self._active_workspaces)} active workspaces")
        
        # Create cleanup tasks
        cleanup_tasks = [
            self.cleanup_workspace(workspace_id, force=True)
            for workspace_id in list(self._active_workspaces.keys())
        ]
        
        # Execute cleanup tasks concurrently
        results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Log any cleanup errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to cleanup workspace: {result}")
    
    async def _copy_files_to_workspace(
        self,
        workspace_path: Path,
        file_paths: List[str],
    ) -> None:
        """Copy files to the workspace directory."""
        for file_path in file_paths:
            src_path = Path(file_path)
            
            if not src_path.exists():
                logger.warning(f"Source file not found: {file_path}")
                continue
            
            if src_path.is_file():
                dest_path = workspace_path / src_path.name
                shutil.copy2(src_path, dest_path)
                logger.debug(f"Copied file: {src_path} -> {dest_path}")
                
            elif src_path.is_dir():
                dest_path = workspace_path / src_path.name
                shutil.copytree(src_path, dest_path)
                logger.debug(f"Copied directory: {src_path} -> {dest_path}")
    
    async def _update_workspace_stats(self, workspace_info: WorkspaceInfo) -> None:
        """Update workspace statistics."""
        try:
            workspace_path = Path(workspace_info.path)
            
            if not workspace_path.exists():
                return
            
            # Calculate size and file count
            total_size = 0
            file_count = 0
            
            for item in workspace_path.rglob('*'):
                if item.is_file():
                    file_count += 1
                    total_size += item.stat().st_size
            
            workspace_info.size_bytes = total_size
            workspace_info.file_count = file_count
            
        except Exception as e:
            logger.warning(f"Failed to update workspace stats: {e}")
    
    async def _force_cleanup_directory(self, path: Path) -> None:
        """Force cleanup of a directory with retry logic."""
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                # Try to remove read-only files on Windows
                def handle_remove_readonly(func, path, exc):
                    if os.name == 'nt' and exc[1].errno == 13:  # Permission denied on Windows
                        os.chmod(path, 0o777)
                        func(path)
                    else:
                        raise
                
                shutil.rmtree(path, onerror=handle_remove_readonly)
                
                if not path.exists():
                    return
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to force cleanup directory {path}: {e}")
                    return
                
                await asyncio.sleep(retry_delay)
                retry_delay *= 2


class WorkspaceContext:
    """Context manager for workspace operations."""
    
    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        workspace_info: WorkspaceInfo,
        auto_cleanup: bool = True,
    ):
        self.workspace_manager = workspace_manager
        self.workspace_info = workspace_info
        self.auto_cleanup = auto_cleanup
    
    @property
    def path(self) -> Path:
        """Get the workspace path."""
        return Path(self.workspace_info.path)
    
    @property
    def workspace_id(self) -> str:
        """Get the workspace ID."""
        return self.workspace_info.workspace_id
    
    async def __aenter__(self) -> "WorkspaceContext":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.auto_cleanup:
            try:
                await self.workspace_manager.cleanup_workspace(
                    self.workspace_info.workspace_id
                )
            except Exception as e:
                logger.error(f"Failed to cleanup workspace in context manager: {e}")


class SecureWorkspaceManager(WorkspaceManager):
    """Enhanced workspace manager with additional security features."""
    
    def __init__(self, config: Optional[ClaudeConfig] = None):
        super().__init__(config)
        self._allowed_extensions: Set[str] = {
            '.py', '.txt', '.md', '.json', '.yaml', '.yml', '.toml',
            '.js', '.ts', '.html', '.css', '.rs', '.go', '.java',
            '.c', '.cpp', '.h', '.hpp', '.sh', '.sql'
        }
        self._max_file_size = 100 * 1024 * 1024  # 100MB
        self._max_workspace_size = 1024 * 1024 * 1024  # 1GB
    
    async def create_workspace(
        self,
        workspace_id: Optional[str] = None,
        base_path: Optional[str] = None,
        copy_files: Optional[List[str]] = None,
        permissions: Optional[int] = None,
    ) -> WorkspaceInfo:
        """Create workspace with security validation."""
        # Validate files before copying
        if copy_files:
            await self._validate_files(copy_files)
        
        return await super().create_workspace(
            workspace_id, base_path, copy_files, permissions
        )
    
    async def _validate_files(self, file_paths: List[str]) -> None:
        """Validate files for security concerns."""
        for file_path in file_paths:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                continue
            
            # Check file extension
            if path.suffix.lower() not in self._allowed_extensions:
                raise WorkspaceError(
                    f"File type not allowed: {path.suffix}",
                    context={"file_path": file_path, "allowed_extensions": list(self._allowed_extensions)}
                )
            
            # Check file size
            if path.is_file() and path.stat().st_size > self._max_file_size:
                raise WorkspaceError(
                    f"File too large: {path.stat().st_size} bytes (max: {self._max_file_size})",
                    context={"file_path": file_path}
                )
    
    def add_allowed_extension(self, extension: str) -> None:
        """Add an allowed file extension."""
        if not extension.startswith('.'):
            extension = '.' + extension
        self._allowed_extensions.add(extension.lower())
    
    def remove_allowed_extension(self, extension: str) -> None:
        """Remove an allowed file extension."""
        if not extension.startswith('.'):
            extension = '.' + extension
        self._allowed_extensions.discard(extension.lower())


# Convenience functions
@asynccontextmanager
async def create_workspace(
    workspace_id: Optional[str] = None,
    copy_files: Optional[List[str]] = None,
    secure: bool = True,
    **kwargs
) -> WorkspaceContext:
    """Create a managed workspace context."""
    manager_class = SecureWorkspaceManager if secure else WorkspaceManager
    manager = manager_class()
    
    workspace_info = await manager.create_workspace(
        workspace_id=workspace_id,
        copy_files=copy_files,
        **kwargs
    )
    
    async with WorkspaceContext(manager, workspace_info) as context:
        yield context


async def cleanup_orphaned_workspaces(base_path: str) -> int:
    """Clean up orphaned workspace directories."""
    base_path = Path(base_path)
    if not base_path.exists():
        return 0
    
    cleaned_count = 0
    current_time = datetime.now()
    
    # Look for directories that look like workspace IDs
    for item in base_path.iterdir():
        if not item.is_dir():
            continue
        
        # Check if it looks like a UUID (workspace ID)
        try:
            uuid.UUID(item.name)
        except ValueError:
            continue
        
        # Check if it's been idle for more than 24 hours
        try:
            modified_time = datetime.fromtimestamp(item.stat().st_mtime)
            if (current_time - modified_time).total_seconds() > 86400:  # 24 hours
                shutil.rmtree(item, ignore_errors=True)
                cleaned_count += 1
                logger.info(f"Cleaned up orphaned workspace: {item}")
        except Exception as e:
            logger.warning(f"Failed to cleanup orphaned workspace {item}: {e}")
    
    return cleaned_count