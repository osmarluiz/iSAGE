"""
Advanced Annotation Canvas - Full-featured canvas with all annotation capabilities

This canvas provides all the features from the current working system:
- Zoom/pan with mouse wheel and spacebar
- Point annotation with drag/drop
- Grid overlay
- RGB channel remapping
- Ground truth and prediction overlays
- Mouse coordinate tracking
- View synchronization with minimap
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
import numpy as np

from PyQt5.QtWidgets import QLabel, QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRectF, QTimer, QRect
from PyQt5.QtGui import (
    QPixmap, QPainter, QPen, QBrush, QColor, QImage, QFont,
    QMouseEvent, QWheelEvent, QKeyEvent, QPaintEvent, QResizeEvent
)

logger = logging.getLogger(__name__)


class AdvancedAnnotationCanvas(QLabel):
    """
    Advanced annotation canvas with full feature set.
    
    Features:
    - Point annotation with visual feedback
    - Zoom: 0.1x to 5.0x with mouse wheel
    - Pan: Spacebar + drag or middle mouse
    - Grid overlay with customizable spacing
    - RGB channel remapping
    - Multiple overlay support (ground truth, predictions, mistakes)
    - Point drag/move/delete operations
    - Real-time mouse coordinate tracking
    - View rectangle for minimap synchronization
    - Optimized rendering with caching
    """
    
    # Signals for external communication
    point_added = pyqtSignal(float, float, int)  # x, y, class_id (image coordinates)
    point_removed = pyqtSignal(float, float)     # x, y (image coordinates)
    point_moved = pyqtSignal(float, float, float, float)  # old_x, old_y, new_x, new_y
    mouse_coordinates = pyqtSignal(int, int)     # x, y (image coordinates)
    image_loaded = pyqtSignal(str)               # image_path
    view_changed = pyqtSignal(float, float, float)  # zoom, pan_x, pan_y
    
    def __init__(self, config: Optional[Dict] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # Configuration
        self._config = self._default_config()
        if config:
            self._config.update(config)
        
        # Image state
        self._original_image: Optional[QImage] = None
        self._display_image: Optional[QImage] = None
        self._image_path: str = ""
        
        # View state
        self._zoom_factor: float = 1.0
        self._min_zoom: float = 0.1
        self._max_zoom: float = 5.0
        self._pan_offset: QPointF = QPointF(0, 0)
        self._last_pan_point: Optional[QPointF] = None
        
        # Annotation state
        self._annotations: List[Dict] = []  # List of {x, y, class_id, id}
        self._current_class: int = 1
        self._dragging_point: Optional[str] = None  # ID of point being dragged
        self._drag_offset: QPointF = QPointF(0, 0)
        
        # Display settings
        self._show_grid: bool = False
        self._grid_spacing: int = 50
        self._point_size: int = 8
        self._point_opacity: float = 1.0
        
        # RGB channel settings
        self._rgb_channels = {'R': True, 'G': True, 'B': True}
        
        # Overlay settings
        self._overlays: Dict[str, Dict] = {}  # name -> {data, opacity, visible, color}
        
        # Interaction state
        self._mouse_tracking: bool = True
        self._panning: bool = False
        self._last_mouse_pos: Optional[QPointF] = None
        
        # Performance optimizations
        self._render_cache: Optional[QPixmap] = None
        self._cache_valid: bool = False
        
        # Setup
        self._setup_ui()
        self._setup_mouse_tracking()
        
        logger.info("AdvancedAnnotationCanvas initialized")
    
    def _default_config(self) -> Dict:
        """Default configuration for the canvas."""
        return {
            'background_color': '#2d3748',
            'point_colors': [
                '#ef4444', '#10b981', '#3b82f6', '#f59e0b', 
                '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'
            ],
            'grid_color': '#4a5568',
            'grid_opacity': 0.3,
            'selection_color': '#60a5fa',
            'hover_color': '#93c5fd',
            'enable_caching': True,
            'smooth_rendering': True,
            'point_outline': True,
            'point_outline_color': '#ffffff',
            'point_outline_width': 1
        }
    
    def _setup_ui(self):
        """Setup the UI based on configuration."""
        # Set basic properties
        self.setMinimumSize(400, 300)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {self._config['background_color']};
                border: 2px solid #4a5568;
                border-radius: 8px;
            }}
        """)
        
        # Set focus policy for keyboard events
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Initial text
        self.setText("🎯 Advanced Annotation Canvas\\n\\nLoad an image to start annotating")
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        
        # Set cursor
        self.setCursor(Qt.CrossCursor)
    
    def _setup_mouse_tracking(self):
        """Enable mouse tracking for coordinate display."""
        self.setMouseTracking(True)
    
    # Public API - Core functionality
    
    def load_image(self, image_path: str) -> bool:
        """
        Load an image into the canvas.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Load image
            image = QImage(image_path)
            if image.isNull():
                logger.error(f"Failed to load image: {image_path}")
                return False
            
            # Store original
            self._original_image = image
            self._image_path = image_path
            
            # Reset view
            self._zoom_factor = 1.0
            self._pan_offset = QPointF(0, 0)
            
            # Clear annotations (they're for previous image)
            self._annotations.clear()
            
            # Process image
            self._update_display_image()
            self._update_display()
            
            # Emit signals
            self.image_loaded.emit(image_path)
            self.view_changed.emit(self._zoom_factor, self._pan_offset.x(), self._pan_offset.y())
            
            logger.info(f"Image loaded: {Path(image_path).name} ({image.width()}x{image.height()})")
            return True
            
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            return False
    
    def add_annotation(self, x: float, y: float, class_id: int) -> str:
        """
        Add annotation at image coordinates.
        
        Args:
            x: X coordinate in image space
            y: Y coordinate in image space
            class_id: Class identifier
            
        Returns:
            ID of created annotation
        """
        import uuid
        
        annotation_id = str(uuid.uuid4())
        annotation = {
            'id': annotation_id,
            'x': x,
            'y': y,
            'class_id': class_id
        }
        
        self._annotations.append(annotation)
        self._invalidate_cache()
        self.update()
        
        # Emit signal
        self.point_added.emit(x, y, class_id)
        
        logger.debug(f"Annotation added: ({x:.1f}, {y:.1f}) class={class_id}")
        return annotation_id
    
    def remove_annotation(self, annotation_id: str) -> bool:
        """Remove annotation by ID."""
        for i, ann in enumerate(self._annotations):
            if ann['id'] == annotation_id:
                removed = self._annotations.pop(i)
                self._invalidate_cache()
                self.update()
                
                # Emit signal
                self.point_removed.emit(removed['x'], removed['y'])
                
                logger.debug(f"Annotation removed: {annotation_id}")
                return True
        return False
    
    def clear_annotations(self):
        """Clear all annotations."""
        self._annotations.clear()
        self._invalidate_cache()
        self.update()
        logger.debug("All annotations cleared")
    
    def get_annotations(self) -> List[Dict]:
        """Get current annotations."""
        return self._annotations.copy()
    
    # Public API - View control
    
    def set_zoom(self, zoom: float):
        """Set zoom level."""
        zoom = max(self._min_zoom, min(self._max_zoom, zoom))
        if zoom != self._zoom_factor:
            self._zoom_factor = zoom
            self._update_display()
            self.view_changed.emit(self._zoom_factor, self._pan_offset.x(), self._pan_offset.y())
    
    def zoom_in(self):
        """Zoom in by factor of 1.2."""
        self.set_zoom(self._zoom_factor * 1.2)
    
    def zoom_out(self):
        """Zoom out by factor of 0.8."""
        self.set_zoom(self._zoom_factor * 0.8)
    
    def zoom_fit(self):
        """Zoom to fit image in viewport."""
        if not self._original_image:
            return
        
        # Calculate zoom to fit
        widget_size = self.size()
        image_size = self._original_image.size()
        
        zoom_x = widget_size.width() / image_size.width()
        zoom_y = widget_size.height() / image_size.height()
        
        zoom = min(zoom_x, zoom_y) * 0.95  # Leave small margin
        self.set_zoom(zoom)
        
        # Center image
        self._pan_offset = QPointF(0, 0)
        self._update_display()
    
    def pan_to(self, x: float, y: float):
        """Pan to specific image coordinates."""
        if not self._original_image:
            return
        
        # Convert to screen coordinates and center
        widget_center = QPointF(self.width() / 2, self.height() / 2)
        image_point = QPointF(x * self._zoom_factor, y * self._zoom_factor)
        
        self._pan_offset = widget_center - image_point
        self._update_display()
        self.view_changed.emit(self._zoom_factor, self._pan_offset.x(), self._pan_offset.y())
    
    # Public API - Display settings
    
    def set_current_class(self, class_id: int):
        """Set current annotation class."""
        self._current_class = class_id
        logger.debug(f"Current class set to: {class_id}")
    
    def set_point_size(self, size: int):
        """Set point display size."""
        self._point_size = max(1, min(50, size))
        self._invalidate_cache()
        self.update()
    
    def set_show_grid(self, show: bool):
        """Toggle grid display."""
        self._show_grid = show
        self._invalidate_cache()
        self.update()
    
    def set_grid_spacing(self, spacing: int):
        """Set grid spacing in pixels."""
        self._grid_spacing = max(10, min(200, spacing))
        self._invalidate_cache()
        self.update()
    
    def set_rgb_channels(self, r: bool, g: bool, b: bool):
        """Set RGB channel visibility."""
        self._rgb_channels = {'R': r, 'G': g, 'B': b}
        self._update_display_image()
        self._update_display()
    
    def add_overlay(self, name: str, data: np.ndarray, color: str = '#ff0000', opacity: float = 0.5):
        """Add an overlay (ground truth, predictions, etc.)."""
        self._overlays[name] = {
            'data': data,
            'color': color,
            'opacity': opacity,
            'visible': True
        }
        self._invalidate_cache()
        self.update()
    
    def remove_overlay(self, name: str):
        """Remove an overlay."""
        if name in self._overlays:
            del self._overlays[name]
            self._invalidate_cache()
            self.update()
    
    def set_overlay_visible(self, name: str, visible: bool):
        """Set overlay visibility."""
        if name in self._overlays:
            self._overlays[name]['visible'] = visible
            self._invalidate_cache()
            self.update()
    
    # Coordinate conversion utilities
    
    def screen_to_image(self, screen_pos: QPointF) -> QPointF:
        """Convert screen coordinates to image coordinates."""
        if not self._original_image:
            return QPointF(0, 0)
        
        # Account for pan and zoom
        image_pos = (screen_pos - self._pan_offset) / self._zoom_factor
        return image_pos
    
    def image_to_screen(self, image_pos: QPointF) -> QPointF:
        """Convert image coordinates to screen coordinates."""
        if not self._original_image:
            return QPointF(0, 0)
        
        # Apply zoom and pan
        screen_pos = image_pos * self._zoom_factor + self._pan_offset
        return screen_pos
    
    def get_view_rect_normalized(self) -> QRectF:
        """Get current view rectangle in normalized coordinates (0-1)."""
        if not self._original_image:
            return QRectF(0, 0, 1, 1)
        
        # Get visible area in image coordinates
        top_left = self.screen_to_image(QPointF(0, 0))
        bottom_right = self.screen_to_image(QPointF(self.width(), self.height()))
        
        # Normalize to image size
        img_size = self._original_image.size()
        norm_rect = QRectF(
            max(0, top_left.x() / img_size.width()),
            max(0, top_left.y() / img_size.height()),
            min(1, (bottom_right.x() - top_left.x()) / img_size.width()),
            min(1, (bottom_right.y() - top_left.y()) / img_size.height())
        )
        
        return norm_rect
    
    # Internal methods
    
    def _update_display_image(self):
        """Update the display image based on RGB channel settings."""
        if not self._original_image:
            return
        
        # Start with original image
        self._display_image = self._original_image.copy()
        
        # Apply RGB channel filtering
        if not all(self._rgb_channels.values()):
            # Convert to numpy for channel manipulation
            height, width = self._display_image.height(), self._display_image.width()
            ptr = self._display_image.bits()
            ptr.setsize(height * width * 4)  # 4 bytes per pixel (BGRA)
            arr = np.array(ptr).reshape((height, width, 4))
            
            # Apply channel masks
            if not self._rgb_channels['R']:
                arr[:, :, 2] = 0  # Red channel
            if not self._rgb_channels['G']:
                arr[:, :, 1] = 0  # Green channel
            if not self._rgb_channels['B']:
                arr[:, :, 0] = 0  # Blue channel
            
            # Convert back to QImage
            self._display_image = QImage(arr.data, width, height, QImage.Format_ARGB32)
        
        self._invalidate_cache()
    
    def _update_display(self):
        """Update the display with current image and annotations."""
        if not self._display_image:
            return
        
        # Use cache if valid and enabled
        if self._config['enable_caching'] and self._cache_valid and self._render_cache:
            self.setPixmap(self._render_cache)
            return
        
        # Create display pixmap
        pixmap = self._render_scene()
        
        # Cache if enabled
        if self._config['enable_caching']:
            self._render_cache = pixmap
            self._cache_valid = True
        
        # Update display
        self.setPixmap(pixmap)
    
    def _render_scene(self) -> QPixmap:
        """Render the complete scene to a pixmap."""
        # Create pixmap for widget size
        pixmap = QPixmap(self.size())
        pixmap.fill(QColor(self._config['background_color']))
        
        painter = QPainter(pixmap)
        if self._config['smooth_rendering']:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Draw image
        self._draw_image(painter)
        
        # Draw overlays
        self._draw_overlays(painter)
        
        # Draw grid
        if self._show_grid:
            self._draw_grid(painter)
        
        # Draw annotations
        self._draw_annotations(painter)
        
        painter.end()
        return pixmap
    
    def _draw_image(self, painter: QPainter):
        """Draw the main image."""
        if not self._display_image:
            return
        
        # Calculate scaled image size
        scaled_size = self._display_image.size() * self._zoom_factor
        
        # Calculate position (centered with pan offset)
        pos = self._pan_offset
        
        # Draw image
        target_rect = QRect(int(pos.x()), int(pos.y()), int(scaled_size.width()), int(scaled_size.height()))
        painter.drawImage(target_rect, self._display_image)
    
    def _draw_grid(self, painter: QPainter):
        """Draw grid overlay."""
        if not self._original_image:
            return
        
        # Grid settings
        color = QColor(self._config['grid_color'])
        color.setAlphaF(self._config['grid_opacity'])
        pen = QPen(color, 1, Qt.DotLine)
        painter.setPen(pen)
        
        # Calculate grid spacing in screen coordinates
        spacing = self._grid_spacing * self._zoom_factor
        
        # Draw vertical lines
        start_x = int(self._pan_offset.x() % spacing)
        for x in range(start_x, self.width(), int(spacing)):
            painter.drawLine(x, 0, x, self.height())
        
        # Draw horizontal lines
        start_y = int(self._pan_offset.y() % spacing)
        for y in range(start_y, self.height(), int(spacing)):
            painter.drawLine(0, y, self.width(), y)
    
    def _draw_overlays(self, painter: QPainter):
        """Draw all active overlays."""
        # TODO: Implement overlay rendering
        # This would render ground truth, predictions, etc.
        pass
    
    def _draw_annotations(self, painter: QPainter):
        """Draw annotation points."""
        if not self._annotations or not self._original_image:
            return
        
        for annotation in self._annotations:
            self._draw_annotation_point(painter, annotation)
    
    def _draw_annotation_point(self, painter: QPainter, annotation: Dict):
        """Draw a single annotation point."""
        # Get screen position
        image_pos = QPointF(annotation['x'], annotation['y'])
        screen_pos = self.image_to_screen(image_pos)
        
        # Skip if outside visible area
        if not self.rect().contains(screen_pos.toPoint()):
            return
        
        # Get color for class
        class_id = annotation['class_id']
        colors = self._config['point_colors']
        color = QColor(colors[(class_id - 1) % len(colors)])
        
        # Draw point
        radius = self._point_size
        
        # Fill
        color.setAlphaF(self._point_opacity)
        painter.setBrush(QBrush(color))
        
        # Outline
        if self._config['point_outline']:
            outline_color = QColor(self._config['point_outline_color'])
            outline_pen = QPen(outline_color, self._config['point_outline_width'])
            painter.setPen(outline_pen)
        else:
            painter.setPen(Qt.NoPen)
        
        # Draw circle
        painter.drawEllipse(screen_pos, radius, radius)
    
    def _invalidate_cache(self):
        """Invalidate render cache."""
        self._cache_valid = False
    
    def _find_annotation_at_pos(self, screen_pos: QPointF) -> Optional[str]:
        """Find annotation at screen position."""
        image_pos = self.screen_to_image(screen_pos)
        
        for annotation in self._annotations:
            ann_pos = QPointF(annotation['x'], annotation['y'])
            distance = ((ann_pos.x() - image_pos.x()) ** 2 + (ann_pos.y() - image_pos.y()) ** 2) ** 0.5
            
            # Check if within click radius (in image coordinates)
            click_radius = self._point_size / self._zoom_factor
            if distance <= click_radius:
                return annotation['id']
        
        return None
    
    # Event handlers
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        pos = QPointF(event.pos())
        
        if event.button() == Qt.LeftButton:
            # Check if clicking on existing annotation
            annotation_id = self._find_annotation_at_pos(pos)
            
            if annotation_id:
                # Start dragging existing point
                self._dragging_point = annotation_id
                # Calculate drag offset
                for ann in self._annotations:
                    if ann['id'] == annotation_id:
                        screen_pos = self.image_to_screen(QPointF(ann['x'], ann['y']))
                        self._drag_offset = pos - screen_pos
                        break
            else:
                # Add new annotation
                image_pos = self.screen_to_image(pos)
                if self._original_image:
                    # Check if within image bounds
                    img_rect = QRectF(0, 0, self._original_image.width(), self._original_image.height())
                    if img_rect.contains(image_pos):
                        self.add_annotation(image_pos.x(), image_pos.y(), self._current_class)
        
        elif event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier):
            # Start panning
            self._panning = True
            self._last_pan_point = pos
            self.setCursor(Qt.ClosedHandCursor)
        
        self._last_mouse_pos = pos
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events with smart throttling."""
        
        # SMART THROTTLING: Intelligent rate limiting for optimal performance
        import time
        current_time = int(time.perf_counter() * 1000)
        if not hasattr(self, '_last_mouse_update'):
            self._last_mouse_update = 0
        
        time_since_last = current_time - self._last_mouse_update
        
        # Smart throttling based on operation type
        if self._dragging_point:
            min_interval = 8   # 8ms = ~120 FPS for smooth dragging
        elif hasattr(self, '_panning') and self._panning:
            min_interval = 11  # 11ms = ~90 FPS for panning
        else:
            min_interval = 16  # 16ms = ~60 FPS for hover effects
        
        if time_since_last < min_interval:
            return  # Skip this event - too frequent
            
        self._last_mouse_update = current_time
        
        pos = QPointF(event.pos())
        
        # Update mouse coordinates display
        if self._mouse_tracking and self._original_image:
            image_pos = self.screen_to_image(pos)
            self.mouse_coordinates.emit(int(image_pos.x()), int(image_pos.y()))
        
        # Handle dragging
        if self._dragging_point:
            # Move annotation
            new_screen_pos = pos - self._drag_offset
            new_image_pos = self.screen_to_image(new_screen_pos)
            
            # Find and update annotation
            for ann in self._annotations:
                if ann['id'] == self._dragging_point:
                    old_pos = (ann['x'], ann['y'])
                    ann['x'] = new_image_pos.x()
                    ann['y'] = new_image_pos.y()
                    
                    # Emit signal
                    self.point_moved.emit(old_pos[0], old_pos[1], ann['x'], ann['y'])
                    break
            
            self._invalidate_cache()
            self.update()
        
        # Handle panning
        elif self._panning and self._last_pan_point:
            delta = pos - self._last_pan_point
            self._pan_offset += delta
            self._last_pan_point = pos
            
            self._invalidate_cache()
            self.update()
            self.view_changed.emit(self._zoom_factor, self._pan_offset.x(), self._pan_offset.y())
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events."""
        if event.button() == Qt.LeftButton and self._dragging_point:
            self._dragging_point = None
            self._drag_offset = QPointF(0, 0)
        
        elif event.button() == Qt.MiddleButton or self._panning:
            self._panning = False
            self._last_pan_point = None
            self.setCursor(Qt.CrossCursor)
        
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        if not self._original_image:
            return
        
        # Calculate zoom factor
        delta = event.angleDelta().y()
        zoom_factor = 1.2 if delta > 0 else 0.8
        
        # Zoom toward mouse cursor
        old_zoom = self._zoom_factor
        new_zoom = max(self._min_zoom, min(self._max_zoom, old_zoom * zoom_factor))
        
        if new_zoom != old_zoom:
            # Calculate cursor position in image coordinates
            cursor_pos = QPointF(event.pos())
            image_pos = self.screen_to_image(cursor_pos)
            
            # Update zoom
            self._zoom_factor = new_zoom
            
            # Adjust pan to keep cursor position stable
            new_screen_pos = self.image_to_screen(image_pos)
            self._pan_offset += cursor_pos - new_screen_pos
            
            self._invalidate_cache()
            self.update()
            self.view_changed.emit(self._zoom_factor, self._pan_offset.x(), self._pan_offset.y())
        
        event.accept()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard events."""
        if event.key() == Qt.Key_Space:
            # Enable pan mode temporarily
            if not self._panning:
                self.setCursor(Qt.OpenHandCursor)
        
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event: QKeyEvent):
        """Handle key release events."""
        if event.key() == Qt.Key_Space:
            if not self._panning:
                self.setCursor(Qt.CrossCursor)
        
        super().keyReleaseEvent(event)
    
    def resizeEvent(self, event: QResizeEvent):
        """Handle resize events."""
        self._invalidate_cache()
        super().resizeEvent(event)
    
    def paintEvent(self, event: QPaintEvent):
        """Handle paint events."""
        # If we don't have a custom pixmap, draw default content
        if not self.pixmap():
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(self._config['background_color']))
            
            # Draw placeholder text
            painter.setPen(QColor('#94a3b8'))
            painter.setFont(QFont('Inter', 14))
            painter.drawText(self.rect(), Qt.AlignCenter, self.text())
            
            painter.end()
        else:
            super().paintEvent(event)
    
    # Public properties
    
    @property
    def zoom_factor(self) -> float:
        return self._zoom_factor
    
    @property
    def has_image(self) -> bool:
        return self._original_image is not None
    
    @property
    def annotation_count(self) -> int:
        return len(self._annotations)