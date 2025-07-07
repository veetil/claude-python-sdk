#!/usr/bin/env python3
"""
Session Management Demo for Claude SDK

This example demonstrates:
1. Getting session ID from Claude responses
2. Resuming sessions with -r flag
3. Error correction within the same session
"""

import asyncio
import os
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.claude_sdk.session_client import SessionAwareClient, SessionAwareResponse


async def check_output_files(expected_files: list[str]) -> list[str]:
    """Check which files are missing from output directory"""
    output_dir = Path("output")
    missing_files = []
    
    for file_name in expected_files:
        file_path = output_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
    
    return missing_files


async def example_with_error_correction():
    """
    Demonstrates the exact use case:
    1. Request to write files to output/
    2. System checks and finds files missing
    3. Corrects the error using same session with -r flag
    """
    print("=== Session Management Demo ===\n")
    
    # Create output directory if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    async with SessionAwareClient() as client:
        # Step 1: Initial request (might have wrong path)
        print("Step 1: Initial request to create files")
        response1 = await client.query_with_session(
            "Write Python code for the following tasks and save to files:\n"
            "1. Sorting algorithms (bubble sort, quick sort) \n"
            "2. Binary search implementation\n"
            "3. Linked list class"
        )
        
        session_id = response1.session_id
        print(f"Response received. Session ID: {session_id}")
        print(f"Content preview: {response1.content[:200]}...\n")
        
        # Step 2: System checks for files
        print("Step 2: Checking for files in output/ directory...")
        expected_files = ["sort.py", "binary_search.py", "linked_list.py"]
        missing_files = await check_output_files(expected_files)
        
        if missing_files:
            print(f"ERROR: Missing files in output/: {missing_files}")
            
            # Step 3: Correct the error using same session
            print(f"\nStep 3: Correcting error in session {session_id}")
            response2 = await client.query_with_session(
                f"ERROR - You need to write the files to the correct folder which is 'output/'. "
                f"Please create the following files in the output/ directory:\n"
                f"- output/sort.py (with bubble sort and quick sort)\n"
                f"- output/binary_search.py (with binary search implementation)\n"
                f"- output/linked_list.py (with linked list class)",
                resume_session_id=session_id  # Resume the same session
            )
            
            print(f"Correction sent in session: {session_id}")
            print("Claude should now write the files to the correct location.")
            
            # Step 4: Verify files were created
            print("\nStep 4: Re-checking for files...")
            missing_files_after = await check_output_files(expected_files)
            
            if not missing_files_after:
                print("✅ SUCCESS: All files created in output/ directory!")
                for file_name in expected_files:
                    file_path = output_dir / file_name
                    if file_path.exists():
                        size = file_path.stat().st_size
                        print(f"  - {file_name}: {size} bytes")
            else:
                print(f"❌ Still missing files: {missing_files_after}")
        else:
            print("✅ All files already exist in output/ directory!")


async def example_multi_step_workflow():
    """
    Demonstrates a multi-step workflow using session continuity
    """
    print("\n\n=== Multi-Step Workflow Demo ===\n")
    
    async with SessionAwareClient() as client:
        # Step 1: Create project structure
        print("Step 1: Creating project structure")
        response1 = await client.query_with_session(
            "Create a Python package structure in output/my_package/ with:\n"
            "- __init__.py\n"
            "- core.py\n" 
            "- utils.py\n"
            "- tests/ directory with __init__.py"
        )
        session_id = response1.session_id
        print(f"Session ID: {session_id}")
        
        # Step 2: Add core functionality
        print(f"\nStep 2: Adding core functionality (session: {session_id})")
        response2 = await client.query_with_session(
            "In output/my_package/core.py, implement a Calculator class with "
            "methods for add, subtract, multiply, and divide",
            auto_resume_last=True  # Automatically use last session
        )
        
        # Step 3: Add utilities
        print(f"\nStep 3: Adding utilities (session: {session_id})")
        response3 = await client.query_with_session(
            "In output/my_package/utils.py, add helper functions for:\n"
            "- validate_number(value) - checks if value is a valid number\n"
            "- format_result(result) - formats result to 2 decimal places",
            resume_session_id=session_id  # Explicitly specify session
        )
        
        # Step 4: Add tests
        print(f"\nStep 4: Adding tests (session: {session_id})")
        response4 = await client.query_with_session(
            "Create output/my_package/tests/test_calculator.py with "
            "unit tests for the Calculator class",
            auto_resume_last=True
        )
        
        print(f"\n✅ Completed multi-step workflow in session: {session_id}")


async def example_validation_workflow():
    """
    Demonstrates validation and retry within same session
    """
    print("\n\n=== Validation and Retry Demo ===\n")
    
    async def validate_file_contains(file_path: str, required_content: list[str]) -> bool:
        """Check if file contains required content"""
        path = Path(file_path)
        if not path.exists():
            return False
        
        content = path.read_text()
        return all(req in content for req in required_content)
    
    async with SessionAwareClient() as client:
        # Request implementation with specific requirements
        print("Requesting implementation with specific requirements...")
        response = await client.query_with_session(
            "Create output/config_parser.py with a ConfigParser class that:\n"
            "1. Has a load_json() method\n"
            "2. Has a load_yaml() method\n"
            "3. Has proper error handling\n"
            "4. Includes docstrings"
        )
        session_id = response.session_id
        print(f"Session ID: {session_id}")
        
        # Validate the implementation
        required_methods = ["load_json", "load_yaml", "try:", "except:", '"""']
        if not validate_file_contains("output/config_parser.py", required_methods):
            print("\n❌ Validation failed! Missing required elements.")
            
            # Retry with more specific instructions in same session
            print(f"Retrying with clarification in session {session_id}...")
            response2 = await client.query_with_session(
                "The ConfigParser class is missing some requirements. Please update output/config_parser.py to ensure:\n"
                "1. load_json() method uses json.load() and handles FileNotFoundError\n"
                "2. load_yaml() method is present (can be a placeholder that raises NotImplementedError)\n"
                "3. Both methods have proper docstrings\n"
                "4. Include try/except blocks for error handling",
                resume_session_id=session_id
            )
            
            # Re-validate
            if validate_file_contains("output/config_parser.py", required_methods):
                print("✅ Validation passed after correction!")
            else:
                print("❌ Still missing requirements")
        else:
            print("✅ Validation passed on first attempt!")


async def main():
    """Run all examples"""
    # Clean up output directory before starting
    output_dir = Path("output")
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Run examples
    await example_with_error_correction()
    await example_multi_step_workflow()
    await example_validation_workflow()
    
    print("\n\n=== Demo Complete ===")
    print("Check the output/ directory for created files!")


if __name__ == "__main__":
    asyncio.run(main())