"""
Bottom Navigation Panel

Creates a dedicated bottom panel for navigation controls, even better than ABILIUS.
This replaces the problematic floating overlay with a clean, professional panel.
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QFrame, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class BottomNavigationPanel(QFrame):
    """
    Professional bottom navigation panel - better than ABILIUS floating overlay.
    
    Features:
    - Clean panel design integrated into main layout
    - [◀ Previous | Next ▶] centered layout  
    - Image counter display
    - Keyboard shortcuts (Q/E)
    - Professional styling with subtle borders
    - Progress indicator integration
    - Better than floating overlay - no positioning issues!
    """
    
    # Signals - ultra minimal
    previousRequested = pyqtSignal()
    nextRequested = pyqtSignal()
    navigationChanged = pyqtSignal(int, int)  # current_index, total_count
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration
        self.current_index = 0
        self.total_count = 0
        
        self.setup_ui()
        self.setup_shortcuts()
        
        logger.info("Bottom navigation panel initialized")
    
    def setup_ui(self):
        """Setup navigation panel UI to match top controls bar exactly."""
        # Match top controls bar styling exactly
        self.setFixedHeight(40)  # Same as top controls bar
        self.setStyleSheet("background: #374151; border: 1px solid #4b5563;")  # Same as top controls
        
        # Main layout - same as top controls
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)  # Same as top controls
        layout.setSpacing(10)
        
        # Left spacer
        left_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addItem(left_spacer)
        
        # Coordinates display (left of PREV) - fixed width
        self.coordinates_label = QLabel("(x: ---, y: ---)")
        self.coordinates_label.setFixedWidth(140)  # Fixed width to prevent shifting
        self.coordinates_label.setAlignment(Qt.AlignCenter)
        self.coordinates_label.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 12px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                padding: 5px 10px;
                background: #1a202c;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.coordinates_label)
        
        # Spacer between coordinates and PREV
        layout.addSpacing(15)
        
        # Previous button - sophisticated monospace design
        self.prev_button = QPushButton("‹ PREV")
        self.prev_button.setFixedSize(85, 32)  # Refined proportions
        self.prev_button.setStyleSheet("""
            QPushButton {
                background: #2d3748;
                color: #e2e8f0;
                border: 1px solid #4a5568;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                font-weight: 500;
                letter-spacing: 0.5px;
                padding: 6px 12px;
            }
            QPushButton:hover { 
                background: #4a5568;
                border-color: #718096;
                color: #ffffff;
            }
            QPushButton:pressed { 
                background: #1a202c;
                border-color: #2d3748;
            }
            QPushButton:disabled { 
                background: #1a202c; 
                color: #4a5568;
                border-color: #2d3748;
            }
        """)
        self.prev_button.clicked.connect(self.on_previous_clicked)
        self.prev_button.setToolTip("Previous image (Q)")
        layout.addWidget(self.prev_button)
        
        # Spacer between buttons for sophisticated spacing
        layout.addSpacing(20)
        
        # Next button - sophisticated monospace design
        self.next_button = QPushButton("NEXT ›")
        self.next_button.setFixedSize(85, 32)  # Refined proportions
        self.next_button.setStyleSheet("""
            QPushButton {
                background: #2d3748;
                color: #e2e8f0;
                border: 1px solid #4a5568;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                font-weight: 500;
                letter-spacing: 0.5px;
                padding: 6px 12px;
            }
            QPushButton:hover { 
                background: #4a5568;
                border-color: #718096;
                color: #ffffff;
            }
            QPushButton:pressed { 
                background: #1a202c;
                border-color: #2d3748;
            }
            QPushButton:disabled { 
                background: #1a202c; 
                color: #4a5568;
                border-color: #2d3748;
            }
        """)
        self.next_button.clicked.connect(self.on_next_clicked)
        self.next_button.setToolTip("Next image (E)")
        layout.addWidget(self.next_button)
        
        # Spacer between NEXT and action
        layout.addSpacing(15)
        
        # Latest action display (right of NEXT) - fixed width
        self.action_label = QLabel("Ready")
        self.action_label.setFixedWidth(180)  # Fixed width to prevent shifting
        self.action_label.setAlignment(Qt.AlignCenter)
        self.action_label.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 12px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                padding: 5px 10px;
                background: #1a202c;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.action_label)
        
        # Right spacer
        right_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addItem(right_spacer)
    
    # Styling now done inline to match top controls bar exactly
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts for navigation."""
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        
        # Get main window for shortcuts
        main_window = self
        while main_window.parent():
            main_window = main_window.parent()
        
        # Q for previous
        prev_shortcut = QShortcut(QKeySequence("Q"), main_window)
        prev_shortcut.activated.connect(self.on_previous_clicked)
        
        # E for next  
        next_shortcut = QShortcut(QKeySequence("E"), main_window)
        next_shortcut.activated.connect(self.on_next_clicked)
        
        # Ultra minimal - only Q/E shortcuts for prev/next
    
    def update_navigation_state(self, current_index: int, total_count: int):
        """Update navigation state with circular navigation support."""
        self.current_index = current_index
        self.total_count = total_count
        
        # Enable buttons if we have more than 1 image (circular navigation)
        has_images = total_count > 1
        self.prev_button.setEnabled(has_images)
        self.next_button.setEnabled(has_images)
        
        # Update tooltips to indicate circular navigation
        if has_images:
            if current_index == 0:
                self.prev_button.setToolTip(f"Previous image (Q) → Image {total_count}")
            else:
                self.prev_button.setToolTip(f"Previous image (Q) → Image {current_index}")
                
            if current_index == total_count - 1:
                self.next_button.setToolTip(f"Next image (E) → Image 1")
            else:
                self.next_button.setToolTip(f"Next image (E) → Image {current_index + 2}")
        
        # Show panel only if we have images
        self.setVisible(total_count > 0)
        
        logger.debug(f"Circular navigation updated: {current_index + 1}/{total_count}")
    
    def on_previous_clicked(self):
        """Handle previous button click with circular navigation."""
        if self.total_count > 1:  # Allow circular navigation if we have multiple images
            logger.debug("Previous navigation requested (circular)")
            self.previousRequested.emit()
    
    def on_next_clicked(self):
        """Handle next button click with circular navigation.""" 
        if self.total_count > 1:  # Allow circular navigation if we have multiple images
            logger.debug("Next navigation requested (circular)")
            self.nextRequested.emit()
    
    # Ultra minimal - removed random functionality
    
    def set_enabled_state(self, enabled: bool):
        """Enable/disable the entire navigation panel."""
        self.prev_button.setEnabled(enabled and self.current_index > 0)
        self.next_button.setEnabled(enabled and self.current_index < self.total_count - 1)
    
    def get_panel_height(self):
        """Get the fixed panel height."""
        return 40  # Same as top controls bar
    
    def update_coordinates(self, x: int, y: int):
        """Update coordinates display with fixed width."""
        self.coordinates_label.setText(f"(x: {x}, y: {y})")
    
    def update_latest_action(self, action: str):
        """Update latest action display with fixed width."""
        self.action_label.setText(action)