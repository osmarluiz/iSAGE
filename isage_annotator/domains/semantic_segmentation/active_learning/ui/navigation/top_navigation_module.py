"""
Top Navigation Module

Creates the discrete "Go:" field for the top canvas controls bar, exactly like ABILIUS.
This provides direct image navigation by number in the top controls area.
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCompleter
from PyQt5.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt5.QtGui import QIntValidator
import logging

logger = logging.getLogger(__name__)


class TopNavigationModule(QWidget):
    """
    ABILIUS-style discrete "Go:" navigation field for top controls bar.
    
    Features:
    - Compact "Go: [field] [Go]" layout like ABILIUS
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
        
        logger.info("Top navigation module initialized")
    
    def setup_ui(self):
        """Setup compact UI exactly like ABILIUS."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # "Go:" label - discrete like ABILIUS
        go_label = QLabel("Go:")
        go_label.setFixedWidth(25)
        go_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        
        # Input field - compact
        self.go_input = QLineEdit()
        self.go_input.setFixedWidth(60)
        self.go_input.setFixedHeight(26)
        self.go_input.setPlaceholderText("113")  # Like ABILIUS screenshot
        self.go_input.returnPressed.connect(self.on_go_clicked)
        
        # Go button - small and discrete  
        self.go_button = QPushButton("Go")
        self.go_button.setFixedSize(35, 26)
        self.go_button.clicked.connect(self.on_go_clicked)
        
        # Add to layout
        layout.addWidget(go_label)
        layout.addWidget(self.go_input)
        layout.addWidget(self.go_button)
        
        # Keep widget compact
        self.setFixedHeight(26)
    
    def setup_validation(self):
        """Setup input validation for image numbers."""
        # Integer validator
        self.validator = QIntValidator(1, 1, self)  # Will update range dynamically
        self.go_input.setValidator(self.validator)
        
        # Auto-completion
        self.completer = QCompleter(self)
        self.completer_model = QStringListModel(self)
        self.completer.setModel(self.completer_model)
        self.go_input.setCompleter(self.completer)
    
    def setup_styling(self):
        """Apply ABILIUS-style discrete styling."""
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
            
            QLineEdit:invalid {
                border-color: #ef4444;
                background-color: rgba(239, 68, 68, 0.1);
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
            
            QPushButton:pressed {
                background-color: #005a9e;
            }
            
            QPushButton:disabled {
                background-color: #4b5563;
                color: #9ca3af;
            }
            
            QLabel {
                color: #ffffff;
            }
        """)
    
    def update_navigation_state(self, current_index: int, total_count: int, image_list=None):
        """Update navigation state and validation range."""
        self.current_index = current_index
        self.total_count = total_count
        
        if image_list:
            self.image_list = image_list
        
        # Update validator range (1-based for user display)
        if total_count > 0:
            self.validator.setRange(1, total_count)
            
            # Update auto-completion
            completions = [str(i) for i in range(1, total_count + 1)]
            self.completer_model.setStringList(completions)
            
            # Enable/disable based on availability
            self.go_input.setEnabled(True)
            self.go_button.setEnabled(True)
            
            # Update placeholder to show current
            self.go_input.setPlaceholderText(str(current_index + 1))
            
        else:
            # No images available
            self.go_input.setEnabled(False)
            self.go_button.setEnabled(False)
            self.go_input.setPlaceholderText("No images")
        
        logger.debug(f"Top navigation updated: {current_index + 1}/{total_count}")
    
    def on_go_clicked(self):
        """Handle Go button click or Enter press."""
        text = self.go_input.text().strip()
        
        if not text:
            # Empty input - could go to current image (no-op) or show message
            return
        
        try:
            # Convert to 1-based user input to 0-based index
            user_number = int(text)
            target_index = user_number - 1
            
            # Validate range
            if 0 <= target_index < self.total_count:
                logger.info(f"Go to image requested: {user_number} (index {target_index})")
                self.goToImageRequested.emit(target_index)
                
                # Clear input after successful navigation
                self.go_input.clear()
                
            else:
                logger.warning(f"Invalid image number: {user_number} (range: 1-{self.total_count})")
                self.show_invalid_input()
                
        except ValueError:
            logger.warning(f"Invalid input format: {text}")
            self.show_invalid_input()
    
    def show_invalid_input(self):
        """Show visual feedback for invalid input."""
        # Temporarily highlight invalid input
        original_style = self.go_input.styleSheet()
        self.go_input.setStyleSheet(original_style + """
            QLineEdit {
                border-color: #ef4444 !important;
                background-color: rgba(239, 68, 68, 0.1) !important;
            }
        """)
        
        # Reset after 2 seconds
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.go_input.setStyleSheet(original_style))
        
        # Select all text for easy correction
        self.go_input.selectAll()
        self.go_input.setFocus()
    
    def set_current_image(self, index: int):
        """Set current image index (called when navigation changes externally)."""
        self.current_index = index
        
        # Update placeholder to reflect current position
        if self.total_count > 0:
            self.go_input.setPlaceholderText(str(index + 1))
    
    def get_compact_size(self):
        """Get the compact size suitable for controls bar."""
        return self.sizeHint()
    
    def set_enabled_state(self, enabled: bool):
        """Enable/disable the entire navigation module."""
        self.go_input.setEnabled(enabled)
        self.go_button.setEnabled(enabled)