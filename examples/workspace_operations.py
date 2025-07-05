"""
Workspace operations examples for the Claude Python SDK.

This script demonstrates how to use workspaces for secure file operations
and isolated execution environments.
"""

import asyncio
import tempfile
from pathlib import Path
from claude_sdk import ClaudeClient
from claude_sdk.core.workspace import create_workspace


async def basic_workspace_example():
    """Example of basic workspace usage."""
    print("=== Basic Workspace Example ===")
    
    # Create some sample files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a Python file
        python_file = temp_path / "hello.py"
        python_file.write_text("""
def greet(name):
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(greet("World"))
""")
        
        # Create a README
        readme_file = temp_path / "README.md"
        readme_file.write_text("""
# Sample Project

This is a simple Python project for demonstration.

## Usage

Run the hello.py script to see a greeting.
""")
        
        async with ClaudeClient() as client:
            # Create workspace with files
            async with client.create_workspace(
                workspace_id="code_review",
                copy_files=[str(python_file), str(readme_file)]
            ) as workspace:
                
                print(f"Created workspace: {workspace.workspace_id}")
                print(f"Workspace path: {workspace.path}")
                
                # Analyze the files in the workspace
                response = await client.query(
                    "Please review this Python code for best practices and suggestions",
                    workspace_id=workspace.workspace_id,
                    files=["hello.py", "README.md"]
                )
                
                print(f"Analysis: {response.content}")


