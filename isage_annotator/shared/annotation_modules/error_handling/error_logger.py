"""
Error Logger for Annotation System
Provides comprehensive error logging with rotation and filtering.
Based on legacy ABILIUS error logging implementation.
"""

import os
import time
import logging
import logging.handlers
import threading
import json
from typing import Dict, List, Optional, Any, TextIO
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

from .error_manager import ErrorInfo, ErrorSeverity, ErrorCategory, get_global_error_manager

# Handle PyQt5 imports for signal support
try:
    from PyQt5.QtCore import QObject, pyqtSignal
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    QObject = object
    def pyqtSignal(*args, **kwargs):
        return None


class LogFormat(Enum):
    """Log output formats."""
    TEXT = "text"
    JSON = "json"
    CSV = "csv"
    XML = "xml"


@dataclass
class LogConfig:
    """Configuration for error logging."""
    log_dir: str = "logs"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_files: int = 10
    log_format: LogFormat = LogFormat.TEXT
    log_level: ErrorSeverity = ErrorSeverity.WARNING
    include_traceback: bool = True
    include_context: bool = True
    rotate_daily: bool = True
    compress_old_logs: bool = True


class ErrorLogger(QObject if PYQT5_AVAILABLE else object):
    """Comprehensive error logging system."""
    
    # Signals for log events
    if PYQT5_AVAILABLE:
        log_written = pyqtSignal(str, str)  # log_level, message
        log_rotated = pyqtSignal(str)       # new_log_file
        log_error = pyqtSignal(str)         # error_message
    
    def __init__(self, config: LogConfig = None):
        if PYQT5_AVAILABLE:
            super().__init__()
        
        self.config = config or LogConfig()
        self._loggers: Dict[str, logging.Logger] = {}
        self._handlers: Dict[str, logging.Handler] = {}
        self._log_files: Dict[str, Path] = {}
        
        # Statistics
        self._log_stats: Dict[str, Dict[str, int]] = {}
        self._session_start_time = time.time()
        
        # Threading
        self._lock = threading.RLock()
        self._shutdown = False
        
        # Setup logging directory
        self._setup_log_directory()
        
        # Setup default loggers
        self._setup_default_loggers()
        
        # Connect to error manager
        self._connect_to_error_manager()
    
    def _setup_log_directory(self) -> None:
        """Setup logging directory structure."""
        try:
            log_dir = Path(self.config.log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            (log_dir / "errors").mkdir(exist_ok=True)
            (log_dir / "components").mkdir(exist_ok=True)
            (log_dir / "archived").mkdir(exist_ok=True)
            
        except Exception as e:
            print(f"Failed to setup log directory: {e}")
    
    def _setup_default_loggers(self) -> None:
        """Setup default loggers for different categories."""
        loggers = [
            ("main", "annotation_errors.log"),
            ("io_errors", "io_errors.log"),
            ("memory_errors", "memory_errors.log"),
            ("network_errors", "network_errors.log"),
            ("ui_errors", "ui_errors.log"),
            ("critical", "critical_errors.log"),
        ]
        
        for logger_name, filename in loggers:
            self.create_logger(logger_name, filename)
    
    def create_logger(self, name: str, filename: str, level: Optional[ErrorSeverity] = None) -> logging.Logger:
        """Create a new logger with specified configuration."""
        with self._lock:
            if name in self._loggers:
                return self._loggers[name]
            
            # Create logger
            logger = logging.getLogger(f"annotation_{name}")
            logger.setLevel(logging.DEBUG)
            
            # Clear existing handlers
            logger.handlers.clear()
            
            # Create file path
            log_file = Path(self.config.log_dir) / filename
            self._log_files[name] = log_file
            
            # Create handler based on configuration
            if self.config.rotate_daily:
                handler = logging.handlers.TimedRotatingFileHandler(
                    log_file,
                    when='midnight',
                    interval=1,
                    backupCount=self.config.max_files,
                    encoding='utf-8'
                )
            else:
                handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=self.config.max_file_size,
                    backupCount=self.config.max_files,
                    encoding='utf-8'
                )
            
            # Create formatter based on format
            formatter = self._create_formatter()
            handler.setFormatter(formatter)
            
            logger.addHandler(handler)
            
            # Store references
            self._loggers[name] = logger
            self._handlers[name] = handler
            
            # Initialize statistics
            self._log_stats[name] = {
                'total_entries': 0,
                'error_count': 0,
                'warning_count': 0,
                'critical_count': 0
            }
            
            return logger
    
    def _create_formatter(self) -> logging.Formatter:
        """Create log formatter based on configuration."""
        if self.config.log_format == LogFormat.JSON:
            return JsonFormatter()
        elif self.config.log_format == LogFormat.CSV:
            return CsvFormatter()
        elif self.config.log_format == LogFormat.XML:
            return XmlFormatter()
        else:
            # Default text format
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            return logging.Formatter(format_string, datefmt='%Y-%m-%d %H:%M:%S')
    
    def log_error(self, error_info: ErrorInfo, logger_name: str = "main") -> None:
        """Log error information."""
        try:
            with self._lock:
                if self._shutdown:
                    return
                
                # Get or create logger
                if logger_name not in self._loggers:
                    self.create_logger(logger_name, f"{logger_name}.log")
                
                logger = self._loggers[logger_name]
                
                # Create log message
                log_data = self._create_log_data(error_info)
                
                # Determine log level
                log_level = self._severity_to_log_level(error_info.severity)
                
                # Log the error
                if self.config.log_format == LogFormat.JSON:
                    logger.log(log_level, json.dumps(log_data, indent=2))
                else:
                    message = self._format_error_message(error_info)
                    logger.log(log_level, message)
                
                # Update statistics
                self._update_stats(logger_name, error_info.severity)
                
                # Emit signal
                if PYQT5_AVAILABLE:
                    self.log_written.emit(error_info.severity.value, error_info.message)
                
        except Exception as e:
            print(f"Failed to log error: {e}")
            if PYQT5_AVAILABLE:
                self.log_error.emit(f"Logging failed: {e}")
    
    def _create_log_data(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """Create structured log data from error info."""
        data = {
            'timestamp': datetime.fromtimestamp(error_info.timestamp).isoformat(),
            'error_id': error_info.error_id,
            'severity': error_info.severity.value,
            'category': error_info.category.value,
            'component': error_info.component,
            'message': error_info.message,
        }
        
        if self.config.include_context and error_info.details:
            data['details'] = error_info.details
        
        if self.config.include_context and error_info.context:
            data['context'] = error_info.context
        
        if self.config.include_traceback and error_info.traceback_str:
            data['traceback'] = error_info.traceback_str
        
        # Add recovery information if available
        data['recovery_attempted'] = error_info.recovery_attempted
        data['recovery_successful'] = error_info.recovery_successful
        data['user_notified'] = error_info.user_notified
        
        return data
    
    def _format_error_message(self, error_info: ErrorInfo) -> str:
        """Format error message for text logging."""
        message = f"[{error_info.component}] {error_info.message}"
        
        if error_info.details:
            message += f" | Details: {error_info.details}"
        
        if self.config.include_context and error_info.context:
            context_str = ", ".join(f"{k}={v}" for k, v in error_info.context.items())
            message += f" | Context: {context_str}"
        
        if error_info.recovery_attempted:
            status = "successful" if error_info.recovery_successful else "failed"
            message += f" | Recovery: {status}"
        
        return message
    
    def _severity_to_log_level(self, severity: ErrorSeverity) -> int:
        """Convert error severity to logging level."""
        mapping = {
            ErrorSeverity.DEBUG: logging.DEBUG,
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        return mapping.get(severity, logging.ERROR)
    
    def _update_stats(self, logger_name: str, severity: ErrorSeverity) -> None:
        """Update logging statistics."""
        if logger_name in self._log_stats:
            stats = self._log_stats[logger_name]
            stats['total_entries'] += 1
            
            if severity == ErrorSeverity.ERROR:
                stats['error_count'] += 1
            elif severity == ErrorSeverity.WARNING:
                stats['warning_count'] += 1
            elif severity == ErrorSeverity.CRITICAL:
                stats['critical_count'] += 1
    
    def _connect_to_error_manager(self) -> None:
        """Connect to error manager for automatic logging."""
        try:
            error_manager = get_global_error_manager()
            
            if PYQT5_AVAILABLE and hasattr(error_manager, 'error_occurred'):
                error_manager.error_occurred.connect(self._handle_error_occurred)
                
        except Exception as e:
            print(f"Failed to connect to error manager: {e}")
    
    def _handle_error_occurred(self, error_info: ErrorInfo) -> None:
        """Handle error from error manager."""
        try:
            # Skip logging if below threshold
            if not self._should_log_error(error_info):
                return
            
            # Determine appropriate logger
            logger_name = self._get_logger_for_error(error_info)
            
            # Log the error
            self.log_error(error_info, logger_name)
            
        except Exception as e:
            print(f"Error handling error occurred signal: {e}")
    
    def _should_log_error(self, error_info: ErrorInfo) -> bool:
        """Check if error should be logged based on configuration."""
        severity_levels = {
            ErrorSeverity.DEBUG: 0,
            ErrorSeverity.INFO: 1,
            ErrorSeverity.WARNING: 2,
            ErrorSeverity.ERROR: 3,
            ErrorSeverity.CRITICAL: 4
        }
        
        min_level = severity_levels.get(self.config.log_level, 2)
        error_level = severity_levels.get(error_info.severity, 3)
        
        return error_level >= min_level
    
    def _get_logger_for_error(self, error_info: ErrorInfo) -> str:
        """Get appropriate logger name for error."""
        category_loggers = {
            ErrorCategory.IO_ERROR: "io_errors",
            ErrorCategory.MEMORY_ERROR: "memory_errors",
            ErrorCategory.NETWORK_ERROR: "network_errors",
            ErrorCategory.UI_ERROR: "ui_errors",
        }
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            return "critical"
        
        return category_loggers.get(error_info.category, "main")
    
    def search_logs(self, 
                   query: str,
                   logger_name: str = None,
                   start_time: Optional[float] = None,
                   end_time: Optional[float] = None,
                   severity: Optional[ErrorSeverity] = None) -> List[Dict[str, Any]]:
        """Search through log files."""
        results = []
        
        try:
            with self._lock:
                loggers_to_search = [logger_name] if logger_name else list(self._log_files.keys())
                
                for name in loggers_to_search:
                    if name not in self._log_files:
                        continue
                    
                    log_file = self._log_files[name]
                    if not log_file.exists():
                        continue
                    
                    file_results = self._search_log_file(
                        log_file, query, start_time, end_time, severity
                    )
                    results.extend(file_results)
                
        except Exception as e:
            print(f"Error searching logs: {e}")
        
        return results
    
    def _search_log_file(self,
                        log_file: Path,
                        query: str,
                        start_time: Optional[float],
                        end_time: Optional[float],
                        severity: Optional[ErrorSeverity]) -> List[Dict[str, Any]]:
        """Search specific log file."""
        results = []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse line based on format
                    if self.config.log_format == LogFormat.JSON:
                        try:
                            log_data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                    else:
                        log_data = self._parse_text_log_line(line)
                    
                    if not log_data:
                        continue
                    
                    # Apply filters
                    if not self._matches_search_criteria(log_data, query, start_time, end_time, severity):
                        continue
                    
                    log_data['file'] = str(log_file)
                    log_data['line_number'] = line_num
                    results.append(log_data)
                    
        except Exception as e:
            print(f"Error searching log file {log_file}: {e}")
        
        return results
    
    def _parse_text_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse text format log line."""
        try:
            # Simple parsing for standard format
            # Expected: timestamp - logger - level - message
            parts = line.split(' - ', 3)
            if len(parts) >= 4:
                return {
                    'timestamp': parts[0],
                    'logger': parts[1],
                    'severity': parts[2].lower(),
                    'message': parts[3]
                }
        except Exception:
            pass
        
        return None
    
    def _matches_search_criteria(self,
                               log_data: Dict[str, Any],
                               query: str,
                               start_time: Optional[float],
                               end_time: Optional[float],
                               severity: Optional[ErrorSeverity]) -> bool:
        """Check if log entry matches search criteria."""
        # Text search
        if query and query.lower() not in str(log_data).lower():
            return False
        
        # Time range
        if start_time or end_time:
            entry_time = self._extract_timestamp(log_data)
            if entry_time:
                if start_time and entry_time < start_time:
                    return False
                if end_time and entry_time > end_time:
                    return False
        
        # Severity filter
        if severity:
            entry_severity = log_data.get('severity', '').lower()
            if entry_severity != severity.value:
                return False
        
        return True
    
    def _extract_timestamp(self, log_data: Dict[str, Any]) -> Optional[float]:
        """Extract timestamp from log data."""
        try:
            timestamp_str = log_data.get('timestamp', '')
            if 'T' in timestamp_str:  # ISO format
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                return dt.timestamp()
            else:
                # Try parsing standard format
                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                return dt.timestamp()
        except Exception:
            return None
    
    def export_logs(self,
                   output_file: str,
                   logger_name: str = None,
                   start_time: Optional[float] = None,
                   end_time: Optional[float] = None,
                   format: LogFormat = LogFormat.JSON) -> bool:
        """Export logs to file."""
        try:
            # Search logs
            logs = self.search_logs("", logger_name, start_time, end_time)
            
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Export based on format
            if format == LogFormat.JSON:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(logs, f, indent=2, default=str)
            elif format == LogFormat.CSV:
                self._export_csv(logs, output_path)
            else:
                self._export_text(logs, output_path)
            
            return True
            
        except Exception as e:
            print(f"Failed to export logs: {e}")
            return False
    
    def _export_csv(self, logs: List[Dict[str, Any]], output_path: Path) -> None:
        """Export logs in CSV format."""
        import csv
        
        if not logs:
            return
        
        fieldnames = set()
        for log in logs:
            fieldnames.update(log.keys())
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(fieldnames))
            writer.writeheader()
            writer.writerows(logs)
    
    def _export_text(self, logs: List[Dict[str, Any]], output_path: Path) -> None:
        """Export logs in text format."""
        with open(output_path, 'w', encoding='utf-8') as f:
            for log in logs:
                timestamp = log.get('timestamp', '')
                severity = log.get('severity', '')
                message = log.get('message', '')
                f.write(f"{timestamp} - {severity.upper()} - {message}\n")
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get logging statistics."""
        with self._lock:
            total_stats = {
                'session_duration': time.time() - self._session_start_time,
                'total_loggers': len(self._loggers),
                'total_entries': 0,
                'total_errors': 0,
                'total_warnings': 0,
                'total_critical': 0,
                'logger_stats': {}
            }
            
            for logger_name, stats in self._log_stats.items():
                total_stats['total_entries'] += stats['total_entries']
                total_stats['total_errors'] += stats['error_count']
                total_stats['total_warnings'] += stats['warning_count']
                total_stats['total_critical'] += stats['critical_count']
                total_stats['logger_stats'][logger_name] = stats.copy()
            
            return total_stats
    
    def cleanup_old_logs(self, max_age_days: int = 30) -> int:
        """Clean up old log files."""
        try:
            with self._lock:
                log_dir = Path(self.config.log_dir)
                current_time = time.time()
                max_age_seconds = max_age_days * 24 * 60 * 60
                
                cleaned_count = 0
                
                for log_file in log_dir.glob("**/*.log*"):
                    try:
                        file_age = current_time - log_file.stat().st_mtime
                        if file_age > max_age_seconds:
                            log_file.unlink()
                            cleaned_count += 1
                    except Exception as e:
                        print(f"Error cleaning log file {log_file}: {e}")
                
                return cleaned_count
                
        except Exception as e:
            print(f"Error during log cleanup: {e}")
            return 0
    
    def rotate_logs(self) -> None:
        """Manually rotate all log files."""
        try:
            with self._lock:
                for handler in self._handlers.values():
                    if hasattr(handler, 'doRollover'):
                        handler.doRollover()
                        
                        if PYQT5_AVAILABLE:
                            self.log_rotated.emit(str(handler.baseFilename))
                            
        except Exception as e:
            print(f"Error rotating logs: {e}")
    
    def shutdown(self) -> None:
        """Shutdown error logger."""
        with self._lock:
            self._shutdown = True
            
            # Close all handlers
            for handler in self._handlers.values():
                try:
                    handler.close()
                except Exception:
                    pass
            
            # Clear references
            self._loggers.clear()
            self._handlers.clear()


# Custom formatters

class JsonFormatter(logging.Formatter):
    """JSON log formatter."""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'funcName': record.funcName,
            'lineno': record.lineno
        }
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class CsvFormatter(logging.Formatter):
    """CSV log formatter."""
    
    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).isoformat()
        message = record.getMessage().replace(',', ';').replace('\n', ' ')
        return f"{timestamp},{record.levelname},{record.name},{message}"


class XmlFormatter(logging.Formatter):
    """XML log formatter."""
    
    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).isoformat()
        message = record.getMessage().replace('<', '&lt;').replace('>', '&gt;')
        
        xml = f"<log>"
        xml += f"<timestamp>{timestamp}</timestamp>"
        xml += f"<level>{record.levelname}</level>"
        xml += f"<logger>{record.name}</logger>"
        xml += f"<message>{message}</message>"
        xml += f"</log>"
        
        return xml


# Global error logger instance
_global_error_logger: Optional[ErrorLogger] = None
_logger_lock = threading.Lock()


def get_global_error_logger() -> ErrorLogger:
    """Get or create global error logger instance."""
    global _global_error_logger
    if _global_error_logger is None:
        with _logger_lock:
            if _global_error_logger is None:
                _global_error_logger = ErrorLogger()
    return _global_error_logger


def log_error(error_info: ErrorInfo, logger_name: str = "main") -> None:
    """Convenience function to log error."""
    logger = get_global_error_logger()
    logger.log_error(error_info, logger_name)


def search_logs(query: str, **kwargs) -> List[Dict[str, Any]]:
    """Convenience function to search logs."""
    logger = get_global_error_logger()
    return logger.search_logs(query, **kwargs)