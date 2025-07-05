"""
Session management examples for the Claude Python SDK.

This script demonstrates how to use sessions for multi-turn conversations
and maintain context across multiple queries.
"""

import asyncio
import json
from claude_sdk import ClaudeClient


async def basic_session_example():
    """Example of basic session usage."""
    print("=== Basic Session Example ===")
    
    async with ClaudeClient() as client:
        async with client.create_session("coding_help") as session:
            # First message in the session
            response1 = await session.query(
                "I'm building a web application with FastAPI. "
                "Can you help me with authentication?"
            )
            print(f"Claude: {response1.content}")
            
            # Follow-up question in the same session
            response2 = await session.query(
                "What about JWT token validation?"
            )
            print(f"Claude: {response2.content}")
            
            # Another follow-up
            response3 = await session.query(
                "Can you show me a code example?"
            )
            print(f"Claude: {response3.content}")


async def multiple_sessions_example():
    """Example of managing multiple sessions concurrently."""
    print("\n=== Multiple Sessions Example ===")
    
    async with ClaudeClient() as client:
        # Create multiple sessions for different topics
        async with client.create_session("python_help") as python_session:
            async with client.create_session("design_help") as design_session:
                
                # Python discussion
                python_response = await python_session.query(
                    "What are Python decorators and how do they work?"
                )
                print(f"Python Session: {python_response.content[:100]}...")
                
                # Design discussion  
                design_response = await design_session.query(
                    "What are the principles of good UI design?"
                )
                print(f"Design Session: {design_response.content[:100]}...")
                
                # Continue Python discussion
                python_follow_up = await python_session.query(
                    "Can you give me an example of a decorator?"
                )
                print(f"Python Follow-up: {python_follow_up.content[:100]}...")


async def session_with_streaming_example():
    """Example of streaming responses within a session."""
    print("\n=== Session with Streaming Example ===")
    
    async with ClaudeClient() as client:
        async with client.create_session("tutorial") as session:
            print("Starting a coding tutorial session...")
            
            # First query - set up the context
            await session.query(
                "I want to learn about Python async programming. "
                "Can you be my tutor?"
            )
            
            print("\nStreaming tutorial content:")
            
            # Stream a detailed explanation
            async for chunk in session.stream_query(
                "Explain async/await with a practical example, step by step"
            ):
                print(chunk, end="", flush=True)
            
            print("\n\nTutorial session completed!")


async def session_state_tracking():
    """Example of tracking session state and metadata."""
    print("\n=== Session State Tracking ===")
    
    async with ClaudeClient() as client:
        # List sessions before creating any
        sessions_before = await client.list_sessions()
        print(f"Sessions before: {len(sessions_before)}")
        
        async with client.create_session("tracked_session") as session:
            # Check session info
            print(f"Session ID: {session.session_id}")
            
            # List sessions while one is active
            sessions_active = await client.list_sessions()
            print(f"Active sessions: {len(sessions_active)}")
            
            # Send a query
            response = await session.query("What is machine learning?")
            print(f"Response length: {len(response.content)} characters")
            
            # Get session details
            for session_info in sessions_active:
                print(f"Session {session_info.session_id}: {session_info.status}")
        
        # List sessions after session is closed
        sessions_after = await client.list_sessions()
        print(f"Sessions after: {len(sessions_after)}")


async def conversation_flow_example():
    """Example of a natural conversation flow."""
    print("\n=== Conversation Flow Example ===")
    
    conversation_history = []
    
    async with ClaudeClient() as client:
        async with client.create_session("conversation") as session:
            
            # Simulate a coding help conversation
            queries = [
                "I'm new to Python and want to build a simple web scraper",
                "What libraries would you recommend?", 
                "How do I handle HTTP requests?",
                "What about parsing HTML?",
                "Can you show me a complete example?"
            ]
            
            for i, query in enumerate(queries, 1):
                print(f"\nUser: {query}")
                
                response = await session.query(query)
                
                # Store conversation
                conversation_history.append({
                    "turn": i,
                    "user": query,
                    "claude": response.content,
                    "session_id": response.session_id,
                    "timestamp": response.timestamp.isoformat()
                })
                
                print(f"Claude: {response.content[:150]}...")
    
    print(f"\nConversation completed with {len(conversation_history)} turns")


async def session_error_handling():
    """Example of error handling within sessions."""
    print("\n=== Session Error Handling ===")
    
    from claude_sdk.exceptions import ClaudeSDKError
    
    async with ClaudeClient() as client:
        try:
            async with client.create_session("error_test") as session:
                # Try a normal query first
                response1 = await session.query("Hello!")
                print(f"Successful query: {response1.content[:50]}...")
                
                # Simulate a problematic query (this would depend on your Claude setup)
                try:
                    response2 = await session.query("", timeout=0.001)  # Empty query with tiny timeout
                except ClaudeSDKError as e:
                    print(f"Caught session error: {e}")
                
                # Continue with the session after error
                response3 = await session.query("Are you still there?")
                print(f"Recovery query: {response3.content[:50]}...")
                
        except Exception as e:
            print(f"Session creation or management error: {e}")


async def main():
    """Run all session management examples."""
    print("Claude Python SDK - Session Management Examples")
    print("=" * 60)
    
    try:
        await basic_session_example()
        await multiple_sessions_example()
        await session_with_streaming_example()
        await session_state_tracking()
        await conversation_flow_example()
        await session_error_handling()
        
    except Exception as e:
        print(f"Example failed: {e}")
        print("Note: These examples require Claude CLI to be installed and configured.")
    
    print("\n" + "=" * 60)
    print("Session management examples completed!")


if __name__ == "__main__":
    asyncio.run(main())