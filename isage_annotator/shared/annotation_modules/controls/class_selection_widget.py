"""
Class Selection Widget - Advanced class management component

This widget provides sophisticated class selection functionality including:
- Visual color-coded class buttons
- Custom class configuration
- Class statistics
- Quick selection shortcuts
- Customizable class properties
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QSpinBox, QGroupBox, QGridLayout, QColorDialog, QLineEdit,
    QCheckBox, QSlider, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont, QPalette

logger = logging.getLogger(__name__)


class ClassButton(QPushButton):
    """Custom button for class selection with color coding."""
    
    def __init__(self, class_id: int, class_name: str, color: str, parent=None):
        super().__init__(parent)
        
        self.class_id = class_id
        self.class_name = class_name
        self.class_color = color
        self.count = 0
        self.active = False
        
        # Setup button
        self.setText(f"{class_id}")
        self.setFixedSize(60, 45)
        self.setCheckable(True)
        self.setToolTip(f"Class {class_id}: {class_name}\nColor: {color}\nCount: {self.count}")
        
        # Update styling
        self.update_style()
        
        # Connect signals
        self.clicked.connect(self.on_clicked)
    
    def update_style(self):
        """Update button styling based on state."""
        if self.active:
            # Active state
            style = f"""
                QPushButton {{
                    background-color: {self.class_color};
                    color: white;
                    border: 3px solid #ffffff;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    border: 3px solid #60a5fa;
                    background-color: {self._lighten_color(self.class_color)};
                }}
            """
        else:
            # Inactive state
            style = f"""
                QPushButton {{
                    background-color: {self._darken_color(self.class_color)};
                    color: #e2e8f0;
                    border: 2px solid {self.class_color};
                    border-radius: 6px;
                    font-weight: normal;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {self.class_color};
                    color: white;
                    border: 2px solid #ffffff;
                }}
                QPushButton:pressed {{
                    background-color: {self._darken_color(self.class_color)};
                }}
            """
        
        self.setStyleSheet(style)
    
    def set_active(self, active: bool):
        """Set active state."""
        self.active = active
        self.setChecked(active)
        self.update_style()
    
    def set_count(self, count: int):
        """Update annotation count for this class."""
        self.count = count
        self.setToolTip(f"Class {self.class_id}: {self.class_name}\nColor: {self.class_color}\nCount: {self.count}")
    
    def set_color(self, color: str):
        """Update class color."""
        self.class_color = color
        self.update_style()
    
    def on_clicked(self):
        """Handle button click."""
        pass  # Handled by parent widget
    
    def _lighten_color(self, color: str, factor: float = 1.3) -> str:
        """Lighten a color for hover effects."""
        try:
            qcolor = QColor(color)
            r, g, b, a = qcolor.getRgb()
            r = min(255, int(r * factor))
            g = min(255, int(g * factor))
            b = min(255, int(b * factor))
            return f"rgb({r}, {g}, {b})"
        except:
            return color
    
    def _darken_color(self, color: str, factor: float = 0.6) -> str:
        """Darken a color for inactive state."""
        try:
            qcolor = QColor(color)
            r, g, b, a = qcolor.getRgb()
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            return f"rgb({r}, {g}, {b})"
        except:
            return color


class ClassSelectionWidget(QWidget):
    """
    Advanced class selection widget with color coding and statistics.
    
    Features:
    - Visual color-coded class buttons
    - Quick number key shortcuts (1-9)
    - Real-time annotation counts per class
    - Customizable class colors and names
    - Expandable/collapsible layout
    - Class configuration dialog
    """
    
    # Signals
    classChanged = pyqtSignal(int)  # class_id
    classColorChanged = pyqtSignal(int, str)  # class_id, color
    classNameChanged = pyqtSignal(int, str)  # class_id, name
    classConfigRequested = pyqtSignal()
    
    def __init__(self, parent=None, name: str = "class_selection_widget", version: str = "1.0.0"):
        super().__init__(parent)
        
        self.name = name
        self.version = version
        
        # State
        self._current_class: int = 1
        self._classes: Dict[int, Dict[str, Any]] = {}
        self._class_buttons: Dict[int, ClassButton] = {}
        self._max_visible_classes: int = 9
        self._expanded: bool = False
        
        # Default class configuration
        self._default_colors = [
            '#ef4444', '#10b981', '#3b82f6', '#f59e0b', '#8b5cf6',
            '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
        ]
        
        # Setup default classes
        self._setup_default_classes()
        
        # Create UI
        self.setup_ui()
        
        logger.info(f"ClassSelectionWidget '{name}' v{version} created")
    
    def _setup_default_classes(self):
        """Setup default class configuration."""
        for i in range(1, 11):  # Classes 1-10
            self._classes[i] = {
                'name': f'Class {i}',
                'color': self._default_colors[(i - 1) % len(self._default_colors)],
                'visible': i <= self._max_visible_classes,
                'count': 0,
                'enabled': True
            }
    
    def setup_ui(self):
        """Create the class selection UI."""
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Current class display
        current_display = self.create_current_class_display()
        layout.addWidget(current_display)
        
        # Class buttons grid
        self.buttons_container = self.create_buttons_container()
        layout.addWidget(self.buttons_container)
        
        # Quick selection spinner
        spinner_container = self.create_spinner_container()
        layout.addWidget(spinner_container)
        
        # Expansion toggle
        expand_toggle = self.create_expand_toggle()
        layout.addWidget(expand_toggle)
        
        # Configuration button
        config_button = self.create_config_button()
        layout.addWidget(config_button)
        
        # Apply theme
        self.apply_dark_theme()
    
    def create_header(self) -> QWidget:
        """Create header section."""
        header = QLabel("🎨 Class Selection")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #f3f4f6;
                padding: 8px;
                border-bottom: 2px solid #374151;
                background: #1f2937;
                border-radius: 4px;
            }
        """)
        return header
    
    def create_current_class_display(self) -> QWidget:
        """Create current class display."""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Current class label
        layout.addWidget(QLabel("Current:"))
        
        # Class info
        self.current_class_info = QLabel()
        self.current_class_info.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #ffffff;
                background: transparent;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.current_class_info)
        
        layout.addStretch()
        
        # Class count
        self.current_class_count = QLabel("0")
        self.current_class_count.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 11px;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.current_class_count)
        
        return container
    
    def create_buttons_container(self) -> QWidget:
        """Create the class buttons grid."""
        # Scrollable container for buttons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setMaximumHeight(280)  # Increased to 280 to comfortably show all 6 classes (2 rows x 3 cols)
        
        # Content widget
        content = QWidget()
        self.buttons_layout = QGridLayout(content)
        self.buttons_layout.setSpacing(6)
        
        # Create class buttons
        self.create_class_buttons()
        
        scroll_area.setWidget(content)
        
        return scroll_area
    
    def create_class_buttons(self):
        """Create all class buttons."""
        # Clear existing buttons
        for button in self._class_buttons.values():
            button.deleteLater()
        self._class_buttons.clear()
        
        # Create new buttons
        row, col = 0, 0
        cols_per_row = 3
        
        for class_id, class_info in self._classes.items():
            if not class_info.get('visible', False):
                continue
            
            button = ClassButton(
                class_id=class_id,
                class_name=class_info['name'],
                color=class_info['color']
            )
            button.clicked.connect(lambda checked, cid=class_id: self.set_current_class(cid))
            
            self._class_buttons[class_id] = button
            self.buttons_layout.addWidget(button, row, col)
            
            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1
        
        # Set initial active button
        self.update_active_button()
    
    def create_spinner_container(self) -> QWidget:
        """Create quick selection spinner."""
        container = QFrame()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(QLabel("Quick Select:"))
        
        self.class_spinner = QSpinBox()
        self.class_spinner.setRange(1, 10)
        self.class_spinner.setValue(self._current_class)
        self.class_spinner.valueChanged.connect(self.set_current_class)
        self.class_spinner.setStyleSheet("""
            QSpinBox {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 4px 8px;
                color: #e2e8f0;
            }
        """)
        layout.addWidget(self.class_spinner)
        
        layout.addStretch()
        
        return container
    
    def create_expand_toggle(self) -> QWidget:
        """Create expand/collapse toggle."""
        self.expand_button = QPushButton("Show All Classes")
        self.expand_button.setCheckable(True)
        self.expand_button.clicked.connect(self.toggle_expansion)
        self.expand_button.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 6px 12px;
                color: #e2e8f0;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
            QPushButton:checked {
                background-color: #3b82f6;
                border-color: #2563eb;
            }
        """)
        return self.expand_button
    
    def create_config_button(self) -> QWidget:
        """Create configuration button."""
        config_btn = QPushButton("⚙️ Configure Classes")
        config_btn.clicked.connect(self.open_class_config)
        config_btn.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        return config_btn
    
    def apply_dark_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1f2937;
                color: #e2e8f0;
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #e2e8f0;
                border: none;
                background: transparent;
            }
            QScrollArea {
                background-color: #111827;
                border: 1px solid #374151;
                border-radius: 6px;
            }
            QScrollArea QWidget {
                background-color: #111827;
            }
        """)
    
    # Public API
    
    def set_current_class(self, class_id: int):
        """Set the current active class."""
        if class_id not in self._classes:
            logger.warning(f"Class {class_id} not found")
            return
        
        self._current_class = class_id
        
        # Update UI
        self.update_active_button()
        self.update_current_class_display()
        self.class_spinner.setValue(class_id)
        
        # Emit signal
        self.classChanged.emit(class_id)
        
        logger.info(f"Current class set to: {class_id}")
    
    def get_current_class(self) -> int:
        """Get current active class."""
        return self._current_class
    
    def update_class_count(self, class_id: int, count: int):
        """Update annotation count for a class."""
        if class_id in self._classes:
            self._classes[class_id]['count'] = count
            
            # Update button tooltip
            if class_id in self._class_buttons:
                self._class_buttons[class_id].set_count(count)
            
            # Update current class display if it's the active class
            if class_id == self._current_class:
                self.current_class_count.setText(str(count))
    
    def update_all_counts(self, counts: Dict[int, int]):
        """Update all class counts at once."""
        for class_id, count in counts.items():
            self.update_class_count(class_id, count)
    
    def set_class_color(self, class_id: int, color: str):
        """Set color for a specific class."""
        if class_id in self._classes:
            self._classes[class_id]['color'] = color
            
            # Update button color
            if class_id in self._class_buttons:
                self._class_buttons[class_id].set_color(color)
            
            # Update current display if active
            if class_id == self._current_class:
                self.update_current_class_display()
            
            # Emit signal
            self.classColorChanged.emit(class_id, color)
    
    def set_class_name(self, class_id: int, name: str):
        """Set name for a specific class."""
        if class_id in self._classes:
            self._classes[class_id]['name'] = name
            
            # Update current display if active
            if class_id == self._current_class:
                self.update_current_class_display()
            
            # Emit signal
            self.classNameChanged.emit(class_id, name)
    
    def get_class_info(self, class_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific class."""
        return self._classes.get(class_id)
    
    def get_all_classes(self) -> Dict[int, Dict[str, Any]]:
        """Get all class information."""
        return self._classes.copy()
    
    # Internal methods
    
    def update_active_button(self):
        """Update which button appears active."""
        for class_id, button in self._class_buttons.items():
            button.set_active(class_id == self._current_class)
    
    def update_current_class_display(self):
        """Update the current class information display."""
        if self._current_class not in self._classes:
            return
        
        class_info = self._classes[self._current_class]
        
        # Update class info with color background
        self.current_class_info.setText(f"Class {self._current_class}: {class_info['name']}")
        self.current_class_info.setStyleSheet(f"""
            QLabel {{
                font-weight: bold;
                color: white;
                background-color: {class_info['color']};
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
        
        # Update count
        self.current_class_count.setText(str(class_info['count']))
    
    def toggle_expansion(self, expanded: bool):
        """Toggle between showing limited and all classes."""
        self._expanded = expanded
        
        if expanded:
            # Show all classes
            for class_id in self._classes:
                self._classes[class_id]['visible'] = True
            self.expand_button.setText("Show Less")
        else:
            # Show only first N classes
            for class_id in self._classes:
                self._classes[class_id]['visible'] = class_id <= self._max_visible_classes
            self.expand_button.setText("Show All Classes")
        
        # Recreate buttons
        self.create_class_buttons()
    
    def open_class_config(self):
        """Open class configuration dialog."""
        # Emit signal for external handling
        self.classConfigRequested.emit()
        logger.info("Class configuration requested")
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for quick class selection."""
        key = event.key()
        
        # Number keys 1-9 for quick class selection
        if Qt.Key_1 <= key <= Qt.Key_9:
            class_id = key - Qt.Key_0  # Convert to number
            if class_id in self._classes and self._classes[class_id].get('enabled', True):
                self.set_current_class(class_id)
                event.accept()
                return
        
        super().keyPressEvent(event)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get widget statistics."""
        return {
            'name': self.name,
            'version': self.version,
            'current_class': self._current_class,
            'total_classes': len(self._classes),
            'visible_classes': sum(1 for c in self._classes.values() if c['visible']),
            'total_annotations': sum(c['count'] for c in self._classes.values()),
            'expanded': self._expanded
        }