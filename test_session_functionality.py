#!/usr/bin/env python3
"""
Test script to verify session ID extraction and resumption functionality
"""

import asyncio
import json
from pathlib import Path

from src.claude_sdk.session_client import SessionAwareClient
from src.claude_sdk.core.config import ClaudeConfig


async def test_session_extraction():
    """Test that we can extract session IDs from Claude responses"""
    print("=== Testing Session ID Extraction ===\n")
    
    config = ClaudeConfig(
        debug_mode=True,  # Show commands being executed
    )
    
    async with SessionAwareClient(config) as client:
        # Simple query that should return a session ID
        response = await client.query_with_session(
            "Say hello and tell me what session this is"
        )
        
        print(f"Response content: {response.content[:200]}...")
        print(f"Extracted session ID: {response.session_id}")
        print(f"Response metadata: {response.metadata}")
        
        if response.raw_json:
            print(f"\nRaw JSON keys: {list(response.raw_json.keys())}")
        
        return response.session_id


async def test_session_resumption(session_id: str):
    """Test that we can resume a session with -r flag"""
    print(f"\n\n=== Testing Session Resumption ===")
    print(f"Resuming session: {session_id}\n")
    
    config = ClaudeConfig(
        debug_mode=True,  # Show commands being executed
    )
    
    async with SessionAwareClient(config) as client:
        # Resume the previous session
        response = await client.query_with_session(
            "What session are we in? What did we discuss before?",
            resume_session_id=session_id
        )
        
        print(f"Response content: {response.content[:300]}...")
        print(f"Session ID: {response.session_id}")
        print(f"Resumed session: {response.metadata.get('resumed_session')}")


async def test_auto_resume():
    """Test automatic session resumption"""
    print("\n\n=== Testing Auto Resume Feature ===\n")
    
    async with SessionAwareClient() as client:
        # First query
        response1 = await client.query_with_session(
            "Remember the number 42 for me"
        )
        print(f"First query - Session ID: {response1.session_id}")
        
        # Second query with auto resume
        response2 = await client.query_with_session(
            "What number did I ask you to remember?",
            auto_resume_last=True
        )
        print(f"Second query - Auto resumed: {client.last_session_id}")
        print(f"Response: {response2.content[:200]}...")


async def test_command_generation():
    """Test that commands are generated correctly with -r flag"""
    print("\n\n=== Testing Command Generation ===\n")
    
    from src.claude_sdk.core.subprocess_wrapper import CommandBuilder
    
    # Test without session
    builder1 = CommandBuilder()
    builder1.add_prompt("Test prompt")
    builder1.set_output_format("json")
    cmd1 = builder1.build()
    print(f"Command without session: {' '.join(cmd1)}")
    
    # Test with session resumption
    builder2 = CommandBuilder()
    builder2.add_prompt("Test prompt")
    builder2.set_output_format("json")
    builder2.add_option("r", "test-session-123")
    cmd2 = builder2.build()
    print(f"Command with -r flag: {' '.join(cmd2)}")


async def main():
    """Run all tests"""
    print("Claude SDK Session Management Tests")
    print("=" * 50)
    
    # Test command generation
    await test_command_generation()
    
    # Test session extraction
    session_id = await test_session_extraction()
    
    # Test session resumption if we got a session ID
    if session_id:
        await test_session_resumption(session_id)
    else:
        print("\n⚠️  No session ID extracted, skipping resumption test")
    
    # Test auto resume
    await test_auto_resume()
    
    print("\n\nTests complete!")


if __name__ == "__main__":
    asyncio.run(main())