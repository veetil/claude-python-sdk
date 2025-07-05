"""
Advanced features examples for the Claude Python SDK.

This script demonstrates advanced usage patterns including concurrent operations,
custom retry strategies, error recovery, and performance optimization.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from claude_sdk import ClaudeClient, ClaudeConfig
from claude_sdk.utils.retry import CircuitBreaker, AdaptiveRetry, retry_with_backoff
from claude_sdk.utils.logging import LogContext, performance_logger


async def concurrent_queries_example():
    """Example of executing multiple queries concurrently."""
    print("=== Concurrent Queries Example ===")
    
    async with ClaudeClient() as client:
        # Prepare multiple queries
        queries = [
            "What is machine learning?",
            "Explain quantum computing",
            "How do neural networks work?",
            "What is blockchain technology?",
            "Describe cloud computing"
        ]
        
        start_time = time.time()
        
        # Execute all queries concurrently
        tasks = [
            client.query(query)
            for query in queries
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        
        print(f"Executed {len(queries)} queries in {end_time - start_time:.2f} seconds")
        
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                print(f"Query {i + 1} failed: {response}")
            else:
                print(f"Query {i + 1}: {response.content[:100]}...")


async def circuit_breaker_example():
    """Example of using circuit breaker for fault tolerance."""
    print("\n=== Circuit Breaker Example ===")
    
    from claude_sdk.exceptions import CommandTimeoutError
    
    # Create a circuit breaker
    circuit_breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=5.0,
        expected_exception=CommandTimeoutError
    )
    
    async def potentially_failing_operation():
        """Simulate an operation that might fail."""
        # This would normally be a real Claude query
        # For demo purposes, we'll simulate failures
        import random
        if random.random() < 0.7:  # 70% chance of failure
            raise CommandTimeoutError("Simulated timeout", 1.0)
        return "Success!"
    
    # Test the circuit breaker
    for i in range(10):
        try:
            result = await circuit_breaker.call(potentially_failing_operation)
            print(f"Attempt {i + 1}: {result}")
        except Exception as e:
            print(f"Attempt {i + 1}: {type(e).__name__}: {e}")
        
        await asyncio.sleep(0.5)


async def adaptive_retry_example():
    """Example of adaptive retry strategy."""
    print("\n=== Adaptive Retry Example ===")
    
    adaptive_retry = AdaptiveRetry()
    
    async def unreliable_operation():
        """Simulate an unreliable operation."""
        import random
        if random.random() < 0.6:  # 60% failure rate initially
            raise ConnectionError("Simulated connection error")
        return "Operation successful!"
    
    # Test adaptive retry over multiple attempts
    for i in range(10):
        try:
            result = await adaptive_retry.execute(unreliable_operation)
            print(f"Attempt {i + 1}: {result}")
        except Exception as e:
            print(f"Attempt {i + 1}: Failed - {e}")
    
    # Show statistics
    stats = adaptive_retry.get_stats()
    print(f"Retry statistics: {stats}")


async def custom_retry_strategy_example():
    """Example of custom retry strategy with specific conditions."""
    print("\n=== Custom Retry Strategy Example ===")
    
    from claude_sdk.exceptions import RateLimitError, AuthenticationError
    
    async def operation_with_custom_retry():
        """Operation that uses custom retry logic."""
        async def claude_operation():
            # Simulate different types of errors
            import random
            error_type = random.choice([
                "success", "rate_limit", "auth_error", "timeout", "other"
            ])
            
            if error_type == "success":
                return "Query successful!"
            elif error_type == "rate_limit":
                raise RateLimitError("Rate limit exceeded", retry_after=2.0)
            elif error_type == "auth_error":
                raise AuthenticationError("Invalid credentials")
            elif error_type == "timeout":
                raise CommandTimeoutError("Request timeout", 30.0)
            else:
                raise ConnectionError("Network error")
        
        # Custom retry with specific exception handling
        try:
            result = await retry_with_backoff(
                claude_operation,
                max_retries=3,
                base_delay=1.0,
                retryable_exceptions=(
                    CommandTimeoutError,
                    RateLimitError,
                    ConnectionError,
                )
            )
            return result
        except AuthenticationError:
            print("Authentication failed - manual intervention required")
            return "Failed - auth error"
        except Exception as e:
            print(f"Operation failed after retries: {e}")
            return "Failed - max retries exceeded"
    
    result = await operation_with_custom_retry()
    print(f"Final result: {result}")


async def performance_monitoring_example():
    """Example of performance monitoring and logging."""
    print("\n=== Performance Monitoring Example ===")
    
    from claude_sdk.utils.logging import log_performance
    
    @log_performance("claude_query")
    async def monitored_query(client, prompt):
        """A query with performance monitoring."""
        return await client.query(prompt)
    
    async with ClaudeClient() as client:
        # Execute monitored queries
        queries = [
            "What is Python?",
            "Explain async programming",
            "How do decorators work?"
        ]
        
        for query in queries:
            try:
                response = await monitored_query(client, query)
                print(f"Query completed: {len(response.content)} characters")
            except Exception as e:
                print(f"Query failed: {e}")


async def context_aware_logging_example():
    """Example of context-aware logging."""
    print("\n=== Context-Aware Logging Example ===")
    
    async with ClaudeClient() as client:
        # Use logging context to add metadata
        with LogContext(user_id="user123", session_type="coding_help"):
            response1 = await client.query("Help me debug this Python code")
            print(f"Contextual query 1 completed")
        
        with LogContext(user_id="user123", session_type="learning"):
            response2 = await client.query("Explain machine learning basics")
            print(f"Contextual query 2 completed")


async def batched_operations_example():
    """Example of batching operations for efficiency."""
    print("\n=== Batched Operations Example ===")
    
    async def batch_processor(client, items, batch_size=3):
        """Process items in batches."""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            print(f"Processing batch {i // batch_size + 1}: {len(batch)} items")
            
            # Process batch concurrently
            batch_tasks = [
                client.query(f"Analyze: {item}")
                for item in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
            
            # Brief pause between batches to be respectful
            if i + batch_size < len(items):
                await asyncio.sleep(1.0)
        
        return results
    
    async with ClaudeClient() as client:
        items_to_process = [
            "Python list comprehension",
            "JavaScript promises", 
            "Rust ownership",
            "Go channels",
            "Java streams",
            "C++ templates",
            "Swift optionals"
        ]
        
        results = await batch_processor(client, items_to_process, batch_size=3)
        
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        print(f"Processed {len(items_to_process)} items:")
        print(f"- Successful: {len(successful_results)}")
        print(f"- Failed: {len(failed_results)}")


async def mixed_sync_async_example():
    """Example of mixing sync and async operations."""
    print("\n=== Mixed Sync/Async Example ===")
    
    def cpu_intensive_task(data):
        """Simulate CPU-intensive processing."""
        import hashlib
        import time
        
        # Simulate work
        time.sleep(0.1)
        return hashlib.md5(data.encode()).hexdigest()
    
    async def hybrid_processing(client, texts):
        """Combine CPU-intensive work with async Claude queries."""
        loop = asyncio.get_running_loop()
        
        # Process texts with thread pool for CPU work
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit CPU work to thread pool
            hash_futures = [
                loop.run_in_executor(executor, cpu_intensive_task, text)
                for text in texts
            ]
            
            # Concurrently run Claude analysis
            claude_futures = [
                client.query(f"Analyze the sentiment of: {text}")
                for text in texts
            ]
            
            # Wait for both types of work
            hashes = await asyncio.gather(*hash_futures)
            analyses = await asyncio.gather(*claude_futures, return_exceptions=True)
        
        return list(zip(texts, hashes, analyses))
    
    async with ClaudeClient() as client:
        sample_texts = [
            "I love programming in Python!",
            "This bug is really frustrating.",
            "The new feature works perfectly."
        ]
        
        results = await hybrid_processing(client, sample_texts)
        
        for text, hash_value, analysis in results:
            if isinstance(analysis, Exception):
                print(f"Text: {text[:30]}... | Hash: {hash_value[:8]}... | Analysis: Failed")
            else:
                print(f"Text: {text[:30]}... | Hash: {hash_value[:8]}... | Analysis: Done")


async def resource_management_example():
    """Example of advanced resource management."""
    print("\n=== Resource Management Example ===")
    
    # Custom configuration for resource optimization
    config = ClaudeConfig(
        max_concurrent_sessions=3,
        default_timeout=15.0,
        workspace_cleanup_on_exit=True,
        stream_buffer_size=4096,
    )
    
    async with ClaudeClient(config=config) as client:
        # Monitor resource usage
        print(f"Max concurrent sessions: {config.max_concurrent_sessions}")
        
        # Create multiple sessions up to the limit
        sessions = []
        try:
            for i in range(config.max_concurrent_sessions):
                session_context = client.create_session(f"session_{i}")
                session = await session_context.__aenter__()
                sessions.append((session_context, session))
                print(f"Created session {i + 1}")
            
            # Use all sessions concurrently
            tasks = [
                session.query(f"Task for session {i}")
                for i, (_, session) in enumerate(sessions)
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    print(f"Session {i + 1} failed: {response}")
                else:
                    print(f"Session {i + 1} completed successfully")
        
        finally:
            # Clean up sessions
            for session_context, _ in sessions:
                await session_context.__aexit__(None, None, None)
            print("All sessions cleaned up")


async def main():
    """Run all advanced feature examples."""
    print("Claude Python SDK - Advanced Features Examples")
    print("=" * 65)
    
    try:
        await concurrent_queries_example()
        await circuit_breaker_example()
        await adaptive_retry_example() 
        await custom_retry_strategy_example()
        await performance_monitoring_example()
        await context_aware_logging_example()
        await batched_operations_example()
        await mixed_sync_async_example()
        await resource_management_example()
        
    except Exception as e:
        print(f"Example failed: {e}")
        print("Note: These examples require Claude CLI to be installed and configured.")
    
    print("\n" + "=" * 65)
    print("Advanced features examples completed!")


if __name__ == "__main__":
    asyncio.run(main())