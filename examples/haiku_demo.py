#!/usr/bin/env python3
"""
Haiku Streaming Demo - Create haiku with live streaming output

Demonstrates:
- Real-time streaming of Claude's responses
- Formatted output with visual indicators
- Session management for continuity
- Raw JSON logging capability
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.claude_sdk.session_client import SessionAwareClient
from src.claude_sdk.core.config import ClaudeConfig


async def main(raw_log_path=None, improve_titles=False):
    """Main demo function
    
    Args:
        raw_log_path: Optional path to save raw JSON stream
        improve_titles: Whether to run title improvement phase
    """
    
    # Create output directory
    output_dir = Path("output/haiku")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure client
    config = ClaudeConfig(
        debug_mode=True,
        enable_prefix_prompt=True,
    )
    
    async with SessionAwareClient(config) as client:
        print("🌸 Haiku Creation with Live Streaming")
        print("=" * 50)
        
        # Build command
        from src.claude_sdk.core.subprocess_wrapper import CommandBuilder
        
        prompt = """Create 3 haiku about nature:
        1. Morning dew
        2. Ocean waves
        3. Autumn leaves
        
        Save each to output/haiku/[slug].txt with a title."""
        
        command_builder = CommandBuilder(config=client.config)
        command_builder.add_prompt(client.config.apply_prefix_prompt(prompt))
        command_builder.set_output_format("stream-json")
        command_builder.add_flag("verbose")
        
        command = command_builder.build()
        
        print("\n📝 Streaming output:\n")
        
        # Variables to track
        session_id = None
        in_tool_call = False
        tool_buffer = []
        
        # Open raw log file if specified
        raw_log_file = None
        if raw_log_path:
            # Create directory if needed
            log_dir = Path(raw_log_path).parent
            if log_dir and not log_dir.exists():
                log_dir.mkdir(parents=True, exist_ok=True)
            
            raw_log_file = open(raw_log_path, 'w')
            print(f"📄 Saving raw JSON to: {raw_log_path}")
            # Write timestamp header
            raw_log_file.write(f"# Stream started at {datetime.now().isoformat()}\n")
            raw_log_file.flush()
            print()
        
        try:
            # Stream execution
            async for chunk in client._stream_command(command, timeout=120.0):
                if not chunk.content.strip():
                    continue
                
                # Write raw JSON to log file if specified
                if raw_log_file:
                    raw_log_file.write(chunk.content)
                    raw_log_file.write('\n')
                    raw_log_file.flush()  # Ensure real-time writing
                
                try:
                    event = json.loads(chunk.content)
                    
                    # Get session ID
                    if not session_id and 'session_id' in event:
                        session_id = event['session_id']
                        print(f"Session: {session_id}\n")
                    
                    # Process assistant messages
                    if event.get('type') == 'assistant':
                        message = event.get('message', {})
                        for item in message.get('content', []):
                            if item.get('type') == 'text':
                                text = item.get('text', '')
                                
                                # Process line by line
                                for line in text.split('\n'):
                                    # Start of tool call
                                    if '<function_calls>' in line:
                                        in_tool_call = True
                                        tool_buffer = []
                                    
                                    # Inside tool call
                                    elif in_tool_call:
                                        tool_buffer.append(line)
                                        
                                        # Look for file path
                                        if 'file_path">' in line and len(tool_buffer) > 1:
                                            # Find the Write invocation
                                            for buf_line in tool_buffer:
                                                if 'invoke name="Write"' in buf_line:
                                                    # Next line after file_path has the path
                                                    idx = tool_buffer.index(line)
                                                    if idx + 1 < len(tool_buffer):
                                                        path = tool_buffer[idx + 1].strip()
                                                        if path and '<' not in path:
                                                            print(f"⏺ Writing: {path}")
                                                    break
                                        
                                        # End of tool call
                                        if '</function_calls>' in line:
                                            in_tool_call = False
                                            tool_buffer = []
                                    
                                    # Function results
                                    elif '<function_results>' in line:
                                        if 'successfully' in line:
                                            print("  ⎿ Created successfully")
                                        elif 'error' in line.lower():
                                            print("  ⎿ Error occurred")
                                    
                                    # Regular text output
                                    elif not in_tool_call and line.strip():
                                        # Skip XML-like lines
                                        if not line.strip().startswith('<') and not line.strip().endswith('>'):
                                            print(line)
                    
                    # Handle completion
                    elif event.get('type') == 'result':
                        if event.get('is_error'):
                            print(f"\n❌ Error: {event.get('error')}")
                        else:
                            print("\n✅ Haiku creation complete!")
                            
                except json.JSONDecodeError:
                    # Not JSON, skip
                    pass
        
        finally:
            # Close raw log file if open
            if raw_log_file:
                raw_log_file.write(f"# Phase 1 ended at {datetime.now().isoformat()}\n")
                raw_log_file.close()
                print(f"\n💾 Raw log saved to: {raw_log_path}")
                print(f"   Size: {Path(raw_log_path).stat().st_size:,} bytes")
        
        # Show created files
        print("\n📁 Created files:")
        created_files = []
        for file in sorted(output_dir.glob("*.txt")):
            print(f"  • {file.name}")
            # Show first line (title)
            with open(file, 'r') as f:
                first_line = f.readline().strip()
                if first_line:
                    print(f"    Title: {first_line}")
                    created_files.append({
                        'path': file,
                        'filename': file.name,
                        'original_title': first_line
                    })
        
        # If raw log exists, show sample
        if raw_log_path and Path(raw_log_path).exists():
            print(f"\n📄 Raw log sample (first 3 lines):")
            with open(raw_log_path, 'r') as f:
                for i, line in enumerate(f):
                    if i >= 3:
                        break
                    if line.startswith('#'):
                        continue
                    print(f"   {line.strip()[:80]}{'...' if len(line.strip()) > 80 else ''}")
        
        # Title improvement phase
        if improve_titles and session_id:
            print("\n\n🎨 Phase 2: Title Improvement")
            print("=" * 50)
            
            # Expected files based on slugs
            expected_files = [
                ("morning-dew.txt", "Morning dew"),
                ("ocean-waves.txt", "Ocean waves"),
                ("autumn-leaves.txt", "Autumn leaves")
            ]
            
            # Check if all expected files exist
            missing_files = []
            haiku_info = []
            
            for filename, theme in expected_files:
                file_path = output_dir / filename
                if not file_path.exists():
                    missing_files.append(filename)
                else:
                    # Read current content
                    with open(file_path, 'r') as f:
                        lines = f.readlines()
                        current_title = lines[0].strip() if lines else "Untitled"
                        haiku_info.append({
                            'filename': filename,
                            'theme': theme,
                            'current_title': current_title,
                            'path': file_path
                        })
            
            if missing_files:
                print(f"\n⚠️  Missing expected files: {', '.join(missing_files)}")
                print("Cannot proceed with title improvement.")
                return
            
            print(f"\n✅ All 3 haiku files found. Resuming session: {session_id}")
            
            # Show current titles
            print("\n📋 Current titles:")
            for info in haiku_info:
                print(f"  • {info['filename']}: {info['current_title']}")
            
            # Build improvement prompt for all haiku at once
            improvement_prompt = """Looking at the 3 haiku files you created, please improve their titles to be more evocative and poetic.

