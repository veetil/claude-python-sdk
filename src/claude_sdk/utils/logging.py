"""
Logging utilities for the Claude Python SDK.

This module provides structured logging configuration, custom formatters,
and integration with the SDK's configuration system.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger
from ..core.config import ClaudeConfig
from ..core.types import LogLevel


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log records."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add SDK context
        log_record['sdk'] = 'claude-python-sdk'
        log_record['version'] = '0.1.0'  # Could be dynamically imported
        
        # Add process information
        log_record['process_id'] = os.getpid()
        
        # Add thread information if available
        if hasattr(record, 'thread'):
            log_record['thread_id'] = record.thread
            log_record['thread_name'] = record.threadName


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive information in logs."""
    
    SENSITIVE_PATTERNS = [
        'api_key', 'token', 'password', 'secret', 'auth',
        'authorization', 'credential', 'key'
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record to mask sensitive data."""
        # Mask sensitive data in the message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._mask_sensitive_data(record.msg)
        
        # Mask sensitive data in arguments
        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self._mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        return True
    
    def _mask_sensitive_data(self, text: str) -> str:
        """Mask sensitive data in text."""
        import re
        
        # Simple pattern to mask values after sensitive keys
        for pattern in self.SENSITIVE_PATTERNS:
            # Pattern like: api_key=value or "api_key": "value"
            text = re.sub(
                rf'({pattern}["\']?\s*[:=]\s*["\']?)([^"\s,}}]+)',
                r'\1***MASKED***',
                text,
                flags=re.IGNORECASE
            )
        
        return text


class DebugModeFilter(logging.Filter):
    """Filter that only allows debug messages when debug mode is enabled."""
    
    def __init__(self, debug_enabled: bool = False):
        super().__init__()
        self.debug_enabled = debug_enabled
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter debug messages based on debug mode."""
        if record.levelno == logging.DEBUG and not self.debug_enabled:
            return False
        return True


def setup_logging(config: ClaudeConfig) -> None:
    """
    Setup logging configuration based on the provided config.
    
    Args:
        config: Claude configuration object
    """
    # Get root logger for the SDK
    logger = logging.getLogger('claude_sdk')
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set log level
    log_level = getattr(logging, config.log_level.value)
    logger.setLevel(log_level)
    
    # Create formatters
    if config.debug_mode or config.verbose_logging:
        # Detailed formatter for debug mode
        console_formatter = logging.Formatter(
            '%(asctime)s [%(name)s] %(levelname)s %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Simple formatter for normal mode
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # JSON formatter for file logging
    json_formatter = StructuredFormatter(
        '%(timestamp)s %(name)s %(levelname)s %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)
    
    # Add filters
    console_handler.addFilter(SensitiveDataFilter())
    console_handler.addFilter(DebugModeFilter(config.debug_mode))
    
    logger.addHandler(console_handler)
    
    # File handler (if configured)
    if config.log_file:
        try:
            log_path = Path(config.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use rotating file handler to prevent large log files
            file_handler = logging.handlers.RotatingFileHandler(
                config.log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            
            file_handler.setFormatter(json_formatter)
            file_handler.setLevel(logging.DEBUG)  # File logs everything
            file_handler.addFilter(SensitiveDataFilter())
            
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.warning(f"Failed to setup file logging: {e}")
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    # Log startup message
    logger.info(f"Logging configured: level={config.log_level.value}, debug={config.debug_mode}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the specified module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    # Ensure the logger is under the SDK namespace
    if not name.startswith('claude_sdk'):
        name = f'claude_sdk.{name}'
    
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding contextual information to logs."""
    
    def __init__(self, **context):
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        # Store the old factory
        self.old_factory = logging.getLogRecordFactory()
        
        # Create new factory that adds context
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore the old factory
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


class PerformanceLogger:
    """Logger for performance metrics and monitoring."""
    
    def __init__(self, logger_name: str = 'claude_sdk.performance'):
        self.logger = get_logger(logger_name)
    
    def log_operation_time(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        **metadata
    ) -> None:
        """Log operation timing information."""
        self.logger.info(
            f"Operation {operation}: {duration:.3f}s",
            extra={
                'operation': operation,
                'duration_seconds': duration,
                'success': success,
                'metadata': metadata,
                'metric_type': 'operation_time'
            }
        )
    
    def log_error_rate(
        self,
        component: str,
        error_count: int,
        total_count: int,
        **metadata
    ) -> None:
        """Log error rate information."""
        error_rate = error_count / max(total_count, 1)
        
        self.logger.info(
            f"Component {component}: {error_count}/{total_count} errors ({error_rate:.2%})",
            extra={
                'component': component,
                'error_count': error_count,
                'total_count': total_count,
                'error_rate': error_rate,
                'metadata': metadata,
                'metric_type': 'error_rate'
            }
        )
    
    def log_resource_usage(
        self,
        resource_type: str,
        usage_value: float,
        unit: str,
        **metadata
    ) -> None:
        """Log resource usage information."""
        self.logger.info(
            f"Resource {resource_type}: {usage_value} {unit}",
            extra={
                'resource_type': resource_type,
                'usage_value': usage_value,
                'unit': unit,
                'metadata': metadata,
                'metric_type': 'resource_usage'
            }
        )


class AuditLogger:
    """Logger for security and audit events."""
    
    def __init__(self, logger_name: str = 'claude_sdk.audit'):
        self.logger = get_logger(logger_name)
    
    def log_command_execution(
        self,
        command: str,
        user_context: Optional[str] = None,
        workspace_id: Optional[str] = None,
        success: bool = True,
        **metadata
    ) -> None:
        """Log command execution for audit purposes."""
        self.logger.info(
            f"Command executed: {command}",
            extra={
                'event_type': 'command_execution',
                'command': command,
                'user_context': user_context,
                'workspace_id': workspace_id,
                'success': success,
                'metadata': metadata,
            }
        )
    
    def log_workspace_operation(
        self,
        operation: str,
        workspace_id: str,
        user_context: Optional[str] = None,
        **metadata
    ) -> None:
        """Log workspace operations for audit purposes."""
        self.logger.info(
            f"Workspace {operation}: {workspace_id}",
            extra={
                'event_type': 'workspace_operation',
                'operation': operation,
                'workspace_id': workspace_id,
                'user_context': user_context,
                'metadata': metadata,
            }
        )
    
    def log_security_event(
        self,
        event_type: str,
        description: str,
        severity: str = 'info',
        **metadata
    ) -> None:
        """Log security events."""
        log_method = getattr(self.logger, severity.lower(), self.logger.info)
        
        log_method(
            f"Security event: {description}",
            extra={
                'event_type': 'security_event',
                'security_event_type': event_type,
                'description': description,
                'severity': severity,
                'metadata': metadata,
            }
        )


# Global logger instances
performance_logger = PerformanceLogger()
audit_logger = AuditLogger()


def log_performance(operation: str):
    """Decorator for logging operation performance."""
    import time
    from functools import wraps
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                performance_logger.log_operation_time(
                    operation, duration, success,
                    function=func.__name__,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys())
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                performance_logger.log_operation_time(
                    operation, duration, success,
                    function=func.__name__,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys())
                )
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator