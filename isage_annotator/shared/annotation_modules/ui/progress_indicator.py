"""
Progress Indicator UI Component for Annotation System
Provides visual progress indication for long-running operations.
Based on legacy ABILIUS progress indication implementation.
"""

import threading
import time
from typing import Optional, Callable, Dict, Any
from ..base_protocols import BaseComponent
from ..threading import ProgressThread, get_progress_manager

# Handle PyQt5 imports
try:
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel, QPushButton
    from PyQt5.QtCore import QTimer, pyqtSignal, Qt
    from PyQt5.QtGui import QFont, QColor, QPalette
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    # Mock widgets for environments without PyQt5
    class QWidget:
        def __init__(self, parent=None):
            self.parent = parent
            
    class QProgressBar:
        def __init__(self, parent=None):
            self.parent = parent
            
    class QLabel:
        def __init__(self, text="", parent=None):
            self.text = text
            self.parent = parent
            
    class QPushButton:
        def __init__(self, text="", parent=None):
            self.text = text
            self.parent = parent
            
    def pyqtSignal(*args, **kwargs):
        return None


class ProgressIndicator(BaseComponent):
    """Visual progress indicator component."""
    
    # Progress indicator signals
    cancelled = pyqtSignal()
    paused = pyqtSignal()
    resumed = pyqtSignal()
    
    def __init__(self, parent=None, name: str = "progress_indicator", version: str = "1.0.0"):
        super().__init__(name, version)
        self.parent = parent
        
        # Progress management
        self._progress_manager = get_progress_manager()
        self._current_operation: Optional[str] = None
        self._progress_thread: Optional[ProgressThread] = None
        
        # UI components
        self._widget: Optional[QWidget] = None
        self._progress_bar: Optional[QProgressBar] = None
        self._status_label: Optional[QLabel] = None
        self._cancel_button: Optional[QPushButton] = None
        self._pause_button: Optional[QPushButton] = None
        
        # Update timer
        self._update_timer: Optional[QTimer] = None
        self._update_interval = 100  # ms
        
        # State
        self._is_visible = False
        self._is_cancellable = True
        self._is_pausable = True
        
        # Initialize UI
        if PYQT5_AVAILABLE:
            self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup UI components."""
        if not PYQT5_AVAILABLE:
            return
            
        # Main widget
        self._widget = QWidget(self.parent)
        self._widget.setVisible(False)
        
        # Layout
        layout = QVBoxLayout(self._widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Status label
        self._status_label = QLabel("Ready", self._widget)
        self._status_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(10)
        self._status_label.setFont(font)
        layout.addWidget(self._status_label)
        
        # Progress bar
        self._progress_bar = QProgressBar(self._widget)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        layout.addWidget(self._progress_bar)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Pause button
        self._pause_button = QPushButton("Pause", self._widget)
        self._pause_button.clicked.connect(self._on_pause_clicked)
        self._pause_button.setEnabled(False)
        button_layout.addWidget(self._pause_button)
        
        # Cancel button
        self._cancel_button = QPushButton("Cancel", self._widget)
        self._cancel_button.clicked.connect(self._on_cancel_clicked)
        self._cancel_button.setEnabled(False)
        button_layout.addWidget(self._cancel_button)
        
        layout.addLayout(button_layout)
        
        # Update timer
        self._update_timer = QTimer(self._widget)
        self._update_timer.timeout.connect(self._update_progress)
        
        # Apply dark theme
        self._apply_dark_theme()
    
    def _apply_dark_theme(self) -> None:
        """Apply dark theme to progress indicator."""
        if not PYQT5_AVAILABLE or not self._widget:
            return
            
        self._widget.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 1px solid #555555;
                border-radius: 6px;
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 12px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
            }
            QLabel {
                color: #ffffff;
                border: none;
            }
        """)
    
    def show_progress(self, operation_name: str, total_steps: int = 100, 
                     cancellable: bool = True, pausable: bool = True) -> bool:
        """Show progress indicator for an operation."""
        try:
            # Store operation info
            self._current_operation = operation_name
            self._is_cancellable = cancellable
            self._is_pausable = pausable
            
            # Create progress thread
            self._progress_thread = self._progress_manager.create_progress_thread(
                operation_name, update_interval=0.1
            )
            
            # Set up callbacks
            self._progress_thread.add_progress_callback(self._on_progress_update)
            self._progress_thread.add_completion_callback(self._on_progress_complete)
            self._progress_thread.add_error_callback(self._on_progress_error)
            
            # Start progress tracking
            self._progress_thread.start(total_steps)
            
            # Show UI
            if PYQT5_AVAILABLE and self._widget:
                self._widget.setVisible(True)
                self._is_visible = True
                
                # Update UI state
                self._status_label.setText(f"Starting {operation_name}...")
                self._progress_bar.setRange(0, total_steps)
                self._progress_bar.setValue(0)
                
                # Update buttons
                self._cancel_button.setEnabled(cancellable)
                self._pause_button.setEnabled(pausable)
                self._pause_button.setText("Pause")
                
                # Start update timer
                self._update_timer.start(self._update_interval)
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error showing progress: {str(e)}")
            return False
    
    def hide_progress(self) -> None:
        """Hide progress indicator."""
        try:
            # Stop update timer
            if self._update_timer:
                self._update_timer.stop()
            
            # Stop progress thread
            if self._progress_thread:
                self._progress_thread.stop()
                self._progress_manager.remove_progress_thread(self._current_operation)
                self._progress_thread = None
            
            # Hide UI
            if PYQT5_AVAILABLE and self._widget:
                self._widget.setVisible(False)
                self._is_visible = False
            
            # Reset state
            self._current_operation = None
            
        except Exception as e:
            self.emit_error(f"Error hiding progress: {str(e)}")
    
    def update_progress(self, current: int, message: str = None) -> None:
        """Update progress value and message."""
        if self._progress_thread:
            self._progress_thread.update_progress(current, message)
    
    def set_total_steps(self, total: int) -> None:
        """Set total number of steps."""
        if self._progress_thread:
            self._progress_thread.set_total_steps(total)
            
        if PYQT5_AVAILABLE and self._progress_bar:
            self._progress_bar.setRange(0, total)
    
    def complete_progress(self, message: str = "Completed") -> None:
        """Mark progress as completed."""
        if self._progress_thread:
            self._progress_thread.complete(message)
    
    def fail_progress(self, message: str = "Failed") -> None:
        """Mark progress as failed."""
        if self._progress_thread:
            self._progress_thread.fail(message)
    
    def cancel_progress(self) -> None:
        """Cancel current operation."""
        if self._progress_thread:
            self._progress_thread.cancel("Operation cancelled")
            
        self.cancelled.emit()
    
    def pause_progress(self) -> None:
        """Pause current operation."""
        if self._progress_thread:
            self._progress_thread.pause()
            
        self.paused.emit()
    
    def resume_progress(self) -> None:
        """Resume paused operation."""
        if self._progress_thread:
            self._progress_thread.resume()
            
        self.resumed.emit()
    
    def _update_progress(self) -> None:
        """Update progress display."""
        if not self._progress_thread or not PYQT5_AVAILABLE:
            return
            
        try:
            # Get current progress
            progress = self._progress_thread.get_current_progress()
            
            # Update progress bar
            if self._progress_bar:
                self._progress_bar.setValue(progress.current)
                
            # Update status label
            if self._status_label:
                self._status_label.setText(progress.message)
                
            # Update pause button state
            if self._pause_button:
                if progress.state.value == "paused":
                    self._pause_button.setText("Resume")
                else:
                    self._pause_button.setText("Pause")
                    
        except Exception as e:
            self.emit_error(f"Error updating progress: {str(e)}")
    
    def _on_progress_update(self, progress) -> None:
        """Handle progress updates."""
        # Progress updates are handled by the update timer
        pass
    
    def _on_progress_complete(self, progress) -> None:
        """Handle progress completion."""
        # Auto-hide after completion
        if PYQT5_AVAILABLE:
            QTimer.singleShot(2000, self.hide_progress)  # Hide after 2 seconds
    
    def _on_progress_error(self, error_msg: str) -> None:
        """Handle progress errors."""
        if PYQT5_AVAILABLE and self._status_label:
            self._status_label.setText(f"Error: {error_msg}")
            
        # Auto-hide after error
        if PYQT5_AVAILABLE:
            QTimer.singleShot(3000, self.hide_progress)  # Hide after 3 seconds
    
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        self.cancel_progress()
    
    def _on_pause_clicked(self) -> None:
        """Handle pause button click."""
        if self._progress_thread:
            current_state = self._progress_thread.get_state()
            if current_state.value == "paused":
                self.resume_progress()
            else:
                self.pause_progress()
    
    def get_widget(self) -> Optional[QWidget]:
        """Get the UI widget."""
        return self._widget
    
    def is_visible(self) -> bool:
        """Check if progress indicator is visible."""
        return self._is_visible
    
    def get_current_operation(self) -> Optional[str]:
        """Get current operation name."""
        return self._current_operation
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get progress indicator statistics."""
        stats = super().get_statistics()
        
        progress_stats = {}
        if self._progress_thread:
            progress_stats = self._progress_thread.get_statistics()
            
        stats.update({
            'visible': self._is_visible,
            'current_operation': self._current_operation,
            'cancellable': self._is_cancellable,
            'pausable': self._is_pausable,
            'progress_stats': progress_stats
        })
        
        return stats


class ProgressNotificationManager:
    """Manages progress notifications for the annotation system."""
    
    def __init__(self):
        self._progress_indicators: Dict[str, ProgressIndicator] = {}
        self._manager_lock = threading.Lock()
    
    def create_progress_indicator(self, operation_name: str, parent=None) -> ProgressIndicator:
        """Create a new progress indicator."""
        with self._manager_lock:
            if operation_name in self._progress_indicators:
                # Remove existing indicator
                old_indicator = self._progress_indicators[operation_name]
                old_indicator.hide_progress()
                
            # Create new indicator
            indicator = ProgressIndicator(parent, f"progress_{operation_name}")
            self._progress_indicators[operation_name] = indicator
            
            return indicator
    
    def get_progress_indicator(self, operation_name: str) -> Optional[ProgressIndicator]:
        """Get progress indicator by operation name."""
        with self._manager_lock:
            return self._progress_indicators.get(operation_name)
    
    def remove_progress_indicator(self, operation_name: str) -> bool:
        """Remove progress indicator."""
        with self._manager_lock:
            if operation_name in self._progress_indicators:
                indicator = self._progress_indicators[operation_name]
                indicator.hide_progress()
                del self._progress_indicators[operation_name]
                return True
        return False
    
    def hide_all_progress(self) -> None:
        """Hide all progress indicators."""
        with self._manager_lock:
            for indicator in self._progress_indicators.values():
                indicator.hide_progress()
    
    def get_active_operations(self) -> list:
        """Get list of active operations."""
        with self._manager_lock:
            return [name for name, indicator in self._progress_indicators.items() 
                   if indicator.is_visible()]
    
    def get_manager_statistics(self) -> Dict[str, Any]:
        """Get manager statistics."""
        with self._manager_lock:
            return {
                'total_indicators': len(self._progress_indicators),
                'active_operations': self.get_active_operations(),
                'indicator_stats': {
                    name: indicator.get_statistics() 
                    for name, indicator in self._progress_indicators.items()
                }
            }


# Global progress notification manager
_global_progress_notification_manager = ProgressNotificationManager()

def get_progress_notification_manager() -> ProgressNotificationManager:
    """Get global progress notification manager."""
    return _global_progress_notification_manager