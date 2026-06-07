"""
Bottom Navigation Panel - Modular navigation controls for annotation interface

This component provides the professional bottom navigation panel that matches
the current functioning system exactly, with improved modularity and reusability.

Features:
- Previous/Next image navigation with keyboard shortcuts (Q/E)
- Coordinates display with monospace font
- Latest action display
- Circular navigation support
- Professional styling matching the functioning system
- Keyboard shortcut integration
"""

import logging
from typing import Optional, List
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QFrame, QSpacerItem, 
    QSizePolicy, QShortcut
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QKeySequence

logger = logging.getLogger(__name__)


class BottomNavigationPanel(QFrame):
    """
    Professional bottom navigation panel matching the functioning system.

    Features:
    - Clean panel design integrated into main layout
    - [◀ Previous | Next ▶] centered layout
    - Image counter and coordinates display
    - Keyboard shortcuts (Q/E)
    - Professional styling with subtle borders
    - Circular navigation support
    - Latest action display
    - Fixed-width elements to prevent UI shifting
    """

    # Signals
    previousRequested = pyqtSignal()
    nextRequested = pyqtSignal()
    navigationChanged = pyqtSignal(int, int)  # current_index, total_count

    def __init__(self, parent=None, name: str = "bottom_navigation_panel", version: str = "1.0.0"):
        super().__init__(parent)

        self.name = name
        self.version = version

        # State
        self.current_index = 0
        self.total_count = 0
        self.image_list = []

        # Display toggles for interactive sections (coordinates and RGB are toggleable)
        self.show_coordinates = True
        self.show_rgb = True
        # GT and Pred are always visible (not toggleable)
        self.show_gt = True
        self.show_pred = True

        # Dynamic class names (loaded from dataset configuration)
        self.class_names = []
        
        # UI components
        self.pixel_info_widget = None
        self.coord_section = None
        self.rgb_section = None
        self.gt_section = None
        self.pred_section = None
        self.prev_button = None
        self.next_button = None
        self.action_label = None
        
        # Setup
        self.setup_ui()
        self.setup_shortcuts()
        
        logger.info(f"BottomNavigationPanel '{name}' v{version} initialized")
    
    def setup_ui(self):
        """Setup navigation panel UI to match the functioning system exactly."""
        # Match the functioning system styling exactly
        self.setFixedHeight(40)  # Same as functioning system
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
        
        # Main layout centered across the entire width
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(0)  # Manual spacing control for perfect centering
        
        # Left expanding spacer to center everything
        left_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addItem(left_spacer)
        
        # Interactive pixel info display with clickable sections  
        self.pixel_info_widget = QWidget()
        self.pixel_info_widget.setFixedWidth(660)  # Wider for better formatting
        pixel_layout = QHBoxLayout(self.pixel_info_widget)
        pixel_layout.setContentsMargins(0, 0, 0, 0)
        pixel_layout.setSpacing(2)
        
        # Create clickable sections with wider fixed widths for stable display
        self.coord_section = self.create_info_section("X:---- Y:----", 140, self.toggle_coordinates)
        self.rgb_section = self.create_info_section("R:--- G:--- B:---", 140, self.toggle_rgb)
        self.gt_section = self.create_info_section("GT:[--] ----------", 150, self.toggle_gt)
        self.pred_section = self.create_info_section("Pred:[--] ----------", 150, self.toggle_pred)
        
        pixel_layout.addWidget(self.coord_section)
        pixel_layout.addWidget(self.create_separator())
        pixel_layout.addWidget(self.rgb_section)
        pixel_layout.addWidget(self.create_separator())
        pixel_layout.addWidget(self.gt_section)
        pixel_layout.addWidget(self.create_separator())
        pixel_layout.addWidget(self.pred_section)
        layout.addWidget(self.pixel_info_widget)
        
        # Spacing between pixel info and navigation
        layout.addSpacing(20)
        
        # Central navigation buttons - perfectly centered
        nav_container = QWidget()
        nav_container.setFixedWidth(190)  # Fixed width for exact centering
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)  # Remove spacing, use manual centering
        
        # Add centering spacer before buttons
        nav_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # Previous button 
        self.prev_button = QPushButton("‹ PREV")
        self.prev_button.setFixedSize(85, 32)
        self.prev_button.setStyleSheet(self._get_navigation_button_style())
        self.prev_button.clicked.connect(self.on_previous_clicked)
        self.prev_button.setToolTip("Previous image (Q)")
        nav_layout.addWidget(self.prev_button)
        
        # Spacing between buttons
        nav_layout.addSpacing(10)
        
        # Next button
        self.next_button = QPushButton("NEXT ›")
        self.next_button.setFixedSize(85, 32)
        self.next_button.setStyleSheet(self._get_navigation_button_style())
        self.next_button.clicked.connect(self.on_next_clicked)
        self.next_button.setToolTip("Next image (E)")
        nav_layout.addWidget(self.next_button)
        
        # Add centering spacer after buttons
        nav_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        layout.addWidget(nav_container)
        
        # Spacing between navigation and action
        layout.addSpacing(20)
        
        # Latest action display - much wider and better positioned
        self.action_label = QLabel("Ready")
        self.action_label.setFixedWidth(400)  # Much wider for full messages
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
        
        # Right expanding spacer to center everything
        right_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addItem(right_spacer)
    
    def _get_navigation_button_style(self) -> str:
        """Get consistent navigation button styling."""
        return """
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
        """
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts for navigation."""
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
        
        logger.debug("Navigation keyboard shortcuts setup: Q (prev), E (next)")
    
    def create_info_section(self, text: str, width: int, click_callback):
        """Create a clickable info section with fixed width."""
        section = QLabel(text)
        section.setFixedWidth(width)
        section.setAlignment(Qt.AlignLeft)  # Left align for consistent spacing
        section.setCursor(Qt.PointingHandCursor)
        section.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 11px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                padding: 4px 8px;
                background: #1a202c;
                border-radius: 3px;
                border: 1px solid #374151;
                text-align: left;
            }
            QLabel:hover {
                background: #374151;
                border-color: #4b5563;
            }
        """)
        section.mousePressEvent = lambda event: click_callback()
        return section
    
    def create_separator(self):
        """Create a styled separator between sections."""
        separator = QLabel("|")
        separator.setStyleSheet("""
            QLabel {
                color: #4b5563;
                font-size: 11px;
                padding: 0px 2px;
            }
        """)
        return separator
    
    def toggle_coordinates(self):
        """Toggle coordinates display."""
        self.show_coordinates = not self.show_coordinates
        self.update_section_styling(self.coord_section, self.show_coordinates)
        logger.debug(f"Coordinates display: {'enabled' if self.show_coordinates else 'disabled'}")
    
    def toggle_rgb(self):
        """Toggle RGB display."""
        self.show_rgb = not self.show_rgb
        self.update_section_styling(self.rgb_section, self.show_rgb)
        logger.debug(f"RGB display: {'enabled' if self.show_rgb else 'disabled'}")
    
    def toggle_gt(self):
        """Toggle ground truth display."""
        self.show_gt = not self.show_gt
        self.update_section_styling(self.gt_section, self.show_gt)
        logger.debug(f"Ground truth display: {'enabled' if self.show_gt else 'disabled'}")
    
    def toggle_pred(self):
        """Toggle prediction display."""
        self.show_pred = not self.show_pred
        self.update_section_styling(self.pred_section, self.show_pred)
        logger.debug(f"Prediction display: {'enabled' if self.show_pred else 'disabled'}")
    
    def update_section_styling(self, section: QLabel, enabled: bool):
        """Update styling for enabled/disabled sections."""
        if enabled:
            section.setStyleSheet("""
                QLabel {
                    color: #10b981;
                    font-size: 11px;
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    padding: 4px 6px;
                    background: #064e3b;
                    border-radius: 3px;
                    border: 1px solid #065f46;
                    font-weight: bold;
                }
                QLabel:hover {
                    background: #065f46;
                    border-color: #10b981;
                }
            """)
        else:
            section.setStyleSheet("""
                QLabel {
                    color: #6b7280;
                    font-size: 11px;
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    padding: 4px 6px;
                    background: #374151;
                    border-radius: 3px;
                    border: 1px solid #4b5563;
                }
                QLabel:hover {
                    background: #4b5563;
                    border-color: #6b7280;
                }
            """)
    
    # Public API

    def set_class_names(self, class_names: List[str]):
        """Set the class names for proper display in GT/Pred sections."""
        self.class_names = class_names
        logger.info(f"Bottom navigation panel: class names set to {class_names}")

    def update_navigation_state(self, current_index: int, total_count: int, image_list: Optional[List[str]] = None):
        """Update navigation state with circular navigation support."""
        self.current_index = current_index
        self.total_count = total_count
        
        if image_list:
            self.image_list = image_list
        
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
        else:
            self.prev_button.setToolTip("Previous image (Q) - No images loaded")
            self.next_button.setToolTip("Next image (E) - No images loaded")
        
        # Show panel only if we have images
        self.setVisible(total_count > 0)
        
        # Emit navigation changed signal
        self.navigationChanged.emit(current_index, total_count)
        
        logger.debug(f"Navigation state updated: {current_index + 1}/{total_count}")
    
    def update_pixel_info(self, x: int, y: int, rgb_values=None, gt_value=None, pred_value=None):
        """Update enhanced pixel info display with fixed-width formatting for stable display."""
        # Update coordinates section with fixed-width formatting
        if self.show_coordinates:
            coord_text = f"X:{x:4d} Y:{y:4d}"  # Fixed 4-digit width
        else:
            coord_text = "X:---- Y:----"
        self.coord_section.setText(coord_text)

        # Update RGB section with fixed-width formatting
        if self.show_rgb and rgb_values and len(rgb_values) >= 3:
            r, g, b = rgb_values[0], rgb_values[1], rgb_values[2]
            rgb_text = f"R:{r:3d} G:{g:3d} B:{b:3d}"  # Fixed 3-digit width
            logger.debug(f"Setting RGB text to: {rgb_text}")
        else:
            rgb_text = "R:--- G:--- B:---"
            logger.debug(f"RGB not available: show_rgb={self.show_rgb}, rgb_values={rgb_values}")
        self.rgb_section.setText(rgb_text)

        # Update ground truth section with index and name (ALWAYS SHOW - not dependent on overlay toggle)
        if gt_value is not None:
            # Extract class index and name from gt_value
            if isinstance(gt_value, str):
                if gt_value.startswith('Class'):
                    try:
                        class_idx = int(gt_value[5:])
                        class_name = gt_value
                    except ValueError:
                        class_idx = 0
                        class_name = gt_value
                else:
                    # Named class - find index (use dynamic class names if available)
                    search_names = self.class_names if self.class_names else ["impervious", "building", "tree", "car", "low_veg", "clutter"]
                    try:
                        class_idx = search_names.index(gt_value)
                        class_name = gt_value
                    except ValueError:
                        class_idx = 0
                        class_name = gt_value
            elif isinstance(gt_value, int):
                class_idx = gt_value
                # Use dynamic class names if available, otherwise use default order
                display_names = self.class_names if self.class_names else ["impervious", "building", "tree", "car", "low_veg", "clutter"]
                logger.debug(f"GT pixel value: {gt_value}, using class_names: {display_names}, result: idx={class_idx}")
                if 0 <= class_idx < len(display_names):
                    class_name = display_names[class_idx]
                else:
                    class_name = f"Class{class_idx}"
            else:
                class_idx = 0
                class_name = str(gt_value)
                
            gt_text = f"GT:[{class_idx:2d}] {class_name:<10}"  # Fixed formatting
        else:
            gt_text = "GT:[--] ----------"
        self.gt_section.setText(gt_text)
        
        # Update prediction section with index and name (ALWAYS SHOW - not dependent on overlay toggle)
        if pred_value is not None:
            # Same logic as GT (use dynamic class names)
            if isinstance(pred_value, str):
                if pred_value.startswith('Class'):
                    try:
                        pred_idx = int(pred_value[5:])
                        pred_name = pred_value
                    except ValueError:
                        pred_idx = 0
                        pred_name = pred_value
                else:
                    # Named class - find index (use dynamic class names if available)
                    search_names = self.class_names if self.class_names else ["impervious", "building", "tree", "car", "low_veg", "clutter"]
                    try:
                        pred_idx = search_names.index(pred_value)
                        pred_name = pred_value
                    except ValueError:
                        pred_idx = 0
                        pred_name = pred_value
            elif isinstance(pred_value, int):
                pred_idx = pred_value
                # Use dynamic class names if available, otherwise use default order
                display_names = self.class_names if self.class_names else ["impervious", "building", "tree", "car", "low_veg", "clutter"]
                if 0 <= pred_idx < len(display_names):
                    pred_name = display_names[pred_idx]
                else:
                    pred_name = f"Class{pred_idx}"
            else:
                pred_idx = 0
                pred_name = str(pred_value)
                
            pred_text = f"Pred:[{pred_idx:2d}] {pred_name:<10}"  # Fixed formatting
        else:
            pred_text = "Pred:[--] ----------"
        self.pred_section.setText(pred_text)
    
    def update_coordinates(self, x: int, y: int):
        """Backward compatibility method - update with coordinates only."""
        self.update_pixel_info(x, y)
    
    def update_latest_action(self, action: str):
        """Update latest action display with fixed width."""
        self.action_label.setText(action[:60])  # Much longer text fits in wider label
    
    def update_from_status_message(self, message: str, msg_type: str = "info"):
        """Update action display from status panel message."""
        # Color code based on message type
        color_map = {
            'info': '#94a3b8',      # Gray
            'success': '#10b981',   # Green  
            'warning': '#f59e0b',   # Yellow
            'error': '#ef4444'      # Red
        }
        
        color = color_map.get(msg_type, '#94a3b8')
        
        # Apply color styling to the action label
        self.action_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 12px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                padding: 5px 10px;
                background: #1a202c;
                border-radius: 4px;
            }}
        """)
        
        # Update text with truncation
        self.action_label.setText(message[:60])
    
    
    def set_enabled_state(self, enabled: bool):
        """Enable/disable the entire navigation panel."""
        has_images = self.total_count > 1
        self.prev_button.setEnabled(enabled and has_images)
        self.next_button.setEnabled(enabled and has_images)
    
    def get_panel_height(self) -> int:
        """Get the fixed panel height."""
        return 40  # Same as functioning system
    
    # Event handlers
    
    def on_previous_clicked(self):
        """Handle previous button click with circular navigation."""
        if self.total_count > 1:  # Allow circular navigation if we have multiple images
            logger.debug("Previous navigation requested (circular)")
            self.previousRequested.emit()
            self.update_latest_action("← Previous image")
    
    def on_next_clicked(self):
        """Handle next button click with circular navigation.""" 
        if self.total_count > 1:  # Allow circular navigation if we have multiple images
            logger.debug("Next navigation requested (circular)")
            self.nextRequested.emit()
            self.update_latest_action("Next image →")
    
    # Display methods for external updates
    
    def show_loading(self, message: str = "Loading..."):
        """Show loading state."""
        self.action_label.setText(message)
        self.set_enabled_state(False)
    
    def show_error(self, error_message: str):
        """Show error state."""
        self.action_label.setText(f"Error: {error_message[:15]}...")
        self.action_label.setStyleSheet("""
            QLabel {
                color: #ef4444;
                font-size: 12px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                padding: 5px 10px;
                background: #7f1d1d;
                border: 1px solid #dc2626;
                border-radius: 4px;
            }
        """)
    
    def clear_error(self):
        """Clear error state and restore normal styling."""
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
        self.update_latest_action("Ready")
    
    def get_current_state(self) -> dict:
        """Get current navigation state."""
        return {
            'name': self.name,
            'version': self.version,
            'current_index': self.current_index,
            'total_count': self.total_count,
            'has_images': len(self.image_list) > 0,
            'enabled': self.prev_button.isEnabled()
        }
    
    def get_statistics(self) -> dict:
        """Get navigation panel statistics."""
        return {
            'name': self.name,
            'version': self.version,
            'current_index': self.current_index,
            'total_count': self.total_count,
            'visible': self.isVisible(),
            'enabled': self.prev_button.isEnabled()
        }