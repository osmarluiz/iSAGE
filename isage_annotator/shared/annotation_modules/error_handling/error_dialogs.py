"""
Error Dialog System for Annotation System
Provides specialized error dialogs with recovery options.
Based on legacy ABILIUS error dialog implementation.
"""

import sys
import traceback
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .error_manager import ErrorInfo, ErrorSeverity, ErrorCategory
from .error_recovery import RecoveryStrategy, get_global_error_recovery

# Handle PyQt5 imports
try:
    from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                                QLabel, QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem,
                                QTabWidget, QWidget, QScrollArea, QSplitter,
                                QCheckBox, QComboBox, QProgressBar, QApplication)
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal
    from PyQt5.QtGui import QFont, QIcon, QPixmap
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False


class DialogResult(Enum):
    """Dialog result types."""
    OK = "ok"
    CANCEL = "cancel"
    RETRY = "retry"
    IGNORE = "ignore"
    DETAILS = "details"
    REPORT = "report"


@dataclass
class DialogConfig:
    """Configuration for error dialogs."""
    show_details: bool = True
    show_recovery_options: bool = True
    show_technical_info: bool = False
    allow_ignore: bool = True
    allow_retry: bool = True
    auto_recovery: bool = True
    modal: bool = True


class ErrorDialogs:
    """Specialized error dialog system."""
    
    def __init__(self):
        self._parent_widget = None
        self._theme_config = {}
        self._dialog_config = DialogConfig()
        self._error_recovery = get_global_error_recovery()
        
        # Dialog history
        self._dialog_history: List[ErrorInfo] = []
        self._max_history = 50
    
    def set_parent_widget(self, parent) -> None:
        """Set parent widget for dialogs."""
        self._parent_widget = parent
    
    def set_theme_config(self, theme_config: Dict[str, Any]) -> None:
        """Set theme configuration for dialogs."""
        self._theme_config = theme_config
    
    def set_dialog_config(self, config: DialogConfig) -> None:
        """Set dialog configuration."""
        self._dialog_config = config
    
    def show_error_dialog(self, error_info: ErrorInfo) -> DialogResult:
        """Show comprehensive error dialog."""
        if not PYQT5_AVAILABLE:
            return self._show_console_error(error_info)
        
        try:
            # Add to history
            self._add_to_history(error_info)
            
            # Create and show dialog
            dialog = ErrorDetailDialog(error_info, self._dialog_config, self._parent_widget)
            self._apply_theme(dialog)
            
            result = dialog.exec_()
            return DialogResult(dialog.get_result())
            
        except Exception as e:
            print(f"Error showing dialog: {e}")
            return self._show_console_error(error_info)
    
    def show_recovery_dialog(self, error_info: ErrorInfo, recovery_options: List[RecoveryStrategy]) -> Tuple[DialogResult, Optional[RecoveryStrategy]]:
        """Show recovery options dialog."""
        if not PYQT5_AVAILABLE:
            return DialogResult.CANCEL, None
        
        try:
            dialog = RecoveryDialog(error_info, recovery_options, self._parent_widget)
            self._apply_theme(dialog)
            
            result = dialog.exec_()
            selected_strategy = dialog.get_selected_strategy()
            
            return DialogResult(dialog.get_result()), selected_strategy
            
        except Exception as e:
            print(f"Error showing recovery dialog: {e}")
            return DialogResult.CANCEL, None
    
    def show_batch_error_dialog(self, errors: List[ErrorInfo]) -> DialogResult:
        """Show dialog for multiple errors."""
        if not PYQT5_AVAILABLE:
            for error in errors:
                self._show_console_error(error)
            return DialogResult.OK
        
        try:
            dialog = BatchErrorDialog(errors, self._dialog_config, self._parent_widget)
            self._apply_theme(dialog)
            
            result = dialog.exec_()
            return DialogResult(dialog.get_result())
            
        except Exception as e:
            print(f"Error showing batch dialog: {e}")
            return DialogResult.OK
    
    def show_critical_error_dialog(self, error_info: ErrorInfo) -> DialogResult:
        """Show critical error dialog with crash reporting."""
        if not PYQT5_AVAILABLE:
            return self._show_console_error(error_info)
        
        try:
            dialog = CriticalErrorDialog(error_info, self._parent_widget)
            self._apply_theme(dialog)
            
            result = dialog.exec_()
            return DialogResult(dialog.get_result())
            
        except Exception as e:
            print(f"Error showing critical dialog: {e}")
            return self._show_console_error(error_info)
    
    def _show_console_error(self, error_info: ErrorInfo) -> DialogResult:
        """Fallback console error display."""
        print(f"\n{'='*60}")
        print(f"ERROR [{error_info.severity.value.upper()}]: {error_info.message}")
        print(f"Component: {error_info.component}")
        print(f"Category: {error_info.category.value}")
        if error_info.details:
            print(f"Details: {error_info.details}")
        if error_info.traceback_str:
            print(f"Traceback:\n{error_info.traceback_str}")
        print(f"{'='*60}\n")
        return DialogResult.OK
    
    def _apply_theme(self, dialog) -> None:
        """Apply theme to dialog."""
        if not self._theme_config:
            return
        
        try:
            stylesheet = self._create_stylesheet()
            dialog.setStyleSheet(stylesheet)
        except Exception as e:
            print(f"Error applying theme: {e}")
    
    def _create_stylesheet(self) -> str:
        """Create stylesheet from theme config."""
        colors = self._theme_config.get('colors', {})
        
        return f"""
        QDialog {{
            background-color: {colors.get('background', '#ffffff')};
            color: {colors.get('text', '#000000')};
        }}
        
        QLabel {{
            color: {colors.get('text', '#000000')};
        }}
        
        QPushButton {{
            background-color: {colors.get('button_background', '#f0f0f0')};
            color: {colors.get('text', '#000000')};
            border: 1px solid {colors.get('border', '#c0c0c0')};
            border-radius: 4px;
            padding: 8px 16px;
            min-height: 20px;
        }}
        
        QPushButton:hover {{
            background-color: {colors.get('button_hover', '#e0e0e0')};
        }}
        
        QPushButton:pressed {{
            background-color: {colors.get('button_pressed', '#d0d0d0')};
        }}
        
        QTextEdit {{
            background-color: {colors.get('input_background', '#ffffff')};
            color: {colors.get('text', '#000000')};
            border: 1px solid {colors.get('input_border', '#c0c0c0')};
            border-radius: 4px;
        }}
        
        QTreeWidget {{
            background-color: {colors.get('input_background', '#ffffff')};
            color: {colors.get('text', '#000000')};
            border: 1px solid {colors.get('input_border', '#c0c0c0')};
        }}
        """
    
    def _add_to_history(self, error_info: ErrorInfo) -> None:
        """Add error to dialog history."""
        self._dialog_history.append(error_info)
        if len(self._dialog_history) > self._max_history:
            self._dialog_history = self._dialog_history[-self._max_history:]
    
    def get_dialog_history(self) -> List[ErrorInfo]:
        """Get dialog history."""
        return self._dialog_history.copy()


