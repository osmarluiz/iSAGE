"""
Zoom Controller - Handles zoom functionality for canvas

This module provides zoom control with mouse wheel support and proper bounds checking.
"""

from typing import Optional, Tuple
import math

# Handle PyQt5 imports gracefully
try:
    from PyQt5.QtCore import pyqtSignal, QPointF
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    class pyqtSignal: 
        def __init__(self, *args): pass
    class QPointF: pass

from ..base_protocols import BaseComponent


class ZoomController(BaseComponent):
    """Controls zoom functionality for canvas."""
    
    # Zoom-specific signals
    zoomChanged = pyqtSignal(float)  # zoom_factor
    zoomLimitsChanged = pyqtSignal(float, float)  # min_zoom, max_zoom
    zoomReset = pyqtSignal()
    
    def __init__(self, name: str = "zoom_controller", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Zoom configuration
        self._zoom_factor: float = 1.0
        self._min_zoom: float = 0.1
        self._max_zoom: float = 10.0
        self._zoom_step: float = 1.2
        
        # Zoom behavior
        self._zoom_to_cursor: bool = True
        self._smooth_zoom: bool = True
        self._zoom_sensitivity: float = 1.0
        
        # State
        self._zoom_center: QPointF = QPointF(0, 0)
        self._canvas_size: Tuple[int, int] = (800, 600)
    
    def initialize(self, **kwargs) -> bool:
        """Initialize zoom controller."""
        self._min_zoom = kwargs.get('min_zoom', 0.1)
        self._max_zoom = kwargs.get('max_zoom', 10.0)
        self._zoom_step = kwargs.get('zoom_step', 1.2)
        self._zoom_to_cursor = kwargs.get('zoom_to_cursor', True)
        self._smooth_zoom = kwargs.get('smooth_zoom', True)
        self._zoom_sensitivity = kwargs.get('zoom_sensitivity', 1.0)
        
        return super().initialize(**kwargs)
    
    def set_zoom_factor(self, factor: float, zoom_center: Optional[QPointF] = None) -> bool:
        """Set zoom factor with optional zoom center."""
        # Clamp to limits
        factor = max(self._min_zoom, min(self._max_zoom, factor))
        
        if factor != self._zoom_factor:
            old_factor = self._zoom_factor
            self._zoom_factor = factor
            
            # Update zoom center if provided
            if zoom_center:
                self._zoom_center = QPointF(zoom_center)
            
            # Emit signals
            self.zoomChanged.emit(factor)
            self.emit_state_changed({
                'zoom_factor': factor,
                'zoom_center': (self._zoom_center.x(), self._zoom_center.y()),
                'zoom_changed': True
            })
            
            return True
        
        return False
    
    def get_zoom_factor(self) -> float:
        """Get current zoom factor."""
        return self._zoom_factor
    
    def zoom_in(self, zoom_center: Optional[QPointF] = None) -> bool:
        """Zoom in by zoom step."""
        new_factor = self._zoom_factor * self._zoom_step
        return self.set_zoom_factor(new_factor, zoom_center)
    
    def zoom_out(self, zoom_center: Optional[QPointF] = None) -> bool:
        """Zoom out by zoom step."""
        new_factor = self._zoom_factor / self._zoom_step
        return self.set_zoom_factor(new_factor, zoom_center)
    
    def zoom_to_fit(self, image_size: Tuple[int, int], canvas_size: Tuple[int, int]) -> bool:
        """Zoom to fit image in canvas."""
        if image_size[0] <= 0 or image_size[1] <= 0:
            return False
        
        # Calculate zoom factor to fit
        zoom_x = canvas_size[0] / image_size[0]
        zoom_y = canvas_size[1] / image_size[1]
        zoom_factor = min(zoom_x, zoom_y)
        
        # Center on canvas
        self._zoom_center = QPointF(canvas_size[0] / 2, canvas_size[1] / 2)
        
        return self.set_zoom_factor(zoom_factor, self._zoom_center)
    
    def zoom_to_actual_size(self) -> bool:
        """Zoom to actual size (1.0x)."""
        return self.set_zoom_factor(1.0)
    
    def reset_zoom(self) -> bool:
        """Reset zoom to default."""
        if self.set_zoom_factor(1.0):
            self.zoomReset.emit()
            return True
        return False
    
    def handle_wheel_event(self, delta: int, cursor_pos: QPointF) -> bool:
        """Handle mouse wheel event for zooming."""
        if delta == 0:
            return False
        
        # Calculate zoom factor based on wheel delta
        steps = delta / 120.0  # Standard wheel step
        steps *= self._zoom_sensitivity
        
        if self._smooth_zoom:
            # Smooth zoom
            zoom_factor = self._zoom_factor * (self._zoom_step ** steps)
        else:
            # Discrete zoom
            if delta > 0:
                zoom_factor = self._zoom_factor * self._zoom_step
            else:
                zoom_factor = self._zoom_factor / self._zoom_step
        
        # Use cursor position as zoom center if enabled
        zoom_center = cursor_pos if self._zoom_to_cursor else None
        
        return self.set_zoom_factor(zoom_factor, zoom_center)
    
    def set_zoom_limits(self, min_zoom: float, max_zoom: float) -> None:
        """Set zoom limits."""
        self._min_zoom = max(0.01, min_zoom)
        self._max_zoom = max(self._min_zoom, max_zoom)
        
        # Clamp current zoom to new limits
        if self._zoom_factor < self._min_zoom or self._zoom_factor > self._max_zoom:
            self.set_zoom_factor(max(self._min_zoom, min(self._max_zoom, self._zoom_factor)))
        
        self.zoomLimitsChanged.emit(self._min_zoom, self._max_zoom)
        self.emit_state_changed({
            'min_zoom': self._min_zoom,
            'max_zoom': self._max_zoom
        })
    
    def get_zoom_limits(self) -> Tuple[float, float]:
        """Get zoom limits."""
        return (self._min_zoom, self._max_zoom)
    
    def set_zoom_step(self, step: float) -> None:
        """Set zoom step factor."""
        self._zoom_step = max(1.01, step)
        self.emit_state_changed({'zoom_step': step})
    
    def get_zoom_step(self) -> float:
        """Get zoom step factor."""
        return self._zoom_step
    
    def set_zoom_to_cursor(self, enabled: bool) -> None:
        """Enable/disable zoom to cursor."""
        self._zoom_to_cursor = enabled
        self.emit_state_changed({'zoom_to_cursor': enabled})
    
    def is_zoom_to_cursor_enabled(self) -> bool:
        """Check if zoom to cursor is enabled."""
        return self._zoom_to_cursor
    
    def set_smooth_zoom(self, enabled: bool) -> None:
        """Enable/disable smooth zoom."""
        self._smooth_zoom = enabled
        self.emit_state_changed({'smooth_zoom': enabled})
    
    def is_smooth_zoom_enabled(self) -> bool:
        """Check if smooth zoom is enabled."""
        return self._smooth_zoom
    
    def set_zoom_sensitivity(self, sensitivity: float) -> None:
        """Set zoom sensitivity."""
        self._zoom_sensitivity = max(0.1, min(5.0, sensitivity))
        self.emit_state_changed({'zoom_sensitivity': sensitivity})
    
    def get_zoom_sensitivity(self) -> float:
        """Get zoom sensitivity."""
        return self._zoom_sensitivity
    
    def set_canvas_size(self, size: Tuple[int, int]) -> None:
        """Set canvas size for zoom calculations."""
        self._canvas_size = size
        self.emit_state_changed({'canvas_size': size})
    
    def get_canvas_size(self) -> Tuple[int, int]:
        """Get canvas size."""
        return self._canvas_size
    
    def get_zoom_center(self) -> QPointF:
        """Get current zoom center."""
        return QPointF(self._zoom_center)
    
    def set_zoom_center(self, center: QPointF) -> None:
        """Set zoom center."""
        self._zoom_center = QPointF(center)
        self.emit_state_changed({
            'zoom_center': (center.x(), center.y())
        })
    
    def calculate_zoom_transform(self, point: QPointF) -> QPointF:
        """Calculate transformed point with current zoom."""
        # Transform point relative to zoom center
        transformed_x = (point.x() - self._zoom_center.x()) * self._zoom_factor + self._zoom_center.x()
        transformed_y = (point.y() - self._zoom_center.y()) * self._zoom_factor + self._zoom_center.y()
        
        return QPointF(transformed_x, transformed_y)
    
    def calculate_inverse_zoom_transform(self, point: QPointF) -> QPointF:
        """Calculate inverse transformed point with current zoom."""
        # Inverse transform point relative to zoom center
        if self._zoom_factor == 0:
            return QPointF(point)
        
        original_x = (point.x() - self._zoom_center.x()) / self._zoom_factor + self._zoom_center.x()
        original_y = (point.y() - self._zoom_center.y()) / self._zoom_factor + self._zoom_center.y()
        
        return QPointF(original_x, original_y)
    
    def get_zoom_percentage(self) -> int:
        """Get zoom as percentage."""
        return int(self._zoom_factor * 100)
    
    def set_zoom_percentage(self, percentage: int) -> bool:
        """Set zoom from percentage."""
        factor = percentage / 100.0
        return self.set_zoom_factor(factor)
    
    def can_zoom_in(self) -> bool:
        """Check if can zoom in further."""
        return self._zoom_factor < self._max_zoom
    
    def can_zoom_out(self) -> bool:
        """Check if can zoom out further."""
        return self._zoom_factor > self._min_zoom
    
    def get_statistics(self) -> dict:
        """Get zoom controller statistics."""
        return {
            'zoom_factor': self._zoom_factor,
            'zoom_percentage': self.get_zoom_percentage(),
            'min_zoom': self._min_zoom,
            'max_zoom': self._max_zoom,
            'zoom_step': self._zoom_step,
            'zoom_to_cursor': self._zoom_to_cursor,
            'smooth_zoom': self._smooth_zoom,
            'zoom_sensitivity': self._zoom_sensitivity,
            'zoom_center': (self._zoom_center.x(), self._zoom_center.y()),
            'canvas_size': self._canvas_size,
            'can_zoom_in': self.can_zoom_in(),
            'can_zoom_out': self.can_zoom_out()
        }