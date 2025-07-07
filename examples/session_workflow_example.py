#!/usr/bin/env python3
"""
Complete Session Workflow Example

Demonstrates:
1. Initial query with session ID extraction
2. File validation
3. Error correction with session resumption using -r flag
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.claude_sdk.session_client import SessionAwareClient
from src.claude_sdk.core.config import ClaudeConfig


async def main():
    """Complete workflow example matching the exact use case"""
    
    print("=== Claude SDK Session Management Example ===\n")
    
    # Configure client with debug mode to see commands
    config = ClaudeConfig(
        debug_mode=True,  # Shows commands with -r flag
        enable_prefix_prompt=True,  # Uses prefix-prompt.md
    )
    
    async with SessionAwareClient(config) as client:
        print("Step 1: Initial request to create files")
        print("-" * 50)
        
        # First request - may not write to correct folder
        response1 = await client.query_with_session(
            "write code for different tasks and write to folder output/"
        )
        
        # Extract session ID from response
        session_id = response1.session_id
        print(f"\n✅ Got session ID: {session_id}")
        print(f"📝 Response preview: {response1.content[:200]}...")
        
        # Step 2: System validation
        print(f"\nStep 2: Checking for files in output/ folder")
        print("-" * 50)
        
        output_dir = Path("output")
        if not output_dir.exists():
            print("❌ ERROR: output/ directory doesn't exist!")
            files_found = False
        else:
            files = list(output_dir.glob("*.py"))
            files_found = len(files) > 0
            if files_found:
                print(f"✅ Found {len(files)} files in output/:")
                for f in files[:5]:  # Show first 5
                    print(f"   - {f.name}")
            else:
                print("❌ ERROR: No files found in output/ directory!")
        
        # Step 3: Error correction if needed
        if not files_found:
            print(f"\nStep 3: Correcting error using session resumption")
            print("-" * 50)
            print(f"🔄 Resuming session {session_id} with -r flag\n")
            
            # Send correction with session resumption
            response2 = await client.query_with_session(
                "error - you have to write to the correct folder which is output/",
                resume_session_id=session_id  # This adds -r flag
            )
            
            print(f"✅ Correction sent in session: {session_id}")
            print(f"📝 Response: {response2.content[:200]}...")
            
            # Step 4: Re-validate
            print(f"\nStep 4: Re-checking output/ folder")
            print("-" * 50)
            
            # Give it a moment for files to be created
            await asyncio.sleep(1)
            
            if output_dir.exists():
                files = list(output_dir.glob("*.py"))
                if files:
                    print(f"✅ SUCCESS: Found {len(files)} files after correction:")
                    for f in files[:5]:
                        print(f"   - {f.name} ({f.stat().st_size} bytes)")
                else:
                    print("⚠️  Still no files found - may need another attempt")
            else:
                print("⚠️  output/ directory still doesn't exist")
        
        # Show the actual commands that were executed
        print("\n" + "="*50)
        print("📋 Commands executed (from debug output above):")
        print(f"1. Initial: claude -p \"...\" --output-format stream-json")
        print(f"2. Resume:  claude -p \"...\" -r {session_id} --output-format stream-json")


async def demo_multi_step():
    """Additional example showing multi-step workflow"""
    print("\n\n=== Multi-Step Session Workflow ===\n")
    
    async with SessionAwareClient() as client:
        # Step 1
        print("Creating project structure...")
        response1 = await client.query_with_session(
            "Create a Python project in output/myapp/ with src/, tests/, and docs/ folders"
        )
        session_id = response1.session_id
        print(f"Session: {session_id}")
        
        # Step 2 - Continue in same session
        print("\nAdding main module...")
        response2 = await client.query_with_session(
            "Create output/myapp/src/main.py with a simple CLI application using argparse",
            auto_resume_last=True  # Automatically uses last session
        )
        
        # Step 3 - Explicit session ID
        print("\nAdding configuration...")
        response3 = await client.query_with_session(
            "Create output/myapp/src/config.py with configuration loading from JSON",
            resume_session_id=session_id
        )
        
        # Step 4 - Add tests
        print("\nAdding tests...")
        response4 = await client.query_with_session(
            "Create unit tests in output/myapp/tests/test_main.py",
            auto_resume_last=True
        )
        
        print(f"\n✅ Completed workflow in session: {session_id}")


if __name__ == "__main__":
    # Clean up before starting
    output_dir = Path("output")
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
    
    # Run examples
    asyncio.run(main())
    asyncio.run(demo_multi_step())