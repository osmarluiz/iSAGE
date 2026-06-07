"""
Simple Status Panel - Basic working implementation for demonstration

A simplified status panel that provides system status and feedback.
This is a minimal working version to demonstrate the modular concept.
"""

import logging
from typing import Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QGroupBox, QProgressBar, QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

logger = logging.getLogger(__name__)


class SimpleStatusPanel(QWidget):
    """
    Simplified status panel for system feedback and monitoring.
    
    Provides status updates, system messages, and progress tracking.
    """
    
    # Signals
    statusChanged = pyqtSignal(str, str)  # status_type, message
    
    def __init__(self, parent=None, name: str = "simple_status_panel", version: str = "1.0.0"):
        super().__init__(parent)
        
        self.name = name
        self.version = version
        self.initialized = False
        
        # State
        self._current_status: str = "Ready"
        self._messages: List[Dict[str, Any]] = []
        self._max_messages: int = 100
        
        # Create UI
        self.setup_ui()
        
        logger.info(f"SimpleStatusPanel '{name}' v{version} created")
    
    def initialize(self, panel_width: int = 384, theme: str = 'dark', **kwargs) -> bool:
        """Initialize the status panel."""
        try:
            # Apply sizing
            if panel_width:
                self.setFixedWidth(panel_width)
            
            # Apply theme
            if theme == 'dark':
                self.apply_dark_theme()
            else:
                self.apply_light_theme()
            
            self.initialized = True
            self.add_status_message("System", "Status panel initialized", "info")
            logger.info(f"SimpleStatusPanel initialized: width={panel_width}, theme={theme}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize status panel: {e}")
            return False
    
    def setup_ui(self):
        """Create the status panel UI."""
        # Check if layout already exists
        existing_layout = self.layout()
        if existing_layout is not None:
            # Clear existing layout
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Current status section
        status_group = self.create_status_section()
        layout.addWidget(status_group)
        
        # System info section
        system_group = self.create_system_info_section()
        layout.addWidget(system_group)
        
        # Progress section
        progress_group = self.create_progress_section()
        layout.addWidget(progress_group)
        
        # Messages section
        messages_group = self.create_messages_section()
        layout.addWidget(messages_group)
        
        # Spacer
        layout.addStretch()
    
    def create_header(self) -> QWidget:
        """Create the header section."""
        header = QLabel("📊 Status Panel")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #e2e8f0;
                background: #374151;
                border: 1px solid #4b5563;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 10px;
            }
        """)
        return header
    
    def create_status_section(self) -> QGroupBox:
        """Create the current status section."""
        group = QGroupBox("🔄 Current Status")
        layout = QVBoxLayout(group)
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #10b981;
                background: #064e3b;
                border: 1px solid #10b981;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Status details
        self.status_details = QLabel("System operational")
        self.status_details.setAlignment(Qt.AlignCenter)
        self.status_details.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.status_details)
        
        return group
    
    def create_system_info_section(self) -> QGroupBox:
        """Create the system info section."""
        group = QGroupBox("⚡ System Info")
        layout = QVBoxLayout(group)
        
        # Component status
        self.canvas_status = QLabel("🧩 Canvas: Ready")
        self.canvas_status.setStyleSheet("color: #10b981; font-size: 12px;")
        layout.addWidget(self.canvas_status)
        
        self.control_status = QLabel("🛠️ Controls: Ready") 
        self.control_status.setStyleSheet("color: #10b981; font-size: 12px;")
        layout.addWidget(self.control_status)
        
        self.tools_status = QLabel("🎯 Tools: Active")
        self.tools_status.setStyleSheet("color: #10b981; font-size: 12px;")
        layout.addWidget(self.tools_status)
        
        # Performance info
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: #4b5563;")
        layout.addWidget(separator)
        
        self.memory_label = QLabel("Memory: Normal")
        self.memory_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.memory_label)
        
        return group
    
    def create_progress_section(self) -> QGroupBox:
        """Create the progress tracking section."""
        group = QGroupBox("📈 Progress")
        layout = QVBoxLayout(group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # Hidden by default
        layout.addWidget(self.progress_bar)
        
        # Progress label
        self.progress_label = QLabel("No active operations")
        self.progress_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.progress_label)
        
        return group
    
    def create_messages_section(self) -> QGroupBox:
        """Create the messages log section."""
        group = QGroupBox("💬 Recent Messages")
        layout = QVBoxLayout(group)
        
        # Messages display
        self.messages_display = QTextEdit()
        self.messages_display.setMaximumHeight(120)
        self.messages_display.setReadOnly(True)
        self.messages_display.setStyleSheet("""
            QTextEdit {
                background-color: #111827;
                border: 1px solid #374151;
                border-radius: 4px;
                color: #e2e8f0;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                padding: 4px;
            }
        """)
        layout.addWidget(self.messages_display)
        
        # Message count
        self.message_count_label = QLabel("0 messages")
        self.message_count_label.setStyleSheet("color: #6b7280; font-size: 10px;")
        layout.addWidget(self.message_count_label)
        
        return group
    
    def apply_dark_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1f2937;
                color: #e2e8f0;
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #374151;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #111827;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #f3f4f6;
            }
            QProgressBar {
                border: 1px solid #374151;
                border-radius: 4px;
                background-color: #111827;
                text-align: center;
                color: #e2e8f0;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
        """)
    
    def apply_light_theme(self):
        """Apply light theme styling."""
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                color: #1f2937;
            }
            QGroupBox {
                border: 2px solid #d1d5db;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #f9fafb;
            }
        """)
    
    def update_status(self, status: str, details: str = "", status_type: str = "info"):
        """Update the current status."""
        self._current_status = status
        self.status_label.setText(status)
        if details:
            self.status_details.setText(details)
        
        # Update styling based on status type
        if status_type == "error":
            style = """
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    color: #ef4444;
                    background: #7f1d1d;
                    border: 1px solid #ef4444;
                    border-radius: 4px;
                    padding: 8px;
                }
            """
        elif status_type == "warning":
            style = """
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    color: #f59e0b;
                    background: #78350f;
                    border: 1px solid #f59e0b;
                    border-radius: 4px;
                    padding: 8px;
                }
            """
        else:  # info/success
            style = """
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    color: #10b981;
                    background: #064e3b;
                    border: 1px solid #10b981;
                    border-radius: 4px;
                    padding: 8px;
                }
            """
        
        self.status_label.setStyleSheet(style)
        self.statusChanged.emit(status_type, status)
        self.add_status_message("System", f"Status: {status}", status_type)
    
    def update_component_status(self, component: str, status: str, status_type: str = "info"):
        """Update individual component status."""
        # Map status types to colors and icons
        if status_type == "error":
            color = "#ef4444"
            icon = "❌"
        elif status_type == "warning":
            color = "#f59e0b"
            icon = "⚠️"
        else:
            color = "#10b981"
            icon = "✅"
        
        status_text = f"{icon} {component}: {status}"
        style = f"color: {color}; font-size: 12px;"
        
        # Update the appropriate component status
        if "canvas" in component.lower():
            self.canvas_status.setText(status_text)
            self.canvas_status.setStyleSheet(style)
        elif "control" in component.lower():
            self.control_status.setText(status_text)
            self.control_status.setStyleSheet(style)
        elif "tool" in component.lower():
            self.tools_status.setText(status_text)
            self.tools_status.setStyleSheet(style)
    
    def show_progress(self, message: str, progress: int = 0):
        """Show progress operation."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
        
        if progress >= 100:
            # Hide progress bar when complete
            QTimer.singleShot(2000, self.hide_progress)
    
    def hide_progress(self):
        """Hide progress bar."""
        self.progress_bar.setVisible(False)
        self.progress_label.setText("No active operations")
    
    def add_status_message(self, source: str, message: str, level: str = "info"):
        """Add a status message to the log."""
        import datetime
        
        # Create message entry
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        message_entry = {
            'timestamp': timestamp,
            'source': source,
            'message': message,
            'level': level
        }
        
        # Add to messages list
        self._messages.append(message_entry)
        
        # Keep only recent messages
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]
        
        # Update display
        self.update_messages_display()
    
    def update_messages_display(self):
        """Update the messages display."""
        # Get recent messages (last 10)
        recent_messages = self._messages[-10:] if len(self._messages) > 10 else self._messages
        
        # Format messages
        formatted_messages = []
        for msg in recent_messages:
            level_color = {
                'info': '#94a3b8',
                'warning': '#f59e0b',
                'error': '#ef4444',
                'success': '#10b981'
            }.get(msg['level'], '#94a3b8')
            
            formatted = f"<span style='color: {level_color}'>[{msg['timestamp']}] {msg['source']}: {msg['message']}</span>"
            formatted_messages.append(formatted)
        
        # Update display
        html_content = "<br>".join(formatted_messages)
        self.messages_display.setHtml(html_content)
        
        # Scroll to bottom
        self.messages_display.moveCursor(self.messages_display.textCursor().End)
        
        # Update count
        self.message_count_label.setText(f"{len(self._messages)} messages")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get status panel statistics."""
        return {
            'name': self.name,
            'version': self.version,
            'initialized': self.initialized,
            'current_status': self._current_status,
            'message_count': len(self._messages),
            'max_messages': self._max_messages
        }