async def file_processing_workflow():
    """Example of processing multiple files in a workspace."""
    print("\n=== File Processing Workflow ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create multiple Python files
        files_to_create = {
            "main.py": """
import utils
from config import DATABASE_URL

def main():
    print("Starting application...")
    utils.setup_logging()
    utils.connect_database(DATABASE_URL)
    print("Application ready!")

if __name__ == "__main__":
    main()
""",
            "utils.py": """
import logging
import sqlite3

def setup_logging():
    logging.basicConfig(level=logging.INFO)

def connect_database(url):
    # This is a mock implementation
    conn = sqlite3.connect(":memory:")
    logging.info("Connected to database")
    return conn
""",
            "config.py": """
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")
""",
            "requirements.txt": """
requests>=2.28.0
flask>=2.2.0
sqlite3
"""
        }
        
        # Write all files
        file_paths = []
        for filename, content in files_to_create.items():
            file_path = temp_path / filename
            file_path.write_text(content)
            file_paths.append(str(file_path))
        
        async with ClaudeClient() as client:
            async with client.create_workspace(
                copy_files=file_paths
            ) as workspace:
                
                print(f"Processing {len(file_paths)} files in workspace")
                
                # Comprehensive code analysis
                analysis_response = await client.query(
                    "Analyze this Python project structure. Check for:\n"
                    "1. Code organization and modularity\n"
                    "2. Security issues (especially in config.py)\n"
                    "3. Best practices compliance\n"
                    "4. Potential improvements",
                    workspace_id=workspace.workspace_id,
                    files=list(files_to_create.keys())
                )
                
                print("=== Code Analysis ===")
                print(analysis_response.content)


async def secure_workspace_example():
    """Example of secure workspace operations."""
    print("\n=== Secure Workspace Example ===")
    
    # Use the secure workspace context manager
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create files with different extensions
        safe_file = temp_path / "data.json"
        safe_file.write_text('{"users": 100, "active": 75}')
        
        python_file = temp_path / "script.py"
        python_file.write_text("print('Safe Python script')")
        
        # Try to create a potentially unsafe file
        try:
            unsafe_file = temp_path / "malicious.exe"
            unsafe_file.write_text("fake executable content")
            
            async with create_workspace(
                copy_files=[str(safe_file), str(python_file), str(unsafe_file)],
                secure=True  # Enable security checks
            ) as workspace:
                print(f"Secure workspace created: {workspace.workspace_id}")
                
        except Exception as e:
            print(f"Security check prevented unsafe operation: {e}")
        
        # Create workspace with only safe files
        async with create_workspace(
            copy_files=[str(safe_file), str(python_file)],
            secure=True
        ) as workspace:
            print(f"Safe workspace created: {workspace.workspace_id}")
            print(f"Files in workspace: {workspace.path.glob('*')}")


async def workspace_with_session_example():
    """Example combining workspaces with sessions."""
    print("\n=== Workspace + Session Example ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a complex project structure
        (temp_path / "src").mkdir()
        (temp_path / "tests").mkdir()
        (temp_path / "docs").mkdir()
        
        # Main application
        (temp_path / "src" / "__init__.py").write_text("")
        (temp_path / "src" / "app.py").write_text("""
from fastapi import FastAPI
from .routes import router

app = FastAPI(title="My API")
app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Hello World"}
""")
        
        (temp_path / "src" / "routes.py").write_text("""
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "healthy"}
""")
        
        # Test file
        (temp_path / "tests" / "test_app.py").write_text("""
import pytest
from src.app import app

def test_root_endpoint():
    # Test implementation would go here
    pass
""")
        
        files_to_copy = [
            str(temp_path / "src" / "app.py"),
            str(temp_path / "src" / "routes.py"),
            str(temp_path / "tests" / "test_app.py"),
        ]
        
        async with ClaudeClient() as client:
            # Create session for code review conversation
            async with client.create_session("code_review_session") as session:
                # Create workspace within the session context
                async with client.create_workspace(
                    workspace_id="fastapi_review",
                    copy_files=files_to_copy
                ) as workspace:
                    
                    # Start the review conversation
                    response1 = await session.query(
                        "I have a FastAPI project I'd like you to review. "
                        "Let's start with the overall structure.",
                        workspace_id=workspace.workspace_id
                    )
                    print("=== Initial Review ===")
                    print(response1.content[:200] + "...")
                    
                    # Follow up with specific questions
                    response2 = await session.query(
                        "What about the error handling? Should I add any middleware?"
                    )
                    print("\n=== Error Handling Discussion ===")
                    print(response2.content[:200] + "...")
                    
                    # Ask for specific improvements
                    response3 = await session.query(
                        "Can you suggest specific code improvements I should make?"
                    )
                    print("\n=== Improvement Suggestions ===")
                    print(response3.content[:200] + "...")


async def workspace_cleanup_example():
    """Example of workspace cleanup and management."""
    print("\n=== Workspace Cleanup Example ===")
    
    async with ClaudeClient() as client:
        workspaces_created = []
        
        try:
            # Create multiple workspaces
            for i in range(3):
                workspace_info = await client._workspace_manager.create_workspace(
                    workspace_id=f"temp_workspace_{i}"
                )
                workspaces_created.append(workspace_info)
                print(f"Created workspace {i + 1}: {workspace_info.workspace_id}")
            
            # List all workspaces
            all_workspaces = await client.list_workspaces()
            print(f"Total workspaces: {len(all_workspaces)}")
            
            # Clean up specific workspace
            await client._workspace_manager.cleanup_workspace(
                workspaces_created[0].workspace_id
            )
            print(f"Cleaned up workspace: {workspaces_created[0].workspace_id}")
            
            # List remaining workspaces
            remaining_workspaces = await client.list_workspaces()
            print(f"Remaining workspaces: {len(remaining_workspaces)}")
            
        finally:
            # Clean up all remaining workspaces
            await client._workspace_manager.cleanup_all_workspaces()
            print("All workspaces cleaned up")


async def main():
    """Run all workspace operation examples."""
    print("Claude Python SDK - Workspace Operations Examples")
    print("=" * 65)
    
    try:
        await basic_workspace_example()
        await file_processing_workflow()
        await secure_workspace_example()
        await workspace_with_session_example()
        await workspace_cleanup_example()
        
    except Exception as e:
        print(f"Example failed: {e}")
        print("Note: These examples require Claude CLI to be installed and configured.")
    
    print("\n" + "=" * 65)
    print("Workspace operations examples completed!")


if __name__ == "__main__":
    asyncio.run(main())