"""
Advanced Control Panel - Enhanced annotation controls matching the functioning system

This component provides advanced class management with scrollable lists, search functionality,
display settings, and comprehensive statistics to match the current functioning system exactly.
"""

import logging
from typing import Dict, Any, Optional, Callable, List, Tuple
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QSpinBox, QGroupBox, QSlider, QCheckBox, QComboBox,
    QListWidget, QListWidgetItem, QLineEdit, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)

# VAIHINGEN dataset class configuration (matches functioning system)
DEFAULT_CLASS_NAMES = [
    "Impervious",
    "Building",
    "Tree",
    "Car",
    "Low vegetation",
    "Clutter"
]

DEFAULT_CLASS_COLORS = [
    (255, 255, 255),    # 0: white
    (0, 0, 255),        # 1: blue
    (0, 255, 0),        # 2: green
    (255, 255, 0),      # 3: yellow
    (0, 255, 255),      # 4: cyan
    (255, 0, 0),        # 5: red
    (255, 0, 255),      # 6: magenta
    (255, 128, 0),      # 7: orange
    (128, 0, 255),      # 8: violet
    (0, 128, 255),      # 9: sky
    (255, 105, 180),    # 10: hot pink
    (132, 204, 22),     # 11: lime
    (139, 69, 19),      # 12: brown
    (0, 128, 128),      # 13: teal
    (255, 215, 0),      # 14: gold
    (75, 0, 130),       # 15: indigo
    (64, 224, 208),     # 16: turquoise
    (128, 128, 0),      # 17: olive
    (250, 128, 114),    # 18: salmon
    (34, 139, 34),      # 19: forest
    (255, 127, 80),     # 20: coral
    (128, 0, 0),        # 21: maroon
    (192, 192, 192),    # 22: silver
    (0, 100, 0),        # 23: dark green
]


