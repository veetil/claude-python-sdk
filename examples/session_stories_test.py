#!/usr/bin/env python3
"""
Session Resume Test: Write 5 Short Stories and Improve Titles

This example demonstrates:
1. Writing 5 short stories in a single session
2. Using session resumption to improve each story's title
3. Maintaining context across multiple interactions
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.claude_sdk.session_client import SessionAwareClient
from src.claude_sdk.core.config import ClaudeConfig


async def extract_story_info(content: str) -> List[Dict[str, str]]:
    """Extract story titles and filenames from Claude's response"""
    stories = []
    lines = content.split('\n')
    
    for line in lines:
        # Look for patterns like "1. Title - filename.txt"
        if any(line.strip().startswith(f"{i}.") for i in range(1, 6)):
            # Extract title and filename
            parts = line.strip().split(' - ')
            if len(parts) >= 2:
                title_part = parts[0].split('. ', 1)
                if len(title_part) == 2:
                    title = title_part[1].strip()
                    filename = parts[1].strip()
                    stories.append({
                        'original_title': title,
                        'filename': filename,
                        'improved_title': None
                    })
    
    return stories


async def main():
    """Main test function"""
    print("=== Session Resume Test: Short Stories with Title Improvement ===\n")
    
    # Create output directory
    output_dir = Path("output/stories")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use custom config if available from command line
    if hasattr(sys.modules['__main__'], 'custom_config'):
        config = sys.modules['__main__'].custom_config
    else:
        # Default config
        config = ClaudeConfig(
            debug_mode=True,  # Show commands with session IDs
            enable_prefix_prompt=True,
        )
    
    # Get custom values from command line
    num_stories = getattr(sys.modules['__main__'], 'num_stories', 5)
    custom_timeout = getattr(sys.modules['__main__'], 'custom_timeout', 300.0)
    
    async with SessionAwareClient(config) as client:
        # Step 1: Write stories
        print(f"Step 1: Writing {num_stories} short stories")
        print("-" * 60)
        
        # Build story themes based on number requested
        themes = [
            "A sci-fi story about time travel",
            "A fantasy story about a magical forest", 
            "A mystery story about a missing painting",
            "A romance story about coffee shop encounters",
            "A horror story about an old mansion",
            "An adventure story about treasure hunting",
            "A comedy story about mistaken identity",
            "A thriller story about a conspiracy",
            "A historical fiction about ancient Rome",
            "A dystopian story about future society"
        ][:num_stories]
        
        # Build the prompt
        story_list = "\n".join([f"{i+1}. {theme}" for i, theme in enumerate(themes)])
        
        response1 = await client.query_with_session(
            f"""Write {num_stories} very short stories (each 100-150 words) on different themes and save them to output/stories/:
{story_list}
            
            For each story:
            - Give it a simple, basic title
            - Save to output/stories/story1.txt, story2.txt, etc.
            - Include the title at the top of each file
            
            After writing all stories, list them with format:
            1. [Title] - story1.txt
            2. [Title] - story2.txt
            etc.""",
            timeout=custom_timeout  # Use custom timeout from command line
        )
        
        session_id = response1.session_id
        print(f"\n✅ Session ID: {session_id}")
        print(f"📝 Response preview: {response1.content[:300]}...\n")
        
        # Extract story information
        stories = await extract_story_info(response1.content)
        
        if not stories:
            # Try to parse from the response differently
            print("⚠️  Couldn't extract story list, checking files directly...")
            stories = []
            for i in range(1, 6):
                filepath = output_dir / f"story{i}.txt"
                if filepath.exists():
                    # Read first line as title
                    with open(filepath, 'r') as f:
                        first_line = f.readline().strip()
                        stories.append({
                            'original_title': first_line,
                            'filename': f"story{i}.txt",
                            'improved_title': None
                        })
        
        print(f"📚 Found {len(stories)} stories:")
        for i, story in enumerate(stories, 1):
            print(f"   {i}. {story['original_title']} - {story['filename']}")
        
        # Step 2: Improve each title using session resumption
        print(f"\nStep 2: Improving titles using session resumption")
        print("-" * 60)
        
        for i, story in enumerate(stories, 1):
            print(f"\n📝 Improving title {i}/{len(stories)}: {story['original_title']}")
            
            # Resume session to improve this specific title
            response = await client.query_with_session(
                f"""Looking at the story in {story['filename']}, the current title is "{story['original_title']}".
                
                Please create a more engaging, creative, and compelling title that:
                - Better captures the essence of the story
                - Is more intriguing and memorable
                - Uses vivid or evocative language
                
                Update the story file with the new title (replace the first line).
                
                Respond with just: "New title: [your improved title]" """,
                resume_session_id=session_id  # Resume the same session
            )
            
            # Extract improved title
            if "New title:" in response.content:
                improved = response.content.split("New title:", 1)[1].strip()
                # Remove quotes if present
                improved = improved.strip('"').strip("'")
                story['improved_title'] = improved
                print(f"   ✨ Improved: {improved}")
            else:
                print(f"   ⚠️  Couldn't extract improved title")
        
        # Step 3: Summary
        print(f"\n\nStep 3: Summary of Improvements")
        print("=" * 60)
        print(f"Session ID used throughout: {session_id}\n")
        
        print("Title Improvements:")
        for i, story in enumerate(stories, 1):
            print(f"\n{i}. {story['filename']}")
            print(f"   Original:  {story['original_title']}")
            if story['improved_title']:
                print(f"   Improved:  {story['improved_title']}")
                print(f"   ✅ Title enhanced!")
            else:
                print(f"   ❌ No improvement captured")
        
        # Step 4: Verify files were updated
        print(f"\n\nStep 4: Verifying File Updates")
        print("-" * 60)
        
        for story in stories:
            filepath = output_dir / story['filename']
            if filepath.exists():
                with open(filepath, 'r') as f:
                    current_title = f.readline().strip()
                print(f"\n{story['filename']}:")
                print(f"  Current first line: {current_title}")
                if story['improved_title'] and story['improved_title'] in current_title:
                    print(f"  ✅ File updated with improved title!")
                else:
                    print(f"  ⚠️  File may not be updated")
        
        # Demonstrate one more interaction in the same session
        print(f"\n\nBonus: Creating a table of contents in the same session")
        print("-" * 60)
        
        response_final = await client.query_with_session(
            """Create a file output/stories/table_of_contents.md that lists all 5 stories with:
            - Their improved titles
            - A one-line description of each story
            - The filename for each
            
            Format it as a nice markdown table.""",
            resume_session_id=session_id
        )
        
        print(f"✅ Table of contents created in session: {session_id}")
        
        # Check if TOC was created
        toc_path = output_dir / "table_of_contents.md"
        if toc_path.exists():
            print(f"\n📄 Table of Contents Preview:")
            with open(toc_path, 'r') as f:
                preview = f.read()[:500]
                print(preview)
                if len(f.read()) > 500:
                    print("...")