Current files and titles:
"""
            for info in haiku_info:
                improvement_prompt += f"- {info['filename']}: \"{info['current_title']}\"\n"
            
            improvement_prompt += """
For each haiku:
1. Read the full haiku to understand its essence
2. Create a more evocative, sensory title that:
   - Captures the emotion and imagery
   - Uses vivid, poetic language
   - Is concise but memorable
   - Avoids clichés

Update each file by replacing its first line with the improved title.

After updating all files, list the improvements:
1. [filename] - New title: [improved title]
2. [filename] - New title: [improved title]  
3. [filename] - New title: [improved title]"""
            
            # Reopen raw log file to append if specified
            raw_log_file = None
            if raw_log_path:
                raw_log_file = open(raw_log_path, 'a')
                raw_log_file.write(f"\n# Phase 2 started at {datetime.now().isoformat()}\n")
                raw_log_file.flush()
            
            try:
                # Build command with session resumption
                command_builder = CommandBuilder(config=client.config)
                command_builder.add_prompt(improvement_prompt)
                command_builder.set_output_format("stream-json")
                command_builder.add_flag("verbose")
                command_builder.add_option("r", session_id)  # Resume session
                
                command = command_builder.build()
                
                print("\n📝 Improving all titles together...\n")
                
                # Track improvements
                improved_titles = []
                in_improvements_list = False
                
                # Stream the improvement
                async for chunk in client._stream_command(command, timeout=120.0):
                    if not chunk.content.strip():
                        continue
                    
                    # Write to raw log if specified
                    if raw_log_file:
                        raw_log_file.write(chunk.content)
                        raw_log_file.write('\n')
                        raw_log_file.flush()
                    
                    try:
                        event = json.loads(chunk.content)
                        
                        if event.get('type') == 'assistant':
                            message = event.get('message', {})
                            for item in message.get('content', []):
                                if item.get('type') == 'text':
                                    text = item.get('text', '')
                                    
                                    # Process line by line for formatted output
                                    for line in text.split('\n'):
                                        # Look for file operations
                                        if 'invoke name="Edit"' in line or 'invoke name="Write"' in line:
                                            print("⏺ Updating titles...")
                                        elif '<function_results>' in line and 'successfully' in line:
                                            print("  ⎿ Title updated")
                                        
                                        # Look for improvements list
                                        elif "New title:" in line:
                                            # Extract filename and new title
                                            parts = line.split(" - New title: ")
                                            if len(parts) == 2:
                                                # Clean up the filename part
                                                filename_part = parts[0].strip()
                                                # Remove numbering if present
                                                if '. ' in filename_part:
                                                    filename_part = filename_part.split('. ', 1)[1]
                                                
                                                new_title = parts[1].strip().strip('"').strip("'")
                                                print(f"   ✨ {filename_part}: {new_title}")
                                                
                                                # Find original title
                                                original = next((h['current_title'] for h in haiku_info 
                                                               if filename_part in h['filename']), "Unknown")
                                                
                                                improved_titles.append({
                                                    'filename': filename_part,
                                                    'original': original,
                                                    'improved': new_title
                                                })
                        
                        elif event.get('type') == 'result':
                            if event.get('is_error'):
                                print(f"\n❌ Error: {event.get('error')}")
                            else:
                                print("\n✅ Title improvement complete!")
                        
                    except json.JSONDecodeError:
                        pass
            
            finally:
                # Close raw log file if open
                if raw_log_file:
                    raw_log_file.write(f"# Phase 2 ended at {datetime.now().isoformat()}\n")
                    raw_log_file.close()
                    print(f"\n💾 Appended to raw log: {raw_log_path}")
                    print(f"   Total size: {Path(raw_log_path).stat().st_size:,} bytes")
            
            # Summary of improvements
            if improved_titles:
                print("\n\n📊 Title Improvement Summary")
                print("=" * 50)
                print(f"Session maintained: {session_id}")
                print(f"\nTitle improvements:")
                
                for item in improved_titles:
                    print(f"\n{item['filename']}:")
                    print(f"  Before:  {item['original']}")
                    print(f"  After:   {item['improved']}")
                    print(f"  {'✅ Enhanced' if item['improved'] != item['original'] else '⚠️  No change'}")
            
            # Verify files were updated
            print("\n\n🔍 Verifying Updates:")
            for filename, _ in expected_files:
                file_path = output_dir / filename
                if file_path.exists():
                    with open(file_path, 'r') as f:
                        current_first_line = f.readline().strip()
                    print(f"  {filename}: {current_first_line}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Haiku Streaming Demo - Create haiku with live streaming output",
        epilog="""
Examples:
  %(prog)s                                      # Create haiku
  %(prog)s --improve-titles                     # Create and improve titles
  %(prog)s --raw-log stream.json                # Save raw JSON stream
  %(prog)s --clean --improve-titles             # Clean, create, and improve
  %(prog)s --improve-titles --raw-log full.log  # All features
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean output directory before starting"
    )
    
    parser.add_argument(
        "--raw-log",
        type=str,
        default=None,
        help="Path to save raw JSON stream (line by line)"
    )
    
    parser.add_argument(
        "--improve-titles",
        action="store_true",
        help="Run title improvement phase after creating haiku"
    )
    
    args = parser.parse_args()
    
    if args.clean:
        import shutil
        output_dir = Path("output/haiku")
        if output_dir.exists():
            shutil.rmtree(output_dir)
            print("🧹 Cleaned output directory")
    
    asyncio.run(main(raw_log_path=args.raw_log, improve_titles=args.improve_titles))