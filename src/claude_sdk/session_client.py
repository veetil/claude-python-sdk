"""
Session-aware Claude Client with automatic session ID management.

This module extends the base ClaudeClient to provide:
- Automatic session ID extraction from responses
- Session resumption with -r flag
- Simplified API for session continuity
"""

import json
import logging
from typing import Optional, Dict, Any, Tuple, AsyncIterator
from pathlib import Path

from .client import ClaudeClient
from .core.config import ClaudeConfig
from .core.subprocess_wrapper import CommandBuilder
from .core.types import OutputFormat, ClaudeResponse


logger = logging.getLogger(__name__)


class SessionAwareResponse(ClaudeResponse):
    """Extended response that includes session information"""
    
    def __init__(self, content: str, session_id: Optional[str] = None, 
                 metadata: Optional[Dict[str, Any]] = None, raw_json: Optional[Dict[str, Any]] = None):
        super().__init__(content, session_id, metadata)
        self.raw_json = raw_json or {}
        self.extracted_session_id = session_id  # Explicitly track extracted session ID
    
    @classmethod
    def from_claude_response(cls, response: ClaudeResponse, extracted_session_id: Optional[str] = None):
        """Create from base ClaudeResponse"""
        return cls(
            content=response.content,
            session_id=extracted_session_id or response.session_id,
            metadata=response.metadata
        )


class SessionAwareClient(ClaudeClient):
    """Claude Client with enhanced session management capabilities"""
    
    def __init__(self, config: Optional[ClaudeConfig] = None, auto_setup_logging: bool = True):
        super().__init__(config, auto_setup_logging)
        self._last_session_id: Optional[str] = None
    
    async def query_with_session(
        self,
        prompt: str,
        *,
        resume_session_id: Optional[str] = None,
        auto_resume_last: bool = False,
        output_format: OutputFormat = OutputFormat.STREAM_JSON,
        timeout: Optional[float] = None,
        workspace_id: Optional[str] = None,
        files: Optional[list[str]] = None,
    ) -> SessionAwareResponse:
        """
        Send a query with automatic session ID management.
        
        Args:
            prompt: The prompt to send to Claude
            resume_session_id: Specific session ID to resume
            auto_resume_last: If True, automatically resume last session
            output_format: Output format (defaults to STREAM_JSON for session extraction)
            timeout: Timeout in seconds
            workspace_id: Optional workspace to execute in
            files: Optional list of files to include
            
        Returns:
            SessionAwareResponse with content and session_id
        """
        # Determine which session to resume
        session_to_resume = resume_session_id
        if auto_resume_last and not session_to_resume:
            session_to_resume = self._last_session_id
        
        # Apply prefix prompt if enabled
        full_prompt = self.config.apply_prefix_prompt(prompt)
        
        # Build command
        command_builder = CommandBuilder(config=self.config)
        command_builder.add_prompt(full_prompt)
        
        # Force stream-json output for session ID extraction
        if output_format == OutputFormat.TEXT:
            output_format = OutputFormat.STREAM_JSON
        command_builder.set_output_format(output_format.value)
        
        # Add verbose flag - required for stream-json format
        if output_format == OutputFormat.STREAM_JSON or self.config.debug_mode or self.config.verbose_logging:
            command_builder.add_flag("verbose")
        
        # Add resume session flag if provided
        if session_to_resume:
            # Add -r flag for session resumption
            command_builder.add_option("r", session_to_resume)
            logger.info(f"Resuming session: {session_to_resume}")
        
        if files:
            for file_path in files:
                command_builder.add_file(file_path)
        
        command = command_builder.build()
        
        # Execute command
        result = await self._execute_command(
            command,
            timeout=timeout,
            workspace_id=workspace_id,
        )
        
        # Parse response and extract session ID
        session_id = None
        content = result.stdout
        raw_json = None
        
        # For stream-json format, parse the lines
        if output_format == OutputFormat.JSON or output_format == OutputFormat.STREAM_JSON:
            try:
                # For stream-json, we need to parse each line
                lines = result.stdout.strip().split('\n')
                
                # Look for the final result line which contains session_id
                for line in reversed(lines):  # Start from the end
                    if not line.strip():
                        continue
                    try:
                        json_obj = json.loads(line)
                        
                        # Check if this is the result line
                        if json_obj.get('type') == 'result':
                            # Check for error in result
                            is_error = json_obj.get('is_error', False)
                            session_id = json_obj.get('session_id')
                            raw_json = json_obj
                            
                            if is_error:
                                # Handle error case
                                error_msg = json_obj.get('error', json_obj.get('result', 'Unknown error'))
                                content = f"Error: {error_msg}"
                                logger.error(f"Error in result: {error_msg}")
                                # Store error info in metadata
                                if not hasattr(self, '_last_error'):
                                    self._last_error = error_msg
                            else:
                                # Success case
                                content = json_obj.get('result', '')
                            
                            logger.debug(f"Found result line - is_error: {is_error}, session_id: {session_id}")
                            break
                        
                        # Also check assistant messages
                        elif json_obj.get('type') == 'assistant':
                            # Extract content from assistant messages
                            message = json_obj.get('message', {})
                            message_content = message.get('content', [])
                            if message_content and isinstance(message_content, list):
                                for item in message_content:
                                    if isinstance(item, dict) and item.get('type') == 'text':
                                        content = item.get('text', '')
                            # Session ID might be in the message too
                            if not session_id and json_obj.get('session_id'):
                                session_id = json_obj.get('session_id')
                    except json.JSONDecodeError:
                        continue
                
                # If we didn't find a result line, try parsing as single JSON
                if not session_id and len(lines) == 1:
                    json_response = json.loads(lines[0])
                    if isinstance(json_response, dict):
                        session_id = json_response.get('session_id')
                        content = (
                            json_response.get('content') or
                            json_response.get('result') or
                            json_response.get('response') or
                            json_response.get('message') or
                            content
                        )
                        raw_json = json_response
                
                logger.debug(f"Extracted session_id: {session_id}, content: {content[:100]}...")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response: {e}")
                # Fallback to plain text
                content = result.stdout
        
        # Update last session ID
        if session_id:
            self._last_session_id = session_id
        
        # Check if we had an error
        is_error = raw_json.get('is_error', False) if raw_json else False
        
        # Create response
        response = SessionAwareResponse(
            content=content,
            session_id=session_id,
            metadata={
                "exit_code": result.exit_code,
                "duration": result.duration,
                "command": result.command,
                "output_format": output_format.value,
                "resumed_session": session_to_resume,
                "is_error": is_error,
                "error": raw_json.get('error') if is_error else None,
            },
            raw_json=raw_json
        )
        
        # If there was an error, you might want to raise an exception
        if is_error:
            error_msg = raw_json.get('error', raw_json.get('result', 'Unknown error'))
            logger.error(f"Claude returned error: {error_msg}")
            # Optionally raise exception:
            # raise ClaudeSDKError(f"Claude error: {error_msg}")
        
        return response
    
    async def query(
        self,
        prompt: str,
        *,
        session_id: Optional[str] = None,
        output_format: OutputFormat = OutputFormat.TEXT,
        timeout: Optional[float] = None,
        workspace_id: Optional[str] = None,
        files: Optional[list[str]] = None,
    ) -> ClaudeResponse:
        """
        Override base query to support -r flag for session resumption.
        
        This maintains backward compatibility while adding session support.
        """
        if session_id and session_id.startswith('resume:'):
            # Handle session resumption
            resume_id = session_id.replace('resume:', '')
            response = await self.query_with_session(
                prompt,
                resume_session_id=resume_id,
                output_format=output_format,
                timeout=timeout,
                workspace_id=workspace_id,
                files=files
            )
            return ClaudeResponse(
                content=response.content,
                session_id=response.session_id,
                metadata=response.metadata
            )
        else:
            # Normal query
            return await super().query(
                prompt,
                session_id=session_id,
                output_format=output_format,
                timeout=timeout,
                workspace_id=workspace_id,
                files=files
            )
    
    @property
    def last_session_id(self) -> Optional[str]:
        """Get the last session ID used"""
        return self._last_session_id
    
    def clear_session(self):
        """Clear the stored session ID"""
        self._last_session_id = None


