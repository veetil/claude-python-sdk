"""
Retry utilities for the Claude Python SDK.

This module provides retry mechanisms with exponential backoff,
circuit breaker patterns, and failure handling strategies.
"""

import asyncio
import logging
import random
import time
from typing import Any, Callable, Optional, Type, Tuple, Union
from enum import Enum
from dataclasses import dataclass
from ..exceptions import (
    ClaudeSDKError,
    CommandTimeoutError,
    RateLimitError,
    AuthenticationError,
)


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    backoff_factor: float = 1.0


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.
    
    The circuit breaker monitors failures and can temporarily stop
    executing operations to allow the downstream service to recover.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before trying again (seconds)
            expected_exception: Exception type that triggers circuit opening
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        
        logger.debug(f"Circuit breaker initialized: threshold={failure_threshold}, timeout={recovery_timeout}")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Original exception: If function fails
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.debug("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise ClaudeSDKError(
                    f"Circuit breaker is OPEN. Will retry after {self.recovery_timeout}s"
                )
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - reset failure count
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            logger.debug("Circuit breaker HALF_OPEN -> CLOSED (success)")
            self.state = CircuitState.CLOSED
        
        self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")
                self.state = CircuitState.OPEN
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        logger.debug("Circuit breaker manually reset")
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED


async def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    **kwargs
) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        *args: Function arguments
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Tuple of exceptions that should trigger retry
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        Exception: Last exception if all retries fail
    """
    if retryable_exceptions is None:
        retryable_exceptions = (
            CommandTimeoutError,
            RateLimitError,
            ConnectionError,
            OSError,
        )
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            if attempt > 0:
                logger.info(f"Retry successful on attempt {attempt + 1}")
            
            return result
            
        except Exception as e:
            last_exception = e
            
            # Don't retry on non-retryable exceptions
            if not isinstance(e, retryable_exceptions):
                logger.debug(f"Non-retryable exception: {type(e).__name__}")
                raise
            
            # Don't retry on authentication errors
            if isinstance(e, AuthenticationError):
                logger.debug("Authentication error - not retrying")
                raise
            
            # Check if we have more attempts
            if attempt >= max_retries:
                logger.warning(f"All {max_retries + 1} attempts failed")
                raise
            
            # Calculate delay
            delay = min(
                base_delay * (exponential_base ** attempt),
                max_delay
            )
            
            # Add jitter if enabled
            if jitter:
                delay *= (0.5 + random.random() * 0.5)
            
            # Handle rate limit specific delay
            if isinstance(e, RateLimitError) and hasattr(e, 'retry_after') and e.retry_after:
                delay = max(delay, e.retry_after)
            
            logger.warning(
                f"Attempt {attempt + 1} failed: {type(e).__name__}: {str(e)}. "
                f"Retrying in {delay:.2f}s..."
            )
            
            await asyncio.sleep(delay)
    
    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
    else:
        raise ClaudeSDKError("Retry failed without exception")


class RetryableOperation:
    """A wrapper for operations that can be retried."""
    
    def __init__(
        self,
        operation: Callable,
        config: Optional[RetryConfig] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        """
        Initialize retryable operation.
        
        Args:
            operation: The operation to make retryable
            config: Retry configuration
            circuit_breaker: Optional circuit breaker
        """
        self.operation = operation
        self.config = config or RetryConfig()
        self.circuit_breaker = circuit_breaker
    
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the operation with retry and circuit breaker logic."""
        async def wrapped_operation(*args, **kwargs):
            if self.circuit_breaker:
                return await self.circuit_breaker.call(self.operation, *args, **kwargs)
            else:
                if asyncio.iscoroutinefunction(self.operation):
                    return await self.operation(*args, **kwargs)
                else:
                    return self.operation(*args, **kwargs)
        
        return await retry_with_backoff(
            wrapped_operation,
            *args,
            max_retries=self.config.max_retries,
            base_delay=self.config.base_delay,
            max_delay=self.config.max_delay,
            exponential_base=self.config.exponential_base,
            jitter=self.config.jitter,
            **kwargs
        )


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    circuit_breaker: Optional[CircuitBreaker] = None,
):
    """
    Decorator to add retry behavior to functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries
        circuit_breaker: Optional circuit breaker
    """
    def decorator(func: Callable) -> Callable:
        config = RetryConfig(max_retries=max_retries, base_delay=base_delay)
        retryable = RetryableOperation(func, config, circuit_breaker)
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await retryable.execute(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                # Convert sync function to async for retry mechanism
                async def async_func(*args, **kwargs):
                    return func(*args, **kwargs)
                
                return asyncio.run(retryable.execute(*args, **kwargs))
            return sync_wrapper
    
    return decorator


class AdaptiveRetry:
    """
    Adaptive retry mechanism that adjusts retry behavior based on
    historical success/failure patterns.
    """
    
    def __init__(self, initial_config: Optional[RetryConfig] = None):
        """Initialize adaptive retry with initial configuration."""
        self.config = initial_config or RetryConfig()
        self.success_count = 0
        self.failure_count = 0
        self.last_success_time: Optional[float] = None
        self.last_failure_time: Optional[float] = None
    
    def _update_config(self) -> None:
        """Update retry configuration based on historical data."""
        total_attempts = self.success_count + self.failure_count
        
        if total_attempts < 10:
            return  # Not enough data
        
        failure_rate = self.failure_count / total_attempts
        
        # Adjust retry count based on failure rate
        if failure_rate > 0.5:
            # High failure rate - increase retries
            self.config.max_retries = min(self.config.max_retries + 1, 10)
            self.config.base_delay = min(self.config.base_delay * 1.5, 10.0)
        elif failure_rate < 0.1:
            # Low failure rate - decrease retries
            self.config.max_retries = max(self.config.max_retries - 1, 1)
            self.config.base_delay = max(self.config.base_delay * 0.8, 0.1)
        
        logger.debug(
            f"Adaptive retry updated: failure_rate={failure_rate:.2f}, "
            f"max_retries={self.config.max_retries}, "
            f"base_delay={self.config.base_delay:.2f}"
        )
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with adaptive retry."""
        try:
            result = await retry_with_backoff(
                func,
                *args,
                max_retries=self.config.max_retries,
                base_delay=self.config.base_delay,
                max_delay=self.config.max_delay,
                exponential_base=self.config.exponential_base,
                jitter=self.config.jitter,
                **kwargs
            )
            
            self.success_count += 1
            self.last_success_time = time.time()
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # Update configuration for future operations
            self._update_config()
            
            raise
    
    def get_stats(self) -> dict:
        """Get retry statistics."""
        total = self.success_count + self.failure_count
        failure_rate = self.failure_count / total if total > 0 else 0
        
        return {
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'total_attempts': total,
            'failure_rate': failure_rate,
            'current_config': {
                'max_retries': self.config.max_retries,
                'base_delay': self.config.base_delay,
                'max_delay': self.config.max_delay,
            }
        }