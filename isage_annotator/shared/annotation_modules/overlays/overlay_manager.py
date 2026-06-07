"""
Advanced Overlay Management System

Provides sophisticated overlay management for annotation interfaces.
Supports layered overlays, blending modes, and interactive control.
Part of the modular annotation system.
"""

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, 
        QSlider, QComboBox, QPushButton, QListWidget, QListWidgetItem,
        QFrame, QSpinBox, QColorDialog
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QObject, QRect
    from PyQt5.QtGui import (
        QPainter, QColor, QPen, QBrush, QPixmap, QImage, 
        QPainterPath, QLinearGradient, QRadialGradient
    )
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    class QObject: pass
    class QWidget: pass
    class pyqtSignal: 
        def __init__(self, *args): pass

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import uuid


class BlendMode(Enum):
    """Overlay blending modes."""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft_light"
    HARD_LIGHT = "hard_light"
    COLOR_DODGE = "color_dodge"
    COLOR_BURN = "color_burn"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    DIFFERENCE = "difference"
    EXCLUSION = "exclusion"


class OverlayType(Enum):
    """Types of overlays."""
    ANNOTATIONS = "annotations"
    PREDICTIONS = "predictions"
    CONFIDENCE = "confidence"
    GRID = "grid"
    MISTAKES = "mistakes"
    REGIONS = "regions"
    MEASUREMENTS = "measurements"
    CUSTOM = "custom"


@dataclass
class OverlaySettings:
    """Settings for an overlay."""
    overlay_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Unnamed Overlay"
    overlay_type: OverlayType = OverlayType.CUSTOM
    visible: bool = True
    opacity: float = 1.0
    blend_mode: BlendMode = BlendMode.NORMAL
    z_order: int = 0
    color_tint: QColor = field(default_factory=lambda: QColor(255, 255, 255, 255))
    locked: bool = False
    
    # Animation settings
    animated: bool = False
    animation_speed: float = 1.0
    animation_direction: int = 1  # 1 for forward, -1 for reverse
    
    # Interaction settings
    interactive: bool = True
    selectable: bool = True
    
    def __post_init__(self):
        if isinstance(self.color_tint, tuple):
            self.color_tint = QColor(*self.color_tint)


class OverlayRenderer(ABC):
    """Abstract base class for overlay renderers."""
    
    @abstractmethod
    def render(self, painter: QPainter, rect: QRect, settings: OverlaySettings, **kwargs):
        """Render the overlay content."""
        pass
    
    @abstractmethod
    def get_bounds(self) -> QRect:
        """Get the bounding rectangle of the overlay content."""
        pass
    
    def is_point_inside(self, point: Tuple[int, int]) -> bool:
        """Check if a point is inside the overlay."""
        x, y = point
        bounds = self.get_bounds()
        return bounds.contains(x, y)


class ImageOverlayRenderer(OverlayRenderer):
    """Renderer for image-based overlays."""
    
    def __init__(self, image: QImage):
        self.image = image
    
    def render(self, painter: QPainter, rect: QRect, settings: OverlaySettings, **kwargs):
        if self.image.isNull():
            return
        
        painter.save()
        
        # Apply opacity
        painter.setOpacity(settings.opacity)
        
        # Apply color tint
        if settings.color_tint != QColor(255, 255, 255, 255):
            # Create tinted version (simplified)
            painter.setCompositionMode(QPainter.CompositionMode_Multiply)
            painter.fillRect(rect, settings.color_tint)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        
        # Draw image
        painter.drawImage(rect, self.image)
        
        painter.restore()
    
    def get_bounds(self) -> QRect:
        return self.image.rect()
    
    def set_image(self, image: QImage):
        """Update the image."""
        self.image = image


