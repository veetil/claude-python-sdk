# Claude Python SDK - Quick Start Guide

## Installation

```bash
# Install from GitHub
pip install git+https://github.com/veetil/claude-python-sdk.git

# Or clone and install in development mode
git clone https://github.com/veetil/claude-python-sdk.git
cd claude-python-sdk
pip install -e ".[dev]"
```

## Prerequisites

- Python 3.9 or higher
- Claude CLI installed and configured (`npm install -g @anthropic-ai/claude-code`)

## Basic Usage

```python
import asyncio
from claude_sdk import ClaudeClient

async def main():
    async with ClaudeClient() as client:
        response = await client.query("Hello, Claude!")
        print(response.content)

asyncio.run(main())
```

## Parallel Execution Example

```python
import asyncio
from claude_sdk import ClaudeClient

async def parallel_queries():
    async with ClaudeClient() as client:
        tasks = [
            client.query("What is Python?"),
            client.query("What is JavaScript?"),
            client.query("What is Rust?")
        ]
        
        responses = await asyncio.gather(*tasks)
        
        for i, response in enumerate(responses):
            print(f"Query {i+1}: {response.content[:100]}...")

asyncio.run(parallel_queries())
```

## Run Examples

```bash
# Basic examples
python examples/basic_usage.py

# Parallel haiku generation
python examples/parallel_haikus.py

# Session management
python examples/session_management.py

# Workspace operations
python examples/workspace_operations.py

# Advanced features
python examples/advanced_features.py
```

## Key Features

- ✅ Async/await support
- ✅ Streaming responses
- ✅ Parallel execution
- ✅ Session management
- ✅ Workspace isolation
- ✅ Comprehensive error handling
- ✅ Retry mechanisms
- ✅ Type safety

## Documentation

See the [README.md](README.md) for full documentation and API reference.