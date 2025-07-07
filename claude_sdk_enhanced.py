#!/usr/bin/env python3
"""
Enhanced Claude SDK with Session ID Return and Resumption Support

This module provides enhanced functionality for the Claude Python SDK:
- Automatically extracts and returns session IDs from Claude responses
- Supports session resumption with -r flag
- Handles JSON parsing to extract session information
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from claude_sdk import ClaudeClient, ClaudeConfig, OutputFormat
from claude_sdk.core.subprocess_wrapper import CommandBuilder


logger = logging.getLogger(__name__)


class EnhancedClaudeResponse:
    """Enhanced response that includes extracted session ID"""
    
    def __init__(self, content: str, session_id: Optional[str] = None, raw_json: Optional[Dict[str, Any]] = None):
        self.content = content
        self.session_id = session_id
        self.raw_json = raw_json or {}
        
    def __str__(self):
        return self.content


class EnhancedClaudeClient(ClaudeClient):
    """Enhanced Claude Client with session ID management"""
    
    def __init__(self, config: Optional[ClaudeConfig] = None, auto_setup_logging: bool = True):
        # Force stream-json output for session ID extraction
        if config is None:
            config = ClaudeConfig()
        config.default_output_format = OutputFormat.STREAM_JSON
        super().__init__(config, auto_setup_logging)
        
    async def query_with_session(
        self,
        prompt: str,
        *,
        resume_session_id: Optional[str] = None,
        timeout: Optional[float] = None,
        workspace_id: Optional[str] = None,
        files: Optional[list[str]] = None,
        return_raw: bool = False
    ) -> EnhancedClaudeResponse:
        """
        Send a query and automatically extract session ID from response.
        
        Args:
            prompt: The prompt to send to Claude
            resume_session_id: Optional session ID to resume (-r flag)
            timeout: Timeout in seconds
            workspace_id: Optional workspace to execute in
            files: Optional list of files to include
            return_raw: If True, return raw JSON response
            
        Returns:
            EnhancedClaudeResponse with content and session_id
        """
        # Apply prefix prompt if enabled
        full_prompt = self.config.apply_prefix_prompt(prompt)
        
        # Build command with stream-json output for better session tracking
        command_builder = CommandBuilder(config=self.config)
        command_builder.add_prompt(full_prompt)
        command_builder.set_output_format("stream-json")
        
        # Add resume session flag if provided
        if resume_session_id:
            command_builder.add_option("r", resume_session_id)
            logger.info(f"Resuming session: {resume_session_id}")
        
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
        
        # Parse stream-json response
        session_id = None
        content = ""
        raw_json = {}
        
        try:
            lines = result.stdout.strip().split('\n')
            
            # Process each JSON line
            for line in lines:
                if not line.strip():
                    continue
                    
                try:
                    json_obj = json.loads(line)
                    
                    # Extract session ID from various message types
                    if json_obj.get('type') == 'system' and json_obj.get('subtype') == 'init':
                        if not session_id:
                            session_id = json_obj.get('session_id')
                    
                    elif json_obj.get('type') == 'assistant':
                        # Extract content from assistant message
                        message = json_obj.get('message', {})
                        message_content = message.get('content', [])
                        for item in message_content:
                            if isinstance(item, dict) and item.get('type') == 'text':
                                content = item.get('text', '')
                        
                        # Session ID in assistant messages
                        if not session_id and json_obj.get('session_id'):
                            session_id = json_obj.get('session_id')
                    
                    elif json_obj.get('type') == 'result':
                        # Final result line - check for errors
                        is_error = json_obj.get('is_error', False)
                        
                        if is_error:
                            # Handle error case
                            error_msg = json_obj.get('error', json_obj.get('result', 'Unknown error'))
                            content = f"Error: {error_msg}"
                            logger.error(f"Error in result: {error_msg}")
                        else:
                            # Success case
                            if json_obj.get('result'):
                                content = json_obj.get('result')
                        
                        if json_obj.get('session_id'):
                            session_id = json_obj.get('session_id')
                        raw_json = json_obj
                        
                except json.JSONDecodeError:
                    continue
            
            logger.debug(f"Extracted session_id: {session_id}, content: {content[:100]}...")
            
            return EnhancedClaudeResponse(
                content=content,
                session_id=session_id,
                raw_json=raw_json if return_raw else None
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse stream-json response: {e}")
            # Fallback to plain text response
            return EnhancedClaudeResponse(
                content=result.stdout,
                session_id=None
            )
    
    async def stream_query_with_session(
        self,
        prompt: str,
        *,
        resume_session_id: Optional[str] = None,
        timeout: Optional[float] = None,
        workspace_id: Optional[str] = None,
        files: Optional[list[str]] = None,
    ) -> Tuple[AsyncIterator[str], Optional[str]]:
        """
        Stream a query with session management.
        
        Returns:
            Tuple of (async iterator for content chunks, session_id)
        """
        # Apply prefix prompt if enabled
        full_prompt = self.config.apply_prefix_prompt(prompt)
        
        # Build command
        command_builder = CommandBuilder(config=self.config)
        command_builder.add_prompt(full_prompt)
        command_builder.set_output_format("stream-json")
        
        if self.config.debug_mode or self.config.verbose_logging:
            command_builder.add_flag("verbose")
        
        # Add resume session flag if provided
        if resume_session_id:
            command_builder.add_option("r", resume_session_id)
            logger.info(f"Resuming streaming session: {resume_session_id}")
        
        if files:
            for file_path in files:
                command_builder.add_file(file_path)
        
        command = command_builder.build()
        
        # Variables to track session ID
        session_id = None
        
        async def stream_with_session_tracking():
            nonlocal session_id
            
            async for chunk in self._stream_command(
                command,
                timeout=timeout,
                workspace_id=workspace_id,
            ):
                # Try to extract session ID from JSON chunks
                if chunk.stream_type == "stdout" and not session_id:
                    try:
                        # Parse JSON line
                        json_data = json.loads(chunk.content)
                        if isinstance(json_data, dict):
                            extracted_id = (
                                json_data.get('session_id') or
                                json_data.get('sessionId') or
                                json_data.get('session', {}).get('id')
                            )
                            if extracted_id:
                                session_id = extracted_id
                                logger.debug(f"Extracted session_id from stream: {session_id}")
                    except:
                        pass
                
                yield chunk.content
        
        return stream_with_session_tracking(), session_id


# Convenience functions for enhanced usage
async def query_with_session(
    prompt: str,
    resume_session_id: Optional[str] = None,
    **kwargs
) -> EnhancedClaudeResponse:
    """Simple query function with session management."""
    async with EnhancedClaudeClient() as client:
        return await client.query_with_session(
            prompt,
            resume_session_id=resume_session_id,
            **kwargs
        )


# Example usage functions
async def example_basic_usage():
    """Example: Basic usage with session ID extraction"""
    print("=== Basic Usage Example ===")
    
    async with EnhancedClaudeClient() as client:
        # First query - creates new session
        response = await client.query_with_session(
            "Write Python code for sorting algorithms and save to output/sort.py"
        )
        
        print(f"Response: {response.content[:200]}...")
        print(f"Session ID: {response.session_id}")
        
        # Follow-up query using same session
        if response.session_id:
            response2 = await client.query_with_session(
                "Also write a test file for the sorting algorithms in output/test_sort.py",
                resume_session_id=response.session_id
            )
            print(f"\nFollow-up response: {response2.content[:200]}...")


async def example_error_correction():
    """Example: Error correction with session resumption"""
    print("\n=== Error Correction Example ===")
    
    async with EnhancedClaudeClient() as client:
        # First attempt - wrong folder
        response1 = await client.query_with_session(
            "Write a fibonacci function to fib.py"
        )
        session_id = response1.session_id
        print(f"Initial session ID: {session_id}")
        
        # Simulate checking for file in wrong location
        output_path = Path("output/fib.py")
        if not output_path.exists():
            print("ERROR: File not found in output/ folder")
            
            # Correction with session resumption
            response2 = await client.query_with_session(
                "You need to write the file to the output/ folder. Please write the fibonacci function to output/fib.py",
                resume_session_id=session_id
            )
            print(f"Correction applied in same session: {session_id}")


async def example_multi_step_workflow():
    """Example: Multi-step workflow with session continuity"""
    print("\n=== Multi-Step Workflow Example ===")
    
    async with EnhancedClaudeClient() as client:
        # Step 1: Create project structure
        response1 = await client.query_with_session(
            "Create a Python project structure in output/ with folders: src, tests, docs"
        )
        session_id = response1.session_id
        print(f"Step 1 - Session ID: {session_id}")
        
        # Step 2: Add main module
        response2 = await client.query_with_session(
            "Now create a main.py file in output/src/ with a simple CLI application",
            resume_session_id=session_id
        )
        print(f"Step 2 - Continuing session: {session_id}")
        
        # Step 3: Add tests
        response3 = await client.query_with_session(
            "Create unit tests for main.py in output/tests/test_main.py",
            resume_session_id=session_id
        )
        print(f"Step 3 - Same session: {session_id}")
        
        # Step 4: Add documentation
        response4 = await client.query_with_session(
            "Create a README.md in output/ explaining the project",
            resume_session_id=session_id
        )
        print(f"Step 4 - Completed in session: {session_id}")


# Wrapper class for backward compatibility
class ClaudeSDKWrapper:
    """Wrapper class providing session management with backward compatibility"""
    
    def __init__(self, config: Optional[ClaudeConfig] = None):
        self.client = EnhancedClaudeClient(config)
        self.last_session_id: Optional[str] = None
    
    async def __aenter__(self):
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def execute(
        self,
        prompt: str,
        resume_last_session: bool = False,
        **kwargs
    ) -> Tuple[str, Optional[str]]:
        """
        Execute a query and return (content, session_id).
        
        Args:
            prompt: The prompt to execute
            resume_last_session: If True, resume the last session
            **kwargs: Additional arguments
            
        Returns:
            Tuple of (response content, session_id)
        """
        resume_id = self.last_session_id if resume_last_session else kwargs.get('resume_session_id')
        
        response = await self.client.query_with_session(
            prompt,
            resume_session_id=resume_id,
            **kwargs
        )
        
        self.last_session_id = response.session_id
        return response.content, response.session_id
    
    async def execute_with_validation(
        self,
        prompt: str,
        validation_func: callable,
        max_retries: int = 3,
        **kwargs
    ) -> Tuple[str, Optional[str]]:
        """
        Execute a query with validation and automatic retry in same session.
        
        Args:
            prompt: The prompt to execute
            validation_func: Function to validate the result
            max_retries: Maximum number of retries
            **kwargs: Additional arguments
            
        Returns:
            Tuple of (response content, session_id)
        """
        for attempt in range(max_retries):
            content, session_id = await self.execute(
                prompt,
                resume_last_session=(attempt > 0),
                **kwargs
            )
            
            if validation_func(content):
                return content, session_id
            
            # Validation failed, prepare retry prompt
            if attempt < max_retries - 1:
                prompt = f"The previous attempt failed validation. {prompt}"
                logger.warning(f"Validation failed, retrying in session {session_id}")
        
        raise ValueError(f"Failed validation after {max_retries} attempts")


if __name__ == "__main__":
    # Run examples
    async def main():
        print("Enhanced Claude SDK Examples\n")
        
        # Run all examples
        await example_basic_usage()
        await example_error_correction()
        await example_multi_step_workflow()
        
        print("\n=== Integration Example ===")
        # Example of the exact use case mentioned
        async with ClaudeSDKWrapper() as sdk:
            # First attempt
            content, session_id = await sdk.execute(
                "write code for different tasks and write to folder output/"
            )
            print(f"Got session ID: {session_id}")
            
            # Check for files
            output_dir = Path("output")
            if not output_dir.exists() or not any(output_dir.iterdir()):
                print("ERROR: No files found in output folder")
                
                # Retry with correction in same session
                content, _ = await sdk.execute(
                    "error - you have to write to the correct folder which is output/",
                    resume_last_session=True
                )
                print(f"Corrected in session: {session_id}")
    
    asyncio.run(main())