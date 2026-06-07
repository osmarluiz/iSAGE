"""
Canvas Controls Bar - Professional toolbar for annotation canvas

This component provides the professional controls bar that sits above the annotation canvas,
matching the functioning system exactly with zoom controls, image navigation, and canvas tools.
"""

import logging
from typing import Optional, List, Dict, Any, Callable
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QFrame, QLineEdit,
    QComboBox, QSpacerItem, QSizePolicy, QCompleter
)
from PyQt5.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt5.QtGui import QIntValidator, QFont

logger = logging.getLogger(__name__)


class TopNavigationModule(QWidget):
    """
    Compact "Go:" navigation field for canvas controls bar.
    
    Features:
    - Compact "Go: [field] [Go]" layout
    - Input validation for valid image numbers
    - Auto-completion with image numbers  
    - Keyboard shortcut (Enter to go)
    - Visual feedback for invalid numbers
    """
    
    # Signals
    goToImageRequested = pyqtSignal(int)  # image_index (0-based)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self.current_index = 0
        self.total_count = 0
        self.image_list = []
        
        self.setup_ui()
        self.setup_validation()
        self.setup_styling()
    
    def setup_ui(self):
        """Setup compact UI."""
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
        layout.setSpacing(5)
        
        # "Go:" label
        go_label = QLabel("Go:")
        go_label.setFixedWidth(25)
        go_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        
        # Input field
        self.go_input = QLineEdit()
        self.go_input.setFixedWidth(60)
        self.go_input.setFixedHeight(26)
        self.go_input.setPlaceholderText("1")
        self.go_input.returnPressed.connect(self.on_go_clicked)
        
        # Go button
        self.go_button = QPushButton("Go")
        self.go_button.setFixedSize(35, 26)
        self.go_button.clicked.connect(self.on_go_clicked)
        
        layout.addWidget(go_label)
        layout.addWidget(self.go_input)
        layout.addWidget(self.go_button)
        
        self.setFixedHeight(26)
    
    def setup_validation(self):
        """Setup input validation for image numbers."""
        self.validator = QIntValidator(1, 1, self)
        self.go_input.setValidator(self.validator)
        
        self.completer = QCompleter(self)
        self.completer_model = QStringListModel(self)
        self.completer.setModel(self.completer_model)
        self.go_input.setCompleter(self.completer)
    
    def setup_styling(self):
        """Apply professional styling."""
        self.setStyleSheet("""
            QLineEdit {
                background-color: rgba(55, 65, 81, 0.8);
                border: 1px solid #4b5563;
                border-radius: 3px;
                color: #ffffff;
                padding: 2px 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #007ACC;
                background-color: rgba(55, 65, 81, 1.0);
            }
            QPushButton {
                background-color: #007ACC;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ba1e2;
            }
        """)
    
    def update_navigation_state(self, current_index: int, total_count: int, image_list=None):
        """Update navigation state and validation range."""
        self.current_index = current_index
        self.total_count = total_count
        
        if image_list:
            self.image_list = image_list
        
        if total_count > 0:
            self.validator.setRange(1, total_count)
            completions = [str(i) for i in range(1, total_count + 1)]
            self.completer_model.setStringList(completions)
            
            self.go_input.setEnabled(True)
            self.go_button.setEnabled(True)
            self.go_input.setPlaceholderText(str(current_index + 1))
        else:
            self.go_input.setEnabled(False)
            self.go_button.setEnabled(False)
            self.go_input.setPlaceholderText("No images")
    
    def on_go_clicked(self):
        """Handle Go button click or Enter press."""
        text = self.go_input.text().strip()
        
        if not text:
            return
        
        try:
            user_number = int(text)
            target_index = user_number - 1
            
            if 0 <= target_index < self.total_count:
                logger.info(f"Go to image requested: {user_number} (index {target_index})")
                self.goToImageRequested.emit(target_index)
                self.go_input.clear()
            else:
                self.show_invalid_input()
                
        except ValueError:
            self.show_invalid_input()
    
    def show_invalid_input(self):
        """Show visual feedback for invalid input."""
        original_style = self.go_input.styleSheet()
        self.go_input.setStyleSheet(original_style + """
            QLineEdit {
                border-color: #ef4444 !important;
                background-color: rgba(239, 68, 68, 0.1) !important;
            }
        """)
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.go_input.setStyleSheet(original_style))
        
        self.go_input.selectAll()
        self.go_input.setFocus()