# Convenience functions
async def query_with_session(
    prompt: str,
    resume_session_id: Optional[str] = None,
    **kwargs
) -> SessionAwareResponse:
    """Execute a query with session management"""
    async with SessionAwareClient() as client:
        return await client.query_with_session(
            prompt,
            resume_session_id=resume_session_id,
            **kwargs
        )


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def example():
        """Example usage of session-aware client"""
        
        # Create client
        client = SessionAwareClient()
        
        async with client:
            # First query - creates new session
            print("=== First Query ===")
            response1 = await client.query_with_session(
                "Create a Python function for calculating factorial and save to output/factorial.py"
            )
            print(f"Content: {response1.content[:100]}...")
            print(f"Session ID: {response1.session_id}")
            
            # Follow-up query in same session
            print("\n=== Follow-up Query ===")
            response2 = await client.query_with_session(
                "Now create a test file for the factorial function in output/test_factorial.py",
                auto_resume_last=True  # Automatically use last session
            )
            print(f"Resumed session: {response2.metadata.get('resumed_session')}")
            
            # Error correction example
            print("\n=== Error Correction ===")
            response3 = await client.query_with_session(
                "Write a fibonacci function to fibonacci.py"
            )
            session_id = response3.session_id
            
            # Simulate checking for file
            if not Path("output/fibonacci.py").exists():
                print("ERROR: File not in output folder!")
                
                # Correct with session resumption
                response4 = await client.query_with_session(
                    "Please write the fibonacci function to output/fibonacci.py instead",
                    resume_session_id=session_id
                )
                print(f"Corrected in session: {session_id}")
    
    asyncio.run(example())