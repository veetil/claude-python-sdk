#!/usr/bin/env python3
"""
Enhanced Session Stories Test with Detailed Streaming Output

This example demonstrates all the features mentioned in the help documentation:
- Detailed streaming responses with visual formatting
- Session management with resumption
- Timeout configuration
- Error handling
- Progress tracking
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.claude_sdk.session_client import SessionAwareClient
from src.claude_sdk.core.config import ClaudeConfig, OutputFormat
from src.claude_sdk.exceptions import ClaudeSDKError, TimeoutError


class StreamingProgressTracker:
    """Track and display streaming progress"""
    
    def __init__(self):
        self.start_time = time.time()
        self.chunks_received = 0
        self.total_bytes = 0
        self.current_task = None
        self.tasks_completed = []
        
    def update(self, chunk: str, event_type: Optional[str] = None):
        """Update progress with new chunk"""
        self.chunks_received += 1
        self.total_bytes += len(chunk)
        
        # Track task changes
        if "Writing story" in chunk or "Creating" in chunk:
            if self.current_task:
                self.tasks_completed.append(self.current_task)
            self.current_task = chunk.strip()
    
    def get_stats(self) -> Dict[str, any]:
        """Get current statistics"""
        elapsed = time.time() - self.start_time
        return {
            'elapsed_seconds': elapsed,
            'chunks': self.chunks_received,
            'bytes': self.total_bytes,
            'bytes_per_second': self.total_bytes / elapsed if elapsed > 0 else 0,
            'current_task': self.current_task,
            'completed_tasks': len(self.tasks_completed)
        }


async def stream_with_progress(client: SessionAwareClient, prompt: str, 
                              session_id: Optional[str] = None,
                              timeout: float = 300.0) -> tuple[str, Optional[str]]:
    """Stream a query with detailed progress output"""
    
    print(f"\n🚀 Starting streaming query (timeout: {timeout}s)")
    print("─" * 60)
    
    tracker = StreamingProgressTracker()
    collected_content = []
    response_session_id = session_id
    
    try:
        # Build command for streaming
        from src.claude_sdk.core.subprocess_wrapper import CommandBuilder
        
        command_builder = CommandBuilder(config=client.config)
        command_builder.add_prompt(client.config.apply_prefix_prompt(prompt))
        command_builder.set_output_format("stream-json")
        command_builder.add_flag("verbose")
        
        if session_id:
            command_builder.add_option("r", session_id)
            print(f"📌 Resuming session: {session_id}")
        
        command = command_builder.build()
        
        # Stream execution
        async for chunk in client._stream_command(command, timeout=timeout):
            # Track progress
            tracker.update(chunk.content)
            
            # Parse JSON events for detailed output
            if chunk.content.strip():
                try:
                    event = json.loads(chunk.content)
                    
                    # Display based on event type
                    if event.get('type') == 'system' and event.get('subtype') == 'init':
                        response_session_id = event.get('session_id')
                        print(f"🔗 Session initialized: {response_session_id}")
                        print(f"🤖 Model: {event.get('model')}")
                        
                    elif event.get('type') == 'assistant':
                        # Extract and display assistant messages
                        message = event.get('message', {})
                        content_items = message.get('content', [])
                        
                        for item in content_items:
                            if item.get('type') == 'text':
                                text = item.get('text', '')
                                collected_content.append(text)
                                
                                # Show progress for specific actions
                                if any(keyword in text.lower() for keyword in ['writing', 'creating', 'saving']):
                                    lines = text.strip().split('\n')
                                    for line in lines:
                                        if line.strip():
                                            print(f"  ⏺ {line.strip()}")
                    
                    elif event.get('type') == 'content':
                        # Content chunks
                        text = event.get('text', '')
                        if text:
                            collected_content.append(text)
                            
                    elif event.get('type') == 'result':
                        # Final result
                        is_error = event.get('is_error', False)
                        if is_error:
                            error_msg = event.get('error', 'Unknown error')
                            print(f"\n❌ Error: {error_msg}")
                        else:
                            print(f"\n✅ Task completed successfully")
                            if event.get('session_id'):
                                response_session_id = event.get('session_id')
                    
                    # Periodic stats update
                    if tracker.chunks_received % 10 == 0:
                        stats = tracker.get_stats()
                        print(f"\r⚡ Progress: {stats['chunks']} chunks, "
                              f"{stats['bytes']/1024:.1f}KB, "
                              f"{stats['bytes_per_second']/1024:.1f}KB/s", 
                              end='', flush=True)
                        
                except json.JSONDecodeError:
                    # Non-JSON content
                    collected_content.append(chunk.content)
                    
    except TimeoutError:
        print(f"\n⏱️  Timeout reached after {timeout}s")
        raise
    except Exception as e:
        print(f"\n❌ Error during streaming: {type(e).__name__}: {e}")
        raise
    
    # Final stats
    stats = tracker.get_stats()
    print(f"\n\n📊 Streaming Statistics:")
    print(f"  • Duration: {stats['elapsed_seconds']:.2f}s")
    print(f"  • Data received: {stats['bytes']/1024:.1f}KB")
    print(f"  • Average speed: {stats['bytes_per_second']/1024:.1f}KB/s")
    print(f"  • Chunks processed: {stats['chunks']}")
    print(f"  • Tasks completed: {stats['completed_tasks']}")
    
    return ''.join(collected_content), response_session_id


async def main():
    """Main demo with all features"""
    
    print("🎭 Claude SDK Advanced Demo - Story Writing with Session Management")
    print("=" * 70)
    
    # Configure with all options
    config = ClaudeConfig(
        # Core settings
        enable_prefix_prompt=True,      # Use prefix prompt
        debug_mode=True,                # Show commands
        verbose_logging=True,           # Detailed logs
        
        # Timeouts
        default_timeout=60.0,           # Default timeout
        
        # Retries
        max_retries=3,                  # Retry failed requests
        retry_delay=2.0,                # Wait between retries
        
        # Output
        default_output_format=OutputFormat.STREAM_JSON,  # For session tracking
    )
    
    # Create output directory
    output_dir = Path("output/stories")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    async with SessionAwareClient(config) as client:
        
        # Phase 1: Write stories with streaming progress
        print("\n📝 PHASE 1: Writing Stories with Streaming Progress")
        print("─" * 70)
        
        try:
            content1, session_id = await stream_with_progress(
                client,
                """Write 5 very short stories (each 100-150 words) on different themes:
                1. A sci-fi story about time travel
                2. A fantasy story about a magical forest
                3. A mystery story about a missing painting
                4. A romance story about coffee shop encounters
                5. A horror story about an old mansion
                
                For each story:
                - Give it a simple, basic title
                - Save to output/stories/story1.txt, story2.txt, etc.
                - Include the title at the top of each file
                
                As you write each story, announce what you're doing.
                
                After writing all stories, list them with format:
                1. [Title] - story1.txt
                2. [Title] - story2.txt
                etc.""",
                timeout=300.0  # 5 minute timeout
            )
            
            print(f"\n🎯 Session established: {session_id}")
            
        except TimeoutError:
            print("\n⏱️  Initial request timed out. Trying with extended timeout...")
            content1, session_id = await stream_with_progress(
                client,
                "Please write the 5 stories as requested",
                timeout=600.0  # 10 minute timeout
            )
        
        # Extract story information
        stories = []
        lines = content1.split('\n')
        for line in lines:
            if any(line.strip().startswith(f"{i}.") for i in range(1, 6)):
                parts = line.strip().split(' - ')
                if len(parts) >= 2:
                    title_part = parts[0].split('. ', 1)
                    if len(title_part) == 2:
                        stories.append({
                            'number': title_part[0],
                            'original_title': title_part[1].strip(),
                            'filename': parts[1].strip()
                        })
        
        if not stories:
            print("\n⚠️  Couldn't extract story list, checking files...")
            for i in range(1, 6):
                filepath = output_dir / f"story{i}.txt"
                if filepath.exists():
                    stories.append({
                        'number': str(i),
                        'original_title': f"Story {i}",
                        'filename': f"story{i}.txt"
                    })
        
        print(f"\n📚 Found {len(stories)} stories")
        
        # Phase 2: Improve titles with detailed progress
        print("\n\n🎨 PHASE 2: Improving Titles with Session Resumption")
        print("─" * 70)
        
        improved_titles = []
        
        for i, story in enumerate(stories, 1):
            print(f"\n🔄 Improving story {i}/{len(stories)}: {story['original_title']}")
            
            try:
                # Show we're resuming the session
                improvement_prompt = f"""Looking at {story['filename']}, improve the title "{story['original_title']}".
                Create a more engaging, creative title that captures the story's essence.
                Update the file with the new title.
                Respond with: "New title: [improved title]" """
                
                # Stream the improvement
                improved_content, _ = await stream_with_progress(
                    client,
                    improvement_prompt,
                    session_id=session_id,  # Resume session
                    timeout=60.0  # 1 minute per title
                )
                
                # Extract improved title
                if "New title:" in improved_content:
                    improved = improved_content.split("New title:", 1)[1].strip()
                    improved = improved.strip('"').strip("'").split('\n')[0]
                    improved_titles.append(improved)
                    print(f"  ✨ Improved: {improved}")
                    
            except Exception as e:
                print(f"  ❌ Error improving title: {e}")
                improved_titles.append(story['original_title'])
        
        # Phase 3: Create summary with streaming
        print("\n\n📊 PHASE 3: Creating Summary Table")
        print("─" * 70)
        
        try:
            summary_content, _ = await stream_with_progress(
                client,
                """Create a comprehensive summary file at output/stories/SUMMARY.md that includes:
                
                1. A markdown table with columns:
                   - Story Number
                   - Original Title
                   - Improved Title
                   - Theme
                   - Word Count
                   - Brief Description (one line)
                
                2. Statistics section showing:
                   - Total stories written
                   - Total word count
                   - Average story length
                   - Themes covered
                
                3. A "Best Lines" section with one memorable quote from each story
                
                Make it visually appealing with emojis and formatting.""",
                session_id=session_id,  # Continue in same session
                timeout=120.0
            )
            
            print("\n✅ Summary created!")
            
        except Exception as e:
            print(f"\n❌ Error creating summary: {e}")
        
        # Display final session info
        print("\n\n🏁 SESSION SUMMARY")
        print("─" * 70)
        print(f"Session ID: {session_id}")
        print(f"Total operations: {3 + len(stories)}")
        print(f"Session maintained throughout: ✅")
        
        # Check created files
        print("\n📁 Created Files:")
        for file in sorted(output_dir.glob("*")):
            size = file.stat().st_size
            print(f"  • {file.name} ({size} bytes)")
        
        # Show preview of summary if it exists
        summary_path = output_dir / "SUMMARY.md"
        if summary_path.exists():
            print("\n📄 Summary Preview:")
            print("─" * 40)
            with open(summary_path, 'r') as f:
                preview = f.read()[:500]
                print(preview)
                if len(f.read()) > 500:
                    print("\n... (truncated)")


async def demo_error_handling():
    """Demonstrate error handling and recovery"""
    
    print("\n\n🛡️  ERROR HANDLING DEMO")
    print("=" * 70)
    
    config = ClaudeConfig(
        debug_mode=True,
        max_retries=2,
        retry_delay=1.0,
    )
    
    async with SessionAwareClient(config) as client:
        # Intentionally short timeout to trigger error
        print("\n1. Testing timeout handling...")
        try:
            response = await client.query_with_session(
                "Write a very long story that will timeout",
                timeout=0.1  # Very short timeout
            )
        except TimeoutError:
            print("  ✅ Timeout properly caught!")
            
            # Retry with longer timeout
            print("\n2. Retrying with extended timeout...")
            response = await client.query_with_session(
                "Just say 'Hello'",
                timeout=30.0
            )
            print(f"  ✅ Success: {response.content}")
            
        # Test error in response
        print("\n3. Testing error response handling...")
        response = await client.query_with_session(
            "Intentionally trigger an error by doing something impossible",
            timeout=30.0
        )
        
        if response.metadata.get('is_error'):
            print(f"  ✅ Error detected: {response.metadata.get('error')}")
        else:
            print(f"  ℹ️  No error in response")


if __name__ == "__main__":
    # Clean up before starting
    output_dir = Path("output/stories")
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
    
    # Run main demo
    print("Starting Claude SDK Advanced Demo...")
    asyncio.run(main())
    
    # Run error handling demo
    asyncio.run(demo_error_handling())
    
    print("\n\n✅ All demos complete! Check output/stories/ for results.")