class CanvasControlsBar(QFrame):
    """
    Professional canvas controls bar matching the functioning system exactly.
    
    Features:
    - Zoom controls (zoom out, zoom in, reset/fit)
    - Zoom percentage display
    - Image name/info display
    - Top navigation module (Go: field)
    - Canvas tools and options
    - Professional styling matching functioning system
    - 40px height for consistency
    """
    
    # Signals
    zoomInRequested = pyqtSignal()
    zoomOutRequested = pyqtSignal()
    zoomResetRequested = pyqtSignal()
    zoomFactorChanged = pyqtSignal(float)  # New zoom factor
    canvasToolChanged = pyqtSignal(str)  # tool_name
    goToImageRequested = pyqtSignal(int)  # image_index
    canvasOptionChanged = pyqtSignal(str, object)  # option_name, value
    
    def __init__(self, parent=None, name: str = "canvas_controls_bar", version: str = "1.0.0"):
        super().__init__(parent)
        
        self.name = name
        self.version = version
        
        # State
        self.current_zoom = 1.0
        self.current_image_name = "No image loaded"
        self.current_image_index = 0
        self.total_images = 0
        self.image_list = []
        
        # UI components
        self.zoom_out_btn = None
        self.zoom_in_btn = None
        self.reset_zoom_btn = None
        self.zoom_label = None
        self.canvas_info = None
        self.top_nav = None
        
        # Setup
        self.setup_ui()
        
        logger.info(f"CanvasControlsBar '{name}' v{version} initialized")
    
    def setup_ui(self):
        """Setup canvas controls bar UI matching functioning system exactly."""
        # Match functioning system styling and height exactly
        self.setFixedHeight(40)
        self.setStyleSheet("background: #374151; border: 1px solid #4b5563;")
        
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
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Zoom controls section
        zoom_section = self.create_zoom_controls()
        layout.addLayout(zoom_section)
        
        # Add spacer between zoom and info
        layout.addStretch()
        
        # Image info section
        self.canvas_info = QLabel(self.current_image_name)
        self.canvas_info.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.canvas_info)
        
        # Add spacing
        layout.addSpacing(20)
        
        # Top navigation module (Go field)
        self.top_nav = TopNavigationModule(self)
        self.top_nav.goToImageRequested.connect(self.on_goto_image_requested)
        layout.addWidget(self.top_nav)
    
    def create_zoom_controls(self) -> QHBoxLayout:
        """Create the zoom controls section matching functioning system."""
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(5)
        
        # Zoom out button
        self.zoom_out_btn = QPushButton("🔍−")
        self.zoom_out_btn.setFixedSize(30, 30)
        self.zoom_out_btn.setStyleSheet(self._get_zoom_button_style())
        self.zoom_out_btn.setToolTip("Zoom out (Ctrl+-)")
        self.zoom_out_btn.clicked.connect(self.on_zoom_out_clicked)
        zoom_layout.addWidget(self.zoom_out_btn)
        
        # Zoom percentage display
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(60)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        zoom_layout.addWidget(self.zoom_label)
        
        # Zoom in button
        self.zoom_in_btn = QPushButton("🔍+")
        self.zoom_in_btn.setFixedSize(30, 30)
        self.zoom_in_btn.setStyleSheet(self._get_zoom_button_style())
        self.zoom_in_btn.setToolTip("Zoom in (Ctrl++)")
        self.zoom_in_btn.clicked.connect(self.on_zoom_in_clicked)
        zoom_layout.addWidget(self.zoom_in_btn)
        
        # Reset/Fit zoom button
        self.reset_zoom_btn = QPushButton("⚏ Fit")
        self.reset_zoom_btn.setFixedSize(50, 30)
        self.reset_zoom_btn.setStyleSheet(self._get_zoom_button_style())
        self.reset_zoom_btn.setToolTip("Reset zoom to fit (Ctrl+0)")
        self.reset_zoom_btn.clicked.connect(self.on_zoom_reset_clicked)
        zoom_layout.addWidget(self.reset_zoom_btn)
        
        return zoom_layout
    
    def _get_zoom_button_style(self) -> str:
        """Get consistent zoom button styling."""
        return """
            QPushButton {
                background: #6b7280;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { 
                background: #9ca3af; 
            }
            QPushButton:pressed {
                background: #4b5563;
            }
            QPushButton:disabled {
                background: #4b5563;
                color: #6b7280;
            }
        """
    
    # Public API
    
    def update_zoom_display(self, zoom_factor: float):
        """Update the zoom display percentage."""
        self.current_zoom = zoom_factor
        percentage = int(zoom_factor * 100)
        self.zoom_label.setText(f"{percentage}%")
        
        # Update button states based on zoom limits
        self.zoom_out_btn.setEnabled(zoom_factor > 0.1)  # min zoom
        self.zoom_in_btn.setEnabled(zoom_factor < 5.0)   # max zoom
        
        logger.debug(f"Zoom display updated: {percentage}%")
    
    def update_image_info(self, image_name: str, image_index: int = 0, total_images: int = 0):
        """Update the image information display."""
        self.current_image_name = image_name
        self.current_image_index = image_index
        self.total_images = total_images
        
        # Display format: "Image: filename.png" or just filename
        if image_name and image_name != "No image loaded":
            display_name = f"Image: {image_name}"
        else:
            display_name = image_name
            
        self.canvas_info.setText(display_name)
        
        # Update top navigation
        self.top_nav.update_navigation_state(image_index, total_images, self.image_list)
        
        logger.debug(f"Image info updated: {image_name} ({image_index + 1}/{total_images})")
    
    def update_navigation_state(self, current_index: int, total_count: int, image_list: Optional[List[str]] = None):
        """Update navigation state for the Go field."""
        self.current_image_index = current_index
        self.total_images = total_count
        
        if image_list:
            self.image_list = image_list
        
        # Update top navigation module
        self.top_nav.update_navigation_state(current_index, total_count, image_list)
        
        logger.debug(f"Navigation state updated: {current_index + 1}/{total_count}")
    
    def set_enabled_state(self, enabled: bool):
        """Enable/disable the entire controls bar."""
        self.zoom_out_btn.setEnabled(enabled and self.current_zoom > 0.1)
        self.zoom_in_btn.setEnabled(enabled and self.current_zoom < 5.0)
        self.reset_zoom_btn.setEnabled(enabled)
        self.top_nav.setEnabled(enabled)
    
    def get_bar_height(self) -> int:
        """Get the fixed bar height."""
        return 40  # Same as functioning system
    
    def get_current_zoom(self) -> float:
        """Get the current zoom factor."""
        return self.current_zoom
    
    def set_zoom_limits(self, min_zoom: float = 0.1, max_zoom: float = 5.0):
        """Set zoom limits and update button states."""
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom
        
        # Update button states
        self.zoom_out_btn.setEnabled(self.current_zoom > min_zoom)
        self.zoom_in_btn.setEnabled(self.current_zoom < max_zoom)
        
        # Update tooltips
        self.zoom_out_btn.setToolTip(f"Zoom out (Min: {int(min_zoom * 100)}%)")
        self.zoom_in_btn.setToolTip(f"Zoom in (Max: {int(max_zoom * 100)}%)")
    
    # Event handlers
    
    def on_zoom_out_clicked(self):
        """Handle zoom out button click."""
        logger.debug("Zoom out requested")
        self.zoomOutRequested.emit()
    
    def on_zoom_in_clicked(self):
        """Handle zoom in button click."""
        logger.debug("Zoom in requested")
        self.zoomInRequested.emit()
    
    def on_zoom_reset_clicked(self):
        """Handle zoom reset/fit button click."""
        logger.debug("Zoom reset (fit) requested")
        self.zoomResetRequested.emit()
    
    def on_goto_image_requested(self, image_index: int):
        """Handle go-to image request from top navigation."""
        logger.info(f"Go-to image requested: index {image_index}")
        self.goToImageRequested.emit(image_index)
    
    # Display and utility methods
    
    def show_loading(self, message: str = "Loading..."):
        """Show loading state in the controls bar."""
        self.canvas_info.setText(message)
        self.set_enabled_state(False)
    
    def show_error(self, error_message: str):
        """Show error state in the controls bar."""
        self.canvas_info.setText(f"Error: {error_message}")
        self.canvas_info.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 14px;")
    
    def clear_error(self):
        """Clear error state and restore normal styling."""
        self.canvas_info.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 14px;")
        self.canvas_info.setText(self.current_image_name)
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current controls bar state."""
        return {
            'name': self.name,
            'version': self.version,
            'current_zoom': self.current_zoom,
            'current_image_name': self.current_image_name,
            'current_image_index': self.current_image_index,
            'total_images': self.total_images,
            'enabled': self.zoom_in_btn.isEnabled() or self.zoom_out_btn.isEnabled()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get controls bar statistics."""
        return {
            'name': self.name,
            'version': self.version,
            'zoom_factor': self.current_zoom,
            'zoom_percentage': int(self.current_zoom * 100),
            'image_count': self.total_images,
            'current_index': self.current_image_index,
            'has_navigation': len(self.image_list) > 0,
            'zoom_enabled': self.zoom_in_btn.isEnabled() or self.zoom_out_btn.isEnabled()
        }