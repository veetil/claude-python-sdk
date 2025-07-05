"""
Stream JSON Output Example

This example demonstrates how to capture and display the raw JSON streaming
output from Claude CLI commands. It shows the real-time data flow and helps
understand the structure of Claude's streaming responses.
"""

import asyncio
import json
import time
from typing import Dict, Any, List
from claude_sdk import ClaudeClient, ClaudeConfig
from claude_sdk.core.types import OutputFormat, StreamChunk
from claude_sdk.core.subprocess_wrapper import CommandBuilder


class StreamJSONCollector:
    """Collects and parses streaming JSON output."""
    
    def __init__(self):
        self.chunks: List[StreamChunk] = []
        self.json_objects: List[Dict[str, Any]] = []
        self.raw_output: List[str] = []
        self.start_time = time.time()
    
    def add_chunk(self, chunk: StreamChunk) -> None:
        """Add a chunk and try to parse any complete JSON objects."""
        self.chunks.append(chunk)
        self.raw_output.append(chunk.content)
        
        # Try to parse JSON objects from the content
        # Stream JSON often comes line by line
        lines = chunk.content.strip().split('\n')
        for line in lines:
            if line.strip():
                try:
                    json_obj = json.loads(line)
                    self.json_objects.append({
                        'timestamp': time.time() - self.start_time,
                        'type': chunk.chunk_type,
                        'data': json_obj
                    })
                except json.JSONDecodeError:
                    # Not a complete JSON object yet
                    pass
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of collected data."""
        return {
            'total_chunks': len(self.chunks),
            'total_json_objects': len(self.json_objects),
            'duration': time.time() - self.start_time,
            'chunk_types': list(set(c.chunk_type for c in self.chunks))
        }


async def stream_json_example(client: ClaudeClient, prompt: str, example_name: str):
    """
    Execute a command with JSON streaming output and display the results.
    
    Args:
        client: Claude client instance
        prompt: The prompt to send to Claude
        example_name: Name for this example
    """
    print(f"\n{'='*60}")
    print(f"Example: {example_name}")
    print(f"{'='*60}")
    print(f"Prompt: {prompt[:100]}...")
    print(f"\nStreaming JSON output:\n")
    
    collector = StreamJSONCollector()
    
    # Build command with JSON streaming output
    builder = CommandBuilder()
    command = (builder
               .add_prompt(prompt)
               .set_output_format("stream-json")
               .build())
    
    try:
        # Stream the command execution
        chunk_count = 0
        async for chunk in client._subprocess_wrapper.execute_streaming(command):
            chunk_count += 1
            collector.add_chunk(chunk)
            
            # Display raw chunk data
            print(f"[Chunk {chunk_count:03d}] Type: {chunk.chunk_type:6s} | "
                  f"Size: {len(chunk.content):4d} | "
                  f"Time: {time.time() - collector.start_time:.2f}s")
            
            # Display the content (truncated if too long)
            content_preview = chunk.content.strip()
            if len(content_preview) > 100:
                content_preview = content_preview[:97] + "..."
            if content_preview:
                print(f"  Content: {content_preview}")
            
            # If we parsed a JSON object, show it
            if collector.json_objects and collector.json_objects[-1]['timestamp'] > chunk_count - 1:
                latest_json = collector.json_objects[-1]['data']
                print(f"  Parsed JSON: {json.dumps(latest_json, indent=2)[:200]}...")
        
        # Show summary
        summary = collector.get_summary()
        print(f"\n{'='*60}")
        print(f"Stream Summary:")
        print(f"  Total chunks: {summary['total_chunks']}")
        print(f"  JSON objects: {summary['total_json_objects']}")
        print(f"  Duration: {summary['duration']:.2f} seconds")
        print(f"  Chunk types: {', '.join(summary['chunk_types'])}")
        
        # Show all parsed JSON objects
        print(f"\nParsed JSON Objects:")
        for i, obj in enumerate(collector.json_objects[:5]):  # Show first 5
            print(f"\n  Object {i+1} (at {obj['timestamp']:.2f}s):")
            print(f"    {json.dumps(obj['data'], indent=4)[:300]}...")
        
        if len(collector.json_objects) > 5:
            print(f"\n  ... and {len(collector.json_objects) - 5} more objects")
        
    except Exception as e:
        print(f"Error: {e}")


async def compare_output_formats(client: ClaudeClient):
    """Compare different output formats for the same prompt."""
    prompt = "What are the benefits of async programming in Python? List 3 key points."
    
    print("\n" + "="*80)
    print("OUTPUT FORMAT COMPARISON")
    print("="*80)
    
    # 1. Regular text output
    print("\n1. REGULAR TEXT OUTPUT:")
    print("-" * 40)
    response = await client.query(prompt, output_format=OutputFormat.TEXT)
    print(response.content[:300] + "..." if len(response.content) > 300 else response.content)
    
    # 2. JSON output (non-streaming)
    print("\n2. JSON OUTPUT (non-streaming):")
    print("-" * 40)
    response = await client.query(prompt, output_format=OutputFormat.JSON)
    try:
        json_data = json.loads(response.content)
        print(json.dumps(json_data, indent=2)[:500] + "...")
    except json.JSONDecodeError:
        print(f"Raw output: {response.content[:300]}...")
    
    # 3. Stream JSON output
    print("\n3. STREAM JSON OUTPUT:")
    print("-" * 40)
    await stream_json_example(client, prompt, "Async Programming Benefits")


async def stream_code_generation():
    """Demonstrate streaming JSON output for code generation."""
    async with ClaudeClient() as client:
        prompt = """Write a Python function that implements a binary search tree with insert and search methods. 
        Include comments explaining the logic."""
        
        await stream_json_example(client, prompt, "Code Generation Stream")


async def stream_multi_turn_conversation():
    """Demonstrate streaming JSON in a multi-turn conversation."""
    async with ClaudeClient() as client:
        prompts = [
            "Let's discuss data structures. What is a hash table?",
            "How does it handle collisions?",
            "Can you show a simple Python implementation?"
        ]
        
        print("\n" + "="*80)
        print("MULTI-TURN CONVERSATION WITH STREAM JSON")
        print("="*80)
        
        session_id = None
        for i, prompt in enumerate(prompts, 1):
            print(f"\n{'='*60}")
            print(f"Turn {i}: {prompt}")
            print(f"{'='*60}")
            
            # Build command with session continuation
            builder = CommandBuilder()
            if session_id:
                builder.set_session_id(session_id)
            
            command = (builder
                      .add_prompt(prompt)
                      .set_output_format("stream-json")
                      .build())
            
            collector = StreamJSONCollector()
            
            async for chunk in client._subprocess_wrapper.execute_streaming(command):
                collector.add_chunk(chunk)
                
                # Look for session ID in JSON objects
                for obj in collector.json_objects:
                    if 'session_id' in obj['data']:
                        session_id = obj['data']['session_id']
            
            print(f"\nCollected {len(collector.json_objects)} JSON objects")
            print(f"Session ID: {session_id}")


async def analyze_stream_timing():
    """Analyze the timing of streaming chunks."""
    async with ClaudeClient() as client:
        prompt = "Count from 1 to 10 slowly, explaining each number's significance in mathematics."
        
        print("\n" + "="*80)
        print("STREAM TIMING ANALYSIS")
        print("="*80)
        print(f"Prompt: {prompt}")
        print("\nChunk arrival timing:")
        print("-" * 40)
        
        builder = CommandBuilder()
        command = (builder
                  .add_prompt(prompt)
                  .set_output_format("stream-json")
                  .build())
        
        chunk_times = []
        start_time = time.time()
        last_time = start_time
        
        async for chunk in client._subprocess_wrapper.execute_streaming(command):
            current_time = time.time()
            elapsed = current_time - start_time
            delta = current_time - last_time
            last_time = current_time
            
            chunk_times.append({
                'elapsed': elapsed,
                'delta': delta,
                'size': len(chunk.content),
                'type': chunk.chunk_type
            })
            
            print(f"[{elapsed:6.2f}s] +{delta:5.3f}s | "
                  f"{chunk.chunk_type:6s} | "
                  f"{len(chunk.content):4d} bytes")
        
        # Statistics
        print(f"\n{'='*40}")
        print("Timing Statistics:")
        print(f"  Total time: {chunk_times[-1]['elapsed']:.2f}s")
        print(f"  Total chunks: {len(chunk_times)}")
        print(f"  Avg chunk interval: {sum(ct['delta'] for ct in chunk_times[1:]) / len(chunk_times[1:]):.3f}s")
        print(f"  Avg chunk size: {sum(ct['size'] for ct in chunk_times) / len(chunk_times):.1f} bytes")


async def main():
    """Run all streaming JSON examples."""
    print("🌊 Claude SDK - Streaming JSON Output Examples")
    print("=" * 80)
    
    # Configure for better debugging
    config = ClaudeConfig(
        debug_mode=True,
        verbose_logging=True,
        default_timeout=60.0,
    )
    
    async with ClaudeClient(config=config) as client:
        # Run examples
        await compare_output_formats(client)
        await asyncio.sleep(1)  # Brief pause between examples
        
        await stream_code_generation()
        await asyncio.sleep(1)
        
        await stream_multi_turn_conversation()
        await asyncio.sleep(1)
        
        await analyze_stream_timing()
    
    print("\n" + "="*80)
    print("✅ All streaming JSON examples completed!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())