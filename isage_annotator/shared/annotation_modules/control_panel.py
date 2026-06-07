"""
Control Panel - Advanced version with modular components

This control panel integrates sophisticated control widgets and provides
a more advanced interface than the simple control panel.
"""

import logging
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QSpinBox, QGroupBox, QSlider, QCheckBox, QComboBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

# Import modular control widgets
try:
    from controls.class_selection_widget import ClassSelectionWidget
    CLASS_SELECTION_AVAILABLE = True
except ImportError:
    CLASS_SELECTION_AVAILABLE = False

logger = logging.getLogger(__name__)


class ControlPanel(QWidget):
    """
    Control panel with modular control widgets.
    
    Features:
    - Advanced class selection widget with visual feedback
    - Tool management with specialized controls
    - Display settings (zoom, grid, overlays)
    - Statistics and session information
    - Modular design allowing component replacement
    """
    
    # Signals (same interface as simple control panel for compatibility)
    classChanged = pyqtSignal(int)  # class_id
    toolChanged = pyqtSignal(str)   # tool_name
    clearRequested = pyqtSignal()
    actionTriggered = pyqtSignal(str, object)  # action_name, data
    pointSizeChanged = pyqtSignal(int)  # size
    gridToggled = pyqtSignal(bool)  # show_grid
    
    # Additional enhanced signals
    zoomChanged = pyqtSignal(float)  # zoom_level
    overlayToggled = pyqtSignal(str, bool)  # overlay_name, visible
    settingsChanged = pyqtSignal(str, object)  # setting_name, value
    
    def __init__(self, parent=None, name: str = "enhanced_control_panel", version: str = "1.0.0"):
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
        self._display_settings: Dict[str, Any] = {
            'point_size': 8,
            'show_grid': False,
            'zoom_level': 1.0,
            'overlays': {}
        }
        
        # Modular components
        self.class_selection_widget = None
        
        # Create UI
        self.setup_ui()
        
        logger.info(f"EnhancedControlPanel '{name}' v{version} created")
    
    def initialize(self, panel_width: int = 384, panel_height: int = 800, theme: str = 'dark', **kwargs) -> bool:
        """Initialize the enhanced control panel."""
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
            
            # Initialize modular components
            if self.class_selection_widget:
                # Connect class selection signals
                self.class_selection_widget.classChanged.connect(self.on_class_changed)
                self.class_selection_widget.classColorChanged.connect(self.on_class_color_changed)
            
            self.initialized = True
            logger.info(f"EnhancedControlPanel initialized: {panel_width}x{panel_height}, theme={theme}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced control panel: {e}")
            return False
    
    def setup_ui(self):
        """Create the enhanced control panel UI."""
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
        
        # Advanced class selection (modular component)
        class_section = self.create_class_section()
        layout.addWidget(class_section)
        
        # Tools section
        tools_group = self.create_tools_section()
        layout.addWidget(tools_group)
        
        # Display settings section
        display_group = self.create_display_section()
        layout.addWidget(display_group)
        
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
        header = QLabel("🧩 Enhanced Control Panel")
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
    
    def create_class_section(self) -> QGroupBox:
        """Create the advanced class selection section."""
        group = QGroupBox("🎨 Advanced Class Selection")
        layout = QVBoxLayout(group)
        
        if CLASS_SELECTION_AVAILABLE:
            # Use the advanced class selection widget
            self.class_selection_widget = ClassSelectionWidget(
                parent=self, 
                name="control_panel_class_selector",
                version="1.0.0"
            )
            layout.addWidget(self.class_selection_widget)
        else:
            # Fallback to simple selection
            fallback_label = QLabel("Advanced class selection not available.\nUsing fallback controls.")
            fallback_label.setStyleSheet("color: #f59e0b; text-align: center; padding: 20px;")
            fallback_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(fallback_label)
            
            # Simple fallback controls
            simple_layout = QHBoxLayout()
            simple_layout.addWidget(QLabel("Class:"))
            
            self.class_spinner = QSpinBox()
            self.class_spinner.setRange(1, 10)
            self.class_spinner.setValue(1)
            self.class_spinner.valueChanged.connect(self.on_class_changed)
            simple_layout.addWidget(self.class_spinner)
            
            layout.addLayout(simple_layout)
        
        return group
    
    def create_tools_section(self) -> QGroupBox:
        """Create the tools section."""
        group = QGroupBox("🛠️ Annotation Tools")
        layout = QVBoxLayout(group)
        
        # Tool selector
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(["Point Tool", "Select Tool", "Pan Tool", "Zoom Tool"])
        self.tool_combo.currentTextChanged.connect(self.on_tool_changed)
        layout.addWidget(QLabel("Active Tool:"))
        layout.addWidget(self.tool_combo)
        
        # Tool-specific settings
        tool_settings = self.create_tool_settings()
        layout.addWidget(tool_settings)
        
        return group
    
    def create_tool_settings(self) -> QWidget:
        """Create tool-specific settings."""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(container)
        
        # Point size
        self.tool_size_label = QLabel("Point Size: 8")
        self.tool_size_slider = QSlider(Qt.Horizontal)
        self.tool_size_slider.setRange(1, 20)
        self.tool_size_slider.setValue(8)
        self.tool_size_slider.valueChanged.connect(self.on_tool_size_changed)
        
        layout.addWidget(self.tool_size_label)
        layout.addWidget(self.tool_size_slider)
        
        return container
    
    def create_display_section(self) -> QGroupBox:
        """Create display settings section."""
        group = QGroupBox("👁️ Display Settings")
        layout = QVBoxLayout(group)
        
        # Grid settings
        self.grid_checkbox = QCheckBox("Show Grid")
        self.grid_checkbox.stateChanged.connect(self.on_grid_toggled)
        layout.addWidget(self.grid_checkbox)
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom:"))
        
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setFixedSize(30, 30)
        self.zoom_out_btn.clicked.connect(lambda: self.zoomChanged.emit(0.8))
        zoom_layout.addWidget(self.zoom_out_btn)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        zoom_layout.addWidget(self.zoom_label)
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(30, 30)
        self.zoom_in_btn.clicked.connect(lambda: self.zoomChanged.emit(1.2))
        zoom_layout.addWidget(self.zoom_in_btn)
        
        self.zoom_fit_btn = QPushButton("Fit")
        self.zoom_fit_btn.clicked.connect(lambda: self.zoomChanged.emit(0.0))  # 0.0 = fit to window
        zoom_layout.addWidget(self.zoom_fit_btn)
        
        layout.addLayout(zoom_layout)
        
        # Overlay controls
        overlay_group = self.create_overlay_controls()
        layout.addWidget(overlay_group)
        
        return group
    
    def create_overlay_controls(self) -> QWidget:
        """Create overlay control widgets."""
        container = QFrame()
        layout = QVBoxLayout(container)
        
        # Overlay toggles
        self.overlays = {}
        overlay_names = ["Ground Truth", "Predictions", "Mistakes", "Confidence"]
        
        for overlay_name in overlay_names:
            checkbox = QCheckBox(overlay_name)
            checkbox.stateChanged.connect(
                lambda state, name=overlay_name: self.on_overlay_toggled(name, state == 2)
            )
            self.overlays[overlay_name] = checkbox
            layout.addWidget(checkbox)
        
        return container
    
    def create_statistics_section(self) -> QGroupBox:
        """Create the statistics section."""
        group = QGroupBox("📊 Session Statistics")
        layout = QVBoxLayout(group)
        
        # Point count statistics (for compatibility)
        self.point_count_label = QLabel("Points: 0")
        self.point_count_label.setStyleSheet("color: #e2e8f0; font-weight: bold;")
        layout.addWidget(self.point_count_label)
        
        self.total_points_label = QLabel("Total Session: 0")
        self.total_points_label.setStyleSheet("color: #94a3b8;")
        layout.addWidget(self.total_points_label)
        
        # Class distribution
        self.class_distribution_label = QLabel("Classes: 0 types")
        self.class_distribution_label.setStyleSheet("color: #10b981;")
        layout.addWidget(self.class_distribution_label)
        
        # Session info
        self.session_info_label = QLabel("Session: Ready")
        self.session_info_label.setStyleSheet("color: #3b82f6;")
        layout.addWidget(self.session_info_label)
        
        return group
    
    def create_actions_section(self) -> QGroupBox:
        """Create the actions section."""
        group = QGroupBox("⚡ Quick Actions")
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
        save_btn = QPushButton("💾 Save Progress")
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
        
        # Load button
        load_btn = QPushButton("📂 Load Session")
        load_btn.clicked.connect(lambda: self.actionTriggered.emit("load", {}))
        load_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        layout.addWidget(load_btn)
        
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
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #4b5563;
                border-radius: 3px;
                background: #374151;
            }
            QCheckBox::indicator:checked {
                background: #3b82f6;
                border-color: #2563eb;
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
    
    # Event handlers (maintaining compatibility with simple control panel)
    
    def on_class_changed(self, class_id: int):
        """Handle class change."""
        self._current_class = class_id
        self.classChanged.emit(class_id)
        
        # Update statistics if class selection widget is available
        if self.class_selection_widget:
            class_info = self.class_selection_widget.get_class_info(class_id)
            if class_info:
                self.session_info_label.setText(f"Class: {class_info['name']}")
        
        logger.info(f"Class changed to: {class_id}")
    
    def on_class_color_changed(self, class_id: int, color: str):
        """Handle class color change."""
        logger.info(f"Class {class_id} color changed to: {color}")
        self.settingsChanged.emit("class_color", {"class_id": class_id, "color": color})
    
    def on_tool_changed(self, tool_name: str):
        """Handle tool change."""
        self._current_tool = tool_name.lower().replace(' ', '_')
        self.toolChanged.emit(self._current_tool)
        logger.info(f"Tool changed to: {tool_name}")
    
    def on_tool_size_changed(self, size: int):
        """Handle tool size change."""
        self.tool_size_label.setText(f"Point Size: {size}")
        self._display_settings['point_size'] = size
        self.pointSizeChanged.emit(size)
    
    def on_grid_toggled(self, state):
        """Handle grid toggle."""
        show_grid = state == 2  # Qt.Checked = 2
        self._display_settings['show_grid'] = show_grid
        self.gridToggled.emit(show_grid)
    
    def on_overlay_toggled(self, overlay_name: str, visible: bool):
        """Handle overlay toggle."""
        self._display_settings['overlays'][overlay_name] = visible
        self.overlayToggled.emit(overlay_name, visible)
        logger.info(f"Overlay '{overlay_name}' {'enabled' if visible else 'disabled'}")
    
    def on_clear_requested(self):
        """Handle clear request."""
        self.clearRequested.emit()
        # Reset statistics
        self.update_point_counts(0, 0)
        if self.class_selection_widget:
            self.class_selection_widget.update_all_counts({})
        logger.info("Clear annotations requested")
    
    # Public API (maintaining compatibility)
    
    def add_tool(self, tool_name: str, tool_config: Dict[str, Any]):
        """Add a tool to the panel."""
        self._tools[tool_name] = tool_config
        logger.info(f"Tool added: {tool_name} - {tool_config.get('name', 'Unknown')}")
    
    def update_point_counts(self, current_points: int, total_points: int):
        """Update point count statistics."""
        self._statistics['total_annotations'] = current_points
        self._statistics['session_points'] = total_points
        
        self.point_count_label.setText(f"Points: {current_points}")
        self.total_points_label.setText(f"Total Session: {total_points}")
    
    def update_zoom_display(self, zoom_factor: float):
        """Update zoom display."""
        percentage = int(zoom_factor * 100)
        self.zoom_label.setText(f"{percentage}%")
        self._display_settings['zoom_level'] = zoom_factor
    
    def update_class_counts(self, counts: Dict[int, int]):
        """Update class-specific annotation counts."""
        if self.class_selection_widget:
            self.class_selection_widget.update_all_counts(counts)
        
        # Update class distribution display
        active_classes = len([c for c in counts.values() if c > 0])
        self.class_distribution_label.setText(f"Classes: {active_classes} types")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get control panel statistics."""
        stats = {
            'name': self.name,
            'version': self.version,
            'initialized': self.initialized,
            'current_class': self._current_class,
            'current_tool': self._current_tool,
            'tools_count': len(self._tools),
            'statistics': self._statistics.copy(),
            'display_settings': self._display_settings.copy()
        }
        
        # Add class selection widget stats if available
        if self.class_selection_widget:
            stats['class_selection'] = self.class_selection_widget.get_statistics()
        
        return stats