class AdvancedControlPanel(QWidget):
    """
    Advanced control panel matching the functioning system exactly.
    
    Features:
    - Scrollable class list with search functionality
    - Color-coded class indicators
    - Professional display settings
    - Point size control with live preview
    - RGB channel mapping
    - Grid and overlay toggles
    - Comprehensive statistics
    - Add/remove class functionality
    """
    
    # Signals - expanded to match functioning system
    classChanged = pyqtSignal(int)  # class_id
    toolChanged = pyqtSignal(str)   # tool_name
    clearRequested = pyqtSignal()
    actionTriggered = pyqtSignal(str, object)  # action_name, data
    pointSizeChanged = pyqtSignal(int)  # size
    gridToggled = pyqtSignal(bool)  # show_grid
    gridSizeChanged = pyqtSignal(int)  # grid_size (10-100px)
    rgbChannelChanged = pyqtSignal(str, int)  # channel (r/g/b), mapping
    overlayToggled = pyqtSignal(str, bool)  # overlay_type, enabled
    overlayOpacityChanged = pyqtSignal(str, float)  # overlay_type, opacity (0.0-1.0)
    pixelInfoToggled = pyqtSignal(bool)  # enabled
    haloToggled = pyqtSignal(bool)  # show halo on points added this iteration
    renderModeChanged = pyqtSignal(str)  # 'auto' | 'smooth' | 'fast'
    classAdded = pyqtSignal(str, tuple)  # class_name, color
    classRemoved = pyqtSignal(int)  # class_id
    
    def __init__(self, parent=None, name: str = "advanced_control_panel", version: str = "1.0.0"):
        super().__init__(parent)
        
        self.name = name
        self.version = version
        self.initialized = False
        
        # State
        self._current_class: int = 1  # Start with Building (same as current system)
        self._current_tool: str = "point_tool"
        self._point_size: int = 3
        self._show_grid: bool = False
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._statistics: Dict[str, int] = {
            'current_points': 0,
            'total_session_points': 0,
            'current_classes': 0
        }
        
        # Class management
        self.class_names = DEFAULT_CLASS_NAMES.copy()
        self.class_colors = DEFAULT_CLASS_COLORS.copy()
        self.class_items = []  # Store list items and widgets
        self.filtered_classes = []  # For search functionality
        
        # RGB channel mappings
        self.rgb_channels = {
            'r': 0,  # Red channel mapping
            'g': 1,  # Green channel mapping  
            'b': 2   # Blue channel mapping
        }
        
        # UI components
        self.class_search = None
        self.class_list = None
        self.size_slider = None
        self.point_count_label = None
        self.total_points_label = None
        self.current_class_label = None
        self.class_count_label = None
        self.class_count_labels = {}  # {class_id: QLabel} for per-class counts
        
        # Create UI
        self.setup_ui()
        
        logger.info(f"AdvancedControlPanel '{name}' v{version} created")
    
    def initialize(self, panel_width: int = 384, panel_height: int = 800, theme: str = 'dark', **kwargs) -> bool:
        """Initialize the advanced control panel."""
        try:
            # Apply sizing - match functioning system exactly
            if panel_width:
                self.setFixedWidth(panel_width)
            if panel_height:
                self.setMinimumHeight(panel_height)
            
            # Apply theme
            if theme == 'dark':
                self.apply_dark_theme()
            else:
                self.apply_light_theme()
            
            # Initialize class list
            self.populate_class_list()
            
            # Set initial state
            if len(self.class_names) > 1:
                self.select_class(1)  # Select Building (same as current system)
            elif self.class_names:
                self.select_class(0)  # Fallback to first class if only one exists
            
            self.initialized = True
            logger.info(f"AdvancedControlPanel initialized: {panel_width}x{panel_height}, theme={theme}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize advanced control panel: {e}")
            return False
    
    def setup_ui(self):
        """Create the advanced control panel UI matching functioning system."""
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
        
        # Class Selection - Scrollable List with Search (main feature)
        # Use stretch factor 1 to expand and fill available vertical space
        class_group = self.create_class_section()
        layout.addWidget(class_group, 1)

        # Display Settings - Professional styling (fixed height)
        display_group = self.create_display_section()
        layout.addWidget(display_group)

        # Actions section (Undo, Clear, Save)
        actions_group = self.create_actions_section()
        layout.addWidget(actions_group)

        # Statistics are now in the right panel (status_panel)
        self.class_count_labels = {}
    
    def create_header(self) -> QWidget:
        """Create the header section."""
        header = QLabel("🎨 Advanced Control Panel")
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
        """Create the advanced class selection section with search."""
        group = QGroupBox("🎨 Class Selection")
        class_layout = QVBoxLayout(group)
        class_layout.setSpacing(8)
        
        # Search box - matches functioning system
        self.class_search = QLineEdit()
        self.class_search.setPlaceholderText("🔍 Search classes...")
        self.class_search.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #4a5568;
                border-radius: 4px;
                background: #1a202c;
                color: #e2e8f0;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #60a5fa;
            }
        """)
        self.class_search.textChanged.connect(self.filter_classes)
        class_layout.addWidget(self.class_search)
        
        # Scrollable list widget - expands to fill available vertical space
        self.class_list = QListWidget()
        self.class_list.setStyleSheet("""
            QListWidget {
                background: #1a202c;
                border: 1px solid #4a5568;
                border-radius: 4px;
                outline: none;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #2d3748;
                min-height: 32px;
            }
            QListWidget::item:selected {
                background: #374151;
                border: 1px solid #60a5fa;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: #2d3748;
                border-radius: 4px;
            }
        """)
        
        # Connect selection change
        self.class_list.itemClicked.connect(self.on_class_list_clicked)

        # Add with stretch factor to fill available space
        class_layout.addWidget(self.class_list, 1)
        
        # Add Class button - matches functioning system (no remove button)
        add_class_layout = QHBoxLayout()
        self.add_class_button = QPushButton("+ Add Class")
        self.add_class_button.setStyleSheet("""
            QPushButton {
                background: #059669;
                color: white;
                border: 1px solid #047857;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #047857;
            }
        """)
        self.add_class_button.clicked.connect(self.on_add_class_requested)
        add_class_layout.addWidget(self.add_class_button)
        add_class_layout.addStretch()
        class_layout.addLayout(add_class_layout)
        
        # Current class indicator
        self.class_indicator = QLabel("Current: Building")
        self.class_indicator.setStyleSheet("font-weight: bold; color: #10b981; font-size: 12px;")
        class_layout.addWidget(self.class_indicator)
        
        return group
    
    def create_display_section(self) -> QGroupBox:
        """Create the display settings section matching functioning system."""
        group = QGroupBox("🎛️ Display Settings")
        display_layout = QVBoxLayout(group)
        display_layout.setSpacing(12)
        
        # 📊 Visualization Aids Category
        viz_container, viz_layout = self.create_display_subsection("📊 Visualization Aids")
        
        # Point Size with professional styling - matches functioning system
        point_row = QHBoxLayout()
        point_label = QLabel("Point Size")
        point_label.setStyleSheet("color: #94a3b8; font-size: 11px; min-width: 65px;")
        point_row.addWidget(point_label)
        
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 20)
        self.size_slider.setValue(3)
        self.size_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #4a5568;
                height: 4px;
                background: #1a202c;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #3b82f6;
                border: 1px solid #2563eb;
                width: 14px;
                height: 14px;
                border-radius: 7px;
                margin: -5px 0;
            }
        """)
        self.size_slider.valueChanged.connect(self.on_point_size_changed)
        point_row.addWidget(self.size_slider, 1)
        
        self.size_value_label = QLabel("3px")
        self.size_value_label.setFixedWidth(50)
        self.size_value_label.setStyleSheet("color: #e2e8f0; font-size: 11px; font-family: monospace;")
        point_row.addWidget(self.size_value_label)
        
        viz_layout.addLayout(point_row)

        # Render mode (smooth vs nearest-neighbor)
        render_row = QHBoxLayout()
        render_label = QLabel("Render")
        render_label.setStyleSheet("color: #94a3b8; font-size: 11px; min-width: 65px;")
        render_row.addWidget(render_label)
        self.render_combo = QComboBox()
        self.render_combo.addItem("Auto (smart)", "auto")
        self.render_combo.addItem("Smooth (bilinear)", "smooth")
        self.render_combo.addItem("Pixel-perfect (nearest)", "fast")
        self.render_combo.setStyleSheet("""
            QComboBox {
                background: #1a202c;
                color: #e2e8f0;
                border: 1px solid #4a5568;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
            }
        """)
        self.render_combo.currentIndexChanged.connect(self.on_render_mode_changed)
        render_row.addWidget(self.render_combo, 1)
        viz_layout.addLayout(render_row)

        # Halo on points added in current iteration (toggle)
        halo_row = QHBoxLayout()
        self.halo_checkbox = QCheckBox("Highlight new points (halo)")
        self.halo_checkbox.setChecked(True)
        self.halo_checkbox.setStyleSheet("""
            QCheckBox {
                color: #e2e8f0;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 2px;
                border: 1px solid #4a5568;
            }
            QCheckBox::indicator:checked {
                background: #10b981;
                border: 1px solid #059669;
            }
        """)
        self.halo_checkbox.toggled.connect(self.on_halo_toggled)
        halo_row.addWidget(self.halo_checkbox)
        viz_layout.addLayout(halo_row)

        # Grid with enhanced styling - matches functioning system inline style
        grid_row = QHBoxLayout()
        self.grid_checkbox = QCheckBox("Grid")
        self.grid_checkbox.setStyleSheet("""
            QCheckBox {
                color: #e2e8f0;
                font-size: 11px;
                min-width: 45px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 2px;
                border: 1px solid #4a5568;
            }
            QCheckBox::indicator:checked {
                background: #10b981;
                border: 1px solid #059669;
            }
        """)
        self.grid_checkbox.toggled.connect(self.on_grid_toggled)
        grid_row.addWidget(self.grid_checkbox)
        
        self.grid_size_slider = QSlider(Qt.Horizontal)
        self.grid_size_slider.setRange(1, 100)
        self.grid_size_slider.setValue(50)
        self.grid_size_slider.setEnabled(False)
        self.grid_size_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #4a5568;
                height: 4px;
                background: #1a202c;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #10b981;
                border: 1px solid #059669;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
        """)
        grid_row.addWidget(self.grid_size_slider, 1)
        
        self.grid_size_label = QLabel("50px")
        self.grid_size_label.setFixedWidth(50)
        self.grid_size_label.setStyleSheet("color: #e2e8f0; font-size: 11px; font-family: monospace;")
        grid_row.addWidget(self.grid_size_label)
        
        # Connect grid size slider signal
        self.grid_size_slider.valueChanged.connect(self.on_grid_size_changed)
        
        viz_layout.addLayout(grid_row)
        
        # Pixel Info toggle
        pixel_info_row = QHBoxLayout()
        self.pixel_info_checkbox = QCheckBox("Pixel Info")
        self.pixel_info_checkbox.setStyleSheet("""
            QCheckBox {
                color: #e2e8f0;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 2px;
                border: 1px solid #4a5568;
            }
            QCheckBox::indicator:checked {
                background: #f59e0b;
                border: 1px solid #d97706;
            }
        """)
        self.pixel_info_checkbox.setChecked(False)  # Start unselected (matches user preference)
        self.pixel_info_checkbox.toggled.connect(self.on_pixel_info_toggled)
        pixel_info_row.addWidget(self.pixel_info_checkbox)
        
        cursor_label = QLabel("Cursor tracking")
        cursor_label.setStyleSheet("color: #6b7280; font-size: 10px;")
        pixel_info_row.addWidget(cursor_label)
        
        viz_layout.addLayout(pixel_info_row)
        display_layout.addWidget(viz_container)
        
        # 🗺️ Data Layers Category  
        layers_container, layers_layout = self.create_display_subsection("🗺️ Data Layers")
        
        # Prediction Overlay
        pred_row = QHBoxLayout()
        self.prediction_checkbox = QCheckBox("Prediction")
        self.prediction_checkbox.setStyleSheet("""
            QCheckBox {
                color: #e2e8f0;
                font-size: 11px;
                min-width: 70px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 2px;
                border: 1px solid #4a5568;
            }
            QCheckBox::indicator:checked {
                background: #8b5cf6;
                border: 1px solid #7c3aed;
            }
        """)
        self.prediction_checkbox.toggled.connect(self.on_prediction_overlay_toggled)
        pred_row.addWidget(self.prediction_checkbox)
        
        self.pred_opacity_slider = QSlider(Qt.Horizontal)
        self.pred_opacity_slider.setRange(0, 100)
        self.pred_opacity_slider.setValue(50)
        self.pred_opacity_slider.setEnabled(False)
        self.pred_opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #4a5568;
                height: 4px;
                background: #1a202c;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #8b5cf6;
                border: 1px solid #7c3aed;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
        """)
        pred_row.addWidget(self.pred_opacity_slider, 1)
        
        self.pred_opacity_label = QLabel("50%")
        self.pred_opacity_label.setFixedWidth(50)
        self.pred_opacity_label.setStyleSheet("color: #8b5cf6; font-size: 11px; font-family: monospace;")
        pred_row.addWidget(self.pred_opacity_label)
        
        # Connect prediction opacity slider signal
        self.pred_opacity_slider.valueChanged.connect(self.on_prediction_opacity_changed)
        
        layers_layout.addLayout(pred_row)
        
        # Ground Truth Overlay
        gt_row = QHBoxLayout()
        self.gt_checkbox = QCheckBox("Ground Truth")
        self.gt_checkbox.setStyleSheet("""
            QCheckBox {
                color: #e2e8f0;
                font-size: 11px;
                min-width: 70px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 2px;
                border: 1px solid #4a5568;
            }
            QCheckBox::indicator:checked {
                background: #f59e0b;
                border: 1px solid #d97706;
            }
        """)
        self.gt_checkbox.toggled.connect(self.on_gt_overlay_toggled)
        gt_row.addWidget(self.gt_checkbox)
        
        self.gt_opacity_slider = QSlider(Qt.Horizontal)
        self.gt_opacity_slider.setRange(0, 100)
        self.gt_opacity_slider.setValue(30)
        self.gt_opacity_slider.setEnabled(False)
        self.gt_opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #4a5568;
                height: 4px;
                background: #1a202c;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #f59e0b;
                border: 1px solid #d97706;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
        """)
        gt_row.addWidget(self.gt_opacity_slider, 1)
        
        self.gt_opacity_label = QLabel("30%")
        self.gt_opacity_label.setFixedWidth(50)
        self.gt_opacity_label.setStyleSheet("color: #f59e0b; font-size: 11px; font-family: monospace;")
        gt_row.addWidget(self.gt_opacity_label)
        
        # Connect GT opacity slider signal
        self.gt_opacity_slider.valueChanged.connect(self.on_gt_opacity_changed)
        
        layers_layout.addLayout(gt_row)
        display_layout.addWidget(layers_container)
        
        # 🎨 Channel Mapping Category
        channels_container, channels_layout = self.create_display_subsection("🎨 Channel Mapping")
        
        # RGB Channel selector with compact design
        rgb_row = QHBoxLayout()
        rgb_label = QLabel("RGB →")
        rgb_label.setStyleSheet("color: #94a3b8; font-size: 11px; min-width: 45px;")
        rgb_row.addWidget(rgb_label)
        
        # R Channel
        self.r_channel_combo = QComboBox()
        self.r_channel_combo.addItems(["0", "1", "2"])
        self.r_channel_combo.setCurrentIndex(0)
        self.r_channel_combo.setFixedWidth(40)
        self.r_channel_combo.setStyleSheet("""
            QComboBox {
                background: #1a202c;
                color: #ef4444;
                border: 1px solid #4a5568;
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 11px;
                font-family: monospace;
                font-weight: bold;
            }
        """)
        
        # G Channel
        self.g_channel_combo = QComboBox()
        self.g_channel_combo.addItems(["0", "1", "2"])
        self.g_channel_combo.setCurrentIndex(1)
        self.g_channel_combo.setFixedWidth(40)
        self.g_channel_combo.setStyleSheet("""
            QComboBox {
                background: #1a202c;
                color: #10b981;
                border: 1px solid #4a5568;
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 11px;
                font-family: monospace;
                font-weight: bold;
            }
        """)
        
        # B Channel
        self.b_channel_combo = QComboBox()
        self.b_channel_combo.addItems(["0", "1", "2"])
        self.b_channel_combo.setCurrentIndex(2)
        self.b_channel_combo.setFixedWidth(40)
        self.b_channel_combo.setStyleSheet("""
            QComboBox {
                background: #1a202c;
                color: #3b82f6;
                border: 1px solid #4a5568;
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 11px;
                font-family: monospace;
                font-weight: bold;
            }
        """)
        
        rgb_row.addWidget(self.r_channel_combo)
        rgb_row.addWidget(self.g_channel_combo)
        rgb_row.addWidget(self.b_channel_combo)
        rgb_row.addStretch()
        
        # Reset button
        reset_btn = QPushButton("🔄")
        reset_btn.setFixedSize(24, 24)
        reset_btn.setStyleSheet("""
            QPushButton {
                background: #374151;
                border: 1px solid #4b5563;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover { background: #4b5563; }
        """)
        reset_btn.setToolTip("Reset to RGB → 012")
        reset_btn.clicked.connect(lambda: [
            self.r_channel_combo.setCurrentIndex(0),
            self.g_channel_combo.setCurrentIndex(1), 
            self.b_channel_combo.setCurrentIndex(2)
        ])
        rgb_row.addWidget(reset_btn)
        
        # Connect RGB channel change signals
        self.r_channel_combo.currentIndexChanged.connect(lambda i: self.on_rgb_channel_changed('r', i))
        self.g_channel_combo.currentIndexChanged.connect(lambda i: self.on_rgb_channel_changed('g', i))
        self.b_channel_combo.currentIndexChanged.connect(lambda i: self.on_rgb_channel_changed('b', i))
        
        channels_layout.addLayout(rgb_row)
        display_layout.addWidget(channels_container)
        
        return group
    
    def create_display_subsection(self, title):
        """Create a professional display section with icon and title (matches functioning system)."""
        section_container = QFrame()
        section_container.setStyleSheet("""
            QFrame {
                background: rgba(55, 65, 81, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(8, 6, 8, 6)
        section_layout.setSpacing(8)
        
        # Section header
        header = QLabel(title)
        header.setStyleSheet("""
            color: #f3f4f6;
            font-size: 12px;
            font-weight: bold;
            padding: 2px 0;
        """)
        section_layout.addWidget(header)
        
        return section_container, section_layout
    
    def create_display_category(self, title: str) -> QFrame:
        """Create a display category container without pre-set layout.
        
        The calling code will add its own layout to this container.
        """
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: rgba(55, 65, 81, 0.3);
                border-radius: 6px;
                padding: 8px;
                margin: 2px;
            }
        """)
        
        # Don't create a layout here - let the calling code create one
        # This prevents the "QLayout: Attempting to add QLayout to QFrame which already has a layout" error
        
        return container
    
    def create_statistics_section(self) -> QGroupBox:
        """Create the statistics section matching functioning system."""
        group = QGroupBox("📊 Statistics")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Point count statistics - matches functioning system exactly
        self.point_count_label = QLabel("Points: 0")
        self.point_count_label.setStyleSheet("""
            color: #e2e8f0;
            font-size: 12px;
            font-weight: bold;
        """)
        layout.addWidget(self.point_count_label)

        self.total_points_label = QLabel("Total Session: 0")
        self.total_points_label.setStyleSheet("""
            color: #94a3b8;
            font-size: 11px;
        """)
        layout.addWidget(self.total_points_label)

        # Per-class counts are now in the status panel (right side)
        self.class_count_labels = {}

        return group
    
    def create_actions_section(self) -> QGroupBox:
        """Create the actions section."""
        group = QGroupBox("⚡ Actions")
        layout = QVBoxLayout(group)
        
        # Undo button - revert last add/remove action
        undo_btn = QPushButton("↶ Undo (Ctrl+Z)")
        undo_btn.clicked.connect(lambda: self.actionTriggered.emit("undo", {}))
        undo_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        layout.addWidget(undo_btn)

        # Clear button - matches functioning system styling
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
                font-size: 12px;
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
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        layout.addWidget(save_btn)
        
        return group
    
    def populate_class_list(self):
        """Populate the class list with all available classes."""
        self.class_list.clear()
        self.class_items.clear()
        
        for i, (name, color) in enumerate(zip(self.class_names, self.class_colors)):
            self.add_class_to_list(i, name, color)
    
    def add_class_to_list(self, class_id: int, name: str, color: Tuple[int, int, int]):
        """Add a class item to the list with proper styling."""
        # Create custom widget for list item
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(6, 4, 6, 4)
        item_layout.setSpacing(8)
        
        # Color indicator - matches functioning system exactly
        color_label = QLabel()
        color_label.setFixedSize(20, 20)
        r, g, b = color
        border_color = '#ffffff' if class_id == self._current_class else '#4a5568'
        color_label.setStyleSheet(f"""
            background-color: rgb({r}, {g}, {b});
            border-radius: 10px;
            border: 2px solid {border_color};
        """)
        
        # Class index (raw index to match current system)
        index_label = QLabel(f"{class_id}")
        index_label.setFixedWidth(25)
        index_label.setStyleSheet("""
            color: #94a3b8;
            font-size: 12px;
            font-weight: bold;
            font-family: monospace;
        """)
        index_label.setAlignment(Qt.AlignCenter)
        
        # Class name
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #e2e8f0; font-size: 12px;")
        
        item_layout.addWidget(color_label)
        item_layout.addWidget(index_label)
        item_layout.addWidget(name_label)
        item_layout.addStretch()
        
        # Create list item
        list_item = QListWidgetItem()
        list_item.setSizeHint(QSize(0, 36))  # Same height as functioning system
        list_item.setData(Qt.UserRole, class_id)  # Store class ID
        
        self.class_list.addItem(list_item)
        self.class_list.setItemWidget(list_item, item_widget)
        
        self.class_items.append((list_item, item_widget, color_label, name_label))
    
    def filter_classes(self, search_text: str):
        """Filter classes based on search text."""
        search_text = search_text.lower().strip()
        
        for i, (list_item, item_widget, color_label, name_label) in enumerate(self.class_items):
            class_name = self.class_names[i].lower()
            
            # Show/hide items based on search
            if not search_text or search_text in class_name:
                list_item.setHidden(False)
            else:
                list_item.setHidden(True)
    
    def select_class(self, class_id: int):
        """Select a specific class and update UI."""
        if 0 <= class_id < len(self.class_names):
            self._current_class = class_id
            
            # Update list selection
            self.class_list.setCurrentRow(class_id)
            
            # Update color indicators
            for i, (list_item, item_widget, color_label, name_label) in enumerate(self.class_items):
                r, g, b = self.class_colors[i]
                border_color = '#ffffff' if i == class_id else '#4a5568'
                color_label.setStyleSheet(f"""
                    background-color: rgb({r}, {g}, {b});
                    border-radius: 8px;
                    border: 2px solid {border_color};
                """)
            
            # Update statistics
            self.update_statistics()
            
            # Emit signal
            self.classChanged.emit(class_id)
            logger.info(f"Class selected: {class_id} - {self.class_names[class_id]}")
    
    def update_statistics(self):
        """Update all statistics displays."""
        if self.class_names and hasattr(self, 'class_indicator') and self.class_indicator:
            class_name = self.class_names[self._current_class]
            # Update class indicator (matches current system)
            self.class_indicator.setText(f"Current: {class_name}")
            
        # Update class count if label exists
        if hasattr(self, 'class_count_label') and self.class_count_label:
            self.class_count_label.setText(f"Classes: {len(self.class_names)}")
            
        # Update current class label if it exists  
        if hasattr(self, 'current_class_label') and self.current_class_label and self.class_names:
            class_name = self.class_names[self._current_class]
            self.current_class_label.setText(f"Current: {class_name}")
    
    def update_point_counts(self, current_points: int, total_points: int):
        """Update point count statistics - matches functioning system interface."""
        self._statistics['current_points'] = current_points
        self._statistics['total_session_points'] = total_points

        # Update labels only if they exist
        if hasattr(self, 'point_count_label') and self.point_count_label:
            self.point_count_label.setText(f"Points: {current_points}")
        if hasattr(self, 'total_points_label') and self.total_points_label:
            self.total_points_label.setText(f"Total Session: {total_points}")

    def update_class_statistics(self, current_class_counts: Dict[int, int], session_class_totals: Dict[int, int]):
        """Update per-class count labels with current image and session totals.

        Args:
            current_class_counts: Dictionary mapping class_id to count in current image
            session_class_totals: Dictionary mapping class_id to total count across all images
        """
        if not hasattr(self, 'class_count_labels') or not self.class_count_labels:
            return

        for class_id, labels in self.class_count_labels.items():
            current_count = current_class_counts.get(class_id, 0)
            total_count = session_class_totals.get(class_id, 0)

            if isinstance(labels, dict):
                # New format with separate labels
                labels['current'].setText(str(current_count))
                labels['total'].setText(str(total_count))
            else:
                # Old format fallback (single label)
                class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"Class {class_id}"
                labels.setText(f"{class_name}: {total_count}")
    
    def apply_dark_theme(self):
        """Apply dark theme styling matching functioning system."""
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
                font-size: 13px;
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
    
    # Event handlers
    
    def on_class_list_clicked(self, item: QListWidgetItem):
        """Handle class list item click."""
        class_id = item.data(Qt.UserRole)
        if class_id is not None:
            self.select_class(class_id)
    
    def on_point_size_changed(self, size: int):
        """Handle point size change."""
        self._point_size = size
        self.size_value_label.setText(f"{size}px")
        self.pointSizeChanged.emit(size)
        logger.debug(f"Point size changed to: {size}")
    
    def on_grid_toggled(self, enabled: bool):
        """Handle grid toggle."""
        self._show_grid = enabled
        self.grid_size_slider.setEnabled(enabled)
        self.gridToggled.emit(self._show_grid)
        logger.debug(f"Grid toggled: {self._show_grid}")

    def on_halo_toggled(self, enabled: bool):
        """Handle halo (highlight new points) toggle."""
        self.haloToggled.emit(bool(enabled))
        logger.debug(f"Halo toggled: {enabled}")

    def on_render_mode_changed(self, idx: int):
        """Handle render mode combobox change."""
        mode = self.render_combo.itemData(idx)
        self.renderModeChanged.emit(str(mode))
        logger.debug(f"Render mode: {mode}")
    
    def on_grid_size_changed(self, value: int):
        """Handle grid size slider change."""
        self.grid_size_label.setText(f"{value}px")
        # Emit signal for grid size change (add to signals if needed)
        if hasattr(self, 'gridSizeChanged'):
            self.gridSizeChanged.emit(value)
        logger.debug(f"Grid size changed: {value}px")
    
    def on_prediction_overlay_toggled(self, enabled: bool):
        """Handle prediction overlay toggle."""
        self.pred_opacity_slider.setEnabled(enabled)
        # Emit signal for prediction overlay (add to signals if needed)
        if hasattr(self, 'overlayToggled'):
            self.overlayToggled.emit("prediction", enabled)
        # Also emit opacity signal to trigger loading (matches functioning system)
        if enabled and hasattr(self, 'overlayOpacityChanged'):
            opacity = self.pred_opacity_slider.value() / 100.0
            self.overlayOpacityChanged.emit("prediction", opacity)
        logger.debug(f"Prediction overlay toggled: {enabled}")
    
    def on_prediction_opacity_changed(self, value: int):
        """Handle prediction overlay opacity change."""
        self.pred_opacity_label.setText(f"{value}%")
        # Emit signal for prediction opacity (add to signals if needed)
        if hasattr(self, 'overlayOpacityChanged'):
            self.overlayOpacityChanged.emit("prediction", value / 100.0)
        logger.debug(f"Prediction overlay opacity: {value}%")
    
    def on_gt_overlay_toggled(self, enabled: bool):
        """Handle ground truth overlay toggle."""
        self.gt_opacity_slider.setEnabled(enabled)
        # Emit signal for GT overlay (add to signals if needed)
        if hasattr(self, 'overlayToggled'):
            self.overlayToggled.emit("ground_truth", enabled)
        # Also emit opacity signal to trigger loading (matches functioning system)
        if enabled and hasattr(self, 'overlayOpacityChanged'):
            opacity = self.gt_opacity_slider.value() / 100.0
            self.overlayOpacityChanged.emit("ground_truth", opacity)
        logger.debug(f"Ground truth overlay toggled: {enabled}")
    
    def on_gt_opacity_changed(self, value: int):
        """Handle ground truth overlay opacity change."""
        self.gt_opacity_label.setText(f"{value}%")
        # Emit signal for GT opacity (add to signals if needed)
        if hasattr(self, 'overlayOpacityChanged'):
            self.overlayOpacityChanged.emit("ground_truth", value / 100.0)
        logger.debug(f"Ground truth overlay opacity: {value}%")
    
    def on_rgb_channel_changed(self, channel: str, index: int):
        """Handle RGB channel mapping change."""
        self.rgb_channels[channel] = index
        self.rgbChannelChanged.emit(channel, index)
        logger.debug(f"RGB channel {channel} mapped to channel {index + 1}")
    
    def on_pixel_info_toggled(self, enabled: bool):
        """Handle pixel info toggle."""
        self.pixelInfoToggled.emit(enabled)
        logger.debug(f"Pixel info {'enabled' if enabled else 'disabled'}")
    
    def on_add_class_requested(self):
        """Handle add class request."""
        from PyQt5.QtWidgets import QInputDialog
        
        # Get class name from user
        name, ok = QInputDialog.getText(self, 'Add Class', 'Enter class name:')
        
        if ok and name.strip():
            # Generate a new color (cycle through colors)
            color_index = len(self.class_names) % len(DEFAULT_CLASS_COLORS)
            new_color = DEFAULT_CLASS_COLORS[color_index]
            
            # Add to lists
            self.class_names.append(name.strip())
            self.class_colors.append(new_color)
            
            # Add to UI
            new_class_id = len(self.class_names) - 1
            self.add_class_to_list(new_class_id, name.strip(), new_color)
            
            # Update statistics
            self.update_statistics()
            
            # Emit signal
            self.classAdded.emit(name.strip(), new_color)
            
            logger.info(f"Class added: {name.strip()} with color {new_color}")
    
    def on_remove_class_requested(self):
        """Handle remove class request."""
        if self._current_class < len(self.class_names) and len(self.class_names) > 1:
            removed_name = self.class_names[self._current_class]
            
            # Remove from lists
            self.class_names.pop(self._current_class)
            self.class_colors.pop(self._current_class)
            
            # Rebuild list
            self.populate_class_list()
            
            # Select new current class
            new_current = min(self._current_class, len(self.class_names) - 1)
            self.select_class(new_current)
            
            # Emit signal
            self.classRemoved.emit(self._current_class)
            
            logger.info(f"Class removed: {removed_name}")
    
    def on_clear_requested(self):
        """Handle clear annotations request."""
        self.clearRequested.emit()
        # Reset point counts
        self.update_point_counts(0, 0)
        logger.info("Clear annotations requested")
    
    # Public API methods
    
    def add_tool(self, tool_name: str, tool_config: Dict[str, Any]):
        """Add a tool to the panel."""
        self._tools[tool_name] = tool_config
        logger.info(f"Tool added: {tool_name} - {tool_config.get('name', 'Unknown')}")
    
    def get_current_class(self) -> int:
        """Get the currently selected class ID."""
        return self._current_class
    
    def get_class_info(self, class_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific class."""
        if 0 <= class_id < len(self.class_names):
            return {
                'id': class_id,
                'name': self.class_names[class_id],
                'color': self.class_colors[class_id]
            }
        return None
    
    def get_all_classes(self) -> List[Dict[str, Any]]:
        """Get information about all classes."""
        return [
            {
                'id': i,
                'name': name,
                'color': color
            }
            for i, (name, color) in enumerate(zip(self.class_names, self.class_colors))
        ]
    
    def update_class_config(self, class_names: List[str], class_colors: List[Tuple[int, int, int]] = None):
        """Update class configuration from session data (matches functioning system)."""
        logger.info(f"Updating class configuration with {len(class_names)} classes")
        
        # Update internal state
        self.class_names = class_names.copy()
        
        # Use provided colors or generate defaults
        if class_colors and len(class_colors) == len(class_names):
            self.class_colors = class_colors.copy()
        else:
            # Generate colors if not provided
            self.class_colors = [
                DEFAULT_CLASS_COLORS[i % len(DEFAULT_CLASS_COLORS)]
                for i in range(len(class_names))
            ]
        
        # Rebuild class list UI
        self.rebuild_class_list()
        
        # Update statistics
        self.update_statistics()
        
        # Emit signal for external components
        if hasattr(self, 'classConfigChanged'):
            self.classConfigChanged.emit(self.class_names, self.class_colors)
        
        logger.info(f"Class configuration updated: {self.class_names}")
    
    def rebuild_class_list(self):
        """Rebuild the class list UI with current configuration."""
        # Just use populate_class_list which already does the right thing
        self.populate_class_list()

        # Restore current class selection if valid
        if 0 <= self._current_class < len(self.class_names):
            self.class_list.setCurrentRow(self._current_class)
        elif self.class_names:
            # Reset to first class if current selection is invalid
            self._current_class = 0
            self.class_list.setCurrentRow(0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive control panel statistics."""
        return {
            'name': self.name,
            'version': self.version,
            'initialized': self.initialized,
            'current_class': self._current_class,
            'current_tool': self._current_tool,
            'point_size': self._point_size,
            'show_grid': self._show_grid,
            'tools_count': len(self._tools),
            'classes_count': len(self.class_names),
            'rgb_channels': self.rgb_channels.copy(),
            'statistics': self._statistics.copy()
        }