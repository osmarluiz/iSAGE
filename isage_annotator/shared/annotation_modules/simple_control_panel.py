"""
Simple Control Panel - Basic working implementation for demonstration

A simplified control panel that provides essential annotation controls.
This is a minimal working version to demonstrate the modular concept.
"""

import logging
from typing import Dict, Any, Optional, Callable
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QSpinBox, QGroupBox, QSlider, QCheckBox, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class SimpleControlPanel(QWidget):
    """
    Simplified control panel for annotation tools.
    
    Provides basic controls for class selection, tool options,
    and annotation management.
    """
    
    # Signals
    classChanged = pyqtSignal(int)  # class_id
    toolChanged = pyqtSignal(str)   # tool_name
    clearRequested = pyqtSignal()
    actionTriggered = pyqtSignal(str, object)  # action_name, data
    pointSizeChanged = pyqtSignal(int)  # size
    gridToggled = pyqtSignal(bool)  # show_grid
    
    def __init__(self, parent=None, name: str = "simple_control_panel", version: str = "1.0.0"):
        super().__init__(parent)
        
        self.name = name
        self.version = version
        self.initialized = False
        
        # State
        self._current_class: int = 1
        self._current_tool: str = "point_tool"
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._statistics: Dict[str, int] = {
            'total_annotations': 0,
            'session_points': 0
        }
        
        # Create UI
        self.setup_ui()
        
        logger.info(f"SimpleControlPanel '{name}' v{version} created")
    
    def initialize(self, panel_width: int = 384, panel_height: int = 800, theme: str = 'dark', **kwargs) -> bool:
        """Initialize the control panel."""
        try:
            # Apply sizing
            if panel_width:
                self.setFixedWidth(panel_width)
            if panel_height:
                self.setMinimumHeight(panel_height)
            
            # Apply theme
            if theme == 'dark':
                self.apply_dark_theme()
            else:
                self.apply_light_theme()
            
            self.initialized = True
            logger.info(f"SimpleControlPanel initialized: {panel_width}x{panel_height}, theme={theme}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize control panel: {e}")
            return False
    
    def setup_ui(self):
        """Create the control panel UI."""
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
        
        # Tools section
        tools_group = self.create_tools_section()
        layout.addWidget(tools_group)
        
        # Class selection section
        class_group = self.create_class_section()
        layout.addWidget(class_group)
        
        # Statistics section
        stats_group = self.create_statistics_section()
        layout.addWidget(stats_group)
        
        # Actions section
        actions_group = self.create_actions_section()
        layout.addWidget(actions_group)
        
        # Spacer to push everything up
        layout.addStretch()
    
    def create_header(self) -> QWidget:
        """Create the header section."""
        header = QLabel("🧩 Shared Control Panel")
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
    
    def create_tools_section(self) -> QGroupBox:
        """Create the tools section."""
        group = QGroupBox("🛠️ Tools")
        layout = QVBoxLayout(group)
        
        # Tool selector
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(["Point Tool", "Select Tool", "Pan Tool"])
        self.tool_combo.currentTextChanged.connect(self.on_tool_changed)
        layout.addWidget(QLabel("Active Tool:"))
        layout.addWidget(self.tool_combo)
        
        # Tool options
        self.tool_size_label = QLabel("Point Size: 8")
        self.tool_size_slider = QSlider(Qt.Horizontal)
        self.tool_size_slider.setRange(1, 20)
        self.tool_size_slider.setValue(8)
        self.tool_size_slider.valueChanged.connect(self.on_tool_size_changed)
        
        layout.addWidget(self.tool_size_label)
        layout.addWidget(self.tool_size_slider)
        
        # Grid options
        self.grid_checkbox = QCheckBox("Show Grid")
        self.grid_checkbox.stateChanged.connect(self.on_grid_toggled)
        layout.addWidget(self.grid_checkbox)
        
        return group
    
    def create_class_section(self) -> QGroupBox:
        """Create the class selection section."""
        group = QGroupBox("🎨 Classes")
        layout = QVBoxLayout(group)
        
        # Class selector
        class_layout = QHBoxLayout()
        class_layout.addWidget(QLabel("Class:"))
        
        self.class_spinner = QSpinBox()
        self.class_spinner.setRange(1, 10)
        self.class_spinner.setValue(1)
        self.class_spinner.valueChanged.connect(self.on_class_changed)
        class_layout.addWidget(self.class_spinner)
        
        layout.addLayout(class_layout)
        
        # Quick class buttons
        buttons_layout = QHBoxLayout()
        self.class_buttons = []
        for i in range(1, 6):  # Classes 1-5
            btn = QPushButton(str(i))
            btn.setFixedSize(40, 30)
            btn.clicked.connect(lambda checked, cls=i: self.set_class(cls))
            self.class_buttons.append(btn)
            buttons_layout.addWidget(btn)
        
        layout.addLayout(buttons_layout)
        
        # Update button states
        self.update_class_buttons()
        
        return group
    
    def create_statistics_section(self) -> QGroupBox:
        """Create the statistics section."""
        group = QGroupBox("📊 Statistics") 
        layout = QVBoxLayout(group)
        
        # Point count statistics (for compatibility with existing system)
        self.point_count_label = QLabel("Points: 0")
        self.point_count_label.setStyleSheet("color: #e2e8f0; font-weight: bold;")
        layout.addWidget(self.point_count_label)
        
        self.total_points_label = QLabel("Total Session: 0")
        self.total_points_label.setStyleSheet("color: #94a3b8;")
        layout.addWidget(self.total_points_label)
        
        # Additional stats
        self.class_info_label = QLabel("Current Class: 1")
        self.class_info_label.setStyleSheet("color: #10b981;")
        layout.addWidget(self.class_info_label)
        
        return group
    
    def create_actions_section(self) -> QGroupBox:
        """Create the actions section."""
        group = QGroupBox("⚡ Actions")
        layout = QVBoxLayout(group)
        
        # Clear button
        clear_btn = QPushButton("Clear All Annotations")
        clear_btn.clicked.connect(self.on_clear_requested)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        layout.addWidget(clear_btn)
        
        # Save button
        save_btn = QPushButton("Save Progress")
        save_btn.clicked.connect(lambda: self.actionTriggered.emit("save", {}))
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        layout.addWidget(save_btn)
        
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
            QPushButton {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 6px 12px;
                color: #e2e8f0;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
            QPushButton:pressed {
                background-color: #1f2937;
            }
            QComboBox, QSpinBox {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 4px 8px;
                color: #e2e8f0;
            }
            QSlider::groove:horizontal {
                background: #374151;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3b82f6;
                border: 1px solid #1e40af;
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
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
    
    def add_tool(self, tool_name: str, tool_config: Dict[str, Any]):
        """Add a tool to the panel."""
        self._tools[tool_name] = tool_config
        logger.info(f"Tool added: {tool_name} - {tool_config.get('name', 'Unknown')}")
    
    def set_class(self, class_id: int):
        """Set the current annotation class."""
        self._current_class = class_id
        self.class_spinner.setValue(class_id)
        self.update_class_buttons()
        self.update_statistics()
        self.classChanged.emit(class_id)
        logger.info(f"Class changed to: {class_id}")
    
    def update_class_buttons(self):
        """Update class button styling."""
        for i, btn in enumerate(self.class_buttons, 1):
            if i == self._current_class:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3b82f6;
                        color: white;
                        border: 2px solid #1e40af;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #374151;
                        color: #e2e8f0;
                        border: 1px solid #4b5563;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #4b5563;
                    }
                """)
    
    def update_statistics(self):
        """Update statistics display."""
        self.class_info_label.setText(f"Current Class: {self._current_class}")
        # Point counts will be updated from external signals
    
    def update_point_counts(self, current_points: int, total_points: int):
        """Update point count statistics."""
        self._statistics['total_annotations'] = current_points
        self._statistics['session_points'] = total_points
        
        self.point_count_label.setText(f"Points: {current_points}")
        self.total_points_label.setText(f"Total Session: {total_points}")
    
    # Event handlers
    def on_class_changed(self, class_id: int):
        """Handle class change from spinner."""
        self.set_class(class_id)
    
    def on_tool_changed(self, tool_name: str):
        """Handle tool change."""
        self._current_tool = tool_name.lower().replace(' ', '_')
        self.toolChanged.emit(self._current_tool)
        logger.info(f"Tool changed to: {tool_name}")
    
    def on_tool_size_changed(self, size: int):
        """Handle tool size change."""
        self.tool_size_label.setText(f"Point Size: {size}")
        self.pointSizeChanged.emit(size)
    
    def on_grid_toggled(self, state):
        """Handle grid toggle."""
        show_grid = state == 2  # Qt.Checked = 2
        self.gridToggled.emit(show_grid)
    
    def on_clear_requested(self):
        """Handle clear request."""
        self.clearRequested.emit()
        # Reset point counts
        self.update_point_counts(0, 0)
        logger.info("Clear annotations requested")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get control panel statistics."""
        return {
            'name': self.name,
            'version': self.version,
            'initialized': self.initialized,
            'current_class': self._current_class,
            'current_tool': self._current_tool,
            'tools_count': len(self._tools),
            'statistics': self._statistics.copy()
        }