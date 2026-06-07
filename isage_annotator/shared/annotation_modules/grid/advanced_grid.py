"""
Advanced Grid System

Provides sophisticated grid overlays for precise annotation alignment.
Supports multiple grid types, snap-to-grid, and customizable appearance.
Part of the modular annotation system.
"""

try:
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QCheckBox, QComboBox
    from PyQt5.QtCore import Qt, pyqtSignal, QRect, QPoint
    from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    class QWidget: pass
    class pyqtSignal: 
        def __init__(self, *args): pass

import numpy as np
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import math


class GridType(Enum):
    """Types of grid overlays."""
    SQUARE = "square"
    RECTANGULAR = "rectangular"
    TRIANGULAR = "triangular"
    HEXAGONAL = "hexagonal"
    POLAR = "polar"
    ISOMETRIC = "isometric"


class SnapMode(Enum):
    """Grid snapping modes."""
    NONE = "none"
    CORNER = "corner"
    CENTER = "center"
    EDGE = "edge"
    INTERSECTION = "intersection"


@dataclass
class GridSettings:
    """Grid configuration settings."""
    grid_type: GridType = GridType.SQUARE
    spacing_x: int = 20
    spacing_y: int = 20
    offset_x: int = 0
    offset_y: int = 0
    
    # Appearance
    primary_color: QColor = None
    secondary_color: QColor = None
    line_width: int = 1
    opacity: float = 0.3
    
    # Snap settings
    snap_mode: SnapMode = SnapMode.CORNER
    snap_distance: int = 10
    snap_enabled: bool = False
    
    # Subdivision
    subdivisions: int = 1
    show_subdivisions: bool = False
    
    def __post_init__(self):
        if self.primary_color is None:
            self.primary_color = QColor(100, 100, 100, int(255 * self.opacity))
        if self.secondary_color is None:
            self.secondary_color = QColor(60, 60, 60, int(255 * self.opacity * 0.5))


