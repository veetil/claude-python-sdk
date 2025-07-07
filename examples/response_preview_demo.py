#!/usr/bin/env python3
"""
Response Preview Demo - Shows different ways to preview Claude's responses

Demonstrates:
- Basic response preview with character limits
- Line-based preview
- Smart preview with word boundaries
- Streaming preview
- JSON response preview
"""

import asyncio
import json
import os
import sys
from typing import List, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.claude_sdk.session_client import SessionAwareClient
from src.claude_sdk.core.config import ClaudeConfig, OutputFormat


def preview_response(content: str, max_chars: int = 200, suffix: str = "...") -> str:
    """
    Create a preview of response content.
    
    Args:
        content: Full response content
        max_chars: Maximum characters to show
        suffix: String to append if truncated
    
    Returns:
        Preview string
    """
    if len(content) <= max_chars:
        return content
    
    # Truncate at word boundary if possible
    preview = content[:max_chars]
    last_space = preview.rfind(' ')
    if last_space > max_chars * 0.8:  # If space is reasonably close to end
        preview = preview[:last_space]
    
    return preview + suffix


def preview_lines(content: str, max_lines: int = 5, max_chars_per_line: int = 80) -> str:
    """
    Preview response by showing first N lines.
    
    Args:
        content: Full response content
        max_lines: Maximum lines to show
        max_chars_per_line: Max characters per line
    
    Returns:
        Line-based preview
    """
    lines = content.split('\n')
    preview_lines = []
    
    for i, line in enumerate(lines[:max_lines]):
        if len(line) > max_chars_per_line:
            line = line[:max_chars_per_line-3] + "..."
        preview_lines.append(line)
    
    result = '\n'.join(preview_lines)
    
    if len(lines) > max_lines:
        result += f"\n... ({len(lines) - max_lines} more lines)"
    
    return result


def smart_preview(content: str, target_length: int = 300) -> dict:
    """
    Create a smart preview with metadata.
    
    Returns dict with:
        - preview: The preview text
        - total_length: Total content length
        - total_lines: Total line count
        - truncated: Whether content was truncated
    """
    lines = content.split('\n')
    
    # Try to include complete sentences/lines
    preview = ""
    line_count = 0
    
    for line in lines:
        if len(preview) + len(line) + 1 > target_length:
            break
        preview += line + '\n'
        line_count += 1
    
    preview = preview.rstrip()
    
    return {
        'preview': preview,
        'total_length': len(content),
        'total_lines': len(lines),
        'preview_lines': line_count,
        'truncated': len(content) > len(preview)
    }


async def demo_basic_preview():
    """Demonstrate basic response preview"""
    print("=== Basic Response Preview ===\n")
    
    config = ClaudeConfig(
        enable_prefix_prompt=False,  # Faster without prefix
        debug_mode=True
    )
    
    async with SessionAwareClient(config) as client:
        # Get a response
        response = await client.query_with_session(
            "Write a paragraph about the importance of clean code in software development.",
            timeout=30.0
        )
        
        # Show different preview lengths
        print("Full response length:", len(response.content), "characters")
        print("\n--- 100 character preview ---")
        print(preview_response(response.content, max_chars=100))
        
        print("\n--- 200 character preview ---")
        print(preview_response(response.content, max_chars=200))
        
        print("\n--- 300 character preview (word boundary) ---")
        print(preview_response(response.content, max_chars=300))


async def demo_line_preview():
    """Demonstrate line-based preview"""
    print("\n\n=== Line-Based Preview ===\n")
    
    async with SessionAwareClient() as client:
        # Get a multi-line response
        response = await client.query_with_session(
            "List 10 programming best practices, one per line",
            timeout=30.0
        )
        
        print("--- First 3 lines ---")
        print(preview_lines(response.content, max_lines=3))
        
        print("\n--- First 5 lines (with truncation) ---")
        print(preview_lines(response.content, max_lines=5, max_chars_per_line=50))


async def demo_smart_preview():
    """Demonstrate smart preview with metadata"""
    print("\n\n=== Smart Preview with Metadata ===\n")
    
    async with SessionAwareClient() as client:
        # Get a structured response
        response = await client.query_with_session(
            """Create a Python function that calculates fibonacci numbers.
            Include:
            1. Function definition
            2. Docstring
            3. Example usage
            4. Time complexity explanation""",
            timeout=30.0
        )
        
        preview_info = smart_preview(response.content, target_length=400)
        
        print("Preview Metadata:")
        print(f"  Total length: {preview_info['total_length']} characters")
        print(f"  Total lines: {preview_info['total_lines']}")
        print(f"  Preview lines: {preview_info['preview_lines']}")
        print(f"  Truncated: {'Yes' if preview_info['truncated'] else 'No'}")
        
        print("\nContent Preview:")
        print("-" * 50)
        print(preview_info['preview'])
        if preview_info['truncated']:
            print("-" * 50)
            print("... (content truncated)")


