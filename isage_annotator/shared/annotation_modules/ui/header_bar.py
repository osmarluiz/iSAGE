"""
Enhanced Header Bar - Advanced header with session info and navigation

This component provides comprehensive header functionality including:
- Session information display
- Current image counter and navigation
- Mode/status indicators  
- Navigation controls (back, help)
- Progress visualization
- Theme support
"""

import logging
from typing import Dict, Optional, List, Any
from pathlib import Path
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QProgressBar, QWidget, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QPixmap, QIcon

logger = logging.getLogger(__name__)


class SessionInfoWidget(QWidget):
    """Widget for displaying session information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup session info display."""
        # Check if layout already exists
        existing_layout = self.layout()
        if existing_layout is not None:
            # Clear existing layout
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Session name
        self.session_label = QLabel("Session: No Session")
        self.session_label.setStyleSheet("""
            QLabel {
                font-family: "Segoe UI", "Helvetica Neue", sans-serif;
                font-size: 14px; 
                font-weight: 400;
                color: #ffffff !important;
                background-color: transparent !important;
                margin-left: 20px;
            }
        """)
        layout.addWidget(self.session_label)
        
        # Iteration/Mode info
        self.mode_label = QLabel("Iteration: 1")
        self.mode_label.setStyleSheet("""
            QLabel {
                font-family: "Segoe UI", "Helvetica Neue", sans-serif;
                font-size: 14px; 
                font-weight: 400;
                color: #ffffff !important;
                background-color: transparent !important;
                margin-left: 20px;
            }
        """)
        layout.addWidget(self.mode_label)
    
    def update_session_info(self, session_name: str, session_data: Optional[Dict] = None):
        """Update session information."""
        display_name = Path(session_name).stem if session_name else "No Session"
        self.session_label.setText(f"Session: {display_name}")
        self.session_label.setToolTip(f"Full path: {session_name}" if session_name else "No session loaded")
        
        if session_data:
            iteration = session_data.get('current_iteration', 1)
            status = session_data.get('status', 'Active')
            self.mode_label.setText(f"Iteration: {iteration} ({status})")
        else:
            self.mode_label.setText("Iteration: 1")


class ImageNavigationWidget(QWidget):
    """Widget for image navigation and counter."""
    
    # Signals
    previousRequested = pyqtSignal()
    nextRequested = pyqtSignal()
    randomRequested = pyqtSignal()
    gotoRequested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self._current_index = 0
        self._total_images = 0
        self._image_list = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup navigation controls."""
        # Check if layout already exists
        existing_layout = self.layout()
        if existing_layout is not None:
            # Clear existing layout
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Previous button
        self.prev_btn = QPushButton("‹")
        self.prev_btn.setFixedSize(32, 28)
        self.prev_btn.setToolTip("Previous image (Q)")
        self.prev_btn.clicked.connect(self.previousRequested.emit)
        layout.addWidget(self.prev_btn)
        
        # Image counter
        self.counter_label = QLabel("0 of 0")
        self.counter_label.setMinimumWidth(80)
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #ffffff;
                background: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
            }
        """)
        self.counter_label.mousePressEvent = self.on_counter_clicked
        self.counter_label.setCursor(Qt.PointingHandCursor)
        self.counter_label.setToolTip("Click to go to specific image")
        layout.addWidget(self.counter_label)
        
        # Next button  
        self.next_btn = QPushButton("›")
        self.next_btn.setFixedSize(32, 28)
        self.next_btn.setToolTip("Next image (E)")
        self.next_btn.clicked.connect(self.nextRequested.emit)
        layout.addWidget(self.next_btn)
        
        # Random button
        self.random_btn = QPushButton("🎲")
        self.random_btn.setFixedSize(32, 28)
        self.random_btn.setToolTip("Random image (R)")
        self.random_btn.clicked.connect(self.randomRequested.emit)
        layout.addWidget(self.random_btn)
        
        # Apply button styling
        button_style = """
            QPushButton {
                background-color: #4b5563;
                border: 1px solid #6b7280;
                border-radius: 4px;
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #6b7280;
                border-color: #9ca3af;
            }
            QPushButton:pressed {
                background-color: #374151;
            }
            QPushButton:disabled {
                background-color: #1f2937;
                color: #6b7280;
                border-color: #374151;
            }
        """
        
        for btn in [self.prev_btn, self.next_btn, self.random_btn]:
            btn.setStyleSheet(button_style)
    
    def update_navigation_state(self, current_index: int, total_images: int, image_list: Optional[List[str]] = None):
        """Update navigation state and display."""
        self._current_index = current_index
        self._total_images = total_images
        
        if image_list:
            self._image_list = image_list
        
        # Update counter display
        if total_images > 0:
            self.counter_label.setText(f"{current_index + 1} of {total_images}")
            
            # Add current image name to tooltip
            if image_list and current_index < len(image_list):
                current_image_name = Path(image_list[current_index]).stem
                self.counter_label.setToolTip(f"Current: {current_image_name}\nClick to go to specific image")
        else:
            self.counter_label.setText("0 of 0")
            self.counter_label.setToolTip("No images loaded")
        
        # Update button states
        self.prev_btn.setEnabled(total_images > 1)
        self.next_btn.setEnabled(total_images > 1)
        self.random_btn.setEnabled(total_images > 1)
    
    def on_counter_clicked(self, event):
        """Handle click on counter to go to specific image."""
        if self._total_images > 1:
            self.gotoRequested.emit()


