"""
Annotation Canvas - PyQt5 widget for displaying images with annotations

This module provides a concrete PyQt5 implementation of the canvas system.
"""

from typing import Optional, List, Dict, Any, Tuple
import numpy as np
from ..base_protocols import BaseComponent, QWidget, QPointF, QPixmap, QRectF
from .base_canvas import BaseCanvas
from .zoom_controller import ZoomController
from .pan_controller import PanController
from .grid_overlay import GridOverlay
from .crosshair_cursor import CrosshairCursor

# Handle PyQt5 imports
try:
    from PyQt5.QtWidgets import QLabel, QVBoxLayout, QSizePolicy
    from PyQt5.QtCore import Qt, QRect, QSize, QTimer
    from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QWheelEvent, QMouseEvent, QPaintEvent, QResizeEvent
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False


class AnnotationCanvas(QLabel, BaseCanvas):
    """PyQt5 widget for displaying images with annotations and overlays."""
    
    def __init__(self, parent=None, name: str = "annotation_canvas", version: str = "1.0.0"):
        if not PYQT5_AVAILABLE:
            raise ImportError("PyQt5 is required for AnnotationCanvas")
        
        QLabel.__init__(self, parent)
        BaseCanvas.__init__(self, name, version)
        
        # Controllers
        self.zoom_controller = ZoomController()
        self.pan_controller = PanController()
        
        # UI Components
        self.grid_overlay = GridOverlay()
        self.crosshair_cursor = CrosshairCursor()
        
        # Widget setup
        self.setMinimumSize(400, 300)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(False)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Rendering
        self._display_pixmap: Optional[QPixmap] = None
        self._overlay_pixmaps: Dict[str, QPixmap] = {}
        self._annotation_layers: List[Any] = []
        
        # Layer caching for optimized rendering (from legacy ABILIUS)
        self._base_layer_cache: Optional[QPixmap] = None
        self._overlay_cache: Optional[QPixmap] = None
        self._needs_base_update: bool = True
        self._needs_overlay_update: bool = True
        self._annotation_dirty: bool = True
        self._optimized_rendering: bool = True
        
        # Performance tracking
        self._last_scale_factor: Optional[float] = None
        self._last_widget_size: Optional[Tuple[int, int]] = None
        self._last_zoom_level: Optional[float] = None
        self._last_pan_offset: Optional[QPointF] = None
        
        
        # Interaction state
        self._mouse_pos: QPointF = QPointF(0, 0)
        self._image_mouse_pos: QPointF = QPointF(0, 0)
        
        # Performance
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render_canvas)
        self._render_delay = 16  # ~60 FPS
        
        # Connect controllers
        self._setup_controllers()
        
        # Apply dark theme
        self.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border: 1px solid #555555;
                border-radius: 4px;
            }
        """)
        
        # Initialize
        self.initialize()
    
    def initialize(self, **kwargs) -> bool:
        """Initialize canvas."""
        # Initialize controllers
        self.zoom_controller.initialize(**kwargs)
        self.pan_controller.initialize(**kwargs)
        
        # Set initial canvas size
        self.zoom_controller.set_canvas_size((self.width(), self.height()))
        self.pan_controller.set_canvas_size((self.width(), self.height()))
        
        return super().initialize(**kwargs)
    
    def _setup_controllers(self) -> None:
        """Setup controller connections."""
        # Zoom controller
        self.zoom_controller.zoomChanged.connect(self._on_zoom_changed)
        
        # Pan controller
        self.pan_controller.panChanged.connect(self._on_pan_changed)
        
        # Forward zoom and pan signals
        self.zoom_controller.zoomChanged.connect(self.zoomChanged.emit)
        self.pan_controller.panChanged.connect(self.panChanged.emit)
    
    def set_image(self, image) -> bool:
        """Set image to display."""
        success = super().set_image(image)
        
        if success and self._image is not None:
            # Update controllers
            self.pan_controller.set_image_size(self._image_size)
            self.zoom_controller.set_canvas_size((self.width(), self.height()))
            
            # Fit to window by default
            self.fit_to_window()
            
            # Invalidate all caches for new image
            self._invalidate_all_caches()
        
        return success
    
    def fit_to_window(self) -> None:
        """Fit image to window."""
        if self._image is not None:
            self.zoom_controller.zoom_to_fit(self._image_size, (self.width(), self.height()))
            self.pan_controller.reset_pan()
    
    def add_overlay(self, name: str, pixmap: QPixmap) -> None:
        """Add overlay pixmap."""
        self._overlay_pixmaps[name] = pixmap
        self._invalidate_overlay_cache()  # Overlay changed, invalidate overlay cache
    
    def remove_overlay(self, name: str) -> None:
        """Remove overlay pixmap."""
        if name in self._overlay_pixmaps:
            del self._overlay_pixmaps[name]
            self._invalidate_overlay_cache()  # Overlay changed, invalidate overlay cache
    
    def clear_overlays(self) -> None:
        """Clear all overlays."""
        self._overlay_pixmaps.clear()
        self._invalidate_overlay_cache()  # Overlays cleared, invalidate overlay cache
    
    def add_annotation_layer(self, layer: Any) -> None:
        """Add annotation layer."""
        self._annotation_layers.append(layer)
        self._invalidate_annotations()  # Annotations changed
    
    def remove_annotation_layer(self, layer: Any) -> None:
        """Remove annotation layer."""
        if layer in self._annotation_layers:
            self._annotation_layers.remove(layer)
            self._invalidate_annotations()  # Annotations changed
    
    def clear_annotation_layers(self) -> None:
        """Clear all annotation layers."""
        self._annotation_layers.clear()
        self._invalidate_annotations()  # Annotations changed
    
    def get_image_coordinates(self, screen_pos: QPointF) -> QPointF:
        """Get image coordinates from screen position."""
        return self.screen_to_image_coords(screen_pos)
    
    def get_screen_coordinates(self, image_pos: QPointF) -> QPointF:
        """Get screen coordinates from image position."""
        return self.image_to_screen_coords(image_pos)
    
    def screen_to_image_coords(self, screen_pos: QPointF) -> QPointF:
        """Convert screen coordinates to image coordinates."""
        if self._image is None:
            return QPointF(0, 0)
        
        # Get widget center
        widget_center = QPointF(self.width() / 2, self.height() / 2)
        
        # Apply pan offset
        pan_offset = self.pan_controller.get_pan_offset()
        adjusted_pos = QPointF(
            screen_pos.x() - widget_center.x() - pan_offset.x(),
            screen_pos.y() - widget_center.y() - pan_offset.y()
        )
        
        # Apply zoom
        zoom_factor = self.zoom_controller.get_zoom_factor()
        if zoom_factor != 0:
            adjusted_pos = QPointF(
                adjusted_pos.x() / zoom_factor,
                adjusted_pos.y() / zoom_factor
            )
        
        # Convert to image coordinates
        image_center = QPointF(self._image_size[0] / 2, self._image_size[1] / 2)
        image_pos = QPointF(
            adjusted_pos.x() + image_center.x(),
            adjusted_pos.y() + image_center.y()
        )
        
        return image_pos
    
    def image_to_screen_coords(self, image_pos: QPointF) -> QPointF:
        """Convert image coordinates to screen coordinates."""
        if self._image is None:
            return QPointF(0, 0)
        
        # Convert from image coordinates
        image_center = QPointF(self._image_size[0] / 2, self._image_size[1] / 2)
        adjusted_pos = QPointF(
            image_pos.x() - image_center.x(),
            image_pos.y() - image_center.y()
        )
        
        # Apply zoom
        zoom_factor = self.zoom_controller.get_zoom_factor()
        adjusted_pos = QPointF(
            adjusted_pos.x() * zoom_factor,
            adjusted_pos.y() * zoom_factor
        )
        
        # Apply pan offset
        pan_offset = self.pan_controller.get_pan_offset()
        widget_center = QPointF(self.width() / 2, self.height() / 2)
        screen_pos = QPointF(
            adjusted_pos.x() + widget_center.x() + pan_offset.x(),
            adjusted_pos.y() + widget_center.y() + pan_offset.y()
        )
        
        return screen_pos
    
    def get_zoom_factor(self) -> float:
        """Get current zoom factor."""
        return self.zoom_controller.get_zoom_factor()
    
    def set_zoom_factor(self, factor: float) -> None:
        """Set zoom factor."""
        self.zoom_controller.set_zoom_factor(factor)
    
    def get_pan_offset(self) -> QPointF:
        """Get current pan offset."""
        return self.pan_controller.get_pan_offset()
    
    def set_pan_offset(self, offset: QPointF) -> None:
        """Set pan offset."""
        self.pan_controller.set_pan_offset(offset)
    
    # Qt event handlers
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle wheel events for zooming."""
        if event.modifiers() & Qt.ControlModifier:
            # Zoom with Ctrl+wheel
            cursor_pos = QPointF(event.pos())
            self.zoom_controller.handle_wheel_event(event.angleDelta().y(), cursor_pos)
        else:
            super().wheelEvent(event)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press events."""
        pos = QPointF(event.pos())
        
        # Update mouse position
        self._mouse_pos = pos
        self._image_mouse_pos = self.screen_to_image_coords(pos)
        
        # Handle pan
        if self.pan_controller.handle_mouse_press(pos, event.button()):
            return
        
        # Emit coordinates changed
        self.coordinatesChanged.emit(self._image_mouse_pos)
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move events with smart throttling."""
        
        # SMART THROTTLING: Intelligent rate limiting for optimal performance
        import time
        current_time = int(time.perf_counter() * 1000)
        if not hasattr(self, '_last_mouse_update'):
            self._last_mouse_update = 0
        
        time_since_last = current_time - self._last_mouse_update
        
        # Smart throttling - base canvas uses standard rate
        min_interval = 16  # 16ms = ~60 FPS for coordinate tracking
        
        if time_since_last < min_interval:
            return  # Skip this event - too frequent
            
        self._last_mouse_update = current_time
        
        pos = QPointF(event.pos())
        
        # Update mouse position
        self._mouse_pos = pos
        self._image_mouse_pos = self.screen_to_image_coords(pos)
        
        # Handle pan
        if self.pan_controller.handle_mouse_move(pos):
            return
        
        # Emit coordinates changed
        self.coordinatesChanged.emit(self._image_mouse_pos)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release events."""
        pos = QPointF(event.pos())
        
        # Handle pan
        if self.pan_controller.handle_mouse_release(pos, event.button()):
            return
        
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """Custom paint event."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor(self._background_color))
        
        # Draw image if available
        if self._display_pixmap:
            self._draw_image(painter)
        
        # Draw overlays
        self._draw_overlays(painter)
        
        # Draw annotation layers
        self._draw_annotation_layers(painter)
    
    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle resize events."""
        new_size = (event.size().width(), event.size().height())
        
        # Update controllers
        self.zoom_controller.set_canvas_size(new_size)
        self.pan_controller.set_canvas_size(new_size)
        
        # Resize requires full cache invalidation
        self._invalidate_all_caches()
        
        super().resizeEvent(event)
    
    # Private methods
    def _on_zoom_changed(self, zoom_factor: float) -> None:
        """Handle zoom changed."""
        self.pan_controller.set_zoom_factor(zoom_factor)
        self._invalidate_base_layer()  # Zoom changed, invalidate base layer
    
    def _on_pan_changed(self, pan_offset: QPointF) -> None:
        """Handle pan changed."""
        self._invalidate_base_layer()  # Pan changed, invalidate base layer
    
    def _schedule_render(self) -> None:
        """Schedule canvas render."""
        if not self._render_timer.isActive():
            self._render_timer.start(self._render_delay)
    
    def _render_canvas(self) -> None:
        """Render canvas display."""
        if self._image is None:
            return
        
        try:
            # Create display pixmap
            zoom_factor = self.zoom_controller.get_zoom_factor()
            
            # Calculate display size
            display_width = int(self._image_size[0] * zoom_factor)
            display_height = int(self._image_size[1] * zoom_factor)
            
            # Create pixmap from image
            self._display_pixmap = self._array_to_pixmap(self._image)
            
            # Scale pixmap
            if zoom_factor != 1.0:
                self._display_pixmap = self._display_pixmap.scaled(
                    display_width, display_height,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            
            # Update display
            self.update()
            
        except Exception as e:
            self.emit_error(f"Error rendering canvas: {str(e)}")
    
    def _draw_image(self, painter: QPainter) -> None:
        """Draw image on canvas."""
        if not self._display_pixmap:
            return
        
        # Calculate position
        widget_center = QPointF(self.width() / 2, self.height() / 2)
        pan_offset = self.pan_controller.get_pan_offset()
        
        pixmap_center = QPointF(
            self._display_pixmap.width() / 2,
            self._display_pixmap.height() / 2
        )
        
        draw_pos = QPointF(
            widget_center.x() - pixmap_center.x() + pan_offset.x(),
            widget_center.y() - pixmap_center.y() + pan_offset.y()
        )
        
        # Draw pixmap
        painter.drawPixmap(draw_pos.toPoint(), self._display_pixmap)
    
    def _draw_overlays(self, painter: QPainter) -> None:
        """Draw overlay pixmaps."""
        for name, pixmap in self._overlay_pixmaps.items():
            if pixmap and not pixmap.isNull():
                # Draw overlay at same position as image
                widget_center = QPointF(self.width() / 2, self.height() / 2)
                pan_offset = self.pan_controller.get_pan_offset()
                
                pixmap_center = QPointF(pixmap.width() / 2, pixmap.height() / 2)
                
                draw_pos = QPointF(
                    widget_center.x() - pixmap_center.x() + pan_offset.x(),
                    widget_center.y() - pixmap_center.y() + pan_offset.y()
                )
                
                painter.drawPixmap(draw_pos.toPoint(), pixmap)
    
    def _draw_annotation_layers(self, painter: QPainter) -> None:
        """Draw annotation layers."""
        for layer in self._annotation_layers:
            if hasattr(layer, 'draw'):
                try:
                    layer.draw(painter, self)
                except Exception as e:
                    self.emit_error(f"Error drawing annotation layer: {str(e)}")
    
    def _array_to_pixmap(self, array: np.ndarray) -> QPixmap:
        """Convert numpy array to QPixmap."""
        if array.dtype != np.uint8:
            # Normalize to 0-255 range
            array_min = array.min()
            array_max = array.max()
            if array_max > array_min:
                array = ((array - array_min) / (array_max - array_min) * 255).astype(np.uint8)
            else:
                array = np.zeros_like(array, dtype=np.uint8)
        
        try:
            from PyQt5.QtGui import QImage
            
            if len(array.shape) == 3:
                if array.shape[2] == 3:  # RGB
                    height, width, channels = array.shape
                    bytes_per_line = channels * width
                    q_image = QImage(array.data, width, height, bytes_per_line, QImage.Format_RGB888)
                elif array.shape[2] == 4:  # RGBA
                    height, width, channels = array.shape
                    bytes_per_line = channels * width
                    q_image = QImage(array.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
                else:
                    # Convert to RGB
                    if array.shape[2] == 1:
                        array = np.repeat(array, 3, axis=2)
                    else:
                        array = array[:, :, :3]
                    height, width, channels = array.shape
                    bytes_per_line = channels * width
                    q_image = QImage(array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            else:  # Grayscale
                height, width = array.shape
                bytes_per_line = width
                q_image = QImage(array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
            
            return QPixmap.fromImage(q_image)
            
        except Exception as e:
            self.emit_error(f"Error converting array to pixmap: {str(e)}")
            return QPixmap()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get canvas statistics."""
        stats = super().get_statistics()
        stats.update({
            'widget_size': (self.width(), self.height()),
            'display_pixmap_size': (
                self._display_pixmap.width() if self._display_pixmap else 0,
                self._display_pixmap.height() if self._display_pixmap else 0
            ),
            'overlay_count': len(self._overlay_pixmaps),
            'annotation_layer_count': len(self._annotation_layers),
            'mouse_pos': (self._mouse_pos.x(), self._mouse_pos.y()),
            'image_mouse_pos': (self._image_mouse_pos.x(), self._image_mouse_pos.y()),
            'zoom_stats': self.zoom_controller.get_statistics(),
            'pan_stats': self.pan_controller.get_statistics(),
            'optimized_rendering': self._optimized_rendering
        })
        return stats
    
    # Optimized rendering methods (from legacy ABILIUS)
    def set_optimized_rendering(self, enabled: bool) -> None:
        """Enable or disable optimized rendering."""
        self._optimized_rendering = enabled
        self._invalidate_all_caches()
    
    def is_optimized_rendering_enabled(self) -> bool:
        """Check if optimized rendering is enabled."""
        return self._optimized_rendering
    
    def _invalidate_all_caches(self) -> None:
        """Invalidate all caches and force full redraw."""
        self._base_layer_cache = None
        self._overlay_cache = None
        self._needs_base_update = True
        self._needs_overlay_update = True
        self._annotation_dirty = True
        self._last_scale_factor = None
        self._last_widget_size = None
        self._last_zoom_level = None
        self._last_pan_offset = None
        self._schedule_render()
    
    def _invalidate_base_layer(self) -> None:
        """Invalidate base layer cache."""
        self._needs_base_update = True
        self._schedule_render()
    
    def _invalidate_overlay_cache(self) -> None:
        """Invalidate overlay cache."""
        self._needs_overlay_update = True
        self._schedule_render()
    
    def _invalidate_annotations(self) -> None:
        """Invalidate annotation cache."""
        self._annotation_dirty = True
        self._schedule_render()
    
    def _needs_cache_update(self) -> bool:
        """Check if cache needs to be updated."""
        current_size = (self.width(), self.height())
        current_zoom = self.zoom_controller.get_zoom_factor()
        current_pan = self.pan_controller.get_pan_offset()
        
        return (
            self._last_widget_size != current_size or
            self._last_zoom_level != current_zoom or
            self._last_pan_offset != current_pan
        )
    
    def _update_cache_tracking(self) -> None:
        """Update cache tracking variables."""
        self._last_widget_size = (self.width(), self.height())
        self._last_zoom_level = self.zoom_controller.get_zoom_factor()
        self._last_pan_offset = self.pan_controller.get_pan_offset()
    
    def _render_canvas_optimized(self) -> None:
        """Optimized canvas rendering with layer caching."""
        if self._image is None:
            return
        
        try:
            # Check if we need to update cache
            if self._needs_cache_update():
                self._invalidate_base_layer()
            
            # Update base layer if needed
            if self._needs_base_update or self._base_layer_cache is None:
                self._update_base_layer()
            
            # Update overlay layer if needed  
            if self._needs_overlay_update or self._overlay_cache is None:
                self._update_overlay_layer()
            
            # Always update annotations (they change frequently)
            self._render_annotations()
            
            # Update tracking
            self._update_cache_tracking()
            
            # Update display
            self.update()
            
        except Exception as e:
            self.emit_error(f"Error in optimized rendering: {str(e)}")
            # Fallback to legacy rendering
            self._render_canvas_legacy()
    
    def _render_canvas_legacy(self) -> None:
        """Legacy canvas rendering (original method)."""
        # This is the original _render_canvas method
        if self._image is None:
            return
        
        try:
            # Create display pixmap
            zoom_factor = self.zoom_controller.get_zoom_factor()
            
            # Calculate display size
            display_width = int(self._image_size[0] * zoom_factor)
            display_height = int(self._image_size[1] * zoom_factor)
            
            # Create pixmap from image
            self._display_pixmap = self._array_to_pixmap(self._image)
            
            # Scale pixmap
            if zoom_factor != 1.0:
                self._display_pixmap = self._display_pixmap.scaled(
                    display_width, display_height,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            
            # Update display
            self.update()
            
        except Exception as e:
            self.emit_error(f"Error rendering canvas: {str(e)}")
    
    def _update_base_layer(self) -> None:
        """Update cached base layer (image + static overlays)."""
        if self._image is None:
            return
        
        try:
            # Calculate display size
            zoom_factor = self.zoom_controller.get_zoom_factor()
            display_width = int(self._image_size[0] * zoom_factor)
            display_height = int(self._image_size[1] * zoom_factor)
            
            # Create base layer pixmap
            base_pixmap = self._array_to_pixmap(self._image)
            
            # Scale if needed
            if zoom_factor != 1.0:
                base_pixmap = base_pixmap.scaled(
                    display_width, display_height,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            
            # Create composite pixmap for widget size
            widget_size = QSize(self.width(), self.height())
            self._base_layer_cache = QPixmap(widget_size)
            self._base_layer_cache.fill(QColor(self._background_color))
            
            # Draw base image
            painter = QPainter(self._base_layer_cache)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate position
            widget_center = QPointF(self.width() / 2, self.height() / 2)
            pan_offset = self.pan_controller.get_pan_offset()
            
            pixmap_center = QPointF(base_pixmap.width() / 2, base_pixmap.height() / 2)
            
            draw_pos = QPointF(
                widget_center.x() - pixmap_center.x() + pan_offset.x(),
                widget_center.y() - pixmap_center.y() + pan_offset.y()
            )
            
            painter.drawPixmap(draw_pos.toPoint(), base_pixmap)
            painter.end()
            
            self._needs_base_update = False
            
        except Exception as e:
            self.emit_error(f"Error updating base layer: {str(e)}")
    
    def _update_overlay_layer(self) -> None:
        """Update cached overlay layer."""
        if not self._overlay_pixmaps:
            self._overlay_cache = None
            self._needs_overlay_update = False
            return
        
        try:
            # Create overlay composite
            widget_size = QSize(self.width(), self.height())
            self._overlay_cache = QPixmap(widget_size)
            self._overlay_cache.fill(Qt.transparent)
            
            painter = QPainter(self._overlay_cache)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw overlays
            for name, pixmap in self._overlay_pixmaps.items():
                if pixmap and not pixmap.isNull():
                    # Scale overlay to match zoom
                    zoom_factor = self.zoom_controller.get_zoom_factor()
                    if zoom_factor != 1.0:
                        scaled_pixmap = pixmap.scaled(
                            int(pixmap.width() * zoom_factor),
                            int(pixmap.height() * zoom_factor),
                            Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                    else:
                        scaled_pixmap = pixmap
                    
                    # Calculate position
                    widget_center = QPointF(self.width() / 2, self.height() / 2)
                    pan_offset = self.pan_controller.get_pan_offset()
                    
                    pixmap_center = QPointF(scaled_pixmap.width() / 2, scaled_pixmap.height() / 2)
                    
                    draw_pos = QPointF(
                        widget_center.x() - pixmap_center.x() + pan_offset.x(),
                        widget_center.y() - pixmap_center.y() + pan_offset.y()
                    )
                    
                    painter.drawPixmap(draw_pos.toPoint(), scaled_pixmap)
            
            painter.end()
            self._needs_overlay_update = False
            
        except Exception as e:
            self.emit_error(f"Error updating overlay layer: {str(e)}")
    
    def _render_annotations(self) -> None:
        """Render annotation layers (always fresh)."""
        # Annotations are drawn fresh each time during paintEvent
        self._annotation_dirty = False
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """Custom paint event with optimized rendering."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self._optimized_rendering:
            self._paint_optimized(painter)
        else:
            self._paint_legacy(painter)
    
    def _paint_optimized(self, painter: QPainter) -> None:
        """Optimized paint method using cached layers."""
        # Draw cached base layer
        if self._base_layer_cache and not self._base_layer_cache.isNull():
            painter.drawPixmap(0, 0, self._base_layer_cache)
        else:
            # Fallback: draw background
            painter.fillRect(self.rect(), QColor(self._background_color))
        
        # Draw cached overlay layer
        if self._overlay_cache and not self._overlay_cache.isNull():
            painter.drawPixmap(0, 0, self._overlay_cache)
        
        # Draw annotation layers (always fresh)
        self._draw_annotation_layers(painter)
    
    def _paint_legacy(self, painter: QPainter) -> None:
        """Legacy paint method."""
        # Draw background
        painter.fillRect(self.rect(), QColor(self._background_color))
        
        # Draw image if available
        if self._display_pixmap:
            self._draw_image(painter)
        
        # Draw overlays
        self._draw_overlays(painter)
        
        # Draw annotation layers
        self._draw_annotation_layers(painter)
    
    def _render_canvas(self) -> None:
        """Main render method - chooses optimized or legacy path."""
        if self._optimized_rendering:
            self._render_canvas_optimized()
        else:
            self._render_canvas_legacy()
    
    def set_show_progress_indicators(self, enabled: bool) -> None:
        """Enable or disable progress indicators."""
        self._show_progress_indicators = enabled
        
    def show_operation_progress(self, operation_name: str, total_steps: int = 100, 
                               cancellable: bool = True, pausable: bool = False) -> bool:
        """Show progress indicator for an operation."""
        if not self._show_progress_indicators:
            return False
            
        try:
            indicator = self._progress_notification_manager.create_progress_indicator(
                operation_name, parent=self
            )
            
            return indicator.show_progress(operation_name, total_steps, cancellable, pausable)
            
        except Exception as e:
            self.emit_error(f"Error showing progress: {str(e)}")
            return False
    
    def update_operation_progress(self, operation_name: str, current: int, message: str = None) -> None:
        """Update progress for an operation."""
        if not self._show_progress_indicators:
            return
            
        indicator = self._progress_notification_manager.get_progress_indicator(operation_name)
        if indicator:
            indicator.update_progress(current, message)
    
    def complete_operation_progress(self, operation_name: str, message: str = "Completed") -> None:
        """Complete progress for an operation."""
        if not self._show_progress_indicators:
            return
            
        indicator = self._progress_notification_manager.get_progress_indicator(operation_name)
        if indicator:
            indicator.complete_progress(message)
    
    def hide_operation_progress(self, operation_name: str) -> None:
        """Hide progress indicator for an operation."""
        self._progress_notification_manager.remove_progress_indicator(operation_name)
    
    def get_progress_statistics(self) -> Dict[str, Any]:
        """Get progress system statistics."""
        return self._progress_notification_manager.get_manager_statistics()
    
    # Grid overlay methods
    def set_grid_visible(self, visible: bool) -> None:
        """Set grid overlay visibility."""
        self.grid_overlay.set_visible(visible)
        self.update()
    
    def is_grid_visible(self) -> bool:
        """Check if grid overlay is visible."""
        return self.grid_overlay.is_visible()
    
    def set_grid_size(self, size: int) -> None:
        """Set grid overlay size (10-200px)."""
        self.grid_overlay.set_grid_size(size)
        self.update()
    
    def get_grid_size(self) -> int:
        """Get current grid overlay size."""
        return self.grid_overlay.get_grid_size()
    
    # Crosshair cursor methods
    def set_crosshair_visible(self, visible: bool) -> None:
        """Set crosshair cursor visibility."""
        self.crosshair_cursor.set_visible(visible)
        self.update()
    
    def is_crosshair_visible(self) -> bool:
        """Check if crosshair cursor is visible."""
        return self.crosshair_cursor.is_visible()