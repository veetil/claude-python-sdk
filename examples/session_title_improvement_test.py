#!/usr/bin/env python3
"""
Simple Session Test: Write Stories and Improve Titles

Demonstrates:
1. Writing 5 short stories with basic titles
2. Using session resume to improve each title
3. Verifying the improvements
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
    """Main test demonstrating session resumption for title improvements"""
    
    print("=== Session Test: Write 5 Stories, Then Improve Titles ===\n")
    
    # Setup
    output_dir = Path("output/stories")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure with debug mode to see session IDs
    config = ClaudeConfig(debug_mode=True)
    
    async with SessionAwareClient(config) as client:
        # STEP 1: Write 5 short stories with simple titles
        print("STEP 1: Writing 5 short stories with basic titles")
        print("-" * 60)
        
        initial_response = await client.query_with_session(
            """Please write 5 very short stories (50-75 words each) and save them to output/stories/.
            
            Stories to write:
            1. Time Travel Story - save as: output/stories/time_travel.txt
               Basic title: "The Time Machine"
            
            2. Magic Forest Story - save as: output/stories/magic_forest.txt  
               Basic title: "The Forest"
            
            3. Mystery Story - save as: output/stories/mystery.txt
               Basic title: "The Missing Item"
            
            4. Coffee Shop Romance - save as: output/stories/romance.txt
               Basic title: "Coffee Date"
            
            5. Haunted House Story - save as: output/stories/horror.txt
               Basic title: "The Old House"
            
            Put the title as the first line of each file, then the story.
            After creating all files, confirm with: "Created 5 stories with basic titles." """
        )
        
        # Capture the session ID
        session_id = initial_response.session_id
        print(f"\n✅ Initial session ID: {session_id}")
        print(f"Response: {initial_response.content[:200]}...")
        
        # Give it a moment for files to be created
        await asyncio.sleep(1)
        
        # STEP 2: Improve each title using session resumption
        print(f"\n\nSTEP 2: Improving titles using session resumption")
        print("=" * 60)
        
        # Define the stories and improvements we want
        stories = [
            {
                'file': 'time_travel.txt',
                'original': 'The Time Machine',
                'theme': 'time paradox and consequences'
            },
            {
                'file': 'magic_forest.txt', 
                'original': 'The Forest',
                'theme': 'enchantment and wonder'
            },
            {
                'file': 'mystery.txt',
                'original': 'The Missing Item',
                'theme': 'suspense and intrigue'
            },
            {
                'file': 'romance.txt',
                'original': 'Coffee Date',
                'theme': 'serendipity and connection'
            },
            {
                'file': 'horror.txt',
                'original': 'The Old House',
                'theme': 'dread and the supernatural'
            }
        ]
        
        improved_titles = []
        
        # Improve each title
        for i, story in enumerate(stories, 1):
            print(f"\n📝 Improving title {i}/5: '{story['original']}'")
            print(f"   File: {story['file']}")
            print(f"   Theme: {story['theme']}")
            
            # Resume the session to improve this specific title
            improvement_response = await client.query_with_session(
                f"""In the file output/stories/{story['file']}, you wrote a story with the title "{story['original']}".
                
                Please improve this title to be more engaging and evocative, capturing the theme of {story['theme']}.
                
                Update the first line of output/stories/{story['file']} with the new improved title.
                
                Reply with just: "Updated title to: [new title]" """,
                resume_session_id=session_id  # RESUME THE SAME SESSION
            )
            
            # Extract the improved title
            content = improvement_response.content
            if "Updated title to:" in content:
                new_title = content.split("Updated title to:", 1)[1].strip()
                new_title = new_title.strip('"').strip("'").strip()
                improved_titles.append({
                    'file': story['file'],
                    'original': story['original'],
                    'improved': new_title
                })
                print(f"   ✅ Improved to: '{new_title}'")
            else:
                print(f"   ⚠️  Couldn't extract improved title")
                improved_titles.append({
                    'file': story['file'],
                    'original': story['original'],
                    'improved': None
                })
        
        # STEP 3: Summary and Verification
        print(f"\n\nSTEP 3: Summary and Verification")
        print("=" * 60)
        print(f"All operations completed in session: {session_id}\n")
        
        print("Title Improvements:")
        print("-" * 60)
        for item in improved_titles:
            print(f"\n{item['file']}:")
            print(f"  Original:  {item['original']}")
            if item['improved']:
                print(f"  Improved:  {item['improved']}")
                print(f"  Change:    {'✅ Enhanced' if item['improved'] != item['original'] else '⚠️  No change'}")
        
        # STEP 4: Verify files exist and check content
        print(f"\n\nSTEP 4: File Verification")
        print("-" * 60)
        
        for item in improved_titles:
            filepath = output_dir / item['file']
            if filepath.exists():
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                    first_line = lines[0].strip() if lines else ""
                    word_count = len(' '.join(lines[1:]).split()) if len(lines) > 1 else 0
                
                print(f"\n{item['file']}:")
                print(f"  ✅ File exists")
                print(f"  Title in file: '{first_line}'")
                print(f"  Story length: ~{word_count} words")
                
                # Check if title was updated
                if item['improved'] and item['improved'] in first_line:
                    print(f"  ✅ Title successfully updated!")
                elif item['original'] in first_line:
                    print(f"  ⚠️  Still has original title")
            else:
                print(f"\n{item['file']}: ❌ File not found")
        
        # BONUS: One more operation in the same session
        print(f"\n\nBONUS: Creating an index in the same session")
        print("-" * 60)
        
        final_response = await client.query_with_session(
            """Create output/stories/index.txt that lists:
            - All 5 story files
            - Their current (improved) titles
            - A star rating (1-5 ⭐) for each based on how compelling the title is
            
            Format:
            filename.txt - "Title Here" - ⭐⭐⭐⭐⭐""",
            resume_session_id=session_id
        )
        
        print(f"✅ Index created in session: {session_id}")
        
        # Check the index
        index_path = output_dir / "index.txt"
        if index_path.exists():
            print(f"\n📄 Index content:")
            with open(index_path, 'r') as f:
                print(f.read())


async def test_session_context():
    """Test that session maintains context"""
    print("\n\n=== Testing Session Context Maintenance ===\n")
    
    async with SessionAwareClient() as client:
        # First query
        resp1 = await client.query_with_session(
            "Remember these numbers: 42, 17, 99. I'll ask about them later."
        )
        session_id = resp1.session_id
        print(f"Session: {session_id}")
        
        # Second query - should remember
        resp2 = await client.query_with_session(
            "What were those numbers I asked you to remember?",
            resume_session_id=session_id
        )
        
        print(f"Response: {resp2.content}")
        if any(num in resp2.content for num in ['42', '17', '99']):
            print("✅ Session context maintained!")
        else:
            print("⚠️  Numbers not found in response")


if __name__ == "__main__":
    # Clean up
    output_dir = Path("output/stories")
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
    
    # Run main test
    asyncio.run(main())
    
    # Run context test
    asyncio.run(test_session_context())
    
    print("\n✅ Tests complete! Check output/stories/ for the stories with improved titles.")