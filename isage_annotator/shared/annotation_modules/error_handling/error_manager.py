"""
Error Manager for Annotation System
Centralized error management with recovery and reporting capabilities.
Based on legacy ABILIUS error handling implementation.
"""

import logging
import traceback
import threading
import time
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass
from enum import Enum
import weakref

# Handle PyQt5 imports
try:
    from PyQt5.QtCore import QObject, pyqtSignal
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    QObject = object
    def pyqtSignal(*args, **kwargs):
        return None

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    IO_ERROR = "io_error"
    MEMORY_ERROR = "memory_error"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    UI_ERROR = "ui_error"
    DATA_ERROR = "data_error"
    SYSTEM_ERROR = "system_error"
    USER_ERROR = "user_error"


@dataclass
class ErrorInfo:
    """Container for error information."""
    error_id: str
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    details: str
    timestamp: float
    component: str
    context: Dict[str, Any]
    traceback_str: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    user_notified: bool = False


class ErrorManager(QObject if PYQT5_AVAILABLE else object):
    """Centralized error management system."""
    
    # Signals for error events
    if PYQT5_AVAILABLE:
        error_occurred = pyqtSignal(object)  # ErrorInfo
        error_recovered = pyqtSignal(str)    # error_id
        critical_error = pyqtSignal(object)  # ErrorInfo
        error_cleared = pyqtSignal(str)      # error_id
    
    def __init__(self):
        if PYQT5_AVAILABLE:
            super().__init__()
        
        self._errors: Dict[str, ErrorInfo] = {}
        self._error_counts: Dict[ErrorCategory, int] = {cat: 0 for cat in ErrorCategory}
        self._error_handlers: Dict[ErrorCategory, List[Callable]] = {cat: [] for cat in ErrorCategory}
        self._recovery_handlers: Dict[ErrorCategory, List[Callable]] = {cat: [] for cat in ErrorCategory}
        
        # Error tracking
        self._error_history: List[ErrorInfo] = []
        self._max_history_size: int = 1000
        self._error_rate_window: float = 300.0  # 5 minutes
        self._max_error_rate: int = 100  # errors per window
        
        # Component tracking
        self._component_registry: Set[str] = set()
        self._component_errors: Dict[str, List[str]] = {}
        
        # Threading
        self._lock = threading.RLock()
        self._shutdown = False
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup error logging."""
        try:
            # Create error-specific logger
            self._error_logger = logging.getLogger('annotation_errors')
            self._error_logger.setLevel(logging.DEBUG)
            
            # Prevent duplicate logs if already configured
            if not self._error_logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                self._error_logger.addHandler(handler)
                
        except Exception as e:
            logger.warning(f"Could not setup error logging: {e}")
    
    def register_component(self, component_name: str) -> None:
        """Register a component for error tracking."""
        with self._lock:
            self._component_registry.add(component_name)
            if component_name not in self._component_errors:
                self._component_errors[component_name] = []
    
    def register_error_handler(self, category: ErrorCategory, handler: Callable[[ErrorInfo], None]) -> None:
        """Register error handler for specific category."""
        with self._lock:
            self._error_handlers[category].append(handler)
    
    def register_recovery_handler(self, category: ErrorCategory, handler: Callable[[ErrorInfo], bool]) -> None:
        """Register recovery handler for specific category."""
        with self._lock:
            self._recovery_handlers[category].append(handler)
    
    def report_error(self, 
                    component: str,
                    message: str,
                    severity: ErrorSeverity = ErrorSeverity.ERROR,
                    category: ErrorCategory = ErrorCategory.SYSTEM_ERROR,
                    details: str = "",
                    context: Optional[Dict[str, Any]] = None,
                    exception: Optional[Exception] = None) -> str:
        """Report an error and return error ID."""
        
        with self._lock:
            if self._shutdown:
                return ""
            
            # Check error rate
            if self._check_error_rate_exceeded():
                self._handle_error_flood()
                return ""
            
            # Generate error ID
            error_id = f"{component}_{category.value}_{int(time.time()*1000)}"
            
            # Create error info
            error_info = ErrorInfo(
                error_id=error_id,
                severity=severity,
                category=category,
                message=message,
                details=details,
                timestamp=time.time(),
                component=component,
                context=context or {},
                traceback_str=traceback.format_exc() if exception else None
            )
            
            # Store error
            self._errors[error_id] = error_info
            self._error_history.append(error_info)
            self._error_counts[category] += 1
            
            # Track component error
            if component in self._component_errors:
                self._component_errors[component].append(error_id)
            
            # Trim history if needed
            if len(self._error_history) > self._max_history_size:
                self._error_history = self._error_history[-self._max_history_size:]
            
            # Log error
            self._log_error(error_info)
            
            # Emit signal
            if PYQT5_AVAILABLE:
                self.error_occurred.emit(error_info)
                if severity == ErrorSeverity.CRITICAL:
                    self.critical_error.emit(error_info)
            
            # Call error handlers
            self._call_error_handlers(error_info)
            
            # Attempt recovery for non-critical errors
            if severity != ErrorSeverity.CRITICAL:
                self._attempt_recovery(error_info)
            
            return error_id
    
    def get_error(self, error_id: str) -> Optional[ErrorInfo]:
        """Get error by ID."""
        with self._lock:
            return self._errors.get(error_id)
    
    def get_errors_by_component(self, component: str) -> List[ErrorInfo]:
        """Get all errors for a component."""
        with self._lock:
            error_ids = self._component_errors.get(component, [])
            return [self._errors[eid] for eid in error_ids if eid in self._errors]
    
    def get_errors_by_category(self, category: ErrorCategory) -> List[ErrorInfo]:
        """Get all errors for a category."""
        with self._lock:
            return [err for err in self._errors.values() if err.category == category]
    
    def get_recent_errors(self, seconds: int = 300) -> List[ErrorInfo]:
        """Get errors from last N seconds."""
        with self._lock:
            cutoff_time = time.time() - seconds
            return [err for err in self._error_history if err.timestamp > cutoff_time]
    
    def clear_error(self, error_id: str) -> bool:
        """Clear specific error."""
        with self._lock:
            if error_id in self._errors:
                error_info = self._errors[error_id]
                del self._errors[error_id]
                
                # Remove from component tracking
                component = error_info.component
                if component in self._component_errors:
                    try:
                        self._component_errors[component].remove(error_id)
                    except ValueError:
                        pass
                
                # Emit signal
                if PYQT5_AVAILABLE:
                    self.error_cleared.emit(error_id)
                
                return True
            return False
    
    def clear_component_errors(self, component: str) -> int:
        """Clear all errors for a component."""
        with self._lock:
            if component not in self._component_errors:
                return 0
            
            error_ids = self._component_errors[component].copy()
            cleared_count = 0
            
            for error_id in error_ids:
                if self.clear_error(error_id):
                    cleared_count += 1
            
            return cleared_count
    
    def clear_old_errors(self, max_age_seconds: int = 3600) -> int:
        """Clear errors older than specified age."""
        with self._lock:
            cutoff_time = time.time() - max_age_seconds
            old_errors = [err.error_id for err in self._errors.values() if err.timestamp < cutoff_time]
            
            cleared_count = 0
            for error_id in old_errors:
                if self.clear_error(error_id):
                    cleared_count += 1
            
            return cleared_count
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics."""
        with self._lock:
            recent_errors = self.get_recent_errors(300)  # Last 5 minutes
            
            stats = {
                'total_errors': len(self._errors),
                'recent_errors': len(recent_errors),
                'error_rate': len(recent_errors) / 5.0,  # errors per minute
                'category_counts': self._error_counts.copy(),
                'component_error_counts': {
                    comp: len(errors) for comp, errors in self._component_errors.items()
                },
                'severity_counts': {},
                'registered_components': len(self._component_registry)
            }
            
            # Count by severity
            for severity in ErrorSeverity:
                stats['severity_counts'][severity.value] = sum(
                    1 for err in self._errors.values() if err.severity == severity
                )
            
            return stats
    
    def _check_error_rate_exceeded(self) -> bool:
        """Check if error rate is too high."""
        recent_errors = self.get_recent_errors(self._error_rate_window)
        return len(recent_errors) >= self._max_error_rate
    
    def _handle_error_flood(self) -> None:
        """Handle error flood situation."""
        logger.critical("Error flood detected - temporarily suppressing error reporting")
        # Could implement emergency measures here
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log error information."""
        try:
            log_message = f"[{error_info.component}] {error_info.message}"
            if error_info.details:
                log_message += f" - {error_info.details}"
            
            if error_info.severity == ErrorSeverity.CRITICAL:
                self._error_logger.critical(log_message)
            elif error_info.severity == ErrorSeverity.ERROR:
                self._error_logger.error(log_message)
            elif error_info.severity == ErrorSeverity.WARNING:
                self._error_logger.warning(log_message)
            else:
                self._error_logger.info(log_message)
                
            # Log traceback if available
            if error_info.traceback_str:
                self._error_logger.debug(f"Traceback for {error_info.error_id}:\n{error_info.traceback_str}")
                
        except Exception as e:
            logger.warning(f"Could not log error: {e}")
    
    def _call_error_handlers(self, error_info: ErrorInfo) -> None:
        """Call registered error handlers."""
        try:
            handlers = self._error_handlers.get(error_info.category, [])
            for handler in handlers:
                try:
                    handler(error_info)
                except Exception as e:
                    logger.warning(f"Error handler failed: {e}")
        except Exception as e:
            logger.warning(f"Error calling error handlers: {e}")
    
    def _attempt_recovery(self, error_info: ErrorInfo) -> None:
        """Attempt error recovery."""
        try:
            error_info.recovery_attempted = True
            
            handlers = self._recovery_handlers.get(error_info.category, [])
            for handler in handlers:
                try:
                    if handler(error_info):
                        error_info.recovery_successful = True
                        if PYQT5_AVAILABLE:
                            self.error_recovered.emit(error_info.error_id)
                        logger.info(f"Successfully recovered from error {error_info.error_id}")
                        break
                except Exception as e:
                    logger.warning(f"Recovery handler failed: {e}")
                    
        except Exception as e:
            logger.warning(f"Error during recovery attempt: {e}")
    
    def shutdown(self) -> None:
        """Shutdown error manager."""
        with self._lock:
            self._shutdown = True
            self._errors.clear()
            self._error_history.clear()
            self._component_errors.clear()


# Global error manager instance
_global_error_manager: Optional[ErrorManager] = None
_manager_lock = threading.Lock()


def get_global_error_manager() -> ErrorManager:
    """Get or create global error manager instance."""
    global _global_error_manager
    if _global_error_manager is None:
        with _manager_lock:
            if _global_error_manager is None:
                _global_error_manager = ErrorManager()
    return _global_error_manager


def report_error(component: str, 
                message: str,
                severity: ErrorSeverity = ErrorSeverity.ERROR,
                category: ErrorCategory = ErrorCategory.SYSTEM_ERROR,
                details: str = "",
                context: Optional[Dict[str, Any]] = None,
                exception: Optional[Exception] = None) -> str:
    """Convenience function to report error to global manager."""
    manager = get_global_error_manager()
    return manager.report_error(component, message, severity, category, details, context, exception)


def clear_component_errors(component: str) -> int:
    """Convenience function to clear component errors."""
    manager = get_global_error_manager()
    return manager.clear_component_errors(component)


def get_error_statistics() -> Dict[str, Any]:
    """Convenience function to get error statistics."""
    manager = get_global_error_manager()
    return manager.get_error_statistics()