class VectorOverlayRenderer(OverlayRenderer):
    """Renderer for vector-based overlays."""
    
    def __init__(self):
        self.shapes = []  # List of (shape_type, data, style)
    
    def add_rectangle(self, rect: QRect, pen: QPen = None, brush: QBrush = None):
        """Add a rectangle to the overlay."""
        self.shapes.append(("rectangle", rect, {"pen": pen, "brush": brush}))
    
    def add_circle(self, center: Tuple[int, int], radius: int, pen: QPen = None, brush: QBrush = None):
        """Add a circle to the overlay."""
        self.shapes.append(("circle", (center, radius), {"pen": pen, "brush": brush}))
    
    def add_path(self, path: QPainterPath, pen: QPen = None, brush: QBrush = None):
        """Add a painter path to the overlay."""
        self.shapes.append(("path", path, {"pen": pen, "brush": brush}))
    
    def clear(self):
        """Clear all shapes."""
        self.shapes.clear()
    
    def render(self, painter: QPainter, rect: QRect, settings: OverlaySettings, **kwargs):
        painter.save()
        
        # Apply opacity
        painter.setOpacity(settings.opacity)
        
        for shape_type, data, style in self.shapes:
            # Apply style
            if style.get("pen"):
                painter.setPen(style["pen"])
            if style.get("brush"):
                painter.setBrush(style["brush"])
            
            # Draw shape
            if shape_type == "rectangle":
                painter.drawRect(data)
            elif shape_type == "circle":
                center, radius = data
                painter.drawEllipse(center[0] - radius, center[1] - radius, 
                                  radius * 2, radius * 2)
            elif shape_type == "path":
                painter.drawPath(data)
        
        painter.restore()
    
    def get_bounds(self) -> QRect:
        if not self.shapes:
            return QRect()
        
        # Calculate bounding box of all shapes
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for shape_type, data, style in self.shapes:
            if shape_type == "rectangle":
                rect = data
                min_x = min(min_x, rect.x())
                min_y = min(min_y, rect.y())
                max_x = max(max_x, rect.x() + rect.width())
                max_y = max(max_y, rect.y() + rect.height())
            elif shape_type == "circle":
                center, radius = data
                min_x = min(min_x, center[0] - radius)
                min_y = min(min_y, center[1] - radius)
                max_x = max(max_x, center[0] + radius)
                max_y = max(max_y, center[1] + radius)
            elif shape_type == "path":
                bounds = data.boundingRect()
                min_x = min(min_x, bounds.x())
                min_y = min(min_y, bounds.y())
                max_x = max(max_x, bounds.x() + bounds.width())
                max_y = max(max_y, bounds.y() + bounds.height())
        
        if min_x == float('inf'):
            return QRect()
        
        return QRect(int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y))


class FunctionOverlayRenderer(OverlayRenderer):
    """Renderer for function-based overlays."""
    
    def __init__(self, render_function: Callable[[QPainter, QRect, OverlaySettings], None]):
        self.render_function = render_function
        self._bounds = QRect()
    
    def render(self, painter: QPainter, rect: QRect, settings: OverlaySettings, **kwargs):
        painter.save()
        painter.setOpacity(settings.opacity)
        
        try:
            self.render_function(painter, rect, settings)
        except Exception as e:
            # Handle rendering errors gracefully
            print(f"Overlay rendering error: {e}")
        
        painter.restore()
    
    def get_bounds(self) -> QRect:
        return self._bounds
    
    def set_bounds(self, bounds: QRect):
        """Set the bounds for this overlay."""
        self._bounds = bounds