async def test_auto_resume():
    """Test automatic session resumption feature"""
    print("\n\n=== Testing Auto-Resume Feature ===\n")
    
    async with SessionAwareClient() as client:
        # Create a story
        print("Creating initial story...")
        response1 = await client.query_with_session(
            "Write a 50-word story about a robot learning to paint. Save it as output/stories/robot_painter.txt"
        )
        
        print(f"Session: {response1.session_id}")
        
        # Auto-resume to add details
        print("\nAuto-resuming to add details...")
        response2 = await client.query_with_session(
            "Add a poetic subtitle to the robot painter story you just wrote",
            auto_resume_last=True  # Automatically use last session
        )
        
        print("✅ Successfully auto-resumed session")
        
        # One more auto-resume
        print("\nAuto-resuming again...")
        response3 = await client.query_with_session(
            "Add the author name 'By Claude' at the end of the robot painter story",
            auto_resume_last=True
        )
        
        print(f"✅ Completed 3 operations in session: {client.last_session_id}")


if __name__ == "__main__":
    import argparse
    
    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Claude SDK Session Resume Test - Write and improve short stories",
        epilog="""
Examples:
  %(prog)s                     # Run full demo with all features
  %(prog)s --stories 3         # Write only 3 stories
  %(prog)s --timeout 600       # Use 10-minute timeout
  %(prog)s --no-cleanup        # Keep existing stories
  %(prog)s --skip-auto-resume  # Skip auto-resume demo
  
Environment Variables:
  CLAUDE_API_KEY              # Your Claude API key
  CLAUDE_MODEL                # Model to use (default: claude-3-5-sonnet-20241022)
  CLAUDE_DEBUG                # Enable debug mode (true/false)
  CLAUDE_PREFIX_PROMPT_FILE   # Path to prefix prompt file
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Add arguments
    parser.add_argument(
        "--stories", "-s",
        type=int,
        default=5,
        help="Number of stories to write (default: 5)"
    )
    
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=300.0,
        help="Timeout in seconds for story generation (default: 300)"
    )
    
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't clean up existing stories before starting"
    )
    
    parser.add_argument(
        "--skip-auto-resume",
        action="store_true",
        help="Skip the auto-resume feature demo"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="output/stories",
        help="Output directory for stories (default: output/stories)"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode (shows commands and session IDs)"
    )
    
    parser.add_argument(
        "--no-prefix",
        action="store_true",
        help="Disable prefix prompt (faster but less capable)"
    )
    
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Claude model to use (overrides environment variable)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Update global variables based on arguments
    output_dir = Path(args.output_dir)
    
    # Clean up before starting (unless --no-cleanup)
    if not args.no_cleanup and output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        print(f"🧹 Cleaned up {output_dir}")
    
    # Create custom config based on arguments
    from claude_sdk import ClaudeConfig
    
    config_args = {
        "debug_mode": args.debug,
        "enable_prefix_prompt": not args.no_prefix,
        "verbose_logging": args.verbose,
    }
    
    if args.model:
        config_args["model"] = args.model
    
    # Override the global config
    import sys
    sys.modules['__main__'].custom_config = ClaudeConfig(**config_args)
    sys.modules['__main__'].custom_timeout = args.timeout
    sys.modules['__main__'].num_stories = args.stories
    
    print(f"🚀 Starting Claude SDK Session Test")
    print(f"📝 Stories to write: {args.stories}")
    print(f"⏱️  Timeout: {args.timeout}s")
    print(f"📁 Output directory: {args.output_dir}")
    print(f"🔧 Debug mode: {'ON' if args.debug else 'OFF'}")
    print(f"📄 Prefix prompt: {'ENABLED' if not args.no_prefix else 'DISABLED'}")
    if args.model:
        print(f"🤖 Model: {args.model}")
    print()
    
    # Modify main function to use arguments
    original_main = main
    
    async def main_with_args():
        # Temporarily modify the function to use our arguments
        import builtins
        original_path = Path
        
        # Monkey-patch to use custom output dir
        class CustomPath(original_path):
            def __new__(cls, *args, **kwargs):
                if args and args[0] == "output/stories":
                    return original_path.__new__(cls, args.output_dir)
                return original_path.__new__(cls, *args, **kwargs)
        
        builtins.Path = CustomPath
        
        try:
            # Run with custom config
            await original_main()
        finally:
            # Restore original Path
            builtins.Path = original_path
    
    # Run main test
    asyncio.run(main_with_args())
    
    # Run auto-resume test (unless skipped)
    if not args.skip_auto_resume:
        asyncio.run(test_auto_resume())
    else:
        print("\n📌 Skipped auto-resume demo")
    
    print(f"\n\n✅ All tests complete! Check {args.output_dir}/ for results.")