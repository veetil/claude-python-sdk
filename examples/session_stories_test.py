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
    
    # Configure client
    config = ClaudeConfig(
        debug_mode=True,  # Show commands with session IDs
        enable_prefix_prompt=True,
    )
    
    async with SessionAwareClient(config) as client:
        # Step 1: Write 5 short stories
        print("Step 1: Writing 5 short stories")
        print("-" * 60)
        
        response1 = await client.query_with_session(
            """Write 5 very short stories (each 100-150 words) on different themes and save them to output/stories/:
            1. A sci-fi story about time travel
            2. A fantasy story about a magical forest
            3. A mystery story about a missing painting
            4. A romance story about coffee shop encounters
            5. A horror story about an old mansion
            
            For each story:
            - Give it a simple, basic title
            - Save to output/stories/story1.txt, story2.txt, etc.
            - Include the title at the top of each file
            
            After writing all stories, list them with format:
            1. [Title] - story1.txt
            2. [Title] - story2.txt
            etc."""
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
    # Clean up before starting
    output_dir = Path("output/stories")
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
    
    # Run main test
    asyncio.run(main())
    
    # Run auto-resume test
    asyncio.run(test_auto_resume())
    
    print("\n\n✅ All tests complete! Check output/stories/ for results.")