class AdvancedGrid:
    """
    Advanced grid system for annotation canvas overlays.
    
    Features:
    - Multiple grid types (square, rectangular, triangular, etc.)
    - Customizable spacing and appearance
    - Snap-to-grid functionality
    - Grid subdivisions for fine alignment
    - Coordinate transformation utilities
    - Performance-optimized rendering
    """
    
    def __init__(self, settings: GridSettings = None):
        self.settings = settings or GridSettings()
        self._cached_grid_points = []
        self._cache_valid = False
        self._canvas_size = (0, 0)
        self._zoom_factor = 1.0
        
    def set_settings(self, settings: GridSettings):
        """Update grid settings and invalidate cache."""
        self.settings = settings
        self._invalidate_cache()
    
    def set_canvas_size(self, width: int, height: int):
        """Set the canvas size for grid calculation."""
        if (width, height) != self._canvas_size:
            self._canvas_size = (width, height)
            self._invalidate_cache()
    
    def set_zoom_factor(self, zoom_factor: float):
        """Set the zoom factor for grid scaling."""
        if zoom_factor != self._zoom_factor:
            self._zoom_factor = zoom_factor
            self._invalidate_cache()
    
    def _invalidate_cache(self):
        """Invalidate the grid points cache."""
        self._cache_valid = False
        self._cached_grid_points.clear()
    
    def _calculate_square_grid(self, width: int, height: int) -> List[Tuple[QPoint, QPoint]]:
        """Calculate square grid lines."""
        lines = []
        
        # Adjust spacing for zoom
        spacing_x = max(1, int(self.settings.spacing_x * self._zoom_factor))
        spacing_y = max(1, int(self.settings.spacing_y * self._zoom_factor))
        
        # Vertical lines
        start_x = self.settings.offset_x % spacing_x
        for x in range(start_x, width, spacing_x):
            lines.append((QPoint(x, 0), QPoint(x, height)))
        
        # Horizontal lines
        start_y = self.settings.offset_y % spacing_y
        for y in range(start_y, height, spacing_y):
            lines.append((QPoint(0, y), QPoint(width, y)))
        
        # Add subdivisions if enabled
        if self.settings.show_subdivisions and self.settings.subdivisions > 1:
            sub_spacing_x = spacing_x // self.settings.subdivisions
            sub_spacing_y = spacing_y // self.settings.subdivisions
            
            if sub_spacing_x > 1:
                for x in range(start_x + sub_spacing_x, width, sub_spacing_x):
                    if x % spacing_x != 0:  # Don't duplicate main grid lines
                        lines.append((QPoint(x, 0), QPoint(x, height)))
            
            if sub_spacing_y > 1:
                for y in range(start_y + sub_spacing_y, height, sub_spacing_y):
                    if y % spacing_y != 0:  # Don't duplicate main grid lines
                        lines.append((QPoint(0, y), QPoint(width, y)))
        
        return lines
    
    def _calculate_triangular_grid(self, width: int, height: int) -> List[Tuple[QPoint, QPoint]]:
        """Calculate triangular grid lines."""
        lines = []
        
        spacing = max(1, int(self.settings.spacing_x * self._zoom_factor))
        row_height = int(spacing * math.sqrt(3) / 2)
        
        # Horizontal lines
        for y in range(0, height, row_height):
            lines.append((QPoint(0, y), QPoint(width, y)))
        
        # Diagonal lines (alternating direction)
        for row in range(0, height // row_height + 1):
            y = row * row_height
            offset = (spacing // 2) if row % 2 == 1 else 0
            
            for x in range(offset, width, spacing):
                # Upward diagonal
                x2 = x + spacing // 2
                y2 = y + row_height
                if x2 < width and y2 < height:
                    lines.append((QPoint(x, y), QPoint(x2, y2)))
                
                # Downward diagonal
                x3 = x - spacing // 2
                y3 = y + row_height
                if x3 >= 0 and y3 < height:
                    lines.append((QPoint(x, y), QPoint(x3, y3)))
        
        return lines
    
    def _calculate_hexagonal_grid(self, width: int, height: int) -> List[Tuple[QPoint, QPoint]]:
        """Calculate hexagonal grid lines."""
        lines = []
        
        spacing = max(1, int(self.settings.spacing_x * self._zoom_factor))
        hex_height = int(spacing * math.sqrt(3))
        
        # Vertical lines
        for x in range(0, width, spacing * 3 // 2):
            lines.append((QPoint(x, 0), QPoint(x, height)))
        
        # Diagonal lines
        for y in range(0, height, hex_height // 2):
            for x in range(0, width, spacing * 3):
                # Top-right diagonal
                x2 = x + spacing * 3 // 4
                y2 = y + hex_height // 4
                if x2 < width and y2 < height:
                    lines.append((QPoint(x, y), QPoint(x2, y2)))
                
                # Bottom-right diagonal
                x3 = x + spacing * 3 // 4
                y3 = y - hex_height // 4
                if x3 < width and y3 >= 0:
                    lines.append((QPoint(x, y), QPoint(x3, y3)))
        
        return lines
    
    def _calculate_polar_grid(self, width: int, height: int) -> List[Tuple[QPoint, QPoint]]:
        """Calculate polar grid lines."""
        lines = []
        
        center_x = width // 2
        center_y = height // 2
        max_radius = max(center_x, center_y)
        
        spacing = max(1, int(self.settings.spacing_x * self._zoom_factor))
        
        # Concentric circles (approximated as many short lines)
        for radius in range(spacing, max_radius, spacing):
            points = []
            num_points = max(8, radius // 2)  # More points for larger circles
            
            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                x = center_x + int(radius * math.cos(angle))
                y = center_y + int(radius * math.sin(angle))
                points.append(QPoint(x, y))
            
            # Connect adjacent points to form circle
            for i in range(len(points)):
                next_i = (i + 1) % len(points)
                lines.append((points[i], points[next_i]))
        
        # Radial lines
        num_radials = 12  # 30-degree increments
        for i in range(num_radials):
            angle = 2 * math.pi * i / num_radials
            x = center_x + int(max_radius * math.cos(angle))
            y = center_y + int(max_radius * math.sin(angle))
            lines.append((QPoint(center_x, center_y), QPoint(x, y)))
        
        return lines
    
    def get_grid_lines(self) -> List[Tuple[QPoint, QPoint]]:
        """Get all grid lines for the current settings."""
        if self._cache_valid and self._cached_grid_points:
            return self._cached_grid_points
        
        width, height = self._canvas_size
        if width <= 0 or height <= 0:
            return []
        
        if self.settings.grid_type == GridType.SQUARE:
            lines = self._calculate_square_grid(width, height)
        elif self.settings.grid_type == GridType.RECTANGULAR:
            lines = self._calculate_square_grid(width, height)  # Same as square but different spacing
        elif self.settings.grid_type == GridType.TRIANGULAR:
            lines = self._calculate_triangular_grid(width, height)
        elif self.settings.grid_type == GridType.HEXAGONAL:
            lines = self._calculate_hexagonal_grid(width, height)
        elif self.settings.grid_type == GridType.POLAR:
            lines = self._calculate_polar_grid(width, height)
        elif self.settings.grid_type == GridType.ISOMETRIC:
            lines = self._calculate_triangular_grid(width, height)  # Similar to triangular
        else:
            lines = []
        
        self._cached_grid_points = lines
        self._cache_valid = True
        
        return lines
    
    def snap_point(self, point: QPoint) -> QPoint:
        """Snap a point to the nearest grid position."""
        if not self.settings.snap_enabled:
            return point
        
        if self.settings.grid_type == GridType.SQUARE:
            return self._snap_to_square_grid(point)
        elif self.settings.grid_type == GridType.POLAR:
            return self._snap_to_polar_grid(point)
        else:
            # Default to square grid snapping for other types
            return self._snap_to_square_grid(point)
    
    def _snap_to_square_grid(self, point: QPoint) -> QPoint:
        """Snap point to square grid."""
        spacing_x = max(1, int(self.settings.spacing_x * self._zoom_factor))
        spacing_y = max(1, int(self.settings.spacing_y * self._zoom_factor))
        
        # Find nearest grid intersection
        grid_x = round((point.x() - self.settings.offset_x) / spacing_x) * spacing_x + self.settings.offset_x
        grid_y = round((point.y() - self.settings.offset_y) / spacing_y) * spacing_y + self.settings.offset_y
        
        snapped_point = QPoint(int(grid_x), int(grid_y))
        
        # Check if within snap distance
        distance = math.sqrt((point.x() - snapped_point.x())**2 + (point.y() - snapped_point.y())**2)
        if distance <= self.settings.snap_distance:
            return snapped_point
        
        return point
    
    def _snap_to_polar_grid(self, point: QPoint) -> QPoint:
        """Snap point to polar grid."""
        width, height = self._canvas_size
        center_x = width // 2
        center_y = height // 2
        
        # Convert to polar coordinates
        dx = point.x() - center_x
        dy = point.y() - center_y
        radius = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)
        
        # Snap radius to grid
        spacing = max(1, int(self.settings.spacing_x * self._zoom_factor))
        snapped_radius = round(radius / spacing) * spacing
        
        # Snap angle to 30-degree increments
        angle_increment = math.pi / 6  # 30 degrees
        snapped_angle = round(angle / angle_increment) * angle_increment
        
        # Convert back to Cartesian
        snapped_x = center_x + int(snapped_radius * math.cos(snapped_angle))
        snapped_y = center_y + int(snapped_radius * math.sin(snapped_angle))
        
        snapped_point = QPoint(snapped_x, snapped_y)
        
        # Check if within snap distance
        distance = math.sqrt((point.x() - snapped_point.x())**2 + (point.y() - snapped_point.y())**2)
        if distance <= self.settings.snap_distance:
            return snapped_point
        
        return point
    
    def paint_grid(self, painter: QPainter):
        """Paint the grid on the given painter."""
        if not PYQT5_AVAILABLE:
            return
        
        painter.save()
        
        lines = self.get_grid_lines()
        if not lines:
            painter.restore()
            return
        
        # Set up pen for main grid lines
        main_pen = QPen(self.settings.primary_color, self.settings.line_width)
        painter.setPen(main_pen)
        
        # Draw main grid lines
        main_lines = []
        subdivision_lines = []
        
        # Separate main lines from subdivision lines
        spacing_x = max(1, int(self.settings.spacing_x * self._zoom_factor))
        spacing_y = max(1, int(self.settings.spacing_y * self._zoom_factor))
        
        for start, end in lines:
            # Check if this is a main grid line or subdivision
            if (self.settings.show_subdivisions and 
                self.settings.subdivisions > 1 and
                (start.x() % spacing_x != 0 or start.y() % spacing_y != 0)):
                subdivision_lines.append((start, end))
            else:
                main_lines.append((start, end))
        
        # Draw subdivision lines first (lighter)
        if subdivision_lines:
            sub_pen = QPen(self.settings.secondary_color, max(1, self.settings.line_width - 1))
            painter.setPen(sub_pen)
            for start, end in subdivision_lines:
                painter.drawLine(start, end)
        
        # Draw main grid lines
        if main_lines:
            painter.setPen(main_pen)
            for start, end in main_lines:
                painter.drawLine(start, end)
        
        painter.restore()
    
    def get_grid_info(self) -> Dict[str, Any]:
        """Get information about the current grid."""
        lines = self.get_grid_lines()
        
        return {
            "grid_type": self.settings.grid_type.value,
            "spacing_x": self.settings.spacing_x,
            "spacing_y": self.settings.spacing_y,
            "line_count": len(lines),
            "snap_enabled": self.settings.snap_enabled,
            "subdivisions": self.settings.subdivisions if self.settings.show_subdivisions else 0,
            "zoom_factor": self._zoom_factor
        }


class GridControlWidget(QWidget):
    """
    Control widget for grid settings.
    
    Features:
    - Grid type selection
    - Spacing controls
    - Snap settings
    - Appearance options
    - Real-time preview
    """
    
    grid_changed = pyqtSignal(GridSettings)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = GridSettings()
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the control UI."""
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Grid type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Grid Type:"))
        
        self.type_combo = QComboBox()
        for grid_type in GridType:
            self.type_combo.addItem(grid_type.value.title(), grid_type)
        type_layout.addWidget(self.type_combo)
        
        layout.addLayout(type_layout)
        
        # Spacing controls
        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(QLabel("Spacing X:"))
        
        self.spacing_x_spin = QSpinBox()
        self.spacing_x_spin.setRange(1, 1000)
        self.spacing_x_spin.setValue(self.settings.spacing_x)
        spacing_layout.addWidget(self.spacing_x_spin)
        
        spacing_layout.addWidget(QLabel("Y:"))
        
        self.spacing_y_spin = QSpinBox()
        self.spacing_y_spin.setRange(1, 1000)
        self.spacing_y_spin.setValue(self.settings.spacing_y)
        spacing_layout.addWidget(self.spacing_y_spin)
        
        layout.addLayout(spacing_layout)
        
        # Snap settings
        self.snap_checkbox = QCheckBox("Enable Snap to Grid")
        self.snap_checkbox.setChecked(self.settings.snap_enabled)
        layout.addWidget(self.snap_checkbox)
        
        # Subdivisions
        sub_layout = QHBoxLayout()
        
        self.subdivision_checkbox = QCheckBox("Show Subdivisions")
        self.subdivision_checkbox.setChecked(self.settings.show_subdivisions)
        sub_layout.addWidget(self.subdivision_checkbox)
        
        self.subdivision_spin = QSpinBox()
        self.subdivision_spin.setRange(1, 10)
        self.subdivision_spin.setValue(self.settings.subdivisions)
        sub_layout.addWidget(self.subdivision_spin)
        
        layout.addLayout(sub_layout)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect UI signals to update handlers."""
        self.type_combo.currentIndexChanged.connect(self._update_settings)
        self.spacing_x_spin.valueChanged.connect(self._update_settings)
        self.spacing_y_spin.valueChanged.connect(self._update_settings)
        self.snap_checkbox.toggled.connect(self._update_settings)
        self.subdivision_checkbox.toggled.connect(self._update_settings)
        self.subdivision_spin.valueChanged.connect(self._update_settings)
    
    def _update_settings(self):
        """Update settings from UI controls."""
        self.settings.grid_type = self.type_combo.currentData()
        self.settings.spacing_x = self.spacing_x_spin.value()
        self.settings.spacing_y = self.spacing_y_spin.value()
        self.settings.snap_enabled = self.snap_checkbox.isChecked()
        self.settings.show_subdivisions = self.subdivision_checkbox.isChecked()
        self.settings.subdivisions = self.subdivision_spin.value()
        
        self.grid_changed.emit(self.settings)
    
    def set_settings(self, settings: GridSettings):
        """Set settings from external source."""
        self.settings = settings
        
        # Update UI controls
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == settings.grid_type:
                self.type_combo.setCurrentIndex(i)
                break
        
        self.spacing_x_spin.setValue(settings.spacing_x)
        self.spacing_y_spin.setValue(settings.spacing_y)
        self.snap_checkbox.setChecked(settings.snap_enabled)
        self.subdivision_checkbox.setChecked(settings.show_subdivisions)
        self.subdivision_spin.setValue(settings.subdivisions)


def main():
    """Test the advanced grid system."""
    if not PYQT5_AVAILABLE:
        print("PyQt5 not available")
        return
    
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    # Create test window
    window = QMainWindow()
    window.setWindowTitle("Advanced Grid System Test")
    window.setGeometry(100, 100, 800, 600)
    
    # Central widget
    central_widget = QWidget()
    layout = QHBoxLayout()
    
    # Grid control widget
    grid_control = GridControlWidget()
    layout.addWidget(grid_control)
    
    # Grid display widget
    class GridDisplayWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.grid = AdvancedGrid()
            self.grid.set_canvas_size(400, 400)
            self.setMinimumSize(400, 400)
        
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(30, 30, 30))
            self.grid.paint_grid(painter)
    
    grid_display = GridDisplayWidget()
    layout.addWidget(grid_display)
    
    # Connect grid control to display
    def update_grid(settings):
        grid_display.grid.set_settings(settings)
        grid_display.update()
    
    grid_control.grid_changed.connect(update_grid)
    
    central_widget.setLayout(layout)
    window.setCentralWidget(central_widget)
    
    window.show()
    
    # Print grid info
    info = grid_display.grid.get_grid_info()
    print(f"Grid system initialized: {info}")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()