"""
Parallel Haiku Generation Example

This script demonstrates parallel task execution using the Claude Python SDK.
It launches 5 concurrent tasks to generate haikus about different animals,
then uses a 6th task to organize and format the results.
"""

import asyncio
import json
import re
from typing import List, Dict, Tuple
from claude_sdk import ClaudeClient, ClaudeConfig
from claude_sdk.core.types import OutputFormat


# Animals for our haikus
ANIMALS = ["elephant", "butterfly", "ocean whale", "mountain eagle", "forest wolf"]


async def generate_haiku(client: ClaudeClient, animal: str, task_id: int) -> Tuple[str, str]:
    """
    Generate a haiku about a specific animal.
    
    Args:
        client: Claude client instance
        animal: Animal to write haiku about
        task_id: Task identifier for tracking
        
    Returns:
        Tuple of (animal, haiku text)
    """
    print(f"Task {task_id}: Starting haiku generation for {animal}...")
    
    prompt = f"""Write a traditional haiku (3 lines, 5-7-5 syllables) about a {animal}. 
    Only return the haiku itself, no explanation or title."""
    
    try:
        response = await client.query(prompt)
        haiku = response.content.strip()
        print(f"Task {task_id}: Completed haiku for {animal}")
        return (animal, haiku)
    except Exception as e:
        print(f"Task {task_id}: Failed to generate haiku for {animal}: {e}")
        return (animal, f"Failed to generate haiku: {str(e)}")


async def organize_haikus(client: ClaudeClient, haikus: List[Tuple[str, str]]) -> str:
    """
    Organize haikus into a formatted markdown document.
    
    Args:
        client: Claude client instance
        haikus: List of (animal, haiku) tuples
        
    Returns:
        Formatted markdown string
    """
    print("Task 6: Organizing haikus into markdown format...")
    
    # Create a prompt with all haikus
    haiku_text = "\n\n".join([f"{animal}:\n{haiku}" for animal, haiku in haikus])
    
    prompt = f"""I have these haikus about animals:

{haiku_text}

Please organize these into a beautiful markdown document with:
1. A title "Animal Haikus Collection"
2. A brief introduction
3. Each haiku in its own section with the animal name as a heading
4. Proper formatting and spacing
5. A concluding note about the beauty of nature

Return only the markdown text."""

    try:
        response = await client.query(prompt)
        return response.content
    except Exception as e:
        # Fallback: create markdown manually if Claude fails
        print(f"Task 6: Claude organization failed, using fallback: {e}")
        return create_fallback_markdown(haikus)


def create_fallback_markdown(haikus: List[Tuple[str, str]]) -> str:
    """Create a fallback markdown document if Claude organization fails."""
    md = "# Animal Haikus Collection\n\n"
    md += "A collection of haikus celebrating the beauty and essence of various animals.\n\n"
    md += "---\n\n"
    
    for animal, haiku in haikus:
        md += f"## {animal.title()}\n\n"
        md += f"```\n{haiku}\n```\n\n"
    
    md += "---\n\n"
    md += "*These haikus capture fleeting moments in nature, each animal's essence distilled into seventeen syllables.*\n"
    
    return md


async def main():
    """Main function to coordinate parallel haiku generation."""
    print("🎋 Parallel Haiku Generator 🎋")
    print("=" * 50)
    
    # Configure client with custom settings for parallel execution
    config = ClaudeConfig(
        max_concurrent_sessions=6,  # Allow 6 concurrent operations
        default_timeout=30.0,
        debug_mode=False,
    )
    
    async with ClaudeClient(config=config) as client:
        # Start timing
        start_time = asyncio.get_event_loop().time()
        
        # Launch 5 parallel tasks for haiku generation
        print(f"\nLaunching {len(ANIMALS)} parallel haiku generation tasks...")
        
        haiku_tasks = [
            generate_haiku(client, animal, i + 1)
            for i, animal in enumerate(ANIMALS)
        ]
        
        # Wait for all haikus to be generated
        haiku_results = await asyncio.gather(*haiku_tasks, return_exceptions=True)
        
        # Filter out any errors and collect successful haikus
        successful_haikus = []
        for result in haiku_results:
            if isinstance(result, tuple) and len(result) == 2:
                successful_haikus.append(result)
            else:
                print(f"Error in haiku generation: {result}")
        
        print(f"\nSuccessfully generated {len(successful_haikus)} haikus")
        
        # Launch the 6th task to organize haikus
        organized_markdown = await organize_haikus(client, successful_haikus)
        
        # Calculate total time
        total_time = asyncio.get_event_loop().time() - start_time
        
        # Save the result
        output_file = "animal_haikus.md"
        with open(output_file, 'w') as f:
            f.write(organized_markdown)
        
        print(f"\n✅ All tasks completed in {total_time:.2f} seconds")
        print(f"📝 Haikus saved to: {output_file}")
        
        # Display the organized haikus
        print("\n" + "=" * 50)
        print("FINAL RESULT:")
        print("=" * 50)
        print(organized_markdown)


async def demonstrate_parallel_efficiency():
    """Demonstrate the efficiency of parallel vs sequential execution."""
    print("\n\n🔬 Parallel vs Sequential Comparison")
    print("=" * 50)
    
    config = ClaudeConfig(max_concurrent_sessions=5)
    
    async with ClaudeClient(config=config) as client:
        # Sequential execution
        print("\nSequential execution (for comparison):")
        seq_start = asyncio.get_event_loop().time()
        
        for i, animal in enumerate(ANIMALS[:3]):  # Just 3 for demo
            await generate_haiku(client, animal, i + 1)
        
        seq_time = asyncio.get_event_loop().time() - seq_start
        print(f"Sequential time for 3 haikus: {seq_time:.2f} seconds")
        
        # Parallel execution
        print("\nParallel execution:")
        par_start = asyncio.get_event_loop().time()
        
        tasks = [generate_haiku(client, animal, i + 1) for i, animal in enumerate(ANIMALS[:3])]
        await asyncio.gather(*tasks)
        
        par_time = asyncio.get_event_loop().time() - par_start
        print(f"Parallel time for 3 haikus: {par_time:.2f} seconds")
        
        print(f"\n⚡ Speedup: {seq_time / par_time:.2f}x faster with parallel execution!")


if __name__ == "__main__":
    # Run the main haiku generation
    asyncio.run(main())
    
    # Optionally demonstrate parallel efficiency
    # asyncio.run(demonstrate_parallel_efficiency())