class Overlay:
    """
    Individual overlay with renderer and settings.
    
    Features:
    - Configurable rendering
    - Blending modes
    - Animation support
    - Interaction handling
    """
    
    def __init__(self, renderer: OverlayRenderer, settings: OverlaySettings = None):
        self.renderer = renderer
        self.settings = settings or OverlaySettings()
        self._animation_time = 0.0
    
    def render(self, painter: QPainter, canvas_rect: QRect):
        """Render the overlay."""
        if not self.settings.visible:
            return
        
        # Apply animation if enabled
        if self.settings.animated:
            self._update_animation()
        
        # Set blend mode
        self._set_blend_mode(painter, self.settings.blend_mode)
        
        # Render content
        self.renderer.render(painter, canvas_rect, self.settings)
    
    def _set_blend_mode(self, painter: QPainter, blend_mode: BlendMode):
        """Set the painter blend mode."""
        mode_map = {
            BlendMode.NORMAL: QPainter.CompositionMode_SourceOver,
            BlendMode.MULTIPLY: QPainter.CompositionMode_Multiply,
            BlendMode.SCREEN: QPainter.CompositionMode_Screen,
            BlendMode.OVERLAY: QPainter.CompositionMode_Overlay,
            BlendMode.SOFT_LIGHT: QPainter.CompositionMode_SoftLight,
            BlendMode.HARD_LIGHT: QPainter.CompositionMode_HardLight,
            BlendMode.COLOR_DODGE: QPainter.CompositionMode_ColorDodge,
            BlendMode.COLOR_BURN: QPainter.CompositionMode_ColorBurn,
            BlendMode.DARKEN: QPainter.CompositionMode_Darken,
            BlendMode.LIGHTEN: QPainter.CompositionMode_Lighten,
            BlendMode.DIFFERENCE: QPainter.CompositionMode_Difference,
            BlendMode.EXCLUSION: QPainter.CompositionMode_Exclusion,
        }
        
        composition_mode = mode_map.get(blend_mode, QPainter.CompositionMode_SourceOver)
        painter.setCompositionMode(composition_mode)
    
    def _update_animation(self):
        """Update animation state."""
        self._animation_time += 0.016 * self.settings.animation_speed  # Assume 60 FPS
        
        # Simple pulsing opacity animation
        if self.settings.animated:
            base_opacity = self.settings.opacity
            pulse = 0.5 + 0.5 * np.sin(self._animation_time * 2 * np.pi)
            self.settings.opacity = base_opacity * (0.5 + 0.5 * pulse)
    
    def is_point_inside(self, point: Tuple[int, int]) -> bool:
        """Check if a point is inside this overlay."""
        if not self.settings.visible or not self.settings.interactive:
            return False
        
        return self.renderer.is_point_inside(point)
    
    def get_bounds(self) -> QRect:
        """Get overlay bounds."""
        return self.renderer.get_bounds()