async def demo_streaming_preview():
    """Demonstrate preview during streaming"""
    print("\n\n=== Streaming Response Preview ===\n")
    
    async with SessionAwareClient() as client:
        print("Streaming response (showing first 500 chars):\n")
        
        collected = []
        preview_shown = False
        char_count = 0
        
        async for chunk in client.stream_query(
            "Write a detailed explanation of how async/await works in Python",
            timeout=60.0
        ):
            collected.append(chunk)
            char_count += len(chunk)
            
            # Show preview once we have enough content
            if not preview_shown and char_count >= 500:
                current_content = ''.join(collected)
                print("\n--- Preview (first 500 chars) ---")
                print(preview_response(current_content, max_chars=500))
                print("\n... (streaming continues)")
                preview_shown = True
            
            # Show progress dots
            if char_count % 100 == 0:
                print(".", end='', flush=True)
        
        print(f"\n\nStreaming complete. Total: {char_count} characters")


async def demo_json_preview():
    """Demonstrate preview of JSON responses"""
    print("\n\n=== JSON Response Preview ===\n")
    
    config = ClaudeConfig(
        default_output_format=OutputFormat.STREAM_JSON,
        debug_mode=True
    )
    
    async with SessionAwareClient(config) as client:
        # Get response with detailed metadata
        response = await client.query_with_session(
            "What is 2+2? Respond with just the number.",
            timeout=30.0
        )
        
        print("Response Content:", response.content)
        print("\nResponse Metadata Preview:")
        
        # Pretty print metadata
        metadata_preview = {
            'session_id': response.session_id,
            'exit_code': response.metadata.get('exit_code'),
            'duration': response.metadata.get('duration'),
            'output_format': response.metadata.get('output_format'),
            'is_error': response.metadata.get('is_error', False)
        }
        
        print(json.dumps(metadata_preview, indent=2))
        
        # If we have raw JSON, show that too
        if hasattr(response, 'raw_json') and response.raw_json:
            print("\nRaw JSON Preview (first 200 chars):")
            json_str = json.dumps(response.raw_json)
            print(preview_response(json_str, max_chars=200))


async def demo_custom_preview_formats():
    """Demonstrate custom preview formats"""
    print("\n\n=== Custom Preview Formats ===\n")
    
    async with SessionAwareClient() as client:
        # Get a code response
        response = await client.query_with_session(
            "Write a Python class for a simple todo list with add, remove, and list methods",
            timeout=30.0
        )
        
        # Code-aware preview (show first function/class)
        lines = response.content.split('\n')
        code_preview = []
        in_code = False
        indent_level = 0
        
        for line in lines:
            if line.strip().startswith('class ') or line.strip().startswith('def '):
                in_code = True
                indent_level = len(line) - len(line.lstrip())
            
            if in_code:
                code_preview.append(line)
                
                # Stop at next class/function or dedent
                if len(code_preview) > 1:
                    current_indent = len(line) - len(line.lstrip()) if line.strip() else indent_level
                    if line.strip() and current_indent <= indent_level and not line.strip().startswith('def '):
                        break
        
        print("--- Code Structure Preview ---")
        print('\n'.join(code_preview[:10]))  # First 10 lines of first class/function
        if len(code_preview) > 10:
            print("    ...")
        
        # Summary preview (extract key points)
        print("\n--- Summary Preview ---")
        summary_lines = []
        for line in lines:
            line = line.strip()
            if any(marker in line for marker in ['class ', 'def ', '# ', 'TODO:', 'NOTE:']):
                if line:
                    summary_lines.append(f"• {line}")
        
        print('\n'.join(summary_lines[:5]))
        if len(summary_lines) > 5:
            print(f"... and {len(summary_lines) - 5} more items")


async def main():
    """Run all preview demonstrations"""
    print("🔍 Claude SDK Response Preview Demo")
    print("=" * 50)
    
    demos = [
        ("Basic Preview", demo_basic_preview),
        ("Line-based Preview", demo_line_preview),
        ("Smart Preview", demo_smart_preview),
        ("Streaming Preview", demo_streaming_preview),
        ("JSON Preview", demo_json_preview),
        ("Custom Formats", demo_custom_preview_formats),
    ]
    
    for i, (name, demo_func) in enumerate(demos):
        if i > 0:
            input(f"\nPress Enter to continue to {name}...")
        
        try:
            await demo_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
    
    print("\n\n✅ All preview demos complete!")


if __name__ == "__main__":
    asyncio.run(main())