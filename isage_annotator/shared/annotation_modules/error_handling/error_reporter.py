"""
Error Reporter for Annotation System
Provides user-friendly error reporting and notification capabilities.
Based on legacy ABILIUS error reporting implementation.
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass
from enum import Enum

from .error_manager import ErrorInfo, ErrorSeverity, ErrorCategory, get_global_error_manager

# Handle PyQt5 imports
try:
    from PyQt5.QtCore import QObject, pyqtSignal, QTimer
    from PyQt5.QtWidgets import QMessageBox, QWidget
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    QObject = object
    QTimer = None
    def pyqtSignal(*args, **kwargs):
        return None

import logging
logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """Notification levels for user interface."""
    SILENT = "silent"
    STATUSBAR = "statusbar"
    TOOLTIP = "tooltip"
    DIALOG = "dialog"
    PERSISTENT = "persistent"


@dataclass
class ErrorReport:
    """User-friendly error report."""
    title: str
    message: str
    details: str
    suggestion: str
    notification_level: NotificationLevel
    show_technical_details: bool = False
    allow_retry: bool = False
    allow_ignore: bool = False


class ErrorReporter(QObject if PYQT5_AVAILABLE else object):
    """User-friendly error reporting system."""
    
    # Signals for UI notifications
    if PYQT5_AVAILABLE:
        notification_requested = pyqtSignal(object)  # ErrorReport
        status_message_requested = pyqtSignal(str, int)  # message, timeout
        tooltip_requested = pyqtSignal(str, object)  # message, widget
    
    def __init__(self):
        if PYQT5_AVAILABLE:
            super().__init__()
        
        self._error_manager = get_global_error_manager()
        self._parent_widget: Optional[QWidget] = None
        self._notification_settings: Dict[ErrorCategory, NotificationLevel] = {}
        self._suppressed_errors: Set[str] = set()
        self._error_templates: Dict[ErrorCategory, ErrorReport] = {}
        
        # Rate limiting
        self._last_notification_time: Dict[str, float] = {}
        self._notification_cooldown: float = 5.0  # seconds
        
        # Batch reporting
        self._batch_notifications: bool = False
        self._batch_timer: Optional[QTimer] = None
        self._pending_reports: List[ErrorReport] = []
        
        # Threading
        self._lock = threading.RLock()
        
        # Setup default notification levels
        self._setup_default_notifications()
        
        # Setup error templates
        self._setup_error_templates()
        
        # Connect to error manager
        if PYQT5_AVAILABLE and hasattr(self._error_manager, 'error_occurred'):
            self._error_manager.error_occurred.connect(self._handle_error)
    
    def set_parent_widget(self, parent: QWidget) -> None:
        """Set parent widget for dialogs."""
        self._parent_widget = parent
    
    def set_notification_level(self, category: ErrorCategory, level: NotificationLevel) -> None:
        """Set notification level for error category."""
        with self._lock:
            self._notification_settings[category] = level
    
    def set_batch_notifications(self, enabled: bool, batch_delay_ms: int = 1000) -> None:
        """Enable/disable batch notifications."""
        with self._lock:
            self._batch_notifications = enabled
            
            if enabled and PYQT5_AVAILABLE:
                if self._batch_timer is None:
                    self._batch_timer = QTimer()
                    self._batch_timer.timeout.connect(self._process_batch_notifications)
                    self._batch_timer.setSingleShot(True)
                self._batch_timer.setInterval(batch_delay_ms)
            elif self._batch_timer:
                self._batch_timer.stop()
    
    def suppress_error_pattern(self, pattern: str) -> None:
        """Suppress errors matching pattern."""
        with self._lock:
            self._suppressed_errors.add(pattern)
    
    def unsuppress_error_pattern(self, pattern: str) -> None:
        """Remove error suppression pattern."""
        with self._lock:
            self._suppressed_errors.discard(pattern)
    
    def report_user_error(self, 
                         title: str,
                         message: str,
                         details: str = "",
                         suggestion: str = "",
                         level: NotificationLevel = NotificationLevel.DIALOG,
                         allow_retry: bool = False) -> None:
        """Report user-facing error directly."""
        
        report = ErrorReport(
            title=title,
            message=message,
            details=details,
            suggestion=suggestion,
            notification_level=level,
            allow_retry=allow_retry,
            allow_ignore=True
        )
        
        self._show_notification(report)
    
    def _handle_error(self, error_info: ErrorInfo) -> None:
        """Handle error from error manager."""
        try:
            with self._lock:
                # Check if error should be suppressed
                if self._should_suppress_error(error_info):
                    return
                
                # Check rate limiting
                if not self._check_rate_limit(error_info):
                    return
                
                # Create user-friendly report
                report = self._create_error_report(error_info)
                
                # Show notification
                if self._batch_notifications:
                    self._add_to_batch(report)
                else:
                    self._show_notification(report)
                    
        except Exception as e:
            logger.warning(f"Error in error reporter: {e}")
    
    def _should_suppress_error(self, error_info: ErrorInfo) -> bool:
        """Check if error should be suppressed."""
        for pattern in self._suppressed_errors:
            if pattern in error_info.message or pattern in error_info.component:
                return True
        return False
    
    def _check_rate_limit(self, error_info: ErrorInfo) -> bool:
        """Check if error notification should be rate limited."""
        key = f"{error_info.component}_{error_info.category.value}"
        current_time = time.time()
        
        if key in self._last_notification_time:
            time_diff = current_time - self._last_notification_time[key]
            if time_diff < self._notification_cooldown:
                return False
        
        self._last_notification_time[key] = current_time
        return True
    
    def _create_error_report(self, error_info: ErrorInfo) -> ErrorReport:
        """Create user-friendly error report."""
        # Get template for category
        template = self._error_templates.get(error_info.category)
        if template:
            report = ErrorReport(
                title=template.title,
                message=self._format_template_message(template.message, error_info),
                details=template.details or error_info.details,
                suggestion=template.suggestion,
                notification_level=template.notification_level,
                show_technical_details=template.show_technical_details,
                allow_retry=template.allow_retry,
                allow_ignore=template.allow_ignore
            )
        else:
            # Create generic report
            report = ErrorReport(
                title=self._get_error_title(error_info),
                message=self._get_user_friendly_message(error_info),
                details=error_info.details,
                suggestion=self._get_error_suggestion(error_info),
                notification_level=self._get_notification_level(error_info),
                show_technical_details=error_info.severity == ErrorSeverity.CRITICAL,
                allow_retry=error_info.category != ErrorCategory.VALIDATION_ERROR,
                allow_ignore=error_info.severity != ErrorSeverity.CRITICAL
            )
        
        return report
    
    def _get_error_title(self, error_info: ErrorInfo) -> str:
        """Get user-friendly error title."""
        if error_info.severity == ErrorSeverity.CRITICAL:
            return "Critical Error"
        elif error_info.severity == ErrorSeverity.ERROR:
            return "Error"
        elif error_info.severity == ErrorSeverity.WARNING:
            return "Warning"
        else:
            return "Information"
    
    def _get_user_friendly_message(self, error_info: ErrorInfo) -> str:
        """Convert technical error message to user-friendly format."""
        message = error_info.message
        
        # Common translations
        translations = {
            "FileNotFoundError": "The requested file could not be found.",
            "PermissionError": "Permission denied. Please check file permissions.",
            "MemoryError": "Insufficient memory to complete the operation.",
            "ValueError": "Invalid value provided.",
            "ConnectionError": "Network connection failed.",
            "TimeoutError": "Operation timed out.",
        }
        
        for tech_term, user_term in translations.items():
            if tech_term in message:
                return user_term
        
        # Remove technical prefixes
        if ": " in message:
            parts = message.split(": ", 1)
            if len(parts) > 1:
                return parts[1]
        
        return message
    
    def _get_error_suggestion(self, error_info: ErrorInfo) -> str:
        """Get suggestion based on error category."""
        suggestions = {
            ErrorCategory.IO_ERROR: "Please check file paths and permissions.",
            ErrorCategory.MEMORY_ERROR: "Try closing other applications or reducing data size.",
            ErrorCategory.NETWORK_ERROR: "Please check your network connection.",
            ErrorCategory.VALIDATION_ERROR: "Please verify your input data.",
            ErrorCategory.USER_ERROR: "Please review your settings and try again.",
        }
        
        return suggestions.get(error_info.category, "Please try again or contact support.")
    
    def _get_notification_level(self, error_info: ErrorInfo) -> NotificationLevel:
        """Get notification level for error."""
        # Check custom settings
        if error_info.category in self._notification_settings:
            return self._notification_settings[error_info.category]
        
        # Default levels based on severity
        if error_info.severity == ErrorSeverity.CRITICAL:
            return NotificationLevel.DIALOG
        elif error_info.severity == ErrorSeverity.ERROR:
            return NotificationLevel.DIALOG
        elif error_info.severity == ErrorSeverity.WARNING:
            return NotificationLevel.STATUSBAR
        else:
            return NotificationLevel.SILENT
    
    def _format_template_message(self, template: str, error_info: ErrorInfo) -> str:
        """Format template message with error info."""
        try:
            return template.format(
                component=error_info.component,
                message=error_info.message,
                details=error_info.details,
                **error_info.context
            )
        except Exception:
            return template
    
    def _add_to_batch(self, report: ErrorReport) -> None:
        """Add report to batch queue."""
        self._pending_reports.append(report)
        
        if PYQT5_AVAILABLE and self._batch_timer:
            self._batch_timer.start()
    
    def _process_batch_notifications(self) -> None:
        """Process batched notifications."""
        if not self._pending_reports:
            return
        
        with self._lock:
            reports = self._pending_reports.copy()
            self._pending_reports.clear()
        
        # Group by notification level
        grouped_reports = {}
        for report in reports:
            level = report.notification_level
            if level not in grouped_reports:
                grouped_reports[level] = []
            grouped_reports[level].append(report)
        
        # Show grouped notifications
        for level, level_reports in grouped_reports.items():
            if level == NotificationLevel.DIALOG:
                self._show_batch_dialog(level_reports)
            else:
                # Show individual notifications for non-dialog levels
                for report in level_reports:
                    self._show_notification(report)
    
    def _show_batch_dialog(self, reports: List[ErrorReport]) -> None:
        """Show batch dialog for multiple errors."""
        if not reports:
            return
        
        if len(reports) == 1:
            self._show_notification(reports[0])
            return
        
        # Create summary message
        title = f"Multiple Errors ({len(reports)})"
        message = f"{len(reports)} errors occurred:\n\n"
        
        for i, report in enumerate(reports[:5], 1):  # Limit to first 5
            message += f"{i}. {report.message}\n"
        
        if len(reports) > 5:
            message += f"... and {len(reports) - 5} more errors."
        
        summary_report = ErrorReport(
            title=title,
            message=message,
            details="\n\n".join(r.details for r in reports if r.details),
            suggestion="Please review the errors and take appropriate action.",
            notification_level=NotificationLevel.DIALOG,
            allow_ignore=True
        )
        
        self._show_notification(summary_report)
    
    def _show_notification(self, report: ErrorReport) -> None:
        """Show notification based on level."""
        try:
            if report.notification_level == NotificationLevel.SILENT:
                return
            elif report.notification_level == NotificationLevel.STATUSBAR:
                self._show_status_message(report)
            elif report.notification_level == NotificationLevel.TOOLTIP:
                self._show_tooltip(report)
            elif report.notification_level == NotificationLevel.DIALOG:
                self._show_dialog(report)
            elif report.notification_level == NotificationLevel.PERSISTENT:
                self._show_persistent_notification(report)
                
        except Exception as e:
            logger.warning(f"Error showing notification: {e}")
    
    def _show_status_message(self, report: ErrorReport) -> None:
        """Show status bar message."""
        if PYQT5_AVAILABLE:
            self.status_message_requested.emit(report.message, 5000)
    
    def _show_tooltip(self, report: ErrorReport) -> None:
        """Show tooltip notification."""
        if PYQT5_AVAILABLE:
            self.tooltip_requested.emit(report.message, self._parent_widget)
    
    def _show_dialog(self, report: ErrorReport) -> None:
        """Show error dialog."""
        if not PYQT5_AVAILABLE or not self._parent_widget:
            print(f"ERROR: {report.title} - {report.message}")
            return
        
        try:
            msg_box = QMessageBox(self._parent_widget)
            msg_box.setWindowTitle(report.title)
            msg_box.setText(report.message)
            
            if report.details:
                msg_box.setDetailedText(report.details)
            
            if report.suggestion:
                msg_box.setInformativeText(report.suggestion)
            
            # Set icon based on title
            if "Critical" in report.title:
                msg_box.setIcon(QMessageBox.Critical)
            elif "Error" in report.title:
                msg_box.setIcon(QMessageBox.Critical)
            elif "Warning" in report.title:
                msg_box.setIcon(QMessageBox.Warning)
            else:
                msg_box.setIcon(QMessageBox.Information)
            
            # Set buttons
            if report.allow_retry and report.allow_ignore:
                msg_box.setStandardButtons(QMessageBox.Retry | QMessageBox.Ignore | QMessageBox.Ok)
            elif report.allow_retry:
                msg_box.setStandardButtons(QMessageBox.Retry | QMessageBox.Ok)
            elif report.allow_ignore:
                msg_box.setStandardButtons(QMessageBox.Ignore | QMessageBox.Ok)
            else:
                msg_box.setStandardButtons(QMessageBox.Ok)
            
            msg_box.exec_()
            
        except Exception as e:
            logger.warning(f"Error showing dialog: {e}")
            print(f"ERROR: {report.title} - {report.message}")
    
    def _show_persistent_notification(self, report: ErrorReport) -> None:
        """Show persistent notification."""
        # This would integrate with system notifications or persistent UI elements
        if PYQT5_AVAILABLE:
            self.notification_requested.emit(report)
    
    def _setup_default_notifications(self) -> None:
        """Setup default notification levels."""
        self._notification_settings = {
            ErrorCategory.CRITICAL: NotificationLevel.DIALOG,
            ErrorCategory.IO_ERROR: NotificationLevel.DIALOG,
            ErrorCategory.MEMORY_ERROR: NotificationLevel.DIALOG,
            ErrorCategory.NETWORK_ERROR: NotificationLevel.STATUSBAR,
            ErrorCategory.VALIDATION_ERROR: NotificationLevel.DIALOG,
            ErrorCategory.UI_ERROR: NotificationLevel.STATUSBAR,
            ErrorCategory.USER_ERROR: NotificationLevel.DIALOG,
            ErrorCategory.DATA_ERROR: NotificationLevel.DIALOG,
            ErrorCategory.SYSTEM_ERROR: NotificationLevel.DIALOG,
        }
    
    def _setup_error_templates(self) -> None:
        """Setup error message templates."""
        self._error_templates = {
            ErrorCategory.IO_ERROR: ErrorReport(
                title="File Operation Error",
                message="Could not access file: {message}",
                details="",
                suggestion="Please check that the file exists and you have permission to access it.",
                notification_level=NotificationLevel.DIALOG,
                allow_retry=True,
                allow_ignore=False
            ),
            
            ErrorCategory.MEMORY_ERROR: ErrorReport(
                title="Memory Error",
                message="Insufficient memory to complete the operation",
                details="",
                suggestion="Try closing other applications or working with smaller datasets.",
                notification_level=NotificationLevel.DIALOG,
                allow_retry=True,
                allow_ignore=False
            ),
            
            ErrorCategory.VALIDATION_ERROR: ErrorReport(
                title="Validation Error",
                message="Invalid input: {message}",
                details="",
                suggestion="Please check your input and try again.",
                notification_level=NotificationLevel.DIALOG,
                allow_retry=False,
                allow_ignore=False
            )
        }


# Global error reporter instance
_global_error_reporter: Optional[ErrorReporter] = None
_reporter_lock = threading.Lock()


def get_global_error_reporter() -> ErrorReporter:
    """Get or create global error reporter instance."""
    global _global_error_reporter
    if _global_error_reporter is None:
        with _reporter_lock:
            if _global_error_reporter is None:
                _global_error_reporter = ErrorReporter()
    return _global_error_reporter


def report_user_error(title: str, 
                     message: str, 
                     details: str = "",
                     suggestion: str = "",
                     level: NotificationLevel = NotificationLevel.DIALOG) -> None:
    """Convenience function to report user error."""
    reporter = get_global_error_reporter()
    reporter.report_user_error(title, message, details, suggestion, level)