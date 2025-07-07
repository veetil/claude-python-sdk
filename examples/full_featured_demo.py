#!/usr/bin/env python3
"""
Full-Featured Claude SDK Demo

This comprehensive example demonstrates all major SDK features:
- (a) Automatic prefix prompt inclusion
- (b) Real-time streaming output  
- (c) Session resumption with context
- (d) Parallel task execution
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_sdk.session_client import SessionAwareClient
from claude_sdk import ClaudeConfig


async def full_featured_demo():
    """Demonstrates all major SDK features in one example"""
    
    # Configure with all features enabled
    config = ClaudeConfig(
        enable_prefix_prompt=True,    # (a) Automatically prepends prefix-prompt.md
        debug_mode=True,              # Shows commands with session IDs
        safe_mode=False,              # Uses --dangerously-skip-permissions
    )
    
    async with SessionAwareClient(config) as client:
        print("=== Full-Featured Claude SDK Demo ===\n")
        
        # PART 1: Initial query with automatic prefix prompt
        print("1. Creating initial content (with prefix prompt automatically applied)")
        initial_response = await client.query_with_session(
            "Create 5 Python files with different algorithms: "
            "sorting, searching, graph traversal, dynamic programming, and ML basics. "
            "Save them in output/algorithms/"
        )
        
        session_id = initial_response.session_id
        print(f"✅ Session ID: {session_id}")
        print(f"📝 Response: {initial_response.content[:200]}...\n")
        
        # PART 2: Real-time streaming with session context
        print("2. Streaming real-time updates")
        stream_chunks = []
        async for chunk in client.stream_query(
            "Add comprehensive docstrings to each algorithm file you created",
            session_id=f"resume:{session_id}"  # Resume previous session
        ):
            stream_chunks.append(chunk)
            if len(stream_chunks) % 10 == 0:  # Print every 10th chunk
                print(f"   Streaming... received {len(stream_chunks)} chunks")
        
        print(f"✅ Streamed {len(stream_chunks)} total chunks\n")
        
        # PART 3: Parallel execution with session resumption
        print("3. Parallel task execution (maintaining session context)")
        
        # Define 5 parallel tasks
        parallel_tasks = [
            ("Add unit tests for sorting.py", "tests/test_sorting.py"),
            ("Add unit tests for searching.py", "tests/test_searching.py"),
            ("Add unit tests for graph.py", "tests/test_graph.py"),
            ("Add unit tests for dp.py", "tests/test_dp.py"),
            ("Add unit tests for ml_basics.py", "tests/test_ml.py"),
        ]
        
        # Execute all tasks in parallel, resuming the same session
        async def create_test_file(prompt, filename):
            response = await client.query_with_session(
                f"{prompt} and save to output/algorithms/{filename}",
                resume_session_id=session_id  # All tasks use same session
            )
            return filename, response.content[:100]
        
        # Launch all tasks concurrently
        results = await asyncio.gather(*[
            create_test_file(prompt, filename) 
            for prompt, filename in parallel_tasks
        ])
        
        print("✅ Parallel execution results:")
        for filename, preview in results:
            print(f"   - {filename}: {preview}...")
        
        # PART 4: Final session operation with full context
        print(f"\n4. Creating summary using full session context")
        summary_response = await client.query_with_session(
            "Create output/algorithms/README.md that lists all algorithm files "
            "and their corresponding test files with brief descriptions",
            resume_session_id=session_id
        )
        
        print(f"✅ Summary created in session: {session_id}")
        
        # Verify files were created
        output_dir = Path("output/algorithms")
        if output_dir.exists():
            files = list(output_dir.glob("**/*.py"))
            print(f"\n📁 Created {len(files)} Python files")
            if (output_dir / "README.md").exists():
                print("📄 README.md successfully created")
                # Show README preview
                with open(output_dir / "README.md", 'r') as f:
                    preview = f.read()[:300]
                    print(f"\nREADME.md preview:\n{preview}...")


async def main():
    # Clean up before demo
    output_dir = Path("output/algorithms")
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
    
    # Run the demo
    await full_featured_demo()
    
    print("\n✅ Demo complete! Check output/algorithms/ for results.")
    print("\nKey features demonstrated:")
    print("- Automatic prefix prompt inclusion (BatchTool usage)")
    print("- Real-time streaming output")
    print("- Session ID extraction and resumption") 
    print("- Parallel task execution with session context")
    print("- All in one simple, practical example!")


if __name__ == "__main__":
    asyncio.run(main())