if PYQT5_AVAILABLE:
    
    class ErrorDetailDialog(QDialog):
        """Detailed error dialog with recovery options."""
        
        def __init__(self, error_info: ErrorInfo, config: DialogConfig, parent=None):
            super().__init__(parent)
            self.error_info = error_info
            self.config = config
            self._result = "cancel"
            
            self.setWindowTitle(f"Error - {error_info.component}")
            self.setModal(config.modal)
            self.resize(600, 400)
            
            self._setup_ui()
            self._setup_recovery_options()
        
        def _setup_ui(self) -> None:
            """Setup dialog UI."""
            layout = QVBoxLayout()
            
            # Main error message
            message_label = QLabel(self.error_info.message)
            message_label.setWordWrap(True)
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            message_label.setFont(font)
            layout.addWidget(message_label)
            
            # Error details
            if self.config.show_details and self.error_info.details:
                details_label = QLabel(self.error_info.details)
                details_label.setWordWrap(True)
                layout.addWidget(details_label)
            
            # Tab widget for additional information
            tab_widget = QTabWidget()
            
            # Technical details tab
            if self.config.show_technical_info:
                tech_widget = self._create_technical_tab()
                tab_widget.addTab(tech_widget, "Technical Details")
            
            # Recovery options tab
            if self.config.show_recovery_options:
                recovery_widget = self._create_recovery_tab()
                tab_widget.addTab(recovery_widget, "Recovery Options")
            
            layout.addWidget(tab_widget)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            if self.config.allow_retry:
                retry_button = QPushButton("Retry")
                retry_button.clicked.connect(lambda: self._set_result("retry"))
                button_layout.addWidget(retry_button)
            
            if self.config.allow_ignore:
                ignore_button = QPushButton("Ignore")
                ignore_button.clicked.connect(lambda: self._set_result("ignore"))
                button_layout.addWidget(ignore_button)
            
            ok_button = QPushButton("OK")
            ok_button.clicked.connect(lambda: self._set_result("ok"))
            ok_button.setDefault(True)
            button_layout.addWidget(ok_button)
            
            layout.addLayout(button_layout)
            self.setLayout(layout)
        
        def _create_technical_tab(self) -> QWidget:
            """Create technical details tab."""
            widget = QWidget()
            layout = QVBoxLayout()
            
            # Error info tree
            tree = QTreeWidget()
            tree.setHeaderLabels(["Property", "Value"])
            
            # Add error information
            items = [
                ("Error ID", self.error_info.error_id),
                ("Severity", self.error_info.severity.value),
                ("Category", self.error_info.category.value),
                ("Component", self.error_info.component),
                ("Timestamp", str(self.error_info.timestamp)),
            ]
            
            for prop, value in items:
                item = QTreeWidgetItem([prop, str(value)])
                tree.addTopLevelItem(item)
            
            # Add context information
            if self.error_info.context:
                context_item = QTreeWidgetItem(["Context", ""])
                tree.addTopLevelItem(context_item)
                
                for key, value in self.error_info.context.items():
                    child_item = QTreeWidgetItem([key, str(value)])
                    context_item.addChild(child_item)
                
                context_item.setExpanded(True)
            
            layout.addWidget(tree)
            
            # Traceback
            if self.error_info.traceback_str:
                layout.addWidget(QLabel("Traceback:"))
                traceback_text = QTextEdit()
                traceback_text.setPlainText(self.error_info.traceback_str)
                traceback_text.setReadOnly(True)
                traceback_text.setFont(QFont("Courier", 9))
                layout.addWidget(traceback_text)
            
            widget.setLayout(layout)
            return widget
        
        def _create_recovery_tab(self) -> QWidget:
            """Create recovery options tab."""
            widget = QWidget()
            layout = QVBoxLayout()
            
            layout.addWidget(QLabel("Available recovery options:"))
            
            # Recovery options list
            self.recovery_list = QTreeWidget()
            self.recovery_list.setHeaderLabels(["Strategy", "Description", "Status"])
            
            layout.addWidget(self.recovery_list)
            
            # Auto-recovery checkbox
            if self.config.auto_recovery:
                self.auto_recovery_checkbox = QCheckBox("Attempt automatic recovery")
                self.auto_recovery_checkbox.setChecked(True)
                layout.addWidget(self.auto_recovery_checkbox)
            
            widget.setLayout(layout)
            return widget
        
        def _setup_recovery_options(self) -> None:
            """Setup recovery options."""
            if not (self.config.show_recovery_options and hasattr(self, 'recovery_list')):
                return
            
            # Get available recovery strategies
            recovery_stats = self._get_recovery_stats()
            
            for strategy in RecoveryStrategy:
                stats = recovery_stats.get(strategy.value, {'attempts': 0, 'success_rate': 0})
                
                item = QTreeWidgetItem([
                    strategy.value,
                    self._get_strategy_description(strategy),
                    f"Success rate: {stats['success_rate']:.1%} ({stats['attempts']} attempts)"
                ])
                
                self.recovery_list.addTopLevelItem(item)
        
        def _get_strategy_description(self, strategy: RecoveryStrategy) -> str:
            """Get description for recovery strategy."""
            descriptions = {
                RecoveryStrategy.RETRY: "Retry the failed operation",
                RecoveryStrategy.FALLBACK: "Use alternative method",
                RecoveryStrategy.RESTORE_BACKUP: "Restore from backup",
                RecoveryStrategy.CLEAR_CACHE: "Clear cache and retry",
                RecoveryStrategy.RESTART_COMPONENT: "Restart component",
                RecoveryStrategy.USER_INTERVENTION: "Manual intervention required",
                RecoveryStrategy.IGNORE: "Ignore the error"
            }
            return descriptions.get(strategy, "Unknown strategy")
        
        def _get_recovery_stats(self) -> Dict[str, Any]:
            """Get recovery statistics."""
            try:
                from .error_recovery import get_global_error_recovery
                recovery = get_global_error_recovery()
                return recovery.get_recovery_statistics().get('strategy_stats', {})
            except Exception:
                return {}
        
        def _set_result(self, result: str) -> None:
            """Set dialog result."""
            self._result = result
            
            # Attempt recovery if enabled
            if (result == "retry" and 
                self.config.auto_recovery and 
                hasattr(self, 'auto_recovery_checkbox') and 
                self.auto_recovery_checkbox.isChecked()):
                
                self._attempt_recovery()
            
            self.accept()
        
        def _attempt_recovery(self) -> None:
            """Attempt automatic recovery."""
            try:
                from .error_recovery import get_global_error_recovery
                recovery = get_global_error_recovery()
                recovery.attempt_recovery(self.error_info)
            except Exception as e:
                print(f"Recovery attempt failed: {e}")
        
        def get_result(self) -> str:
            """Get dialog result."""
            return self._result
    
    
    class RecoveryDialog(QDialog):
        """Dialog for selecting recovery strategy."""
        
        def __init__(self, error_info: ErrorInfo, recovery_options: List[RecoveryStrategy], parent=None):
            super().__init__(parent)
            self.error_info = error_info
            self.recovery_options = recovery_options
            self._result = "cancel"
            self._selected_strategy = None
            
            self.setWindowTitle("Recovery Options")
            self.setModal(True)
            self.resize(500, 300)
            
            self._setup_ui()
        
        def _setup_ui(self) -> None:
            """Setup dialog UI."""
            layout = QVBoxLayout()
            
            # Message
            message = QLabel(f"Multiple recovery options are available for the error in {self.error_info.component}:")
            message.setWordWrap(True)
            layout.addWidget(message)
            
            # Recovery options
            self.strategy_combo = QComboBox()
            for strategy in self.recovery_options:
                self.strategy_combo.addItem(strategy.value, strategy)
            
            layout.addWidget(QLabel("Select recovery strategy:"))
            layout.addWidget(self.strategy_combo)
            
            # Description
            self.description_label = QLabel()
            self.description_label.setWordWrap(True)
            layout.addWidget(self.description_label)
            
            # Update description when selection changes
            self.strategy_combo.currentTextChanged.connect(self._update_description)
            self._update_description()
            
            # Buttons
            button_layout = QHBoxLayout()
            
            apply_button = QPushButton("Apply Recovery")
            apply_button.clicked.connect(lambda: self._set_result("apply"))
            button_layout.addWidget(apply_button)
            
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(lambda: self._set_result("cancel"))
            button_layout.addWidget(cancel_button)
            
            layout.addLayout(button_layout)
            self.setLayout(layout)
        
        def _update_description(self) -> None:
            """Update strategy description."""
            strategy = self.strategy_combo.currentData()
            if strategy:
                descriptions = {
                    RecoveryStrategy.RETRY: "Retry the failed operation with the same parameters",
                    RecoveryStrategy.FALLBACK: "Use an alternative method to accomplish the task",
                    RecoveryStrategy.RESTORE_BACKUP: "Restore from a previous backup if available",
                    RecoveryStrategy.CLEAR_CACHE: "Clear cache and temporary data, then retry",
                    RecoveryStrategy.RESTART_COMPONENT: "Restart the affected component",
                    RecoveryStrategy.USER_INTERVENTION: "Manual intervention is required",
                    RecoveryStrategy.IGNORE: "Ignore the error and continue"
                }
                self.description_label.setText(descriptions.get(strategy, ""))
        
        def _set_result(self, result: str) -> None:
            """Set dialog result."""
            self._result = result
            if result == "apply":
                self._selected_strategy = self.strategy_combo.currentData()
            self.accept()
        
        def get_result(self) -> str:
            """Get dialog result."""
            return self._result
        
        def get_selected_strategy(self) -> Optional[RecoveryStrategy]:
            """Get selected recovery strategy."""
            return self._selected_strategy
    
    
    class BatchErrorDialog(QDialog):
        """Dialog for multiple errors."""
        
        def __init__(self, errors: List[ErrorInfo], config: DialogConfig, parent=None):
            super().__init__(parent)
            self.errors = errors
            self.config = config
            self._result = "ok"
            
            self.setWindowTitle(f"Multiple Errors ({len(errors)})")
            self.setModal(config.modal)
            self.resize(700, 500)
            
            self._setup_ui()
        
        def _setup_ui(self) -> None:
            """Setup dialog UI."""
            layout = QVBoxLayout()
            
            # Summary
            summary_label = QLabel(f"{len(self.errors)} errors occurred:")
            font = QFont()
            font.setBold(True)
            summary_label.setFont(font)
            layout.addWidget(summary_label)
            
            # Error list
            self.error_tree = QTreeWidget()
            self.error_tree.setHeaderLabels(["Component", "Message", "Severity", "Time"])
            
            for error in self.errors:
                item = QTreeWidgetItem([
                    error.component,
                    error.message[:100] + "..." if len(error.message) > 100 else error.message,
                    error.severity.value,
                    str(int(error.timestamp))
                ])
                self.error_tree.addTopLevelItem(item)
            
            layout.addWidget(self.error_tree)
            
            # Details area
            self.details_text = QTextEdit()
            self.details_text.setReadOnly(True)
            self.details_text.hide()
            
            # Show details when item selected
            self.error_tree.itemClicked.connect(self._show_error_details)
            
            layout.addWidget(self.details_text)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            details_button = QPushButton("Show Details")
            details_button.clicked.connect(self._toggle_details)
            button_layout.addWidget(details_button)
            
            clear_button = QPushButton("Clear All")
            clear_button.clicked.connect(lambda: self._set_result("clear"))
            button_layout.addWidget(clear_button)
            
            ok_button = QPushButton("OK")
            ok_button.clicked.connect(lambda: self._set_result("ok"))
            ok_button.setDefault(True)
            button_layout.addWidget(ok_button)
            
            layout.addLayout(button_layout)
            self.setLayout(layout)
        
        def _show_error_details(self, item, column) -> None:
            """Show details for selected error."""
            row = self.error_tree.indexOfTopLevelItem(item)
            if 0 <= row < len(self.errors):
                error = self.errors[row]
                details = f"Error ID: {error.error_id}\n"
                details += f"Component: {error.component}\n"
                details += f"Category: {error.category.value}\n"
                details += f"Severity: {error.severity.value}\n\n"
                details += f"Message: {error.message}\n\n"
                if error.details:
                    details += f"Details: {error.details}\n\n"
                if error.traceback_str:
                    details += f"Traceback:\n{error.traceback_str}"
                
                self.details_text.setPlainText(details)
                self.details_text.show()
        
        def _toggle_details(self) -> None:
            """Toggle details visibility."""
            if self.details_text.isVisible():
                self.details_text.hide()
            else:
                self.details_text.show()
        
        def _set_result(self, result: str) -> None:
            """Set dialog result."""
            self._result = result
            self.accept()
        
        def get_result(self) -> str:
            """Get dialog result."""
            return self._result
    
    
    class CriticalErrorDialog(QDialog):
        """Dialog for critical errors with crash reporting."""
        
        def __init__(self, error_info: ErrorInfo, parent=None):
            super().__init__(parent)
            self.error_info = error_info
            self._result = "ok"
            
            self.setWindowTitle("Critical Error")
            self.setModal(True)
            self.resize(600, 500)
            
            self._setup_ui()
        
        def _setup_ui(self) -> None:
            """Setup dialog UI."""
            layout = QVBoxLayout()
            
            # Critical error message
            title_label = QLabel("A critical error has occurred")
            font = QFont()
            font.setPointSize(14)
            font.setBold(True)
            title_label.setFont(font)
            layout.addWidget(title_label)
            
            message_label = QLabel(self.error_info.message)
            message_label.setWordWrap(True)
            layout.addWidget(message_label)
            
            # System information
            sys_info = self._get_system_info()
            info_text = QTextEdit()
            info_text.setPlainText(sys_info)
            info_text.setReadOnly(True)
            info_text.setMaximumHeight(200)
            
            layout.addWidget(QLabel("System Information:"))
            layout.addWidget(info_text)
            
            # Traceback
            if self.error_info.traceback_str:
                traceback_text = QTextEdit()
                traceback_text.setPlainText(self.error_info.traceback_str)
                traceback_text.setReadOnly(True)
                traceback_text.setFont(QFont("Courier", 9))
                
                layout.addWidget(QLabel("Error Details:"))
                layout.addWidget(traceback_text)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            report_button = QPushButton("Send Report")
            report_button.clicked.connect(lambda: self._set_result("report"))
            button_layout.addWidget(report_button)
            
            restart_button = QPushButton("Restart Application")
            restart_button.clicked.connect(lambda: self._set_result("restart"))
            button_layout.addWidget(restart_button)
            
            close_button = QPushButton("Close")
            close_button.clicked.connect(lambda: self._set_result("close"))
            close_button.setDefault(True)
            button_layout.addWidget(close_button)
            
            layout.addLayout(button_layout)
            self.setLayout(layout)
        
        def _get_system_info(self) -> str:
            """Get system information for crash report."""
            try:
                import platform
                import sys
                
                info = f"Platform: {platform.platform()}\n"
                info += f"Python: {sys.version}\n"
                info += f"Error ID: {self.error_info.error_id}\n"
                info += f"Component: {self.error_info.component}\n"
                info += f"Timestamp: {self.error_info.timestamp}\n"
                
                return info
            except Exception:
                return "System information unavailable"
        
        def _set_result(self, result: str) -> None:
            """Set dialog result."""
            self._result = result
            
            if result == "restart":
                # Restart application
                QApplication.quit()
                sys.exit(0)
            
            self.accept()
        
        def get_result(self) -> str:
            """Get dialog result."""
            return self._result


# Global error dialogs instance
_global_error_dialogs: Optional[ErrorDialogs] = None


def get_global_error_dialogs() -> ErrorDialogs:
    """Get or create global error dialogs instance."""
    global _global_error_dialogs
    if _global_error_dialogs is None:
        _global_error_dialogs = ErrorDialogs()
    return _global_error_dialogs