class ProgressIndicatorWidget(QWidget):
    """Widget for showing annotation progress."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup progress indicator."""
        # Check if layout already exists
        existing_layout = self.layout()
        if existing_layout is not None:
            # Clear existing layout
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(120, 18)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #4b5563;
                border-radius: 3px;
                background: #1f2937;
            }
            QProgressBar::chunk {
                background: #10b981;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Progress label
        self.progress_label = QLabel("0%")
        self.progress_label.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 11px;
                font-weight: bold;
                margin-left: 4px;
            }
        """)
        layout.addWidget(self.progress_label)
    
    def update_progress(self, current: int, total: int):
        """Update progress display."""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_label.setText(f"{percentage}%")
            self.progress_bar.setToolTip(f"Progress: {current} of {total} images")
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText("0%")
            self.progress_bar.setToolTip("No images loaded")


class HeaderBar(QFrame):
    """
    Enhanced header bar with comprehensive session and navigation information.
    
    Features:
    - Session information display with tooltips
    - Image navigation with counter and controls
    - Progress visualization
    - Mode/status indicators
    - Back button and help access
    - Responsive layout that adapts to content
    - Theme support
    """
    
    # Signals
    backRequested = pyqtSignal()
    helpRequested = pyqtSignal()
    previousImageRequested = pyqtSignal()
    nextImageRequested = pyqtSignal()
    randomImageRequested = pyqtSignal()
    gotoImageRequested = pyqtSignal()
    
    def __init__(self, parent=None, name: str = "enhanced_header_bar", version: str = "1.0.0"):
        super().__init__(parent)
        
        self.name = name
        self.version = version
        
        # Components
        self.session_widget = None
        self.navigation_widget = None
        self.progress_widget = None
        
        # State
        self._session_info = {"name": "", "data": None}
        self._navigation_state = {"index": 0, "total": 0, "list": []}
        
        # Setup
        self.setup_ui()
        self.apply_dark_theme()
        
        logger.info(f"HeaderBar '{name}' v{version} created")
    
    def setup_ui(self):
        """Setup the header bar UI."""
        self.setFixedHeight(55)
        self.setFrameStyle(QFrame.StyledPanel)
        
        # Check if layout already exists
        existing_layout = self.layout()
        if existing_layout is not None:
            # Clear existing layout
            while existing_layout.count():
                child = existing_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            existing_layout.deleteLater()
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(16)
        
        # Only keep the left section: Title and session info (minimalistic design)
        left_section = self.create_left_section()
        layout.addWidget(left_section)
        
        # Add spacer to push content to the left
        layout.addStretch()
    
    def create_left_section(self) -> QWidget:
        """Create left section with title and session info."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Title
        title_label = QLabel("Sparse Annotation Tool")
        title_label.setStyleSheet("""
            QLabel {
                font-family: "Segoe UI", "Helvetica Neue", sans-serif;
                font-size: 20px; 
                font-weight: 300;
                letter-spacing: 0.5px;
                color: #ffffff !important;
                background-color: transparent !important;
            }
        """)
        layout.addWidget(title_label)
        
        # Session info widget
        self.session_widget = SessionInfoWidget()
        layout.addWidget(self.session_widget)
        
        return widget
    
    def create_center_section(self) -> QWidget:
        """Create center section with navigation and progress."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Navigation widget
        self.navigation_widget = ImageNavigationWidget()
        self.navigation_widget.previousRequested.connect(self.previousImageRequested.emit)
        self.navigation_widget.nextRequested.connect(self.nextImageRequested.emit)
        self.navigation_widget.randomRequested.connect(self.randomImageRequested.emit)
        self.navigation_widget.gotoRequested.connect(self.gotoImageRequested.emit)
        layout.addWidget(self.navigation_widget)
        
        # Progress widget
        self.progress_widget = ProgressIndicatorWidget()
        layout.addWidget(self.progress_widget)
        
        return widget
    
    def create_right_section(self) -> QWidget:
        """Create right section with control buttons."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Help button
        self.help_btn = QPushButton("❓")
        self.help_btn.setFixedSize(32, 32)
        self.help_btn.setToolTip("Show help (F1)")
        self.help_btn.clicked.connect(self.helpRequested.emit)
        layout.addWidget(self.help_btn)
        
        # Back button
        self.back_btn = QPushButton("← Back")
        self.back_btn.setFixedHeight(32)
        self.back_btn.setToolTip("Return to Mode Grid (Esc)")
        self.back_btn.clicked.connect(self.backRequested.emit)
        layout.addWidget(self.back_btn)
        
        # Apply button styling
        button_style = """
            QPushButton {
                background-color: #dc2626;
                border: 1px solid #b91c1c;
                border-radius: 6px;
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                border-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """
        
        help_button_style = """
            QPushButton {
                background-color: #3b82f6;
                border: 1px solid #2563eb;
                border-radius: 6px;
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #60a5fa;
                border-color: #3b82f6;
            }
            QPushButton:pressed {
                background-color: #2563eb;
            }
        """
        
        self.help_btn.setStyleSheet(help_button_style)
        self.back_btn.setStyleSheet(button_style)
        
        return widget
    
    def apply_dark_theme(self):
        """Apply dark theme styling to the header bar."""
        self.setStyleSheet("""
            HeaderBar {
                background-color: #374151 !important;
                border-bottom: 1px solid #4b5563;
            }
            HeaderBar QWidget {
                background-color: #374151 !important;
            }
            HeaderBar QLabel {
                background-color: transparent !important;
                background: none !important;
                border: none !important;
                padding: 0px !important;
                margin: 0px !important;
            }
        """)
    
    def apply_light_theme(self):
        """Apply light theme styling to the header bar."""
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f3f4f6, stop: 1 #e5e7eb);
                border-bottom: 2px solid #d1d5db;
                border-top: 1px solid #9ca3af;
            }
        """)
    
    # Public API
    
    def update_session_info(self, session_name: str, session_data: Optional[Dict] = None):
        """Update session information display."""
        self._session_info = {"name": session_name, "data": session_data}
        if self.session_widget:
            self.session_widget.update_session_info(session_name, session_data)
        logger.debug(f"Session info updated: {session_name}")
    
    def update_navigation_state(self, current_index: int, total_images: int, image_list: Optional[List[str]] = None):
        """Update navigation state and controls."""
        self._navigation_state = {
            "index": current_index, 
            "total": total_images, 
            "list": image_list or []
        }
        
        if self.navigation_widget:
            self.navigation_widget.update_navigation_state(current_index, total_images, image_list)
        
        if self.progress_widget:
            self.progress_widget.update_progress(current_index, total_images)
        
        logger.debug(f"Navigation updated: {current_index + 1} of {total_images}")
    
    def set_mode_info(self, mode: str, status: str = "Active"):
        """Set mode/status information."""
        if self.session_widget:
            # Update the mode label directly
            self.session_widget.mode_label.setText(f"Mode: {mode} ({status})")
        logger.debug(f"Mode set to: {mode} ({status})")
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current header state."""
        return {
            'name': self.name,
            'version': self.version,
            'session_info': self._session_info,
            'navigation_state': self._navigation_state
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get header bar statistics."""
        return {
            'name': self.name,
            'version': self.version,
            'has_session': bool(self._session_info.get('name')),
            'total_images': self._navigation_state.get('total', 0),
            'current_index': self._navigation_state.get('index', 0)
        }