class OverlayManager(QObject):
    """
    Advanced overlay management system.
    
    Features:
    - Layer management with z-ordering
    - Blending modes and opacity control
    - Animation support
    - Interactive overlay selection
    - Batch operations
    - Performance optimization
    """
    
    overlay_added = pyqtSignal(str)  # overlay_id
    overlay_removed = pyqtSignal(str)  # overlay_id
    overlay_changed = pyqtSignal(str)  # overlay_id
    selection_changed = pyqtSignal(list)  # list of overlay_ids
    
    def __init__(self):
        super().__init__()
        self.overlays: Dict[str, Overlay] = {}
        self.overlay_order: List[str] = []  # Z-order (bottom to top)
        self.selected_overlays: List[str] = []
        self.enabled = True
        
        # Performance settings
        self.use_caching = True
        self.max_cache_size = 50
        self._render_cache = {}
    
    def add_overlay(self, overlay: Overlay, name: str = None) -> str:
        """Add an overlay to the manager."""
        overlay_id = overlay.settings.overlay_id
        
        if name:
            overlay.settings.name = name
        
        self.overlays[overlay_id] = overlay
        
        # Insert in correct z-order position
        self._insert_in_z_order(overlay_id, overlay.settings.z_order)
        
        self.overlay_added.emit(overlay_id)
        return overlay_id
    
    def remove_overlay(self, overlay_id: str) -> bool:
        """Remove an overlay from the manager."""
        if overlay_id not in self.overlays:
            return False
        
        del self.overlays[overlay_id]
        self.overlay_order.remove(overlay_id)
        
        if overlay_id in self.selected_overlays:
            self.selected_overlays.remove(overlay_id)
        
        # Clear cache entries for this overlay
        keys_to_remove = [k for k in self._render_cache.keys() if overlay_id in k]
        for key in keys_to_remove:
            del self._render_cache[key]
        
        self.overlay_removed.emit(overlay_id)
        return True
    
    def get_overlay(self, overlay_id: str) -> Optional[Overlay]:
        """Get an overlay by ID."""
        return self.overlays.get(overlay_id)
    
    def get_overlay_by_name(self, name: str) -> Optional[Overlay]:
        """Get an overlay by name."""
        for overlay in self.overlays.values():
            if overlay.settings.name == name:
                return overlay
        return None
    
    def set_overlay_visibility(self, overlay_id: str, visible: bool):
        """Set overlay visibility."""
        if overlay_id in self.overlays:
            self.overlays[overlay_id].settings.visible = visible
            self.overlay_changed.emit(overlay_id)
    
    def set_overlay_opacity(self, overlay_id: str, opacity: float):
        """Set overlay opacity."""
        if overlay_id in self.overlays:
            self.overlays[overlay_id].settings.opacity = max(0.0, min(1.0, opacity))
            self.overlay_changed.emit(overlay_id)
    
    def set_overlay_z_order(self, overlay_id: str, z_order: int):
        """Set overlay z-order."""
        if overlay_id in self.overlays:
            overlay = self.overlays[overlay_id]
            overlay.settings.z_order = z_order
            
            # Reposition in order list
            self.overlay_order.remove(overlay_id)
            self._insert_in_z_order(overlay_id, z_order)
            
            self.overlay_changed.emit(overlay_id)
    
    def _insert_in_z_order(self, overlay_id: str, z_order: int):
        """Insert overlay in correct z-order position."""
        inserted = False
        for i, existing_id in enumerate(self.overlay_order):
            existing_overlay = self.overlays[existing_id]
            if z_order < existing_overlay.settings.z_order:
                self.overlay_order.insert(i, overlay_id)
                inserted = True
                break
        
        if not inserted:
            self.overlay_order.append(overlay_id)
    
    def render_all_overlays(self, painter: QPainter, canvas_rect: QRect):
        """Render all visible overlays in z-order."""
        if not self.enabled:
            return
        
        painter.save()
        
        # Render overlays in z-order (bottom to top)
        for overlay_id in self.overlay_order:
            overlay = self.overlays[overlay_id]
            
            if overlay.settings.visible and not overlay.settings.locked:
                overlay.render(painter, canvas_rect)
        
        painter.restore()
    
    def find_overlays_at_point(self, point: Tuple[int, int]) -> List[str]:
        """Find all overlays that contain the given point."""
        overlays_at_point = []
        
        # Check in reverse z-order (top to bottom) for interaction
        for overlay_id in reversed(self.overlay_order):
            overlay = self.overlays[overlay_id]
            
            if overlay.is_point_inside(point):
                overlays_at_point.append(overlay_id)
        
        return overlays_at_point
    
    def select_overlay(self, overlay_id: str, multi_select: bool = False):
        """Select an overlay."""
        if overlay_id not in self.overlays:
            return
        
        overlay = self.overlays[overlay_id]
        if not overlay.settings.selectable:
            return
        
        if not multi_select:
            self.selected_overlays.clear()
        
        if overlay_id not in self.selected_overlays:
            self.selected_overlays.append(overlay_id)
        
        self.selection_changed.emit(self.selected_overlays.copy())
    
    def deselect_overlay(self, overlay_id: str):
        """Deselect an overlay."""
        if overlay_id in self.selected_overlays:
            self.selected_overlays.remove(overlay_id)
            self.selection_changed.emit(self.selected_overlays.copy())
    
    def clear_selection(self):
        """Clear all selections."""
        if self.selected_overlays:
            self.selected_overlays.clear()
            self.selection_changed.emit([])
    
    def get_overlay_list(self) -> List[Dict[str, Any]]:
        """Get list of all overlays with their info."""
        overlay_list = []
        
        for overlay_id in self.overlay_order:
            overlay = self.overlays[overlay_id]
            overlay_info = {
                "id": overlay_id,
                "name": overlay.settings.name,
                "type": overlay.settings.overlay_type.value,
                "visible": overlay.settings.visible,
                "opacity": overlay.settings.opacity,
                "z_order": overlay.settings.z_order,
                "locked": overlay.settings.locked,
                "selected": overlay_id in self.selected_overlays
            }
            overlay_list.append(overlay_info)
        
        return overlay_list
    
    def batch_set_opacity(self, overlay_ids: List[str], opacity: float):
        """Set opacity for multiple overlays."""
        for overlay_id in overlay_ids:
            self.set_overlay_opacity(overlay_id, opacity)
    
    def batch_set_visibility(self, overlay_ids: List[str], visible: bool):
        """Set visibility for multiple overlays."""
        for overlay_id in overlay_ids:
            self.set_overlay_visibility(overlay_id, visible)
    
    def clear_all_overlays(self):
        """Remove all overlays."""
        overlay_ids = list(self.overlays.keys())
        for overlay_id in overlay_ids:
            self.remove_overlay(overlay_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overlay manager statistics."""
        visible_count = sum(1 for overlay in self.overlays.values() if overlay.settings.visible)
        animated_count = sum(1 for overlay in self.overlays.values() if overlay.settings.animated)
        
        type_counts = {}
        for overlay in self.overlays.values():
            overlay_type = overlay.settings.overlay_type.value
            type_counts[overlay_type] = type_counts.get(overlay_type, 0) + 1
        
        return {
            "total_overlays": len(self.overlays),
            "visible_overlays": visible_count,
            "animated_overlays": animated_count,
            "selected_overlays": len(self.selected_overlays),
            "type_distribution": type_counts,
            "cache_size": len(self._render_cache)
        }


class OverlayControlWidget(QWidget):
    """
    Control widget for overlay management.
    
    Features:
    - Overlay list with visibility toggles
    - Opacity controls
    - Z-order management
    - Blend mode selection
    - Batch operations
    """
    
    def __init__(self, overlay_manager: OverlayManager, parent=None):
        super().__init__(parent)
        self.overlay_manager = overlay_manager
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the control UI."""
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("🎨 Overlay Manager")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 4px;")
        layout.addWidget(header_label)
        
        # Overlay list
        self.overlay_list = QListWidget()
        self.overlay_list.setMaximumHeight(200)
        layout.addWidget(self.overlay_list)
        
        # Controls frame
        controls_frame = QFrame()
        controls_layout = QVBoxLayout(controls_frame)
        
        # Opacity control
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel("100%")
        opacity_layout.addWidget(self.opacity_label)
        
        controls_layout.addLayout(opacity_layout)
        
        # Blend mode
        blend_layout = QHBoxLayout()
        blend_layout.addWidget(QLabel("Blend:"))
        
        self.blend_combo = QComboBox()
        for blend_mode in BlendMode:
            self.blend_combo.addItem(blend_mode.value.title(), blend_mode)
        blend_layout.addWidget(self.blend_combo)
        
        controls_layout.addLayout(blend_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)
        
        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.setEnabled(False)
        button_layout.addWidget(self.duplicate_btn)
        
        controls_layout.addLayout(button_layout)
        
        layout.addWidget(controls_frame)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect UI signals."""
        self.overlay_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.blend_combo.currentIndexChanged.connect(self._on_blend_mode_changed)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        
        # Connect overlay manager signals
        self.overlay_manager.overlay_added.connect(self._refresh_overlay_list)
        self.overlay_manager.overlay_removed.connect(self._refresh_overlay_list)
        self.overlay_manager.overlay_changed.connect(self._refresh_overlay_list)
    
    def _refresh_overlay_list(self):
        """Refresh the overlay list display."""
        self.overlay_list.clear()
        
        overlay_list = self.overlay_manager.get_overlay_list()
        for overlay_info in reversed(overlay_list):  # Show in reverse z-order
            item = QListWidgetItem(f"{overlay_info['name']} ({overlay_info['type']})")
            item.setData(Qt.UserRole, overlay_info['id'])
            
            # Set item appearance based on overlay state
            if not overlay_info['visible']:
                item.setForeground(QColor(150, 150, 150))
            if overlay_info['locked']:
                item.setIcon(self.style().standardIcon(self.style().SP_BrowserStop))
            
            self.overlay_list.addItem(item)
    
    def _on_selection_changed(self):
        """Handle overlay selection change."""
        selected_items = self.overlay_list.selectedItems()
        has_selection = len(selected_items) > 0
        
        self.delete_btn.setEnabled(has_selection)
        self.duplicate_btn.setEnabled(len(selected_items) == 1)
        
        if has_selection:
            # Update controls for first selected overlay
            item = selected_items[0]
            overlay_id = item.data(Qt.UserRole)
            overlay = self.overlay_manager.get_overlay(overlay_id)
            
            if overlay:
                self.opacity_slider.setValue(int(overlay.settings.opacity * 100))
                self.opacity_label.setText(f"{int(overlay.settings.opacity * 100)}%")
                
                # Set blend mode
                for i in range(self.blend_combo.count()):
                    if self.blend_combo.itemData(i) == overlay.settings.blend_mode:
                        self.blend_combo.setCurrentIndex(i)
                        break
    
    def _on_opacity_changed(self, value):
        """Handle opacity slider change."""
        selected_items = self.overlay_list.selectedItems()
        if not selected_items:
            return
        
        opacity = value / 100.0
        self.opacity_label.setText(f"{value}%")
        
        for item in selected_items:
            overlay_id = item.data(Qt.UserRole)
            self.overlay_manager.set_overlay_opacity(overlay_id, opacity)
    
    def _on_blend_mode_changed(self, index):
        """Handle blend mode change."""
        selected_items = self.overlay_list.selectedItems()
        if not selected_items:
            return
        
        blend_mode = self.blend_combo.itemData(index)
        
        for item in selected_items:
            overlay_id = item.data(Qt.UserRole)
            overlay = self.overlay_manager.get_overlay(overlay_id)
            if overlay:
                overlay.settings.blend_mode = blend_mode
                self.overlay_manager.overlay_changed.emit(overlay_id)
    
    def _on_delete_clicked(self):
        """Handle delete button click."""
        selected_items = self.overlay_list.selectedItems()
        
        for item in selected_items:
            overlay_id = item.data(Qt.UserRole)
            self.overlay_manager.remove_overlay(overlay_id)


def main():
    """Test the overlay management system."""
    if not PYQT5_AVAILABLE:
        print("PyQt5 not available")
        return
    
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    # Create test window
    window = QMainWindow()
    window.setWindowTitle("Overlay Manager Test")
    window.setGeometry(100, 100, 1000, 600)
    
    # Create overlay manager
    overlay_manager = OverlayManager()
    
    # Create test overlays
    # Image overlay
    test_image = QImage(100, 100, QImage.Format_ARGB32)
    test_image.fill(QColor(255, 0, 0, 128))
    image_renderer = ImageOverlayRenderer(test_image)
    image_overlay = Overlay(image_renderer, OverlaySettings(name="Test Image", overlay_type=OverlayType.ANNOTATIONS))
    overlay_manager.add_overlay(image_overlay)
    
    # Vector overlay
    vector_renderer = VectorOverlayRenderer()
    vector_renderer.add_rectangle(QRect(50, 50, 100, 100), QPen(QColor(0, 255, 0), 2))
    vector_renderer.add_circle((150, 150), 30, QPen(QColor(0, 0, 255), 2))
    vector_overlay = Overlay(vector_renderer, OverlaySettings(name="Vector Shapes", overlay_type=OverlayType.REGIONS, z_order=1))
    overlay_manager.add_overlay(vector_overlay)
    
    # Central widget
    central_widget = QWidget()
    layout = QHBoxLayout()
    
    # Control widget
    control_widget = OverlayControlWidget(overlay_manager)
    layout.addWidget(control_widget)
    
    # Display widget
    class OverlayDisplayWidget(QWidget):
        def __init__(self, manager):
            super().__init__()
            self.manager = manager
            self.setMinimumSize(400, 400)
        
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(50, 50, 50))
            
            # Render all overlays
            self.manager.render_all_overlays(painter, self.rect())
    
    display_widget = OverlayDisplayWidget(overlay_manager)
    layout.addWidget(display_widget)
    
    # Connect signals for updates
    overlay_manager.overlay_changed.connect(display_widget.update)
    overlay_manager.overlay_added.connect(display_widget.update)
    overlay_manager.overlay_removed.connect(display_widget.update)
    
    central_widget.setLayout(layout)
    window.setCentralWidget(central_widget)
    
    window.show()
    
    # Print statistics
    stats = overlay_manager.get_statistics()
    print(f"Overlay manager statistics: {stats}")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()